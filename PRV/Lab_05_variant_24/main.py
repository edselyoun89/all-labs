"""Точка входа для запуска сервера или GUI-клиента геочата."""

from __future__ import annotations

import argparse
import logging

from client import run_gui
from server import ChatServer


def main() -> None:
    """Разобрать режим запуска и запустить сервер либо клиент."""
    parser = argparse.ArgumentParser(description="GeoChat, лабораторная работа 5, вариант 24")
    parser.add_argument("mode", choices=["server", "client"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--username", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    if args.mode == "server":
        server = ChatServer(args.host, args.port, logging.getLogger("geo_chat.server"))
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
    else:
        run_gui(args.host, args.port, args.username)


if __name__ == "__main__":
    main()
