"""Check that every entry in a reference list is a real paper.

AI chatbots sometimes invent references that look real. For each reference,
this pulls out the title, looks it up in OpenAlex, and compares the year and
first author with what was written.
"""

import os
import re
import unicodedata

import requests

from search_papers import FIELDS, WORKS_URL, clean_search_text, get_json, to_paper

SEMANTIC_SCHOLAR_MATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/match"

# How similar two titles must be (0 to 1) to count as the same paper.
TITLE_MATCH = 0.85


def split_references(text):
    """One reference per line; blank lines are skipped."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def find_year(reference):
    """'Smith, J. (2021) ...' -> 2021"""
    match = re.search(r"\((\d{4})[a-z]?\)", reference)
    return int(match.group(1)) if match else None


def find_doi(reference):
    """Pull out a DOI like 10.1038/nature04286, if the reference has one."""
    match = re.search(r"10\.\d{4,9}/[^\s]+", reference)
    return match.group(0).rstrip(".,;") if match else None


def find_title(reference):
    """Pull the title out of an APA or Harvard reference.

    Harvard puts the title in quotes; APA puts it straight after "(2021). ".
    Both come after the year, so only the text after the year is searched.
    """
    year = re.search(r"\(\d{4}[a-z]?\)\.?\s*", reference)
    after_year = reference[year.end():] if year else reference
    quoted = re.match(r"[‘'\"“](.{10,}?)[’'\"”]", after_year)
    if quoted:
        return quoted.group(1).strip()
    plain = re.match(r"(.{10,}?[.?!])(\s|$)", after_year)
    return plain.group(1).rstrip(".").strip() if plain else None


def letters_only(text):
    """"O’Reilly" -> "oreilly" and "Şeyda" -> "seyda", so small spelling differences don't matter."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", plain.lower())


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def title_similarity(a, b):
    """1 means the same words; 0 means nothing in common."""
    a_words, b_words = words(a), words(b)
    if not a_words or not b_words:
        return 0
    return len(a_words & b_words) / max(len(a_words), len(b_words))


def author_matches(paper, reference):
    """Is the paper's first author's surname written in the reference?"""
    if not paper["authors"]:
        return True
    surname = paper["authors"][0]["name"].split()[-1]
    return letters_only(surname) in letters_only(reference)


def search_openalex(title, year):
    """Look the title up in OpenAlex: once overall, and once in the reference's year.

    The same paper is sometimes listed twice with different years, so the second
    search helps find the copy with the right year.
    """
    params = {"search": clean_search_text(title), "per_page": 5, "select": FIELDS}
    papers = [to_paper(work) for work in get_json(WORKS_URL, params).get("results", [])]
    if year:
        params["filter"] = "publication_year:" + str(year)
        papers += [to_paper(work) for work in get_json(WORKS_URL, params).get("results", [])]
    return papers


def search_semantic_scholar(title):
    """A second opinion from Semantic Scholar's title matcher (only with an API key)."""
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if not api_key:
        return []
    try:
        data = get_json(
            SEMANTIC_SCHOLAR_MATCH_URL,
            {"query": title, "fields": "title,year,authors,url,externalIds,venue,journal,abstract"},
            headers={"x-api-key": api_key},
        )
    except requests.RequestException:
        # 404 means "no match"; any other problem just means no second opinion.
        return []
    papers = []
    for match in data.get("data", []):
        # Fill in anything missing so these look like OpenAlex papers to the rest of the code.
        match["authors"] = match.get("authors") or []
        match["externalIds"] = match.get("externalIds") or {}
        match["journal"] = match.get("journal") or {}
        papers.append(match)
    return papers


def check_reference(reference):
    """Return a dict: the verdict, a message for the student, and the matching paper (if any)."""
    result = {"reference": reference, "verdict": "not_found", "message": "", "paper": None}
    year = find_year(reference)

    # A DOI points to exactly one paper, so try that first.
    doi = find_doi(reference)
    if doi:
        try:
            result["paper"] = to_paper(get_json(WORKS_URL + "/doi:" + doi, {"select": FIELDS}))
        except requests.HTTPError:
            result["message"] = "This DOI doesn't lead to any paper. The reference may be made up, so check it carefully."
            return result

    if not result["paper"]:
        title = find_title(reference)
        if not title:
            result["verdict"] = "unreadable"
            result["message"] = "Couldn't find a title in this reference. Is it written in APA or Harvard style?"
            return result
        candidates = search_openalex(title, year) + search_semantic_scholar(title)
        matches = [paper for paper in candidates if title_similarity(title, paper["title"]) >= TITLE_MATCH]
        if not matches:
            result["message"] = (
                "No paper with this title was found. It may be made up (AI chatbots often invent "
                "references), so check it carefully. Books and websites are sometimes missing from "
                "the databases, so if it's one of those, check it on Google instead."
            )
            return result
        # Pick the closest match: first author right counts most, then the year.
        matches.sort(key=lambda paper: (not author_matches(paper, reference), paper["year"] != year))
        result["paper"] = matches[0]

    # Compare the details that were written with the real paper's.
    paper = result["paper"]
    problems = []
    if year and paper["year"] and abs(year - paper["year"]) > 1:
        problems.append("the databases list the year as " + str(paper["year"]) + ", not " + str(year))
    if not author_matches(paper, reference):
        problems.append("the first author is " + paper["authors"][0]["name"])

    if problems:
        result["verdict"] = "check_details"
        result["message"] = "This paper exists, but " + " and ".join(problems) + ". Check your reference."
    else:
        result["verdict"] = "found"
        result["message"] = "This paper exists, and the title, year and first author match."
    return result


def check_reference_list(text):
    results = []
    for reference in split_references(text):
        try:
            results.append(check_reference(reference))
        except requests.RequestException:
            # One busy moment shouldn't stop the rest of the list being checked.
            results.append({
                "reference": reference,
                "verdict": "error",
                "message": "Couldn't check this one right now because the database was busy. Try again in a moment.",
                "paper": None,
            })
    return results
