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
    return surname + ", " + inits if inits else surname


def doi_link(paper):
    doi = (paper.get("externalIds") or {}).get("DOI")
    return "https://doi.org/" + doi if doi else paper.get("url")


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
    reference = author_text + " (" + str(year) + "). " + paper["title"].rstrip(".") + "."

    journal, volume, pages = journal_details(paper)
    if journal:
        reference += " " + journal
        if volume:
            reference += ", " + volume
        if pages:
            reference += ", " + pages
        reference += "."
    link = doi_link(paper)
    if link:
        reference += " " + link
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
    reference = author_text + " (" + str(year) + ") '" + paper["title"].rstrip(".") + "'"

    journal, volume, pages = journal_details(paper)
    if journal:
        reference += ", " + journal
        if volume:
            reference += ", " + volume
        if pages:
            reference += ", pp. " + pages
    reference += "."
    link = doi_link(paper)
    if link:
        reference += " Available at: " + link
    return reference


def surnames(paper):
    return [initials(author["name"])[0] for author in paper.get("authors", [])]


def intext_apa(paper):
    """APA 7 in-text citation: (Smith, 2020), (Smith & Jones, 2020) or (Smith et al., 2020)."""
    names = surnames(paper)
    year = str(paper.get("year") or "n.d.")
    if len(names) >= 3:
        author_text = names[0] + " et al."
    elif len(names) == 2:
        author_text = names[0] + " & " + names[1]
    elif names:
        author_text = names[0]
    else:
        # No authors: APA uses the title instead.
        author_text = paper["title"]
    return "(" + author_text + ", " + year + ")"


def intext_harvard(paper):
    """Harvard in-text citation: up to three surnames, then "et al." from four authors."""
    names = surnames(paper)
    year = str(paper.get("year") or "no date")
    if len(names) >= 4:
        author_text = names[0] + " et al."
    elif len(names) > 1:
        author_text = ", ".join(names[:-1]) + " and " + names[-1]
    elif names:
        author_text = names[0]
    else:
        author_text = paper["title"]
    return "(" + author_text + ", " + year + ")"


def first_and_last(name):
    """'Ada Mary Lovelace' -> ('Ada Mary', 'Lovelace')"""
    parts = name.split()
    return " ".join(parts[:-1]), parts[-1]


def title_case_name(name, surname_first):
    """MLA and Chicago write the first author surname first, and the rest normally."""
    first, last = first_and_last(name)
    if not first:
        return last
    return last + ", " + first if surname_first else first + " " + last


def join_with_and(names, final_comma=True):
    """['A', 'B', 'C'] -> 'A, B, and C' (or 'A, B and C' without the final comma)."""
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return names[0] + " and " + names[1]
    return ", ".join(names[:-1]) + ("," if final_comma else "") + " and " + names[-1]


def format_mla(paper):
    """MLA 9: Lovelace, Ada, and Alan Turing. "Title." Journal, vol. 30, 2017, pp. 1-10."""
    names = [author["name"] for author in paper.get("authors", [])]
    if len(names) >= 3:
        author_text = title_case_name(names[0], True) + ", et al"
    elif len(names) == 2:
        author_text = title_case_name(names[0], True) + ", and " + title_case_name(names[1], False)
    elif names:
        author_text = title_case_name(names[0], True)
    else:
        author_text = ""

    reference = (author_text.rstrip(".") + ". ") if author_text else ""
    reference += '"' + paper["title"].rstrip(".") + '."'
    journal, volume, pages = journal_details(paper)
    if journal:
        reference += " " + journal + ","
    if volume:
        reference += " vol. " + volume + ","
    if paper.get("year"):
        reference += " " + str(paper["year"]) + ","
    if pages:
        reference += " pp. " + pages + ","
    reference = reference.rstrip(",")
    if not reference.endswith('."'):
        reference += "."
    link = doi_link(paper)
    if link:
        reference += " " + link + "."
    return reference


