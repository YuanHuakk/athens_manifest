#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Copy the audited, Google-signed Pixel Tips APK into local build inputs."""

import argparse
import hashlib
import shutil
from pathlib import Path

# Pixel Tips 6.0.0.734377952 from BP4A.260205.001.
APK_SHA256 = "598cd06316951df2eef8c654984eb4d69b37b953da29fe11eaa7a3e717c5f4c5"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.apk.read_bytes()).hexdigest() != APK_SHA256:
        parser.error("Pixel Tips APK does not match the audited build")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.apk, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
