# AGENTS.md

This repo is Alpha Romer Coma's resume as code. `Alpha_Romer_Coma_CV.yaml` is the
single source of truth; [RenderCV](https://docs.rendercv.com) (pinned in `uv.lock`)
turns it into PDF, PNG, Markdown, and HTML. The live copy is served at
<https://alpharomer.com/resume> from the latest GitHub release of this repo.

## Commands

```bash
./scripts/render.sh                                   # render + enforce one page -> rendercv_output/
uv run rendercv render Alpha_Romer_Coma_CV.yaml -w    # live re-render while editing
```

Never commit `rendercv_output/`; CI rebuilds it.

## How a change ships

1. Edit `Alpha_Romer_Coma_CV.yaml`.
2. Run `./scripts/render.sh` and look at `rendercv_output/Alpha_Romer_Coma_CV.png`.
3. Commit with a Conventional Commit subject in lowercase that says what changed
   in the resume, e.g. `feat(experience): add viableview multi-cloud pipeline`.
   The commit subjects become the release notes.
4. Push to `master`. `.github/workflows/release.yml` re-renders, fails if the resume
   is more than one page, and publishes a release tagged `vYYYY.MM.DD` (`.2`, `.3`
   for later releases the same day). The website picks it up within an hour.

Every release is a version: to see or restore an old resume, use the release list
or `git log -p Alpha_Romer_Coma_CV.yaml`.

## Editing rules

- **Only write what is true and sourced.** Take facts from Alpha, from their public
  profiles (alpharomer.com, LinkedIn, GitHub), or from links already in the YAML.
  Never invent or round up metrics, dates, titles, or employers. If a detail is
  missing, leave it out and ask.
- **One page, always.** If something new pushes it over, cut or merge the weakest
  older bullet rather than shrinking the type further. Ask before dropping a
  whole entry.
- **Keep the voice.** Bullets start with a past-tense verb, run one line where
  possible, end with a period, and lead with a concrete number. Bold (`**...**`)
  only the one headline metric per bullet, sparingly.
- **Newest first** within every section. Dates are `YYYY-MM`; ongoing roles use
  `end_date: present`.
- **Link titles, not URLs.** Use Markdown links on the entry name or company.
- **Quote any line containing `: `** (colon + space), or YAML reads it as a mapping.
- Entry type is inferred from its fields, and one section holds one type:
  `company`+`position` (experience-style), `name` (projects), `label`+`details`
  (skills), `institution`+`area` (education), plain strings (text). The schema
  is linked on line 1 of the YAML for editor validation.
- Change `design:` only when asked. To upgrade RenderCV, run `uv lock --upgrade-package rendercv`,
  update the schema URL on line 1 to the new tag, re-render, and compare the PNG.
