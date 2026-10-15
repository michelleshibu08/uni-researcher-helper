from datetime import date

import anthropic
from flask import Flask, Response, redirect, render_template, request, url_for
from requests import HTTPError, RequestException

from citations import STYLES
from claim_checker import check_paragraph
from essay_checker import check_essay
from search_papers import get_paper, search_papers
from summary import can_summarise, summarise
from research_tools import related_papers, start_research
from verify_references import check_reference_list, find_doi
from word_export import essay_docx, reference_list_docx

app = Flask(__name__)


def error_message(error):
    """Turn an error from OpenAlex into a message a student can act on."""
    if isinstance(error, HTTPError) and error.response.status_code == 429:
        return "OpenAlex is busy right now. Wait a few seconds and try again."
    if isinstance(error, HTTPError) and error.response.status_code == 404:
        return "Couldn't find that paper. Check the paper ID."
    return "Couldn't reach OpenAlex. Check your internet connection and try again."


def add_references(paper):
    """Add the reference and in-text citation in every style, e.g. paper["mla"] and paper["intext_mla"]."""
    for key, (name, format_reference, format_intext) in STYLES.items():
        paper[key] = format_reference(paper)
        paper["intext_" + key] = format_intext(paper) if format_intext else None


def saved_data(paper):
    """What the Save button stores in the browser: the paper's ID plus every style."""
    data = {
        "id": paper["paperId"],
        "title": paper["title"],
        "year": paper.get("year"),
        "authors": ", ".join(author["name"] for author in paper.get("authors", [])),
        "url": paper.get("url"),
        "hasAbstract": bool(paper.get("abstract")),
    }
    for key in STYLES:
        data[key] = paper[key]
        data["intext_" + key] = paper["intext_" + key]
    return data


# Let every page use these. Papers from the last 2 years get a "New" label.
app.jinja_env.globals.update(STYLES=STYLES, saved_data=saved_data, recent_year=date.today().year - 2)


PER_PAGE = 25
# OpenAlex only lets you page through the first 10,000 results of a search.
MAX_PAGE = 10000 // PER_PAGE


@app.route("/")
def home():
    """Show the search box, and the results if the user searched for something."""
    query = request.args.get("q", "").strip()
    # How many years back to search; "" (the default) means any time.
    years = request.args.get("years", "")
    since_year = date.today().year - int(years) if years.isdigit() else None
    # Which page of results to show, kept between 1 and MAX_PAGE.
    page = request.args.get("page", "1")
    page = min(max(int(page), 1), MAX_PAGE) if page.isdigit() else 1

    papers = []
    total = 0
    error = None
    # A pasted DOI or link (like https://doi.org/10.1038/nature04286) goes straight to that paper.
    doi = find_doi(query)
    if query and doi:
        try:
            papers, total = [get_paper("doi:" + doi)], 1
        except HTTPError as e:
            if e.response.status_code == 404:
                error = "Couldn't find a paper with the DOI " + doi + ". Check the link, or search by title instead."
            else:
                error = error_message(e)
        except RequestException as e:
            error = error_message(e)
    elif query:
        try:
            papers, total = search_papers(query, page=page, per_page=PER_PAGE, since_year=since_year)
        except RequestException as e:
            error = error_message(e)
        if not papers and not error:
            error = "No papers found. Try different keywords."
    for paper in papers:
        add_references(paper)

    first = (page - 1) * PER_PAGE + 1
    last = first + len(papers) - 1
    has_older = last < total and page < MAX_PAGE
    return render_template(
        "index.html",
        query=query,
        years=years,
        papers=papers,
        error=error,
        page=page,
        total=total,
        first=first,
        last=last,
        has_older=has_older,
    )


