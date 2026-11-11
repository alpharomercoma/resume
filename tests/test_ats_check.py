"""Prove the ATS check can fail: break the rendered text on purpose and expect it to notice.

A check that passes on the real resume proves nothing unless it also rejects a
damaged one. Each case below edits PyMuPDF's text of the rendered PDF the way a
bad template change or a bad extractor would, and asserts the check flags it.

Run after ./scripts/render.sh (it needs rendercv_output/Alpha_Romer_Coma_CV.pdf):
    uv run --frozen pytest -q tests
"""

import sys
from pathlib import Path

import pymupdf
import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ats_check  # noqa: E402

PDF = ROOT / "rendercv_output" / "Alpha_Romer_Coma_CV.pdf"


@pytest.fixture(scope="module")
def exp():
    cv = YAML(typ="safe").load(ats_check.YAML_PATH.read_text(encoding="utf-8"))["cv"]
    exp = ats_check.expected(cv)
    exp["section_titles"] = list(cv["sections"])
    ats_check.check_headings(exp, ats_check.Report())
    return exp


@pytest.fixture(scope="module")
def raw():
    if not PDF.exists():
        pytest.skip("render the resume first: ./scripts/render.sh")
    return pymupdf.open(PDF)[0].get_text()


def failures(text, exp):
    report = ats_check.Report()
    ats_check.check_extractor("test", text, exp, report)
    return report.failures


def test_rendered_resume_passes(raw, exp):
    assert failures(raw, exp) == []


def test_lost_bullet_fails(raw, exp):
    bullet = exp["entries"][0].bullets[0]
    assert any("lost" in f for f in failures(raw.replace(bullet[:40], "", 1), exp))


def test_words_run_together_fail(raw, exp):
    bullet = exp["entries"][0].bullets[0]
    words = bullet.split()
    glued = bullet.replace(f"{words[1]} {words[2]}", f"{words[1]}{words[2]}", 1)
    assert any("run together" in f for f in failures(raw.replace(bullet, glued, 1), exp))


def test_job_date_read_in_the_next_section_fails(raw, exp):
    last_job = [e for e in exp["entries"] if e.section == exp["entries"][0].section][-1]
    next_heading = exp["headings"][exp["headings"].index(last_job.section.upper()) + 1]
    moved = raw.replace(last_job.date, "", 1).replace(next_heading, f"{next_heading}\n{last_job.date}", 1)
    assert any("outside its entry" in f for f in failures(moved, exp))


def test_headings_out_of_order_fail(raw, exp):
    a, b = exp["headings"][0], exp["headings"][1]
    swapped = raw.replace(a, "\0", 1).replace(b, a, 1).replace("\0", b, 1)
    assert any("out of order" in f for f in failures(swapped, exp))


@pytest.mark.parametrize("bad", ["ﬁ", "(cid:12)", "​", "�"])
def test_bad_characters_fail(raw, exp, bad):
    assert failures(raw + bad, exp)


def test_missing_required_keyword_fails(raw):
    report = ats_check.Report()
    ats_check.check_keywords({"test": raw.replace("vLLM", "v-L-L-M")}, report)
    assert any("'vLLM'" in f for f in report.failures)
