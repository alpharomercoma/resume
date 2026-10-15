# AGENTS.md

This repo is Alpha Romer Coma's resume as code. `Alpha_Romer_Coma_CV.yaml` is the
single source of truth; [RenderCV](https://docs.rendercv.com) (pinned in `uv.lock`)
turns it into PDF, PNG, Markdown, and HTML through the custom theme in `alpha/`.
The live copy is served at <https://alpharomer.com/resume> from the latest GitHub
release of this repo.

## Commands

```bash
./scripts/render.sh                                   # render + check -> rendercv_output/
uv run rendercv render Alpha_Romer_Coma_CV.yaml -w    # live re-render while editing
```

`scripts/render.sh` runs `scripts/check.py`, which fails if the resume runs past one
page, if any bullet wraps onto a second line, or if the PDF text layer picks up
icon glyphs or invisible characters. Never commit `rendercv_output/`; CI rebuilds it.

## How a change ships

1. Edit `Alpha_Romer_Coma_CV.yaml`.
2. Run `./scripts/render.sh` and look at `rendercv_output/Alpha_Romer_Coma_CV.png`.
3. Commit with a Conventional Commit subject in lowercase that says what changed
   in the resume, e.g. `feat(experience): add viableview multi-cloud pipeline`.
   The commit subjects become the release notes.
4. Push to `master`. `.github/workflows/release.yml` re-renders, runs the same
   check, and publishes a release tagged `vYYYY.MM.DD` (`.2`, `.3` for later
   releases the same day), then refreshes alpharomer.com/resume so the new
   version is live within seconds.

Every release is a version: to see or restore an old resume, use the release list
or `git log -p Alpha_Romer_Coma_CV.yaml`.

## Editing rules

- **Only write what is true and sourced.** Take facts from Alpha, from their public
  profiles (alpharomer.com, LinkedIn, GitHub), or from links already in the YAML.
  Never invent or round up metrics, dates, titles, or employers. If a detail is
  missing, leave it out and ask.
- **Every bullet fits on one line.** This is deliberate and enforced. Tighten the
  wording rather than letting a bullet wrap; never shrink the type or margins.
- **One page, always.** If something new pushes it over, cut or merge the weakest
  older bullet. Ask before dropping a whole entry.
- **Keep the voice.** Bullets start with a past-tense verb, end with a period, and
  lead with a concrete number. Bold (`**...**`) only the headline metric or phrase.
- **Machine learning first.** Alpha is applying for competitive ML roles. Projects must
  be machine learning or deep learning work (training, post-training, inference,
  accelerators, evaluation); never scrapers, web apps, or tooling. Lead with the
  measured result, and say exactly what moved (e.g. answer format, not accuracy).
- **Link only public pages.** Some repos are private; link the public Hugging Face
  model, site, or event page instead.
- **Newest first** within every section. Dates are `YYYY-MM`; ongoing roles use
  `end_date: present`.
- **Link titles, not URLs.** Markdown links on the entry title get the small
  external-link mark automatically.
- **Quote any line containing `: `** (colon + space), or YAML reads it as a mapping.

## How the YAML maps to the layout

- `Summary` is special: it renders centered under the contact line with no heading.
- `Professional Experience` entries use `company` + `position` and render as
  "**Company**, **Position**".
- `Projects & Research`, `Speaking & Community`, and `Awards & Recognition` entries
  use `name`, written with explicit bold so the organization is optional:
  `"**[Title](link)**, **Organization**"` or just `"**[Title](link)**"`. An award can
  carry a one-line detail after a colon: `"**[Title](link)**, **Org**: detail"`.
- Talks are grouped under one "International Conference Speaker" entry, one bullet
  per talk, all in one format with no bold:
  `Presenting “Exact Title” at [Event](session link), City.` (`Presented` once given).
  If a title is too long for one line, quote only its main title, up to the colon;
  never reword a title. Community roles share one entry. Add to these rather than
  adding entries.
- `Certifications` entries use `bullet:` and render in two columns, filled top to bottom.
- `Education` renders "**DEGREE in AREA, INSTITUTION**" with `summary` as the
  indented line underneath.
- Section names render in uppercase; keep them in Title Case in the YAML.

## Design

The look lives in `alpha/Preamble.j2.typ`. It reproduces the original FlowCV
resume: A4, 1cm side margins, Roboto 9pt body on a 10.5pt line pitch, a 14pt bold name
with an 11pt italic headline on the same line, 10pt bold uppercase section titles over
a 1.5pt rule, `#333333` for name, titles, rules and dates, and black body text.
Change it only when asked, and compare the PNG before and after.

To upgrade RenderCV, run `uv lock --upgrade-package rendercv`, update the schema URL
on line 1 of the YAML to the new tag, re-render, and compare the PNG.
