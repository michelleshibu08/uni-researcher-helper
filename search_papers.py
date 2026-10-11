"""Search Semantic Scholar for academic papers and print the top results."""

import os
import time

import requests

from citations import format_apa, format_harvard

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
        print(f"API is busy, retrying in {attempt * 2} seconds...")
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
        print(f"\n{number}. {paper['title']} ({paper.get('year')})")
        print(f"   Authors: {authors}")
        print(f"   Venue: {paper.get('venue') or 'unknown'}")
        print(f"   Cited by: {paper.get('citationCount')}")
        print(f"   Link: {paper.get('url')}")
        print(f"   APA:     {format_apa(paper)}")
        print(f"   Harvard: {format_harvard(paper)}")


if __name__ == "__main__":
    main()
