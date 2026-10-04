"""Проверка парсинга HTML, экспорта и обработки недоступного сайта."""

from __future__ import annotations

import functools
import http.server
import logging
import sys
import tempfile
import threading
import time
from pathlib import Path

from parser import parse_with_error_logging, save_results

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Lab_06_variant_24"))
from parser import publish_to_shared_document
from server import SharedDocumentServer


def main() -> None:
    """Запустить локальный HTTP-сервер, выполнить парсинг и проверить ошибку."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "index.html").write_text("<html><head><title>Test Site</title></head><body><h1>News</h1><p>Important data</p><a href='/next'>Next page</a></body></html>", encoding="utf-8")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            data = parse_with_error_logging(f"http://127.0.0.1:{server.server_port}/index.html", keyword="data")
            assert data["title"] == "Test Site"
            assert data["paragraphs"] == ["Important data"]
            output = root / "results"
            paths = save_results(data, output)
            assert all(path.exists() for path in paths)
            project_output = Path(__file__).resolve().parent / "results"
            project_paths = save_results(data, project_output)
            assert all(path.exists() for path in project_paths)

            shared_server = SharedDocumentServer("127.0.0.1", 0, logging.getLogger("lr7.test"))
            shared_thread = threading.Thread(target=shared_server.start, daemon=True)
            shared_thread.start()
            assert shared_server.ready_event.wait(3)
            publish_to_shared_document(data, "127.0.0.1", shared_server.port, "Admin")
            time.sleep(0.1)
            shared_server.stop()
            shared_thread.join(timeout=2)
            assert "Test Site" in shared_server.document
        finally:
            server.shutdown()
            thread.join(timeout=2)
    try:
        parse_with_error_logging("http://127.0.0.1:1/unavailable", timeout=0.2)
    except RuntimeError as exc:
        assert "Не удалось обработать сайт" in str(exc)
    else:
        raise AssertionError("Недоступный сайт не вызвал ошибку")
    print("integration_test: OK")


if __name__ == "__main__":
    main()
