from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rag_chunker.batch_cli import build_output_path, iter_markdown_files, main
from rag_chunker.pipeline import chunk_markdown_file


class BatchCliTest(unittest.TestCase):
    def test_batch_cli_writes_multiple_outputs_and_skips_non_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            input_dir = base / "samples"
            output_dir = base / "outputs"
            input_dir.mkdir()
            (input_dir / "alpha.md").write_text("# Alpha\n\n## A\n正文 A\n", encoding="utf-8")
            (input_dir / "beta.md").write_text("# Beta\n\n## B\n正文 B\n", encoding="utf-8")
            (input_dir / "notes.txt").write_text("skip me", encoding="utf-8")

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(input_dir), "--out-dir", str(output_dir)])

            self.assertEqual(exit_code, 0)
            alpha_output = output_dir / "samples" / "alpha.json"
            beta_output = output_dir / "samples" / "beta.json"
            self.assertTrue(alpha_output.exists())
            self.assertTrue(beta_output.exists())
            self.assertFalse((output_dir / "samples" / "notes.json").exists())

            alpha_payload = json.loads(alpha_output.read_text(encoding="utf-8"))
            self.assertEqual(alpha_payload["doc_id"], "alpha")
            self.assertIn("OK", stdout.getvalue())
            self.assertIn("成功: 2  失败: 0", stdout.getvalue())

    def test_batch_cli_creates_output_directory_for_empty_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            input_dir = base / "samples"
            output_dir = base / "outputs"
            input_dir.mkdir()

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(input_dir), "--out-dir", str(output_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_dir.exists())
            self.assertIn("成功: 0  失败: 0", stdout.getvalue())

    def test_batch_cli_continues_after_single_file_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            input_dir = base / "samples"
            output_dir = base / "outputs"
            input_dir.mkdir()
            (input_dir / "broken.md").write_text("# Broken\n\n## B\n正文 B\n", encoding="utf-8")
            (input_dir / "good.md").write_text("# Good\n\n## G\n正文 G\n", encoding="utf-8")

            def fake_chunk_markdown_file(input_path: Path) -> dict[str, object]:
                if input_path.name == "broken.md":
                    raise OSError("broken file")
                return chunk_markdown_file(input_path)

            stdout = StringIO()
            with patch("rag_chunker.batch_cli.chunk_markdown_file", side_effect=fake_chunk_markdown_file):
                with redirect_stdout(stdout):
                    exit_code = main([str(input_dir), "--out-dir", str(output_dir)])

            output = stdout.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("FAIL", output)
            self.assertIn("broken file", output)
            self.assertIn("OK", output)
            self.assertIn("成功: 1  失败: 1", output)
            self.assertFalse((output_dir / "samples" / "broken.json").exists())
            self.assertTrue((output_dir / "samples" / "good.json").exists())

    def test_batch_cli_reports_output_path_collision_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            input_dir = base / "samples"
            output_dir = base / "outputs"
            input_dir.mkdir()
            (input_dir / "same.markdown").write_text("# Markdown\n\n## A\n正文 A\n", encoding="utf-8")
            (input_dir / "same.md").write_text("# Md\n\n## B\n正文 B\n", encoding="utf-8")

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main([str(input_dir), "--out-dir", str(output_dir)])

            output = stdout.getvalue()
            output_path = output_dir / "samples" / "same.json"
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 1)
            self.assertIn("Output path collision", output)
            self.assertIn("成功: 1  失败: 1", output)
            self.assertEqual(payload["doc_title"], "Markdown")

    def test_batch_cli_rejects_missing_input_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            missing_dir = Path(temporary_dir) / "missing"
            output_dir = Path(temporary_dir) / "outputs"

            with redirect_stderr(StringIO()):
                exit_code = main([str(missing_dir), "--out-dir", str(output_dir)])

            self.assertEqual(exit_code, 2)

    def test_iter_markdown_files_returns_stable_supported_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_dir = Path(temporary_dir) / "samples"
            nested_dir = input_dir / "nested"
            nested_dir.mkdir(parents=True)
            (input_dir / "b.md").write_text("# B\n", encoding="utf-8")
            (input_dir / "a.markdown").write_text("# A\n", encoding="utf-8")
            (nested_dir / "c.md").write_text("# C\n", encoding="utf-8")
            (input_dir / "ignored.txt").write_text("ignored", encoding="utf-8")

            files = [path.relative_to(input_dir).as_posix() for path in iter_markdown_files(input_dir)]

            self.assertEqual(files, ["a.markdown", "b.md", "nested/c.md"])

    def test_build_output_path_preserves_input_root_name_and_relative_path(self) -> None:
        input_dir = Path("/repo/samples")
        input_path = Path("/repo/samples/nested/demo.md")
        output_dir = Path("/repo/outputs")

        output_path = build_output_path(input_path, input_dir, output_dir)

        self.assertEqual(output_path, Path("/repo/outputs/samples/nested/demo.json"))


if __name__ == "__main__":
    unittest.main()
