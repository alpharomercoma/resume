# Alpha Romer Coma — Resume

Resume as code, rendered with [RenderCV](https://github.com/rendercv/rendercv).

- **Live:** <https://alpharomer.com/resume> · [PDF](https://alpharomer.com/resume.pdf)
- **Source:** [`Alpha_Romer_Coma_CV.yaml`](Alpha_Romer_Coma_CV.yaml)
- **Versions:** every change on `master` is published as a dated [release](../../releases).

```bash
uv sync
./scripts/render.sh   # writes rendercv_output/ and fails if it runs past one page
```

See [AGENTS.md](AGENTS.md) for editing rules and the release flow.
