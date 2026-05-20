# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Render a profile-specific CV from a master CV YAML.

Profiles are defined in a separate profiles.yaml (auto-discovered next to the
CV YAML, or specified with --profiles). The CV YAML stays rendercv-compatible
with no extra keys, so `rendercv render raeedcv.yaml` and CI both work as-is.

Usage:
    # Render the full CV (passes straight through to rendercv)
    uv run render_profile.py raeedcv.yaml

    # List available profiles
    uv run render_profile.py raeedcv.yaml --list

    # Render a specific profile
    uv run render_profile.py raeedcv.yaml teaching

    # Preview the filtered YAML without rendering
    uv run render_profile.py raeedcv.yaml teaching --dry-run

    # Use a custom profiles file
    uv run render_profile.py raeedcv.yaml teaching --profiles my_profiles.yaml

Example profiles.yaml:

    teaching:
      sections:
        - education
        - teaching experience
        - publications
        - skills
        - awards, fellowships and grants
    research:
      sections:
        - research experience
        - education
        - publications
        - conference talks
        - poster presentations
        - awards, fellowships and grants
        - skills
"""

import argparse
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def normalize_key(key: str) -> str:
    """Strip trailing/leading whitespace for matching."""
    return key.strip().lower()


def build_section_lookup(sections: dict) -> dict[str, str]:
    """Map normalized key -> original key for all CV sections."""
    return {normalize_key(k): k for k in sections}


def find_profiles_file(cv_path: Path) -> Path | None:
    """Look for profiles.yaml next to the CV YAML."""
    candidate = cv_path.parent / "profiles.yaml"
    return candidate if candidate.exists() else None


def load_profiles(cv_path: Path, explicit_path: Path | None) -> dict:
    """Load profiles from an explicit path or auto-discovered file."""
    if explicit_path:
        if not explicit_path.exists():
            print(f"Error: profiles file not found: {explicit_path}", file=sys.stderr)
            sys.exit(1)
        return load_yaml(explicit_path)

    found = find_profiles_file(cv_path)
    if found:
        return load_yaml(found)

    return {}


def filter_cv(cv_data: dict, profiles: dict, profile_name: str) -> dict:
    """Return a copy of cv_data with sections filtered and reordered per profile."""
    if profile_name not in profiles:
        available = ", ".join(profiles.keys()) or "(none defined)"
        print(
            f"Error: profile '{profile_name}' not found. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    profile = profiles[profile_name]
    requested_sections = profile.get("sections", [])

    if not requested_sections:
        print(
            f"Error: profile '{profile_name}' has no sections defined.",
            file=sys.stderr,
        )
        sys.exit(1)

    original_sections = cv_data["cv"]["sections"]
    lookup = build_section_lookup(original_sections)

    # Build filtered sections in the order specified by the profile
    filtered = {}
    for req in requested_sections:
        norm = normalize_key(req)
        if norm in lookup:
            original_key = lookup[norm]
            filtered[original_key] = original_sections[original_key]
        else:
            print(
                f"Warning: section '{req}' not found in CV, skipping.",
                file=sys.stderr,
            )

    out = deepcopy(cv_data)
    out["cv"]["sections"] = filtered
    return out


def list_profiles(cv_data: dict, profiles: dict) -> None:
    """Print available profiles and their sections."""
    if not profiles:
        print("No profiles found.")
        print()
        print("Create a profiles.yaml next to your CV YAML, e.g.:")
        print()
        print("  teaching:")
        print("    sections:")
        print("      - education")
        print("      - teaching experience")
        return

    print("Available profiles:")
    print()
    for name, profile in profiles.items():
        sections = profile.get("sections", [])
        print(f"  {name}:")
        for s in sections:
            print(f"    - {s}")
        print()

    print("All CV sections:")
    for k in cv_data["cv"]["sections"]:
        print(f"  - {k.strip()}")


def main():
    parser = argparse.ArgumentParser(
        description="Render profile-specific CVs from a master YAML."
    )
    parser.add_argument("yaml_file", type=Path, help="Path to master CV YAML")
    parser.add_argument(
        "profile",
        nargs="?",
        default=None,
        help="Profile name to render (omit for full CV)",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=None,
        help="Path to profiles YAML (default: profiles.yaml next to CV)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available profiles and exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print filtered YAML to stdout instead of rendering",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for rendered CV (default: rendercv_output/)",
    )

    args = parser.parse_args()
    cv_data = load_yaml(args.yaml_file)
    profiles = load_profiles(args.yaml_file, args.profiles)

    if args.list:
        list_profiles(cv_data, profiles)
        return

    # No profile: pass straight through to rendercv
    if args.profile is None:
        cmd = ["rendercv", "render", str(args.yaml_file)]
        if args.output_dir:
            cmd.extend(["--output-folder-name", str(args.output_dir)])
        sys.exit(subprocess.run(cmd).returncode)

    # Profile specified: filter and render
    out = filter_cv(cv_data, profiles, args.profile)

    if args.dry_run:
        yaml.dump(
            out, sys.stdout,
            default_flow_style=False, allow_unicode=True, sort_keys=False,
        )
        return

    # Write temp file next to the source YAML so rendercv outputs there
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix=f".cv_{args.profile}_",
        dir=args.yaml_file.parent,
        delete=False,
    ) as tmp:
        yaml.dump(
            out, tmp,
            default_flow_style=False, allow_unicode=True, sort_keys=False,
        )
        tmp_path = tmp.name

    cmd = ["rendercv", "render", tmp_path]
    if args.output_dir:
        cmd.extend(["--output-folder-name", str(args.output_dir)])

    print(f"Rendering {args.profile} CV...")
    print(f"  command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)
    Path(tmp_path).unlink(missing_ok=True)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()