"""Check whether a claim is backed up by a paper.

Without an API key it uses free keyword matching. Add ANTHROPIC_API_KEY to your
.env file and it switches to Claude, which compares meaning instead of words.
"""

import os
import re
from typing import Literal

import anthropic
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

# Load secret keys from the .env file (git ignores it, so keys never reach GitHub).
load_dotenv()

PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
MODEL = "claude-opus-5-5"

# Words too common to tell us anything about whether a claim matches.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "it", "its", "this",
    "that", "these", "those", "we", "our", "they", "their", "can", "may", "has", "have",
    "had", "which", "than", "more", "most", "also", "not", "into", "such",
}

INSTRUCTIONS = """You check claims in student essays against the paper they cite.
You only see the paper's title and abstract, so judge the claim against that text alone.
- "supported": the abstract clearly says the same thing as the claim.
- "partly_supported": the abstract backs part of the claim, or says it more cautiously.
- "not_supported": the abstract says something different or the opposite.
- "not_enough_info": the abstract does not cover this claim.
For evidence, copy the single most relevant sentence from the abstract word for word.
If no sentence is relevant, leave evidence empty."""


class ClaimCheck(BaseModel):
    """The shape of the answer we ask Claude for."""

    verdict: Literal["supported", "partly_supported", "not_supported", "not_enough_info"]
    evidence: str
    explanation: str


def get_paper(paper_id):
    """Download one paper's title and abstract from Semantic Scholar."""
    response = requests.get(
        PAPER_URL.format(paper_id=paper_id),
        params={"fields": "title,abstract"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def check_claim(claim, paper):
    """Check the claim with Claude if there's an API key, otherwise with free keyword matching."""
    if not paper.get("abstract"):
        return ClaimCheck(
            verdict="not_enough_info",
            evidence="",
            explanation="Semantic Scholar has no abstract for this paper, so it can't be checked.",
        )
    if os.environ.get("ANTHROPIC_API_KEY"):
        return check_with_claude(claim, paper)
    return check_with_keywords(claim, paper)


def keywords(text):
    """'Sleep improves memory.' -> {'sleep', 'improv', 'memory'}"""
    words = re.findall(r"[a-z0-9]+", text.lower())
    # Cut common endings so "improves" and "improved" count as the same word.
    return {re.sub(r"(ing|ed|es|s)$", "", word) for word in words if word not in STOP_WORDS}


def check_with_keywords(claim, paper):
    """Free check: find the abstract sentence that shares the most keywords with the claim."""
    claim_words = keywords(claim)
    if not claim_words:
        return ClaimCheck(verdict="not_enough_info", evidence="", explanation="The claim has no keywords to look for.")

    sentences = re.split(r"(?<=[.!?])\s+", paper["abstract"])
    best = max(sentences, key=lambda sentence: len(claim_words & keywords(sentence)))
    overlap = len(claim_words & keywords(best)) / len(claim_words)

    # Keyword matching can't tell "X improves Y" from "X does not improve Y",
    # so it never says "not_supported"; only Claude can judge that.
    if overlap >= 0.7:
        verdict = "supported"
    elif overlap >= 0.4:
        verdict = "partly_supported"
    else:
        return ClaimCheck(
            verdict="not_enough_info",
            evidence="",
            explanation=f"No sentence in the abstract shares enough keywords with the claim ({overlap:.0%} at best).",
        )
    return ClaimCheck(
        verdict=verdict,
        evidence=best,
        explanation=(
            f"This sentence contains {overlap:.0%} of the claim's keywords. "
            "Keyword matching only checks shared words, not meaning, so read the sentence yourself."
        ),
    )


def check_with_claude(claim, paper):
    """Ask Claude whether the paper's abstract backs up the claim."""
    client = anthropic.Anthropic()  # reads your key from ANTHROPIC_API_KEY
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        # If Claude declines a request, the API retries it on another model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=INSTRUCTIONS,
        messages=[{
            "role": "user",
            "content": f"Title: {paper['title']}\n\nAbstract: {paper['abstract']}\n\nClaim: {claim}",
        }],
        output_format=ClaimCheck,
    )
    result = response.parsed_output

    # Don't just trust Claude: the quoted evidence must really appear in the abstract.
    if result.evidence and result.evidence not in paper["abstract"]:
        result.explanation += " (Warning: the quoted evidence was not found word for word in the abstract.)"
    return result


def main():
    paper_id = input("Paper ID (from the Semantic Scholar link): ").strip()
    claim = input("What claim does your essay make about this paper? ").strip()

    paper = get_paper(paper_id)
    result = check_claim(claim, paper)

    print(f"\nPaper: {paper['title']}")
    print(f"Verdict: {result.verdict.replace('_', ' ')}")
    if result.evidence:
        print(f'Evidence: "{result.evidence}"')
    print(f"Why: {result.explanation}")


if __name__ == "__main__":
    main()
