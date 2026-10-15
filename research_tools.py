"""Help a student get started on an essay and follow the trail of sources.

- start_research: turns an essay question into key papers to read first
- related_papers: for one paper, what it cites and which papers cite it
"""

import re
from datetime import date

from search_papers import FIELDS, WORKS_URL, clean_search_text, fill_missing_abstracts, get_json, to_paper

# Words that appear in essay questions but aren't the topic itself.
QUESTION_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "to", "for", "with", "by", "is", "are", "was",
    "were", "be", "do", "does", "did", "how", "what", "why", "when", "which", "who", "whether",
    "can", "could", "should", "would", "will", "it", "its", "this", "that", "these", "those",
    "discuss", "evaluate", "explain", "assess", "analyse", "analyze", "examine", "critically",
    "extent", "far", "role", "impact", "effect", "effects", "influence", "essay", "about", "your",
    "between", "has", "have", "there", "their", "they", "them", "than", "more", "most", "any",
    # Opinion words: the question asks about them, but papers don't use them in titles.
    "harm", "harms", "affect", "affects", "cause", "causes", "lead", "leads", "improve", "improves",
    "increase", "increases", "reduce", "reduces", "benefit", "benefits", "good", "bad", "really",
    "help", "helps", "positive", "negative", "important", "much", "many", "people",
    "affecting", "affected", "impacts", "causing", "leading", "improving", "increasing", "reducing",
}

# Papers often use a different word from students, so search for any of these.
SYNONYMS = {
    "teenagers": ["adolescents", "teenagers", "youth"],
    "teens": ["adolescents", "teenagers", "youth"],
    "adolescents": ["adolescents", "teenagers", "youth"],
    "kids": ["children", "kids"],
    "children": ["children", "kids"],
    "students": ["students", "undergraduates"],
    "uni": ["university", "college"],
    "university": ["university", "college"],
    "phones": ["smartphones", "phones", "mobile"],
    "phone": ["smartphone", "phone", "mobile"],
}

# Research papers only, not things like peer-review reports.
RESEARCH_TYPES = "type:article|review|book|book-chapter"


def key_terms(question):
    """'To what extent does social media harm teenagers' sleep?' -> ['social', 'media', 'harm', 'teenagers', 'sleep']"""
    words = re.findall(r"[a-zA-Z][a-zA-Z'-]+", question.lower())
    terms = []
    for word in words:
        word = word.strip("'").removesuffix("'s")
        if word not in QUESTION_WORDS and len(word) > 2 and word not in terms:
            terms.append(word)
    return terms


def find_works(filters, sort, limit):
    params = {"filter": ",".join(filters), "sort": sort, "per_page": limit, "select": FIELDS}
    return [to_paper(work) for work in get_json(WORKS_URL, params).get("results", [])]


def start_research(question, limit=5):
    """Return the key terms plus four lists to start reading from: reviews, classics, recent, topics."""
    terms = key_terms(question)
    if not terms:
        return None
    # "teenagers" becomes "(adolescents OR teenagers OR youth)" to catch papers' wording.
    search_words = []
    for term in terms:
        if term in SYNONYMS:
            search_words.append("(" + " OR ".join(SYNONYMS[term]) + ")")
        else:
            search_words.append(clean_search_text(term))
    topic = "title_and_abstract.search:" + " ".join(search_words)

    # Review papers sum up a whole area of research, so they're the best first read.
    reviews = find_works([topic, "type:review"], "cited_by_count:desc", limit)
    classics = find_works([topic, RESEARCH_TYPES], "cited_by_count:desc", limit)
    recent_year = date.today().year - 3
    recent = find_works(
        [topic, RESEARCH_TYPES, "from_publication_date:" + str(recent_year) + "-01-01"],
        "cited_by_count:desc",
        limit,
    )

    # OpenAlex tags every paper with a research topic; the most common ones are angles to explore.
    groups = get_json(WORKS_URL, {"filter": topic, "group_by": "primary_topic.id"}).get("group_by", [])
    topics = [group["key_display_name"] for group in groups[:6]]

    fill_missing_abstracts(reviews + classics + recent)
    return {"terms": terms, "reviews": reviews, "classics": classics, "recent": recent, "topics": topics}


def related_papers(paper_id, limit=25):
    """Return (references, cited_by): the papers this one cites, and the papers that cite it.

    Both are sorted by how often they've been cited, so the most influential come first.
    """
    referenced = get_json(WORKS_URL + "/" + paper_id, {"select": "referenced_works"}).get("referenced_works", [])
    # "https://openalex.org/W123" -> "W123"; OpenAlex accepts up to 50 IDs joined with "|".
    ids = [url.split("/")[-1] for url in referenced][:50]
    references = []
    if ids:
        references = find_works(["openalex_id:" + "|".join(ids)], "cited_by_count:desc", limit)

    cited_by = find_works(["cites:" + paper_id], "cited_by_count:desc", limit)
    fill_missing_abstracts(references + cited_by)
    return references, cited_by
