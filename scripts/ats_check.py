"""Read the rendered resume the way applicant tracking systems do, and fail on loss.

An ATS never sees the page, only what its PDF text extractor returns. This runs
four independent extractors over the PDF (PyMuPDF, pdfminer.six, pypdf, and
Mozilla's pdf.js through Node, which browser-based parsers such as OpenResume
use) and fails if any of them loses or scrambles something a parser or a
recruiter's keyword search needs:

  * the name, email and profile links, as text and as clickable links;
  * every section heading, in order, with the core three under names parsers know;
  * every employer, title, date, entry and bullet, with each job's dates read
    inside that job's entry (parsers compute years of experience from them);
  * words that run together, ligatures, unmapped glyphs or hidden characters;
  * the file itself: a real text layer, embedded fonts, no encryption or images,
    a small size, and title and author metadata.

It also checks ats/keywords.yaml: a missing `required` term fails the build, and
`preferred` terms are reported as coverage. Everything is written to
rendercv_output/ats_report.md, and to the GitHub Actions run summary in CI.

    uv run --frozen python scripts/ats_check.py rendercv_output/Alpha_Romer_Coma_CV.pdf

pdf.js needs `npm ci` first. Locally it is skipped with a warning when Node or
node_modules is missing; CI sets ATS_REQUIRE_PDFJS=1 so that it never is.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from pdfminer.high_level import extract_text as pdfminer_extract
from pypdf import PdfReader
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "Alpha_Romer_Coma_CV.yaml"
KEYWORDS_PATH = ROOT / "ats" / "keywords.yaml"
REPORT_PATH = ROOT / "rendercv_output" / "ats_report.md"
PDFJS_SCRIPT = ROOT / "scripts" / "ats" / "pdfjs_text.mjs"

MAX_BYTES = 1_000_000  # parsers have upload and parse limits; stay far below them
MIN_TEXT_CHARS = 1_500  # a one-page resume with less text is probably an image
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
# The sections parsers map to structured fields. Each must exist under one of these names.
CORE_HEADINGS = {
    "experience": {"PROFESSIONAL EXPERIENCE", "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT"},
    "education": {"EDUCATION"},
    "skills": {"TECHNICAL SKILLS", "SKILLS"},
}
DASHES = re.compile("[‐-―−-]")
BAD_CHARS = {
    "ligature": re.compile("[ﬀ-ﬆ]"),
    "replacement character (undecodable glyph)": re.compile("�"),
    "unmapped glyph": re.compile(r"\(cid:\d+\)"),
    "soft hyphen": re.compile("­"),
}


@dataclass
class Entry:
    section: str
    label: str  # employer, project or entry title as rendered
    detail: str | None  # position, or degree line
    date: str | None
    bullets: list[str] = field(default_factory=list)


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# --- text helpers ---------------------------------------------------------------


def plain(markdown: str) -> str:
    """The text RenderCV prints for a markdown string: links become their text, bold disappears."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(markdown))
    return text.replace("**", "").replace("*", "").strip()


def norm(text: str) -> str:
    """Compare text the way a tolerant parser would: unify dashes, quotes and spacing, ignore case."""
    text = unicodedata.normalize("NFKC", text)
    text = DASHES.sub("-", text).replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ([,.;:])", r"\1", text)  # the link mark leaves "Company , Title"
    return text.strip().lower()


def squash(text: str) -> str:
    return re.sub(r"\s+", "", norm(text))


def month(value) -> str:
    value = str(value)
    if value.lower() == "present":
        return "Present"
    year, mon = value.split("-")[:2]
    return f"{MONTHS[int(mon) - 1]} {year}"


def date_text(item: dict) -> str | None:
    if "date" in item:
        return month(item["date"])
    if "start_date" in item:
        return f"{month(item['start_date'])} – {month(item.get('end_date', 'present'))}"
    return None


# --- what the PDF must contain, read from the YAML ------------------------------


