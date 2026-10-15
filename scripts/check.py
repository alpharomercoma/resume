"""Check a rendered resume PDF for layout and ATS regressions.

Run by scripts/render.sh after every render, locally and in CI:
    uv run python scripts/check.py rendercv_output/Alpha_Romer_Coma_CV.pdf
"""

import re
import sys
import unicodedata

import pymupdf

ALLOWED_FONTS = {"Roboto-Regular", "Roboto-Bold", "Roboto-Italic", "Lato-Regular"}
BULLET_FONT = "Lato-Regular"  # the theme sets its bullet glyph in Lato
RIGHT_MARGIN = 28.35  # 1cm, as set in alpha/Preamble.j2.typ
DATE = re.compile(r"^[A-Z][a-z]{2} \d{4}( – ([A-Z][a-z]{2} \d{4}|Present))?$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def expected_dates(yaml_path: str) -> int:
    """Count entries in the YAML that carry a date, to catch dates that vanish or split."""
    count = 0
    for line in open(yaml_path, encoding="utf-8"):
        key = line.strip().removeprefix("- ").split(":", 1)[0]
        if key in ("date", "start_date"):
            count += 1
    return count


def main(path: str, yaml_path: str = "Alpha_Romer_Coma_CV.yaml") -> int:
    doc = pymupdf.open(path)
    errors: list[str] = []

    if doc.page_count != 1:
        fail(errors, f"resume is {doc.page_count} pages; it must fit on one page")
    page = doc[0]
    if abs(page.rect.width - 595.3) > 1 or abs(page.rect.height - 841.9) > 1:
        fail(errors, f"page is {page.rect.width:.0f}x{page.rect.height:.0f}pt; the theme is designed for A4")

    spans: list[dict] = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                glyphs = [c for c in span["chars"] if c["c"].strip()]
                if not glyphs:
                    continue
                span_text = "".join(c["c"] for c in span["chars"])
                font = span["font"].split("+")[-1]
                if font not in ALLOWED_FONTS:
                    fail(errors, f"unexpected font {font!r} in {span_text!r}")
                spans.append(
                    {
                        "x": glyphs[0]["bbox"][0],
                        "right": glyphs[-1]["bbox"][2],
                        "y": glyphs[0]["origin"][1],
                        "font": font,
                        "text": span_text,
                    }
                )

    text = page.get_text()
    hidden = sorted({f"U+{ord(c):04X}" for c in text if unicodedata.category(c) in ("Co", "Cf") or c == "\u00a0"})
    if hidden:
        fail(errors, f"hidden or private-use characters in the text layer: {', '.join(hidden)}")

    # Every bullet must fit on one line. A wrapped bullet leaves a line that
    # starts at a bullet's text indent but has no bullet of its own. (The bullet
    # glyph sits slightly above its line's baseline, hence the tolerance.)
    bullets = [s for s in spans if s["font"] == BULLET_FONT and s["text"].strip() == "•"]
    words = [s for s in spans if s not in bullets]
    indents: list[float] = []
    bullet_lines: set[float] = set()
    for bullet in bullets:
        right = [w for w in words if abs(w["y"] - bullet["y"]) < 1.5 and w["x"] > bullet["x"]]
        if right:
            first = min(right, key=lambda w: w["x"])
            indents.append(first["x"])
            bullet_lines.add(round(first["y"], 1))
    line_starts: dict[float, dict] = {}
    for w in words:
        y = round(w["y"], 1)
        if y not in line_starts or w["x"] < line_starts[y]["x"]:
            line_starts[y] = w
    for y, first in sorted(line_starts.items()):
        if y not in bullet_lines and any(abs(first["x"] - x) < 0.4 for x in indents):
            fail(errors, f"bullet wraps onto a second line: {first['text'].strip()[:60]!r}")
    if not bullets:
        fail(errors, "no bullets found; did the theme's bullet font change?")

    # Dates sit flush right on their entry's title line. A title that grows too
    # long pushes its date onto a line of its own, away from the right margin.
    right_edge = page.rect.width - RIGHT_MARGIN
    dates = [s for s in spans if DATE.match(s["text"].strip())]
    for date in dates:
        if abs(date["right"] - right_edge) > 1:
            fail(errors, f"date {date['text'].strip()!r} is not flush right; is its title too long?")
        elif not any(abs(w["y"] - date["y"]) < 0.5 and w["x"] < date["x"] - 20 for w in spans):
            fail(errors, f"date {date['text'].strip()!r} sits on a line of its own; is its title too long?")
    want = expected_dates(yaml_path)
    if len(dates) != want:
        fail(errors, f"found {len(dates)} intact dates but the YAML has {want}; one may have wrapped or split")

    if errors:
        print("check failed:", *errors, sep="\n  - ", file=sys.stderr)
        return 1
    print(f"ok: 1 page, {len(bullets)} bullets each on one line, {len(dates)} dates flush right, clean text layer")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
