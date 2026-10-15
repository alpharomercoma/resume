#!/usr/bin/env bash
# Render the CV, then check it (one page, no wrapped bullets, clean text layer).
# Used locally and in CI.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf rendercv_output
uv run --frozen rendercv render Alpha_Romer_Coma_CV.yaml --quiet
uv run --frozen python scripts/check.py rendercv_output/Alpha_Romer_Coma_CV.pdf
mv rendercv_output/Alpha_Romer_Coma_CV_1.png rendercv_output/Alpha_Romer_Coma_CV.png
