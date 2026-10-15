"""Turn a reference list into a Word document, formatted the way essays expect."""

from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt

# What each style calls its reference list.
HEADINGS = {
    "apa": "References",
    "harvard": "Reference list",
    "mla": "Works Cited",
    "chicago": "Bibliography",
    "ieee": "References",
    "oscola": "Bibliography",
}


def reference_list_docx(style, references):
    """Return the bytes of a .docx file with a heading and one paragraph per reference."""
    document = Document()
    font = document.styles["Normal"].font
    font.name = "Times New Roman"
    font.size = Pt(12)

    document.add_heading(HEADINGS.get(style, "References"), level=1)
    for reference in references:
        paragraph = document.add_paragraph(reference)
        # A "hanging indent": the first line starts at the margin and the rest are
        # indented, which is how APA, Harvard, MLA and Chicago lay out reference lists.
        paragraph.paragraph_format.left_indent = Inches(0.5)
        paragraph.paragraph_format.first_line_indent = Inches(-0.5)
        paragraph.paragraph_format.space_after = Pt(12)

    # Save into memory instead of a file on disk, so it can be sent straight to the browser.
    file = BytesIO()
    document.save(file)
    return file.getvalue()
