#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Sync the two development repositories into an existing PixelOS work tree."""

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"


def git(project, *args, env=None, data=None):
    return subprocess.check_output(
        ["git", "-C", str(project), *args], env=env, input=data
    )


@contextlib.contextmanager
def index(project, base):
    with tempfile.TemporaryDirectory(prefix="athens-index-") as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        git(project, "read-tree", base, env=env)
        yield env


def patch_paths(project, patch):
    if not patch.strip():
        return set()
    output = git(project, "apply", "--numstat", "-z", data=patch)
    return {entry.split(b"\t", 2)[2].decode() for entry in output.split(b"\0") if entry}


def expected_tree(project, base, patch):
    with index(project, base) as env:
        if patch.strip():
            git(
                project, "apply", "--cached", "--whitespace=nowarn", env=env, data=patch
            )
        return git(project, "write-tree", env=env).decode().strip()


def working_tree(project, base, paths):
    with index(project, base) as env:
        git(project, "add", "-u", "--", ".", env=env)
        present = sorted(
            p for p in paths if (project / p).exists() or (project / p).is_symlink()
        )
        if present:
            git(project, "add", "--", *present, env=env)
        return git(project, "write-tree", env=env).decode().strip()


def check_base(project, entry):
    head = git(project, "rev-parse", "HEAD").decode().strip()
    if head != entry["base_commit"]:
        raise ValueError(f"{entry['project']}: HEAD differs from the pinned baseline")


def patch_plan(tree, entries, patch_root, saved):
    plan = []
    for entry in entries:
        project = tree / entry["project"]
        check_base(project, entry)
        new = (patch_root / entry["patch"]).read_bytes()
        previous = saved / entry["patch"]
        old = previous.read_bytes() if previous.exists() else new
        base = entry["base_commit"]
        desired = expected_tree(project, base, new)
        before = desired if old == new else expected_tree(project, base, old)
        paths = patch_paths(project, old) | patch_paths(project, new)
        actual = working_tree(project, base, paths)
        if actual == desired:
            delta = b""
        elif (
            actual == before
            or actual == git(project, "rev-parse", base + "^{tree}").decode().strip()
        ):
            delta = git(project, "diff", "--binary", "--full-index", actual, desired)
            if delta:
                git(project, "apply", "--check", data=delta)
        else:
            files = git(project, "diff", "--name-only", before, actual).decode().strip()
            raise ValueError(
                f"Unrecorded changes in {entry['project']}:\n{files}\n"
                f"Use workspace.py capture {entry['project']} after reviewing them."
            )
        plan.append((project, delta, previous, new))
    return plan


def source_files(repository):
    names = git(
        repository, "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    )
    return {
        n.decode()
        for n in names.split(b"\0")
        if n and os.path.lexists(repository / n.decode())
    }


def contents(path):
    if path.is_symlink():
        return ("link", os.readlink(path))
    if path.is_file():
        return ("file", path.stat().st_mode & 0o111, path.read_bytes())
    return None


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        target.unlink()
    if source.is_symlink():
        if target.exists():
            target.unlink()
        target.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, target)


