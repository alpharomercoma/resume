// Print a PDF's text the way pdf.js reads it, one line per text line.
//
// Browser-based resume parsers (OpenResume's among them) and many ATS upload
// previews are built on pdf.js, so this is one of the extractors
// scripts/ats_check.py compares. Items come out in content-stream order, which
// is exactly what such a parser sees before it applies its own heuristics.
//
//   node scripts/ats/pdfjs_text.mjs rendercv_output/Alpha_Romer_Coma_CV.pdf

import { readFile } from "node:fs/promises";
import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";

const path = process.argv[2];
if (!path) {
  console.error("usage: node scripts/ats/pdfjs_text.mjs <file.pdf>");
  process.exit(2);
}

const data = new Uint8Array(await readFile(path));
const task = getDocument({ data, verbosity: 0, isEvalSupported: false });
const pdf = await task.promise;

const lines = [];
for (let n = 1; n <= pdf.numPages; n++) {
  const page = await pdf.getPage(n);
  const { items } = await page.getTextContent();
  let line = "";
  for (const item of items) {
    if (!("str" in item)) continue;
    line += item.str;
    if (item.hasEOL) {
      lines.push(line);
      line = "";
    }
  }
  if (line) lines.push(line);
}
await task.destroy();
process.stdout.write(lines.join("\n") + "\n");
