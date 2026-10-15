# Research Helper

A web app that helps university students **find** academic papers, **cite** them correctly, and **check** that what they say a paper shows is actually in it.

![The homepage](docs/home.jpg)

## Why I built it

Writing an essay with academic sources has three fiddly steps: finding relevant papers, getting the APA or Harvard references exactly right, and making sure you haven't cited a paper for something it doesn't say. That last one matters more now that AI chatbots can confidently invent what a source says. This app handles all three in one place.

## Features

- **Check my essay:** paste your essay and reference list to get one report: citations with no matching reference, references you never cite, references that look made up, and claims your sources don't back up.
- **Fake reference detector:** paste your reference list and every entry is looked up to check the paper really exists and that the year and first author match. When details are wrong, it gives you the corrected reference in your style, ready to copy. AI chatbots often invent convincing-looking references, so this catches them before you submit.
- **Search papers:** type a topic and see every paper from [OpenAlex](https://openalex.org) (a free database of over 300 million academic works) with those words in its title, newest first, 25 at a time. Or paste a paper's link or DOI to go straight to it.
- **References in six styles:** every paper comes with **APA 7** and **Harvard**, plus a picker for **MLA 9**, **Chicago**, **IEEE** and **OSCOLA**, each with a Copy button and the short in-text citation to use in your essay.
- **Reference list builder:** press **Save** on the papers you use, and **My references** collects them into one list in any style, sorted the way that style requires. Copy it all at once or **download it as a Word document**. The list is stored in your browser, so there's no account to make.
- **Claim checker:** paste a sentence or paragraph and each sentence is checked against the paper's abstract, with the sentence it's based on.
- **Plain-English summary (needs a Claude key):** explains a paper's abstract in simple words.

Free, no sign-up, no ads, and nothing you paste is saved.

![An essay report](docs/essay-report.jpg)

![Checking a claim against a paper](docs/claim-check.jpg)

## How the claim checker works

It has two modes:

1. **Free keyword matching (default):** splits the abstract into sentences and finds the one that shares the most important words with the claim. It's free and fast, but it compares words, not meaning, so it can't tell "X improves Y" from "X does not improve Y". Because of that, it never answers "not supported" and tells you to read the sentence yourself.
2. **Claude (optional):** if an Anthropic API key is set, the app asks Claude to compare the meaning of the claim and the abstract instead. The code then double-checks that the sentence Claude quotes really appears word for word in the abstract, so the AI can't make up evidence.

Both modes only see the abstract, not the full paper. About 1 in 4 papers in OpenAlex has no abstract, so with a Semantic Scholar API key the app asks [Semantic Scholar](https://www.semanticscholar.org/product/api) for the missing ones in a single batch request. In my tests this filled in about 4 out of 10 of the gaps. If neither source has an abstract, the app says so instead of guessing.

## Tech stack

- **Python** and **Flask** for the web app
- **OpenAlex API** for paper search and details
- **Semantic Scholar API** (optional) to fill in missing abstracts
- **Anthropic Claude API** for the optional meaning-based claim check
- **python-docx** to build Word documents
- HTML templates (Jinja) and plain CSS

## Project structure

| File | What it does |
| --- | --- |
| `app.py` | The Flask web app: the search page and the claim-check page |
| `search_papers.py` | Talks to OpenAlex, retries when it's busy, converts results into a simple paper format, and fills missing abstracts from Semantic Scholar |
| `citations.py` | Turns paper details into references (APA 7, Harvard, MLA 9, Chicago, IEEE, OSCOLA) and in-text citations |
| `claim_checker.py` | Checks a claim (or a paragraph, sentence by sentence) against an abstract, by keywords or with Claude |
| `summary.py` | Explains an abstract in plain English with Claude |
| `essay_checker.py` | Finds the citations in an essay and builds the full report |
| `word_export.py` | Turns a reference list into a Word document |
| `verify_references.py` | Checks each reference in a list is a real paper with matching details |
| `templates/` | The HTML for each page |
| `static/style.css` | The site's design |

## Run it yourself

You need Python 3.12 or newer.

```bash
git clone https://github.com/michelleshibu08/uni-researcher-helper.git
cd uni-researcher-helper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5001** in your browser.

### Optional: API keys

The app works without any keys. To turn on the extras, create a file called `.env` in the project folder:

```
# Your own OpenAlex allowance (without it, everyone on your network shares a small daily one)
OPENALEX_API_KEY=your-key-here
# Fills in abstracts that OpenAlex is missing, and double-checks references
SEMANTIC_SCHOLAR_API_KEY=your-key-here
# Uses Claude for meaning-based claim checks and plain-English summaries
ANTHROPIC_API_KEY=your-key-here
```

Get them from [OpenAlex](https://help.openalex.org/api/authentication/), [Semantic Scholar](https://www.semanticscholar.org/product/api#api-key-form) and [Anthropic](https://console.anthropic.com). All three are optional, and the OpenAlex and Semantic Scholar keys are free.

Git ignores `.env`, so the key never gets uploaded.

### Command-line versions

You can also use the search and the claim checker without the website:

```bash
python search_papers.py
python claim_checker.py
```

## What I'd add next

- Put the app online so it can be used without installing anything
- Automated tests for the citation formatting and the claim checker
- Upload an essay as a Word or PDF file instead of pasting it
- Check claims against the full text of open-access papers, not just the abstract

## License

MIT. See [LICENSE](LICENSE).
