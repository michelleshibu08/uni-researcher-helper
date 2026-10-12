from flask import Flask, render_template, request
from requests import HTTPError, RequestException

from citations import format_apa, format_harvard
from claim_checker import check_claim
from search_papers import get_paper, search_papers

app = Flask(__name__)


def error_message(error):
    """Turn an error from OpenAlex into a message a student can act on."""
    if isinstance(error, HTTPError) and error.response.status_code == 429:
        return "OpenAlex is busy right now. Wait a few seconds and try again."
    if isinstance(error, HTTPError) and error.response.status_code == 404:
        return "Couldn't find that paper. Check the paper ID."
    return "Couldn't reach OpenAlex. Check your internet connection and try again."


@app.route("/")
def home():
    """Show the search box, and the results if the user searched for something."""
    query = request.args.get("q", "").strip()
    papers = []
    error = None
    if query:
        try:
            papers = search_papers(query)
        except RequestException as e:
            error = error_message(e)
        if not papers and not error:
            error = "No papers found. Try different keywords."
        # Add the references to each paper so the page can show them.
        for paper in papers:
            paper["apa"] = format_apa(paper)
            paper["harvard"] = format_harvard(paper)
    return render_template("index.html", query=query, papers=papers, error=error)


@app.route("/check", methods=["GET", "POST"])
def check():
    """Let the user check a claim from their essay against one paper."""
    # request.values reads the paper ID from the link (GET) or the form (POST).
    paper_id = request.values.get("paper_id", "").strip()
    claim = request.form.get("claim", "").strip()
    paper = None
    result = None
    error = None
    try:
        if paper_id:
            paper = get_paper(paper_id)
        # Only run the check once the form has been sent with a claim.
        if paper and claim:
            result = check_claim(claim, paper)
    except RequestException as e:
        error = error_message(e)
    return render_template(
        "check.html", paper_id=paper_id, paper=paper, claim=claim, result=result, error=error
    )


if __name__ == "__main__":
    # Port 5000 is taken by AirPlay on Macs, so use 5001 instead.
    app.run(debug=True, port=5001)
