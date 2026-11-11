#!/usr/bin/env bash
# Render the CV, then check it. Used locally and in CI.
#   check.py      layout: one page, no wrapped bullets, dates flush right, clean text
#   ats_check.py  ATS: four text extractors read every item, dates stay in their
#                 entries, contact links work, required keywords present
#   tests/        proves the ATS check still fails on a damaged resume
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf rendercv_output
uv run --frozen rendercv render Alpha_Romer_Coma_CV.yaml --quiet
mv rendercv_output/Alpha_Romer_Coma_CV_1.png rendercv_output/Alpha_Romer_Coma_CV.png
uv run --frozen python scripts/check.py rendercv_output/Alpha_Romer_Coma_CV.pdf
uv run --frozen python scripts/ats_check.py rendercv_output/Alpha_Romer_Coma_CV.pdf
uv run --frozen pytest -q -p no:warnings tests
