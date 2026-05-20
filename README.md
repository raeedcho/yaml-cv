# CV

My CV, managed as a YAML file and rendered with [rendercv](https://github.com/rendercv/rendercv).

## Setup

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv tool install "rendercv[full]"
```

## Usage

### Render the full CV

```bash
rendercv render raeedcv.yaml
```

Output (PDF, HTML, Markdown, PNG pages) goes to `rendercv_output/`.

### Render a profile-specific CV

The `render_profile.py` script filters and reorders sections based on profiles defined in `profiles.yaml`. This is useful for tailoring the CV to different contexts (job applications, teaching portfolios, annual reports).

```bash
# List available profiles
uv run render_profile.py raeedcv.yaml --list

# Render a specific profile
uv run render_profile.py raeedcv.yaml teaching

# Preview the filtered YAML without rendering
uv run render_profile.py raeedcv.yaml teaching --dry-run
```

Profiles are defined in `profiles.yaml` (auto-discovered next to the CV YAML):

```yaml
teaching:
  sections:
    - education
    - teaching experience
    - research experience
    - publications
    - skills
    - awards, fellowships and grants
```

The section order in each profile controls the order they appear in the rendered CV.

### Snapshot a version

Use git tags for point-in-time snapshots (e.g., a promotion packet or annual report):

```bash
git tag cv/promotion-2026
git push origin cv/promotion-2026
```

## File structure

```
raeedcv.yaml          # CV content (single source of truth, rendercv-compatible)
profiles.yaml         # Profile definitions for section filtering
render_profile.py     # Profile rendering script (run with uv)
classic/              # Custom rendercv Typst templates (moderncv theme)
markdown/             # Custom rendercv Markdown templates
.github/workflows/    # GitHub Action to build full CV on push
```

## CI

On every push to `main`, the GitHub Action renders the full CV and uploads the PDF as a downloadable artifact.
