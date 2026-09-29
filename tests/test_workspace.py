# SPDX-License-Identifier: Apache-2.0
"""Development sync must retain local inputs and reject unrecorded edits."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "workspace", Path(__file__).resolve().parents[1] / "tools/workspace.py"
)
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.git("init", "-q")
        (self.project / ".gitignore").write_text("*.apk\n")
        (self.project / "code").write_text("base\n")
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "base",
        )
        self.base = self.git("rev-parse", "HEAD").decode().strip()

    def git(self, *args):
        return workspace.git(self.project, *args)

    def entry(self):
        return {
            "project": "project",
            "base_commit": self.base,
            "patch": "project.patch",
        }

    def patch(self, text):
        (self.project / "code").write_text(text)
        return self.git("diff", "--binary", "--full-index", self.base)

    def test_patch_upgrade_and_dirty_file_detection(self):
        patches = self.root / "patches"
        saved = self.root / "saved"
        patches.mkdir()
        saved.mkdir()
        old = self.patch("old\n")
        new = self.patch("new\n")
        (patches / "project.patch").write_bytes(new)
        (saved / "project.patch").write_bytes(old)
        (self.project / "code").write_text("old\n")
        index_before = (self.project / ".git/index").read_bytes()
        plan = workspace.patch_plan(self.root, [self.entry()], patches, saved)
        self.assertEqual(index_before, (self.project / ".git/index").read_bytes())
        self.assertEqual((self.project / "code").read_text(), "old\n")
        workspace.git(self.project, "apply", data=plan[0][1])
        self.assertEqual((self.project / "code").read_text(), "new\n")
        (self.project / "code").write_text("unrecorded\n")
        with self.assertRaisesRegex(ValueError, "Unrecorded changes"):
            workspace.patch_plan(self.root, [self.entry()], patches, saved)

    def test_new_source_export_does_not_stage_real_index(self):
        index_before = (self.project / ".git/index").read_bytes()
        (self.project / "new.cpp").write_text("new source\n")
        tree = workspace.working_tree(self.project, self.base, {"new.cpp"})
        patch = self.git("diff", "--binary", self.base, tree)
        self.assertIn(b"new.cpp", patch)
        self.assertEqual(index_before, (self.project / ".git/index").read_bytes())
        self.assertEqual(workspace.expected_tree(self.project, self.base, patch), tree)

    def test_device_deletion_preserves_apk_and_rejects_local_edits(self):
        target = self.root / "target"
        baseline = self.root / "baseline"
        for name in workspace.source_files(self.project):
            workspace.copy_file(self.project / name, target / name)
            workspace.copy_file(self.project / name, baseline / name)
        (target / "camera.apk").write_bytes(b"local proprietary input")
        (self.project / "code").unlink()
        _, changes = workspace.device_plan(self.project, target, baseline)
        self.assertEqual(changes, [("code", False)])
        self.assertEqual(
            (target / "camera.apk").read_bytes(), b"local proprietary input"
        )
        (target / "code").write_text("unrecorded\n")
        with self.assertRaisesRegex(ValueError, "Unrecorded device-tree change"):
            workspace.device_plan(self.project, target, baseline)
        (target / "new.cpp").write_text("forgotten source\n")
        with self.assertRaisesRegex(ValueError, "Unrecorded device-tree files"):
            workspace.device_plan(self.project, target, baseline)


if __name__ == "__main__":
    unittest.main()