def expected(cv: dict) -> dict:
    sections = cv["sections"]
    entries: list[Entry] = []
    certifications: list[str] = []
    skills: list[str] = []
    for title, items in sections.items():
        for item in items:
            if isinstance(item, str):  # Summary
                continue
            if "company" in item:
                entries.append(Entry(title, plain(item["company"]), plain(item["position"]), date_text(item),
                                     [plain(h) for h in item.get("highlights", [])]))
            elif "institution" in item:
                entries.append(Entry(title, plain(item["institution"]),
                                     f"{item['degree']} in {plain(item['area'])}", date_text(item),
                                     [plain(item["summary"])] if item.get("summary") else []))
            elif "name" in item:
                entries.append(Entry(title, plain(item["name"]), None, date_text(item),
                                     [plain(h) for h in item.get("highlights", [])]))
            elif "bullet" in item:
                certifications.append(plain(item["bullet"]))
            elif "label" in item:
                skills.append(f"{plain(item['label'])}: {plain(item['details'])}")
    networks = {n["network"].lower(): n["username"] for n in cv.get("social_networks", [])}
    links_text, link_uris = [], {f"mailto:{cv['email']}"}
    if cv.get("website"):
        site = re.sub(r"^https?://(www\.)?", "", cv["website"]).rstrip("/")
        links_text.append(site)
        link_uris.add(f"https://{site}")
    if "linkedin" in networks:
        links_text.append(f"linkedin.com/in/{networks['linkedin']}")
        link_uris.add(f"https://linkedin.com/in/{networks['linkedin']}")
    if "github" in networks:
        links_text.append(f"github.com/{networks['github']}")
        link_uris.add(f"https://github.com/{networks['github']}")
    return {
        "name": cv["name"],
        "email": cv["email"],
        "links_text": links_text,
        "link_uris": link_uris,
        "headings": [t.upper() for t in sections if t != "Summary"],
        "summary": [plain(s) for s in sections.get("Summary", [])],
        "entries": entries,
        "certifications": certifications,
        "skills": skills,
    }


# --- extractors -----------------------------------------------------------------


def extract(pdf: Path, report: Report) -> dict[str, str]:
    doc = pymupdf.open(pdf)
    texts = {
        "PyMuPDF": "\n".join(page.get_text() for page in doc),
        "pdfminer.six": pdfminer_extract(str(pdf)),
        "pypdf": "\n".join(page.extract_text() or "" for page in PdfReader(pdf).pages),
    }
    node = shutil.which("node")
    if node and (ROOT / "node_modules" / "pdfjs-dist").exists():
        run = subprocess.run([node, str(PDFJS_SCRIPT), str(pdf)], capture_output=True, text=True)
        if run.returncode != 0:
            report.fail(f"pdf.js could not read the PDF: {run.stderr.strip()[:300]}")
        else:
            texts["pdf.js"] = run.stdout
    elif os.environ.get("ATS_REQUIRE_PDFJS"):
        report.fail("pdf.js is required (ATS_REQUIRE_PDFJS) but Node or node_modules/pdfjs-dist is missing; run npm ci")
    else:
        report.warn("pdf.js skipped: run `npm ci` to include it (CI always does)")
    return texts


# --- checks ---------------------------------------------------------------------


def find(haystack: str, needle: str, start: int = 0) -> int:
    return haystack.find(norm(needle), start)


