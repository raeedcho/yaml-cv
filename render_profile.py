# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml"]
# ///
"""
Render a profile-specific CV from a master raeedcv.yaml.

Profiles are defined in the YAML under a top-level `profiles` key (which
rendercv ignores). Each profile lists the sections to include, in order.

Usage:
    # List available profiles
    python render_profile.py raeedcv.yaml --list

    # Render a specific profile
    python render_profile.py raeedcv.yaml teaching

    # Preview the filtered YAML without rendering
    python render_profile.py raeedcv.yaml teaching --dry-run

    # Render the full CV (no filtering)
    python render_profile.py raeedcv.yaml

Example profiles block in raeedcv.yaml:

    profiles:
      teaching:
        sections:
          - education
          - teaching experience
          - skills
          - publications
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


def get_profiles(data: dict) -> dict:
    return data.get("profiles", {})


def normalize_key(key: str) -> str:
    """Strip trailing/leading whitespace for matching."""
    return key.strip().lower()


def build_section_lookup(sections: dict) -> dict[str, str]:
    """Map normalized key -> original key for all CV sections."""
    return {normalize_key(k): k for k in sections}


def filter_cv(data: dict, profile_name: str) -> dict:
    """Return a copy of the data with sections filtered and reordered per profile."""
    profiles = get_profiles(data)
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

    original_sections = data["cv"]["sections"]
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

    # Build output: full data minus profiles key, with filtered sections
    out = deepcopy(data)
    out.pop("profiles", None)
    out["cv"]["sections"] = filtered

    return out


def list_profiles(data: dict) -> None:
    """Print available profiles and their sections."""
    profiles = get_profiles(data)
    if not profiles:
        print("No profiles defined in YAML.")
        print()
        print("Add a top-level 'profiles' key, e.g.:")
        print()
        print("  profiles:")
        print("    teaching:")
        print("      sections:")
        print("        - education")
        print("        - teaching experience")
        return

    original_sections = data["cv"]["sections"]
    section_keys = list(original_sections.keys())

    print("Available profiles:")
    print()
    for name, profile in profiles.items():
        sections = profile.get("sections", [])
        print(f"  {name}:")
        for s in sections:
            print(f"    - {s}")
        print()

    print("All CV sections:")
    for k in section_keys:
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
    data = load_yaml(args.yaml_file)

    if args.list:
        list_profiles(data)
        return

    # No profile specified: render full CV (strip profiles key only)
    if args.profile is None:
        out = deepcopy(data)
        out.pop("profiles", None)
    else:
        out = filter_cv(data, args.profile)

    if args.dry_run:
        yaml.dump(out, sys.stdout, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return

    # Write temp file next to the source YAML so rendercv outputs there
    suffix = f"_{args.profile}" if args.profile else ""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix=f".cv{suffix}_",
        dir=args.yaml_file.parent,
        delete=False,
    ) as tmp:
        yaml.dump(out, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_path = tmp.name

    cmd = ["rendercv", "render", tmp_path]
    if args.output_dir:
        cmd.extend(["--output-folder-name", str(args.output_dir)])

    print(f"Rendering{' ' + args.profile if args.profile else ' full'} CV...")
    print(f"  temp file: {tmp_path}")
    print(f"  command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    # Clean up temp file
    Path(tmp_path).unlink(missing_ok=True)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()