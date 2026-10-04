"""Автоматический smoke-test сетевого протокола GeoChat без GUI."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from pathlib import Path

from server import ChatServer


class TestClient:
    """Минимальный JSON-lines клиент для интеграционного теста."""

    def __init__(self, host: str, port: int, username: str) -> None:
        """Подключиться к серверу и зарегистрировать пользователя."""
        self.sock = socket.create_connection((host, port), timeout=3)
        self.sock.settimeout(3)
        self.events: list[dict] = []
        self.lock = threading.Lock()
        self.sock.sendall((json.dumps({"type": "hello", "username": username}) + "\n").encode())

    def receive_until(self, event_type: str, timeout: float = 3.0) -> dict:
        """Прочитать события до получения нужного типа."""
        deadline = time.monotonic() + timeout
        buffer = ""
        while time.monotonic() < deadline:
            self.sock.settimeout(max(0.1, deadline - time.monotonic()))
            data = self.sock.recv(4096)
            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                event = json.loads(line)
                self.events.append(event)
                if event.get("type") == event_type:
                    return event
        raise AssertionError(f"Не получено событие {event_type}: {self.events}")

    def send(self, payload: dict) -> None:
        """Отправить JSON-команду."""
        self.sock.sendall((json.dumps(payload) + "\n").encode())

    def close(self) -> None:
        """Закрыть тестовый сокет."""
        self.sock.close()


def main() -> None:
    """Запустить сервер и проверить hello, chat, location и nearby."""
    logging.basicConfig(level=logging.WARNING)
    server = ChatServer("127.0.0.1", 0, logging.getLogger("test"))
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    assert server.ready_event.wait(3)
    alice = TestClient("127.0.0.1", server.port, "Alice")
    bob = TestClient("127.0.0.1", server.port, "Bob")
    assert alice.receive_until("welcome")["username"] == "Alice"
    assert bob.receive_until("welcome")["username"] == "Bob"
    alice.send({"type": "location", "latitude": 55.7558, "longitude": 37.6173, "label": "Москва"})
    bob.send({"type": "location", "latitude": 55.7600, "longitude": 37.6200, "label": "Рядом"})
    alice.receive_until("location")
    bob.receive_until("location")
    alice.send({"type": "chat", "text": "Проверка геочата"})
    assert bob.receive_until("chat")["text"] == "Проверка геочата"
    alice.send({"type": "nearby", "latitude": 55.7558, "longitude": 37.6173, "radius_km": 5})
    nearby = alice.receive_until("nearby")
    assert {item["username"] for item in nearby["users"]} == {"Alice", "Bob"}
    alice.close()
    bob.close()
    server.stop()
    thread.join(timeout=2)
    print("integration_test: OK")


if __name__ == "__main__":
    main()
