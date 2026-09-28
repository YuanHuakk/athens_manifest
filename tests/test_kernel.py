# SPDX-License-Identifier: Apache-2.0
"""Check concatenated DTB boundaries and ordering."""

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "prepare_kernel", Path(__file__).resolve().parents[1] / "tools/prepare-kernel.py"
)
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)


class DtbTest(unittest.TestCase):
    def test_preserves_fdt_order_and_contents(self):
        first = struct.pack(">II", 0xD00DFEED, 44) + bytes(32) + b"tree"
        second = struct.pack(">II", 0xD00DFEED, 48) + bytes(32) + b"nexttree"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dtb"
            self.assertEqual(kernel.split_dtb(first + second, output), 2)
            self.assertEqual((output / "raw01.dtb").read_bytes(), first)
            self.assertEqual((output / "raw02.dtb").read_bytes(), second)

    def test_rejects_truncated_tree(self):
        data = struct.pack(">II", 0xD00DFEED, 80) + bytes(32)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Invalid FDT"):
                kernel.split_dtb(data, Path(temporary) / "dtb")


if __name__ == "__main__":
    unittest.main()