def check_extractor(name: str, raw: str, exp: dict, report: Report) -> int:
    """Check one extractor's text; return how many expected items it read intact."""
    text, flat = norm(raw), squash(raw)
    phrases: list[tuple[str, str]] = [("name", exp["name"]), ("email", exp["email"])]
    phrases += [("link", t) for t in exp["links_text"]]
    phrases += [("summary", s) for s in exp["summary"]]
    phrases += [("heading", h) for h in exp["headings"]]
    for e in exp["entries"]:
        phrases.append((f"{e.section} entry", e.label))
        if e.detail:
            phrases.append((f"{e.section} title", e.detail))
        if e.date:
            phrases.append((f"{e.section} date", e.date))
        phrases += [(f"{e.section} bullet", b) for b in e.bullets]
    phrases += [("certification", c) for c in exp["certifications"]]
    phrases += [("skills row", s) for s in exp["skills"]]

    intact = 0
    for kind, phrase in phrases:
        if norm(phrase) in text:
            intact += 1
        elif squash(phrase) in flat:
            report.fail(f"{name}: words run together in {kind} {phrase[:70]!r}; keyword search would miss them")
        else:
            report.fail(f"{name}: lost {kind} {phrase[:70]!r}")

    # Section headings must be read in the order they are printed.
    spots = [find(text, h) for h in exp["headings"]]
    if all(s >= 0 for s in spots) and spots != sorted(spots):
        report.fail(f"{name}: section headings are read out of order")

    # Locate headings in sequence, so a section name that also occurs inside an
    # earlier bullet is not mistaken for the heading.
    heads: dict[str, int] = {}
    cursor = 0
    for h in exp["headings"]:
        heads[h] = find(text, h, cursor)
        if heads[h] >= 0:
            cursor = heads[h] + 1

    # Each dated entry's date must be read inside its own entry: after its label and
    # before the next entry's label, or before the next section for the last entry.
    # A parser that attaches a date to the wrong job gets the experience wrong.
    for section in dict.fromkeys(e.section for e in exp["entries"]):
        group = [e for e in exp["entries"] if e.section == section]
        top = heads.get(section.upper(), -1)
        if top < 0:
            continue  # already reported as lost
        later = [p for p in heads.values() if p > top]
        section_end = min(later) if later else len(text)
        starts, cursor = [], top
        for e in group:
            pos = find(text, e.label, cursor)
            starts.append(pos)
            if pos >= 0:
                cursor = pos + 1
        if any(s < 0 for s in starts):
            continue  # already reported as lost
        for i, e in enumerate(group):
            end = starts[i + 1] if i + 1 < len(group) else section_end
            if e.date:
                d = find(text, e.date, starts[i])
                if d < 0 or d >= end:
                    msg = f"{name}: date {e.date!r} of {e.label!r} is read outside its entry"
                    # Employment and education dates feed parsed fields; project dates do not.
                    (report.fail if section in exp["headings_core"] else report.warn)(msg)

    for label, pattern in BAD_CHARS.items():
        hits = sorted(set(pattern.findall(raw)))
        if hits:
            report.fail(f"{name}: {label} in the text: {', '.join(repr(h) for h in hits[:5])}")
    hidden = sorted({f"U+{ord(c):04X}" for c in raw if unicodedata.category(c) in ("Co", "Cf")})
    if hidden:
        report.fail(f"{name}: hidden or private-use characters: {', '.join(hidden)}")
    return intact


def check_file(pdf: Path, exp: dict, report: Report) -> None:
    size = pdf.stat().st_size
    if size > MAX_BYTES:
        report.fail(f"file is {size:,} bytes; keep it under {MAX_BYTES:,}")
    doc = pymupdf.open(pdf)
    if doc.is_encrypted or doc.needs_pass:
        report.fail("PDF is encrypted; parsers cannot read it")
    text = "".join(page.get_text() for page in doc)
    if len(text) < MIN_TEXT_CHARS:
        report.fail(f"text layer has only {len(text)} characters; is the page an image?")
    for page in doc:
        if page.get_images():
            report.fail(f"page {page.number + 1} has {len(page.get_images())} image(s); parsers cannot read text in images")
    for _, ext, _, basefont, *_ in doc.get_page_fonts(0):
        if ext == "n/a":
            report.fail(f"font {basefont!r} is not embedded")
    meta = doc.metadata or {}
    if not meta.get("title"):
        report.fail("PDF has no title metadata")
    if (meta.get("author") or "").strip() != exp["name"]:
        report.fail(f"PDF author metadata is {meta.get('author')!r}, expected {exp['name']!r}")
    uris = {(link.get("uri") or "").rstrip("/").replace("://www.", "://") for page in doc for link in page.get_links()}
    for uri in sorted(exp["link_uris"]):
        if uri.rstrip("/") not in uris:
            report.fail(f"contact link {uri!r} is not clickable in the PDF")
    report.notes.append(f"{size:,} bytes, {len(doc)} page, {len(text):,} characters, "
                        f"{len(doc.get_page_fonts(0))} embedded fonts, {len(uris)} links, no images")