def device_plan(source, target, baseline):
    names = source_files(source)
    previous = {
        str(p.relative_to(baseline))
        for p in baseline.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    extra = []
    for directory, directories, files in os.walk(target):
        directories[:] = [name for name in directories if name != ".git"]
        for name in files:
            relative = str((Path(directory) / name).relative_to(target))
            if relative not in names | previous and relative != ".git":
                extra.append(relative)
    if extra:
        result = subprocess.run(
            ["git", "-C", str(source), "check-ignore", "--no-index", "-z", "--stdin"],
            input=b"\0".join(name.encode() for name in extra) + b"\0",
            capture_output=True,
        )
        if result.returncode not in (0, 1):
            raise ValueError(result.stderr.decode())
        ignored = set(result.stdout.decode().split("\0"))
        unmanaged = sorted(set(extra) - ignored)
        if unmanaged:
            raise ValueError("Unrecorded device-tree files:\n" + "\n".join(unmanaged))
    plan = []
    for name in sorted(names | previous):
        desired = contents(source / name) if name in names else None
        current = contents(target / name)
        old = contents(baseline / name)
        if current != desired and current != old:
            raise ValueError(f"Unrecorded device-tree change: {target / name}")
        if current != desired:
            plan.append((name, name in names))
    return names, plan


def sync(config, check=False):
    tree, device = Path(config["tree"]), Path(config["device"])
    entries = json.loads((ROOT / "patches/series.json").read_text())
    patches = patch_plan(tree, entries, ROOT / "patches", LOCAL / "applied")
    target = tree / "device/xiaomi/athens"
    baseline = LOCAL / "device-base"
    names, changes = device_plan(device, target, baseline)
    print(
        f"Sync: {len(changes)} device files, {sum(bool(p[1]) for p in patches)} upstream projects"
    )
    if check:
        return
    for project, delta, saved, new in patches:
        if delta:
            git(project, "apply", "--whitespace=nowarn", data=delta)
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(new)
    for name, present in changes:
        if present:
            copy_file(device / name, target / name)
        else:
            (target / name).unlink(missing_ok=True)
    if baseline.exists():
        shutil.rmtree(baseline)
    for name in names:
        copy_file(device / name, baseline / name)


def capture(config, name, include):
    entries = json.loads((ROOT / "patches/series.json").read_text())
    entry = next((e for e in entries if e["project"] == name), None)
    if entry is None:
        raise ValueError(
            "Register this project and its pinned baseline in patches/series.json first"
        )
    project = Path(config["tree"]) / name
    check_base(project, entry)
    patch = ROOT / "patches" / entry["patch"]
    paths = patch_paths(project, patch.read_bytes()) | set(include)
    for path in paths:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError(f"Expected a project-relative file: {path}")
    actual = working_tree(project, entry["base_commit"], paths)
    data = git(
        project, "diff", "--binary", "--full-index", entry["base_commit"], actual
    )
    patch.write_bytes(data)
    print(f"Captured {name} -> {patch.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("configure")
    setup.add_argument("--tree", required=True, type=Path)
    setup.add_argument("--device", required=True, type=Path)
    setup.add_argument("--stock", type=Path)
    setup.add_argument("--sdk", type=Path)
    commands.add_parser("status")
    commands.add_parser("sync")
    export = commands.add_parser("capture")
    export.add_argument("project")
    export.add_argument(
        "--include",
        action="append",
        default=[],
        help="New project-relative source file",
    )
    build = commands.add_parser("build")
    build.add_argument("targets", nargs="*", default=["pixelos"])
    commands.add_parser("camera")
    commands.add_parser("vendor")
    args = parser.parse_args()
    if args.command == "configure":
        if not (args.tree / ".repo").is_dir():
            parser.error("--tree must be an existing repo checkout")
        git(args.device, "rev-parse", "--show-toplevel")
        config = {
            k: str(v.resolve()) for k, v in vars(args).items() if isinstance(v, Path)
        }
        path = LOCAL / "workspace.json"
        if path.exists() and json.loads(path.read_text()) != config:
            parser.error(
                "This repository already has a workspace; use a separate checkout for another tree"
            )
        LOCAL.mkdir(exist_ok=True)
        path.write_text(json.dumps(config, indent=2) + "\n")
        print(path)
        return
    config = json.loads((LOCAL / "workspace.json").read_text())
    if args.command == "capture":
        capture(config, args.project, args.include)
        return
    sync(config, check=args.command == "status")
    tree = Path(config["tree"])
    if args.command == "build":
        env = dict(os.environ, TREE=str(tree))
        subprocess.run(
            ["bash", str(ROOT / "tools/build.sh"), *(args.targets or ["pixelos"])],
            env=env,
            check=True,
        )
    elif args.command == "camera":
        security = tree / "build/make/target/product/security"
        subprocess.run(
            [
                "python3",
                str(ROOT / "tools/prepare-miui-camera.py"),
                "--tree",
                str(tree),
                "--stock-apk",
                str(
                    Path(config["stock"]) / "product/priv-app/MiuiCamera/MiuiCamera.apk"
                ),
                "--build-tools",
                str(Path(config["sdk"]) / "build-tools/37.0.0"),
                "--key",
                os.environ.get("KEY", str(security / "platform.pk8")),
                "--cert",
                os.environ.get("CERT", str(security / "platform.x509.pem")),
                "--output",
                str(tree / "device/xiaomi/athens/camera/MiuiCamera.apk"),
            ],
            check=True,
        )
    elif args.command == "vendor":
        subprocess.run(
            ["./extract-files.py", config["stock"]],
            cwd=tree / "device/xiaomi/athens",
            check=True,
        )


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        KeyError,
        FileNotFoundError,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(str(error)) from error
