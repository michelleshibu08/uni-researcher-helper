"""Explain a paper's abstract in plain English, using Claude.

This needs ANTHROPIC_API_KEY in your .env file. Without it, the website
hides the Summarise button.
"""

import os

import anthropic
from dotenv import load_dotenv

# Load secret keys from the .env file (git ignores it, so keys never reach GitHub).
load_dotenv()

MODEL = "claude-opus-5-5"

INSTRUCTIONS = """You explain academic papers to first-year university students.
Using only the title and abstract you're given, write a short plain-English summary:
- one sentence on what question the paper asks
- one or two sentences on what it found
- one sentence on why it matters
Avoid jargon; if you must use a technical term, explain it in brackets.
Don't add anything that isn't in the abstract. Keep it under 120 words."""


def can_summarise():
    """Summaries need a Claude API key."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def summarise(paper):
    """Return a plain-English summary of the paper's abstract."""
    client = anthropic.Anthropic()  # reads your key from ANTHROPIC_API_KEY
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=2000,
        # A short summary doesn't need much thinking, so keep it quick and cheap.
        output_config={"effort": "low"},
        # If Claude declines a request, the API retries it on another model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=INSTRUCTIONS,
        messages=[{
            "role": "user",
            "content": "Title: " + paper["title"] + "\n\nAbstract: " + paper["abstract"],
        }],
    )
    if response.stop_reason == "refusal":
        return "Sorry, a summary couldn't be made for this paper."
    return "".join(block.text for block in response.content if block.type == "text").strip()