def format_chicago(paper):
    """Chicago (17th, bibliography): Lovelace, Ada, and Alan Turing. "Title." Journal 30 (2017): 1-10."""
    names = [author["name"] for author in paper.get("authors", [])]
    # Chicago lists up to ten authors; with more, it gives the first seven and "et al."
    shortened = len(names) > 10
    if shortened:
        names = names[:7]
    written = [title_case_name(name, index == 0) for index, name in enumerate(names)]
    if len(written) == 2:
        author_text = written[0] + ", and " + written[1]
    else:
        author_text = join_with_and(written)
    if shortened:
        author_text += ", et al"

    reference = (author_text.rstrip(".") + ". ") if author_text else ""
    reference += '"' + paper["title"].rstrip(".") + '."'
    journal, volume, pages = journal_details(paper)
    if journal:
        reference += " " + journal
        if volume:
            reference += " " + volume
    if paper.get("year"):
        reference += " (" + str(paper["year"]) + ")"
    if pages:
        reference += ": " + pages
    if not reference.endswith('."'):
        reference += "."
    link = doi_link(paper)
    if link:
        reference += " " + link + "."
    return reference


def format_ieee(paper):
    """IEEE: A. Lovelace and A. Turing, "Title," Journal, vol. 30, pp. 1-10, 2017, doi: 10.xxxx."""
    names = []
    for author in paper.get("authors", []):
        surname, inits = initials(author["name"])
        names.append((inits + " " + surname).strip())
    # IEEE gives up to six authors; with more, the first one and "et al."
    if len(names) > 6:
        author_text = names[0] + " et al."
    else:
        author_text = join_with_and(names, final_comma=len(names) > 2)

    details = []
    journal, volume, pages = journal_details(paper)
    if journal:
        details.append(journal)
    if volume:
        details.append("vol. " + volume)
    if pages:
        details.append("pp. " + pages)
    if paper.get("year"):
        details.append(str(paper["year"]))
    doi = (paper.get("externalIds") or {}).get("DOI")
    if doi:
        details.append("doi: " + doi)

    reference = (author_text + ", ") if author_text else ""
    title = paper["title"].rstrip(".")
    if details:
        return reference + '"' + title + '," ' + ", ".join(details) + "."
    return reference + '"' + title + '."'


def format_oscola(paper):
    """OSCOLA (bibliography): Lovelace A and Turing A, 'Title' (2017) 30 Journal 1."""
    names = []
    for author in paper.get("authors", []):
        surname, inits = initials(author["name"])
        names.append((surname + " " + inits.replace(".", "").replace(" ", "")).strip())
    # OSCOLA names up to three authors; with more, the first one and "and others".
    if len(names) > 3:
        author_text = names[0] + " and others"
    else:
        author_text = join_with_and(names, final_comma=False)

    reference = (author_text + ", ") if author_text else ""
    reference += "'" + paper["title"].rstrip(".") + "'"
    if paper.get("year"):
        reference += " (" + str(paper["year"]) + ")"
    journal, volume, pages = journal_details(paper)
    if volume:
        reference += " " + volume
    if journal:
        reference += " " + journal
    if pages:
        # OSCOLA only gives the first page.
        reference += " " + pages.split("-")[0]
    return reference


def intext_mla(paper):
    """MLA in-text citation: (Lovelace), (Lovelace and Turing) or (Lovelace et al.)."""
    names = surnames(paper)
    if len(names) >= 3:
        return "(" + names[0] + " et al.)"
    if len(names) == 2:
        return "(" + names[0] + " and " + names[1] + ")"
    return "(" + (names[0] if names else paper["title"]) + ")"


# Every style the site offers: the name students see, the reference, and the
# in-text citation (None where the style uses numbers or footnotes instead).
STYLES = {
    "apa": ("APA 7", format_apa, intext_apa),
    "harvard": ("Harvard", format_harvard, intext_harvard),
    "mla": ("MLA 9", format_mla, intext_mla),
    "chicago": ("Chicago", format_chicago, None),
    "ieee": ("IEEE", format_ieee, None),
    "oscola": ("OSCOLA", format_oscola, None),
}
