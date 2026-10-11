"""Check whether a claim is backed up by a paper, using Claude to compare meaning."""

from typing import Literal

import anthropic
import requests
from pydantic import BaseModel

PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
MODEL = "claude-opus-5-5"

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
    """Ask Claude whether the paper's abstract backs up the claim."""
    if not paper.get("abstract"):
        return ClaimCheck(
            verdict="not_enough_info",
            evidence="",
            explanation="Semantic Scholar has no abstract for this paper, so it can't be checked.",
        )

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
