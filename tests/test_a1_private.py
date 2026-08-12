import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.a1_private import A1PrivateInputError, private_path, private_root


class A1PrivateInputTests(unittest.TestCase):
    def test_private_root_has_no_tracked_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(A1PrivateInputError, "A1_PRIVATE_DIR is required"):
                private_root()

    def test_private_path_requires_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"A1_PRIVATE_DIR": directory}):
                with self.assertRaisesRegex(A1PrivateInputError, "is missing"):
                    private_path("a1/review.csv")

    def test_private_path_resolves_inside_configured_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "a1/review.csv"
            target.parent.mkdir()
            target.write_text("synthetic", encoding="utf-8")
            with patch.dict(os.environ, {"A1_PRIVATE_DIR": directory}):
                self.assertEqual(target, private_path("a1/review.csv"))


if __name__ == "__main__":
    unittest.main()
