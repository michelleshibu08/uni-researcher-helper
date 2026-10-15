"""Check a whole essay's sources in one go.

Given an essay and its reference list, this finds every in-text citation like
(Smith, 2020) or Smith et al. (2020), then reports:
- citations with no matching reference
- references that are never cited
- references that look made up or have wrong details
- cited sentences that the source's abstract doesn't back up
It works with author-date styles such as APA and Harvard.
"""

import re
from concurrent.futures import ThreadPoolExecutor

from claim_checker import check_claim
from search_papers import fill_missing_abstracts
from verify_references import check_reference, find_year, letters_only, split_references

SURNAME = r"[A-Z][\w'’-]+"
# Smith (2020), Smith and Jones (2020), Smith & Jones (2020), Smith et al. (2020)
NARRATIVE = re.compile(
    "(" + SURNAME + r")(?:\s+et al\.?|\s+(?:and|&)\s+" + SURNAME + r")?\s*\((\d{4})[a-z]?(?:,[^)]*)?\)"
)
# (Smith, 2020), (Smith et al., 2020; Jones & Lee, 2019, p. 4)
BRACKETS = re.compile(r"\(([^()]*\d{4}[^()]*)\)")


def find_citations(sentence):
    """Return the (surname, year) of every citation in a sentence."""
    citations = [(surname, int(year)) for surname, year in NARRATIVE.findall(sentence)]
    for inside in BRACKETS.findall(sentence):
        # Brackets can hold several citations separated by semicolons.
        for part in inside.split(";"):
            year = re.search(r"\b(\d{4})[a-z]?\b", part)
            surname = re.search(SURNAME, part)
            if year and surname and surname.start() < year.start():
                citations.append((surname.group(0), int(year.group(1))))
    # A narrative citation also matches the bracket pattern, so remove repeats.
    return list(dict.fromkeys(citations))


def remove_citations(sentence):
    """'Sleep helps memory (Smith, 2020).' -> 'Sleep helps memory.' so only the claim is checked."""
    sentence = BRACKETS.sub("", sentence)
    sentence = NARRATIVE.sub("", sentence)
    return " ".join(sentence.replace(" .", ".").replace(" ,", ",").split())


def split_essay(essay):
    """Split an essay into sentences without breaking at "et al." or "p." inside citations."""
    protected = essay.replace("et al.", "et al\u0000").replace("p.", "p\u0001")
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", " ".join(protected.split()))
    return [s.replace("\u0000", ".").replace("\u0001", ".") for s in sentences if s.strip()]


def matching_reference(citation, references):
    """Find the reference whose authors include the surname and whose year matches."""
    surname, year = citation
    for reference in references:
        if letters_only(surname) in letters_only(reference) and find_year(reference) == year:
            return reference
    return None


def check_essay(essay, reference_text):
    """Return a report (a dict of lists) about the essay's citations and references."""
    references = split_references(reference_text)

    # Look every reference up at the same time, instead of one after another.
    with ThreadPoolExecutor(max_workers=4) as pool:
        reference_results = list(pool.map(check_reference, references))
    results_by_reference = dict(zip(references, reference_results))

    missing = []
    cited = set()
    claims = []
    for sentence in split_essay(essay):
        for citation in find_citations(sentence):
            reference = matching_reference(citation, references)
            label = "(" + citation[0] + ", " + str(citation[1]) + ")"
            if not reference:
                missing.append({"citation": label, "sentence": sentence})
                continue
            cited.add(reference)

            # Check the claim against the paper this reference points to.
            paper = results_by_reference[reference]["paper"]
            claim = remove_citations(sentence)
            if not paper or not claim:
                continue
            if not paper.get("abstract"):
                fill_missing_abstracts([paper])
            claims.append({
                "sentence": sentence,
                "citation": label,
                "paper_title": paper["title"],
                # None means there was no abstract to check the claim against.
                "result": check_claim(claim, paper) if paper.get("abstract") else None,
            })

    return {
        "citation_count": sum(len(find_citations(s)) for s in split_essay(essay)),
        "missing": missing,
        "uncited": [reference for reference in references if reference not in cited],
        "references": reference_results,
        "claims": claims,
    }
