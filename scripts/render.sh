#!/usr/bin/env bash
# Render the CV and enforce the one-page rule. Used locally and in CI.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf rendercv_output
uv run --frozen rendercv render Alpha_Romer_Coma_CV.yaml --quiet

# RenderCV writes one PNG per page, so a second PNG means the resume overflowed.
pages=$(find rendercv_output -name 'Alpha_Romer_Coma_CV_*.png' | wc -l | tr -d ' ')
if [ "$pages" -ne 1 ]; then
	echo "error: resume renders to $pages pages; it must fit on one page." >&2
	exit 1
fi
mv rendercv_output/Alpha_Romer_Coma_CV_1.png rendercv_output/Alpha_Romer_Coma_CV.png
echo "ok: rendered one page to rendercv_output/"
