"""Search OpenAlex for academic papers and print the top results."""

import time

import requests

from citations import format_apa, format_harvard

WORKS_URL = "https://api.openalex.org/works"
MAX_ATTEMPTS = 3
# Only ask OpenAlex for the details we use, so responses stay small and fast.
FIELDS = (
    "id,display_name,publication_year,authorships,primary_location,"
    "cited_by_count,doi,biblio,abstract_inverted_index"
)


def get_json(url, params):
    """Download data from OpenAlex, waiting and retrying if it's busy."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.get(url, params=params, timeout=10)
        # 429 means "too many requests": the API is busy, so wait and retry.
        if response.status_code != 429 or attempt == MAX_ATTEMPTS:
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


def search_papers(query, limit=10, since_year=None):
    """Return a list of papers (as dicts) matching the search query.

    since_year keeps only papers published in or after that year, e.g. 2016.
    """
    params = {"search": query, "per_page": limit, "select": FIELDS}
    if since_year:
        params["filter"] = "from_publication_date:" + str(since_year) + "-01-01"
    data = get_json(WORKS_URL, params)
    return [to_paper(work) for work in data.get("results", [])]


def get_paper(paper_id):
    """Download one paper by its OpenAlex ID, like "W2626778328"."""
    return to_paper(get_json(WORKS_URL + "/" + paper_id, {"select": FIELDS}))


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
