"""Turn paper data from Semantic Scholar into APA 7 and Harvard references."""


def initials(name):
    """'Ada Mary Lovelace' -> ('Lovelace', 'A. M.')"""
    parts = name.split()
    surname = parts[-1]
    first_names = parts[:-1]
    return surname, " ".join(part[0] + "." for part in first_names)


def short_name(name):
    """'Ada Mary Lovelace' -> 'Lovelace, A. M.' (the form both styles use)."""
    surname, inits = initials(name)
    return f"{surname}, {inits}" if inits else surname


def doi_link(paper):
    doi = (paper.get("externalIds") or {}).get("DOI")
    return f"https://doi.org/{doi}" if doi else paper.get("url")


def journal_details(paper):
    """Return (journal name, volume, pages), using the venue if there is no journal."""
    journal = paper.get("journal") or {}
    name = journal.get("name") or paper.get("venue") or ""
    return name, journal.get("volume"), (journal.get("pages") or "").strip()


def format_apa(paper):
    """APA 7: Surname, A., & Surname, B. (2020). Title. Journal, 12, 1-10. https://doi.org/..."""
    names = [short_name(author["name"]) for author in paper.get("authors", [])]
    # APA lists up to 20 authors; with more, it shows the first 19, "...", then the last.
    if len(names) > 20:
        names = names[:19] + ["..."] + names[-1:]
    if len(names) == 1:
        author_text = names[0]
    elif names:
        author_text = ", ".join(names[:-1]) + ", & " + names[-1]
    else:
        author_text = paper["title"]

    year = paper.get("year") or "n.d."
    reference = f"{author_text} ({year}). {paper['title'].rstrip('.')}."

    journal, volume, pages = journal_details(paper)
    if journal:
        reference += f" {journal}"
        if volume:
            reference += f", {volume}"
        if pages:
            reference += f", {pages}"
        reference += "."
    link = doi_link(paper)
    if link:
        reference += f" {link}"
    return reference


def format_harvard(paper):
    """Harvard (Cite Them Right): Surname, A. and Surname, B. (2020) 'Title', Journal, 12, pp. 1-10."""
    names = [short_name(author["name"]) for author in paper.get("authors", [])]
    # Harvard shortens four or more authors to the first one plus "et al.".
    if len(names) >= 4:
        author_text = names[0] + " et al."
    elif len(names) > 1:
        author_text = ", ".join(names[:-1]) + " and " + names[-1]
    elif names:
        author_text = names[0]
    else:
        author_text = paper["title"]

    year = paper.get("year") or "no date"
    reference = f"{author_text} ({year}) '{paper['title'].rstrip('.')}'"

    journal, volume, pages = journal_details(paper)
    if journal:
        reference += f", {journal}"
        if volume:
            reference += f", {volume}"
        if pages:
            reference += f", pp. {pages}"
    reference += "."
    link = doi_link(paper)
    if link:
        reference += f" Available at: {link}"
    return reference