@app.route("/check", methods=["GET", "POST"])
def check():
    """Let the user check their essay against one paper, or get a plain-English summary."""
    # request.values reads the paper ID from the link (GET) or the form (POST).
    paper_id = request.values.get("paper_id", "").strip()
    claim = request.form.get("claim", "").strip()
    # Which button was pressed: "check" or "summarise".
    action = request.form.get("action", "")
    paper = None
    results = []
    summary_text = None
    error = None
    try:
        if paper_id:
            paper = get_paper(paper_id)
        if paper and action == "check" and claim:
            # A paragraph is checked one sentence at a time.
            results = check_paragraph(claim, paper)
        if paper and action == "summarise" and can_summarise() and paper["abstract"]:
            summary_text = summarise(paper)
    except RequestException as e:
        error = error_message(e)
    except anthropic.APIError:
        error = "Claude couldn't be reached right now. Try again in a moment."
    if paper:
        add_references(paper)
    return render_template(
        "check.html",
        paper_id=paper_id,
        paper=paper,
        claim=claim,
        results=results,
        summary=summary_text,
        can_summarise=can_summarise(),
        error=error,
    )


@app.route("/verify", methods=["GET", "POST"])
def verify():
    """Check that every reference in a pasted reference list is a real paper."""
    text = request.form.get("references", "").strip()
    # The style the student writes in, so corrected references come out the same way.
    style = request.form.get("style", "apa")
    if style not in STYLES:
        style = "apa"
    results = []
    error = None
    if text:
        try:
            results = check_reference_list(text)
        except RequestException as e:
            error = error_message(e)
    # "Fix it for me": the real paper's reference, written in the student's style.
    format_reference = STYLES[style][1]
    for result in results:
        if result["verdict"] == "check_details":
            result["fixed"] = format_reference(result["paper"])
    return render_template("verify.html", text=text, style=style, results=results, error=error)


@app.route("/essay", methods=["GET", "POST"])
def essay():
    """Check a whole essay's citations, references and claims in one report."""
    essay_text = request.form.get("essay", "").strip()
    reference_text = request.form.get("references", "").strip()
    report = None
    error = None
    if essay_text and reference_text:
        try:
            report = check_essay(essay_text, reference_text)
        except RequestException as e:
            error = error_message(e)
        except anthropic.APIError:
            error = "Claude couldn't be reached right now. Try again in a moment."
    return render_template(
        "essay.html", essay=essay_text, references=reference_text, report=report, error=error
    )


@app.route("/references/download", methods=["POST"])
def download_references():
    """Send the reference list (already sorted by the page) back as a Word document."""
    data = request.get_json(silent=True) or {}
    style = data.get("style", "apa")
    references = [str(reference) for reference in data.get("references", [])]
    return Response(
        reference_list_docx(style, references),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=reference-list.docx"},
    )


@app.route("/start")
def start():
    """Turn an essay question into key papers to read first."""
    question = request.args.get("question", "").strip()
    research = None
    error = None
    if question:
        try:
            research = start_research(question)
        except RequestException as e:
            error = error_message(e)
        if research is None and not error:
            error = "Couldn't find a topic in that question. Try writing it in a few more words."
        if research:
            for paper in research["reviews"] + research["classics"] + research["recent"]:
                add_references(paper)
    return render_template("start.html", question=question, research=research, error=error)


@app.route("/explore/<paper_id>")
def explore(paper_id):
    """Show a paper with what it cites and which papers cite it."""
    paper = None
    references = []
    cited_by = []
    error = None
    try:
        paper = get_paper(paper_id)
        references, cited_by = related_papers(paper_id)
    except RequestException as e:
        error = error_message(e)
    for each in ([paper] if paper else []) + references + cited_by:
        add_references(each)
    return render_template("explore.html", paper=paper, references=references, cited_by=cited_by, error=error)


@app.route("/project")
def project():
    """The essay workspace. Projects live in the browser, so the page fills itself in."""
    return render_template("project.html")


@app.route("/references")
def references():
    """The old reference list page is now part of the project workspace."""
    return redirect(url_for("project") + "#references")


@app.route("/essay/download", methods=["POST"])
def download_essay():
    """Send the student's draft and reference list back as a Word document."""
    data = request.get_json(silent=True) or {}
    file = essay_docx(
        str(data.get("title", "My essay")),
        str(data.get("draft", "")),
        str(data.get("style", "harvard")),
        [str(reference) for reference in data.get("references", [])],
    )
    return Response(
        file,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=essay.docx"},
    )


if __name__ == "__main__":
    # Port 5000 is taken by AirPlay on Macs, so use 5001 instead.
    app.run(debug=True, port=5001)
