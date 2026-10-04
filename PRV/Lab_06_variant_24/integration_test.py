"""Интеграционный тест ролей, редактирования, комментариев и конфликтов."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time

from server import SharedDocumentServer


class RawClient:
    """Минимальный клиент JSON Lines для тестирования сервера."""

    def __init__(self, host: str, port: int, username: str) -> None:
        """Подключиться и отправить hello."""
        self.sock = socket.create_connection((host, port), timeout=3)
        self.sock.sendall((json.dumps({"type": "hello", "username": username}) + "\n").encode())

    def send(self, payload: dict) -> None:
        """Отправить команду."""
        self.sock.sendall((json.dumps(payload) + "\n").encode())

    def receive(self, wanted: str, timeout: float = 3.0) -> dict:
        """Читать события до нужного типа."""
        self.sock.settimeout(timeout)
        buffer = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self.sock.recv(4096)
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                event = json.loads(line)
                if event.get("type") == wanted:
                    return event
        raise AssertionError(f"Событие {wanted} не получено")

    def close(self) -> None:
        """Закрыть сокет."""
        self.sock.close()


def main() -> None:
    """Проверить сценарий admin/editor/commenter/viewer."""
    server = SharedDocumentServer("127.0.0.1", 0, logging.getLogger("test"))
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    assert server.ready_event.wait(3)
    admin, editor, viewer = (RawClient("127.0.0.1", server.port, name) for name in ("Admin", "Editor", "Viewer"))
    assert admin.receive("welcome")["role"] == "admin"
    assert editor.receive("welcome")["role"] == "viewer"
    assert viewer.receive("welcome")["role"] == "viewer"
    admin.send({"type": "set_role", "username": "Editor", "role": "editor"})
    admin.send({"type": "set_role", "username": "Viewer", "role": "commenter"})
    time.sleep(0.1)
    editor.send({"type": "edit", "content": "Общий документ\nРедакция Editor", "base_version": 0})
    assert admin.receive("document")["version"] == 1
    viewer.send({"type": "edit", "content": "Запрещённая редакция", "base_version": 1})
    assert viewer.receive("error")["message"]
    viewer.send({"type": "comment", "line": 2, "text": "Проверить этот пункт"})
    assert admin.receive("comment")["comment"]["author"] == "Viewer"
    editor.send({"type": "edit", "content": "Версия A", "base_version": 1})
    assert admin.receive("document")["version"] == 2
    editor.send({"type": "edit", "content": "Устаревшая версия", "base_version": 1})
    assert editor.receive("conflict")["version"] == 2
    for client in (admin, editor, viewer):
        client.close()
    server.stop()
    thread.join(timeout=2)
    print("integration_test: OK")


if __name__ == "__main__":
    main()
