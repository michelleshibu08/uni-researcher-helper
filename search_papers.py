"""Search Semantic Scholar for academic papers and print the top results."""

import os
import time

import requests
from dotenv import load_dotenv

from citations import format_apa, format_harvard

# Load secret keys from the .env file (git ignores it, so keys never reach GitHub).
load_dotenv()

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_ATTEMPTS = 3
# Optional: a free key from Semantic Scholar gives you your own rate limit.
API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")


def search_papers(query, limit=5):
    """Return a list of papers (as dicts) matching the search query."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors,venue,citationCount,url,journal,externalIds",
    }
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
        # 429 means "too many requests": the free API is busy, so wait and retry.
        if response.status_code != 429 or attempt == MAX_ATTEMPTS:
            break
        print("API is busy, retrying in " + str(attempt * 2) + " seconds...")
        time.sleep(attempt * 2)
    response.raise_for_status()
    return response.json().get("data", [])


def main():
    query = input("What topic are you researching? ")
    papers = search_papers(query)

    if not papers:
        print("No papers found. Try different keywords.")
        return

    for number, paper in enumerate(papers, start=1):
        authors = ", ".join(author["name"] for author in paper.get("authors", []))
        print("\n" + str(number) + ". " + paper["title"] + " (" + str(paper.get("year")) + ")")
        print("   Authors: " + authors)
        print("   Venue: " + (paper.get("venue") or "unknown"))
        print("   Cited by: " + str(paper.get("citationCount")))
        print("   Link: " + str(paper.get("url")))
        print("   APA:     " + format_apa(paper))
        print("   Harvard: " + format_harvard(paper))


if __name__ == "__main__":
    main()
