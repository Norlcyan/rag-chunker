from __future__ import annotations

import unittest


try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError):
    TestClient = None
    app = None
else:
    from rag_chunker.server import app


@unittest.skipIf(TestClient is None, "FastAPI dependencies are not installed.")
class ServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_chunk_endpoint_returns_http_wrapped_chunk_json(self) -> None:
        response = self.client.post(
            "/v1/chunk",
            files={"file": ("demo.md", b"# Demo\n\n## Intro\nHello\n", "text/markdown")},
            data={"source_type": "markdown"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["doc_id"], "demo")
        self.assertEqual(payload["doc_title"], "Demo")
        self.assertEqual(payload["source_type"], "markdown")
        self.assertEqual(len(payload["chunks"]), 1)

    def test_chunk_endpoint_defaults_source_type_to_markdown(self) -> None:
        response = self.client.post(
            "/v1/chunk",
            files={"file": ("demo.md", b"# Demo\n\n## Intro\nHello\n", "text/markdown")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_chunk_endpoint_rejects_unsupported_source_type(self) -> None:
        response = self.client.post(
            "/v1/chunk",
            files={"file": ("demo.md", b"# Demo\n", "text/markdown")},
            data={"source_type": "pdf"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertIn("Unsupported source_type", payload["error"])

    def test_chunk_endpoint_rejects_non_markdown_file(self) -> None:
        response = self.client.post(
            "/v1/chunk",
            files={"file": ("demo.txt", b"# Demo\n", "text/plain")},
            data={"source_type": "markdown"},
        )

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertIn("Unsupported input type", payload["error"])


if __name__ == "__main__":
    unittest.main()
