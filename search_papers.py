"""Search OpenAlex for academic papers and print the top results.

If SEMANTIC_SCHOLAR_API_KEY is in your .env file, papers that OpenAlex has no
abstract for get one from Semantic Scholar instead.
"""

import os
import time

import requests
from dotenv import load_dotenv

from citations import format_apa, format_harvard

# Load secret keys from the .env file (git ignores it, so keys never reach GitHub).
load_dotenv()

WORKS_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
MAX_ATTEMPTS = 3
# Only ask OpenAlex for the details we use, so responses stay small and fast.
FIELDS = (
    "id,display_name,publication_year,authorships,primary_location,"
    "cited_by_count,doi,biblio,abstract_inverted_index"
)


def get_json(url, params, body=None, headers=None):
    """Download data from an API, waiting and retrying if it's busy.

    With a body, the data is sent as a POST request instead of a GET.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if body is None:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        else:
            response = requests.post(url, params=params, json=body, headers=headers, timeout=10)
        # 429 means "too many requests" and 5xx means a server hiccup: both are
        # usually temporary, so wait and try again.
        busy = response.status_code == 429 or response.status_code >= 500
        if not busy or attempt == MAX_ATTEMPTS:
            break
        print("API is busy, retrying in " + str(attempt * 2) + " seconds...")
        time.sleep(attempt * 2)
    response.raise_for_status()
    return response.json()


def rebuild_abstract(inverted_index):
    """OpenAlex stores abstracts as {"word": [positions]}; put the words back in order."""
    if not inverted_index:
        return None
    positions = []
    for word, places in inverted_index.items():
        for place in places:
            positions.append((place, word))
    positions.sort()
    return " ".join(word for place, word in positions)


def to_paper(work):
    """Turn an OpenAlex record into the simple paper dictionary the rest of the app uses."""
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    biblio = work.get("biblio") or {}
    doi = (work.get("doi") or "").replace("https://doi.org/", "")

    pages = biblio.get("first_page") or ""
    if pages and biblio.get("last_page"):
        pages = pages + "-" + biblio["last_page"]

    return {
        # "https://openalex.org/W123" -> "W123", short enough to put in a link.
        "paperId": work["id"].split("/")[-1],
        "title": work.get("display_name") or "Untitled",
        "year": work.get("publication_year"),
        "authors": [{"name": a["author"]["display_name"]} for a in work.get("authorships", [])],
        "venue": source.get("display_name"),
        "citationCount": work.get("cited_by_count"),
        "url": work.get("doi") or location.get("landing_page_url") or work["id"],
        "journal": {"name": source.get("display_name"), "volume": biblio.get("volume"), "pages": pages},
        "externalIds": {"DOI": doi} if doi else {},
        "abstract": rebuild_abstract(work.get("abstract_inverted_index")),
    }


def fill_missing_abstracts(papers):
    """Ask Semantic Scholar for any abstracts OpenAlex didn't have.

    This is only a backup: without a key, or if Semantic Scholar fails,
    the papers are left as they were.
    """
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    missing = [p for p in papers if not p["abstract"] and p["externalIds"].get("DOI")]
    if not api_key or not missing:
        return

    # One request for all the papers at once, looked up by their DOI.
    ids = ["DOI:" + p["externalIds"]["DOI"] for p in missing]
    try:
        results = get_json(
            SEMANTIC_SCHOLAR_BATCH_URL,
            {"fields": "abstract"},
            body={"ids": ids},
            headers={"x-api-key": api_key},
        )
    except requests.RequestException:
        return

    # Results come back in the same order as the IDs; a paper it doesn't know is None.
    for paper, result in zip(missing, results):
        if result and result.get("abstract"):
            paper["abstract"] = result["abstract"]


def search_papers(query, limit=10, since_year=None):
    """Return a list of papers (as dicts) matching the search query.

    since_year keeps only papers published in or after that year, e.g. 2016.
    """
    params = {"search": query, "per_page": limit, "select": FIELDS}
    if since_year:
        params["filter"] = "from_publication_date:" + str(since_year) + "-01-01"
    data = get_json(WORKS_URL, params)
    papers = [to_paper(work) for work in data.get("results", [])]
    fill_missing_abstracts(papers)
    return papers


def get_paper(paper_id):
    """Download one paper by its OpenAlex ID, like "W2626778328"."""
    paper = to_paper(get_json(WORKS_URL + "/" + paper_id, {"select": FIELDS}))
    fill_missing_abstracts([paper])
    return paper


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
