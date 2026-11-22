#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply device patches to the checked-out upstream revisions."""

import argparse
import json
import subprocess
from pathlib import Path


def apply_patches(
    tree: Path, series_path: Path, check_only: bool = False, reverse: bool = False
) -> None:
    pending = []
    direction = ["--reverse"] if reverse else []
    opposite = [] if reverse else ["--reverse"]
    for entry in json.loads(series_path.read_text()):
        project = tree / entry["project"]
        patch = series_path.parent / entry["patch"]
        git = ["git", "-C", str(project)]
        head = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
        base = entry.get("base_commit")
        if base is not None and head != base:
            raise ValueError(
                f"Wrong baseline: {entry['project']} (expected {base}, got {head})"
            )

        check = [*git, "apply", "--check"]
        if reverse:
            staged = subprocess.run([*git, "diff", "--cached", "--quiet", head, "--"])
            if staged.returncode == 1:
                raise ValueError(
                    f"Staged changes in {entry['project']}; commit or unstage them first"
                )
            staged.check_returncode()
            upstream = subprocess.run(
                [*check, "--cached", "--reverse", str(patch)], capture_output=True
            )
            if upstream.returncode == 0:
                print(f"already upstream: {entry['project']}")
                continue
            baseline = subprocess.run(
                [*check, "--cached", str(patch)], capture_output=True, text=True
            )
            if baseline.returncode:
                raise ValueError(
                    f"Cannot reverse {entry['project']}: patch does not apply "
                    f"cleanly to {head}:\n{baseline.stderr}"
                )

        result = subprocess.run(
            [*check, *direction, str(patch)], capture_output=True, text=True
        )
        if result.returncode == 0:
            pending.append((project, patch))
            print(f"ready: {entry['project']}")
            continue

        alternate = subprocess.run([*check, *opposite, str(patch)], capture_output=True)
        if alternate.returncode != 0:
            operation = "reverse" if reverse else "apply"
            raise ValueError(
                f"Cannot {operation} {entry['project']} at {head}:\n{result.stderr}"
            )
        status = "not applied" if reverse else "already applied"
        print(f"{status}: {entry['project']}")

    # Validate the whole series before changing any project.
    if check_only:
        return
    for project, patch in pending:
        subprocess.run(
            ["git", "-C", str(project), "apply", *direction, str(patch)], check=True
        )
    status = "Reversed" if reverse else "Applied"
    print(f"{status} {len(pending)} project patches.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="Check without applying")
    parser.add_argument("--reverse", action="store_true", help="Remove applied patches")
    args = parser.parse_args()
    series_path = Path(__file__).resolve().parents[1] / "patches/series.json"
    try:
        apply_patches(args.tree.resolve(), series_path, args.check, args.reverse)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
