#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare athens stock kernel inputs and the pinned UAPI bundle."""

import argparse
import gzip
import io
import json
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

KERNEL_RELEASE = "6.12.69-android16-6-g0d80ee00f747-ab15461283-4k"
HEADER_MAKEFILE = b"""VERSION = 6
PATCHLEVEL = 12

headers_install:
\t@mkdir -p $(O)/usr/include
\t@rsync -mrq $(shell pwd)/* $(O)/usr/include

all:
\t@true
"""


def split_dtb(data: bytes, output: Path) -> int:
    output.mkdir()
    offset = 0
    count = 0
    while offset < len(data):
        if len(data) - offset < 40:
            raise ValueError(f"Truncated FDT header at {offset}")
        magic, size = struct.unpack_from(">II", data, offset)
        if magic != 0xD00DFEED or size < 40 or offset + size > len(data):
            raise ValueError(f"Invalid FDT at {offset}")
        count += 1
        (output / f"raw{count:02d}.dtb").write_bytes(data[offset : offset + size])
        offset += size
    return count


def fetch_uapi_sources(cache: Path, lock: Path) -> None:
    for name, entry in json.loads(lock.read_text()).items():
        destination = cache / name
        if not destination.exists():
            destination.mkdir(parents=True)
            commands = [
                ["init", "--quiet"],
                ["remote", "add", "origin", entry["url"]],
                ["sparse-checkout", "init", "--cone"],
                ["sparse-checkout", "set", *entry["paths"]],
                [
                    "fetch",
                    "--depth=1",
                    "--filter=blob:none",
                    "origin",
                    entry["revision"],
                ],
                ["checkout", "--detach", "FETCH_HEAD"],
            ]
            for command in commands:
                subprocess.run(["git", "-C", str(destination), *command], check=True)
        revision = subprocess.check_output(
            ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != entry["revision"]:
            raise ValueError(f"Wrong UAPI source revision: {name}")
        subprocess.run(
            [
                "git",
                "-C",
                str(destination),
                "diff",
                "--exit-code",
                "HEAD",
                "--",
                *entry["paths"],
            ],
            check=True,
        )


def write_headers(cache: Path, output: Path) -> int:
    files = {}
    inputs = (
        (cache / "gki/include/uapi", ""),
        (cache / "gki/arch/arm64/include/uapi/asm", "asm/"),
        (cache / "qti/include/uapi", ""),
    )
    # Preserve the UAPI composition used by r12, including QTI overrides.
    # This is a source-header bundle, not a make headers_install export.
    for source, prefix in inputs:
        for path in source.rglob("*"):
            if path.is_file() and path.name not in ("Kbuild", "Makefile"):
                files[prefix + path.relative_to(source).as_posix()] = path.read_bytes()
    files["Makefile"] = HEADER_MAKEFILE
    with output.open("wb") as stream:
        with gzip.GzipFile(
            fileobj=stream, mode="wb", filename="", mtime=0
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name, data in sorted(files.items()):
                    info = tarfile.TarInfo(f"usr/include/{name}")
                    info.size = len(data)
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(data))
    return len(files)


def prepare_kernel(
    tree: Path, images: Path, stock: Path, cache: Path, output: Path
) -> None:
    lock = Path(__file__).resolve().parents[1] / "uapi-sources.json"
    fetch_uapi_sources(cache, lock)
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="athens-kernel-") as temporary:
        work = Path(temporary)
        for name in ("boot", "vendor_boot"):
            subprocess.run(
                [
                    sys.executable,
                    str(tree / "system/tools/mkbootimg/unpack_bootimg.py"),
                    "--boot_img",
                    str(images / f"{name}.img"),
                    "--out",
                    str(work / name),
                ],
                check=True,
            )
        kernel = work / "boot/kernel"
        if KERNEL_RELEASE.encode() not in kernel.read_bytes():
            raise ValueError("Kernel release does not match the athens device tree")
        shutil.copy2(kernel, output / "kernel")
        shutil.copy2(images / "dtbo.img", output / "dtbo.img")
        count = split_dtb((work / "vendor_boot/dtb").read_bytes(), output / "dtb")
        if count != 12:
            raise ValueError(f"Expected 12 stock DTBs, found {count}")

        ramdisk = work / "ramdisk"
        ramdisk.mkdir()
        for fragment in sorted((work / "vendor_boot").glob("vendor_ramdisk[0-9][0-9]")):
            cpio = work / "ramdisk.cpio"
            subprocess.run(["lz4", "-d", "-f", str(fragment), str(cpio)], check=True)
            with cpio.open("rb") as stream:
                subprocess.run(
                    [
                        "cpio",
                        "-idm",
                        "--no-absolute-filenames",
                        "--no-preserve-owner",
                        "lib/modules/*",
                    ],
                    stdin=stream,
                    cwd=ramdisk,
                    check=True,
                )
        inputs = {
            "vendor_ramdisk": ramdisk / "lib/modules",
            "vendor_dlkm": stock / "vendor_dlkm/lib/modules",
            "system_dlkm": stock / f"system_dlkm/lib/modules/{KERNEL_RELEASE}",
            "system_dlkm_flatten": stock / "system_dlkm/flatten/lib/modules",
        }
        for name, source in inputs.items():
            shutil.copytree(source, output / name, symlinks=True)
    headers = write_headers(cache, output / "kernel-headers.tar.gz")
    print(f"Kernel inputs: {output} ({count} DTBs, {headers} UAPI files)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tree", "images", "stock", "uapi-cache", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    prepare_kernel(
        args.tree.resolve(),
        args.images.resolve(),
        args.stock.resolve(),
        args.uapi_cache.resolve(),
        args.output.resolve(),
    )


if __name__ == "__main__":
    main()
