#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extract the athens OS3.0.306.0 fastboot package for blob extraction."""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PARTITIONS = (
    "system",
    "system_ext",
    "product",
    "vendor",
    "odm",
    "vendor_dlkm",
    "system_dlkm",
    "mi_ext",
)


def prepare_stock(tree: Path, images: Path, output: Path) -> None:
    # Use the parser version already pinned by the ROM manifest.
    sys.path.insert(0, str(tree / "tools/extract-utils"))
    from extract_utils.lp import LpImage
    from extract_utils.sparse_img import SPARSE_HEADER_MAGIC, unsparse_images

    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix=".stock-", dir=output.parent) as temporary:
        work = Path(temporary)
        source = images / "super.img"
        with source.open("rb") as stream:
            sparse = int.from_bytes(stream.read(4), "little") == SPARSE_HEADER_MAGIC
        if sparse:
            source = work / "super.raw.img"
            unsparse_images([str(images / "super.img")], str(source))
        with source.open("rb") as stream:
            super_image = LpImage(stream)
            for name in PARTITIONS:
                print(f"Extracting {name}", flush=True)
                image = work / f"{name}.img"
                super_image.extract_partition(name, str(image), slot=0)
                filesystem = work / name
                subprocess.run(
                    [
                        "fsck.erofs",
                        f"--extract={filesystem}",
                        "--no-preserve",
                        str(image),
                    ],
                    check=True,
                )
                # The stock system image uses system-as-root; extract-utils expects
                # system/build.prop, not system/system/build.prop.
                content = filesystem / "system" if name == "system" else filesystem
                shutil.move(str(content), output / name)
                image.unlink()

    vendor_props = (output / "vendor/build.prop").read_text()
    if "OS3.0.306.0.WPICNXM" not in vendor_props:
        raise ValueError("Expected athens OS3.0.306.0.WPICNXM vendor")
    odm_props = (output / "odm/etc/build.prop").read_text()
    if "ro.product.odm.device=athens" not in odm_props:
        raise ValueError("Expected athens ODM")
    print(f"Stock dump: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New dump directory")
    args = parser.parse_args()
    prepare_stock(args.tree.resolve(), args.images.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
