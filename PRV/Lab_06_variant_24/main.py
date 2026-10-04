"""Точка входа лабораторной работы №6."""

from __future__ import annotations

import argparse
import logging

from client import run_gui
from server import SharedDocumentServer


def main() -> None:
    """Запустить сервер или GUI-клиент общего документа."""
    parser = argparse.ArgumentParser(description="Shared Document, лабораторная работа 6")
    parser.add_argument("mode", choices=["server", "client"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12346)
    parser.add_argument("--username", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    if args.mode == "server":
        server = SharedDocumentServer(args.host, args.port, logging.getLogger("shared_document.server"))
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
    else:
        run_gui(args.host, args.port, args.username)


if __name__ == "__main__":
    main()