def check_headings(exp: dict, report: Report) -> None:
    """The core sections must use names parsers map to fields; remember which titles they are."""
    known = set().union(*CORE_HEADINGS.values())
    for field_name, names in CORE_HEADINGS.items():
        if not set(exp["headings"]) & names:
            report.fail(f"no {field_name} section under a name parsers recognise ({', '.join(sorted(names))})")
    exp["headings_core"] = {t for t in exp["section_titles"] if t.upper() in known}


def check_keywords(texts: dict[str, str], report: Report) -> list[str]:
    yaml = YAML(typ="safe")
    spec = yaml.load(KEYWORDS_PATH.read_text(encoding="utf-8")) or {}

    def terms(group: str) -> list[tuple[str, list[str]]]:
        out = []
        for item in spec.get(group) or []:
            if isinstance(item, dict):
                for term, aliases in item.items():
                    out.append((term, [term, *(aliases or [])]))
            else:
                out.append((str(item), [str(item)]))
        return out

    def present(text: str, forms: list[str]) -> bool:
        return any(re.search(rf"(?<![A-Za-z0-9]){re.escape(f)}(?![A-Za-z0-9])", text, re.I) for f in forms)

    lines = []
    for group in ("required", "preferred"):
        rows = terms(group)
        if not rows:
            continue
        found = []
        for term, forms in rows:
            missing_in = [n for n, t in texts.items() if not present(t, forms)]
            if len(missing_in) == len(texts):
                if group == "required":
                    report.fail(f"required keyword {term!r} is not on the resume")
            elif missing_in:
                report.fail(f"keyword {term!r} is on the page but {', '.join(missing_in)} cannot read it")
            else:
                found.append(term)
        missing = [t for t, _ in rows if t not in found]
        lines.append(f"- **{group.title()}**: {len(found)}/{len(rows)} present"
                     + (f"; missing: {', '.join(missing)}" if missing else ""))
    return lines


def main(argv: list[str]) -> int:
    pdf = Path(argv[1] if len(argv) > 1 else ROOT / "rendercv_output" / "Alpha_Romer_Coma_CV.pdf")
    report = Report()
    cv = YAML(typ="safe").load(YAML_PATH.read_text(encoding="utf-8"))["cv"]
    exp = expected(cv)
    exp["section_titles"] = list(cv["sections"].keys())

    check_headings(exp, report)
    check_file(pdf, exp, report)
    texts = extract(pdf, report)
    total = (2 + len(exp["links_text"]) + len(exp["summary"]) + len(exp["headings"])
             + sum(1 + bool(e.detail) + bool(e.date) + len(e.bullets) for e in exp["entries"])
             + len(exp["certifications"]) + len(exp["skills"]))
    rows = [f"| {name} | {check_extractor(name, raw, exp, report)}/{total} |" for name, raw in texts.items()]
    keyword_lines = check_keywords(texts, report)

    status = "FAILED" if report.failures else "passed"
    md = [f"## ATS check {status}", "",
          "Each extractor below is one way an applicant tracking system reads this PDF.", "",
          "| Extractor | Items read intact |", "|---|---|", *rows, "",
          "**File:** " + "; ".join(report.notes), "", "**Keywords** (`ats/keywords.yaml`):", *keyword_lines]
    if report.failures:
        md += ["", "**Failures**", *[f"- {f}" for f in report.failures]]
    if report.warnings:
        md += ["", "**Warnings**", *[f"- {w}" for w in report.warnings]]
    out = "\n".join(md) + "\n"
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(out, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(out)

    if report.failures:
        print("ats check failed:", *report.failures, sep="\n  - ", file=sys.stderr)
        for w in report.warnings:
            print(f"  warning: {w}", file=sys.stderr)
        return 1
    print(f"ats ok: {len(texts)} extractors read all {total} items; " + "; ".join(l.lstrip('- ').replace('**', '') for l in keyword_lines))
    for w in report.warnings:
        print(f"  warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
