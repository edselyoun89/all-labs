"""Сервер общего документа с ролями и комментариями."""

from __future__ import annotations

import json
import logging
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


ROLES = {"admin", "editor", "commenter", "viewer"}


def timestamp() -> str:
    """Вернуть UTC timestamp для событий документа."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def send_json(sock: socket.socket, payload: dict[str, Any], lock: threading.Lock) -> None:
    """Атомарно отправить JSON Lines-сообщение."""
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with lock:
        sock.sendall(data)


@dataclass
class Session:
    """Состояние подключённого клиента."""

    username: str
    sock: socket.socket
    send_lock: threading.Lock
    role: str


class SharedDocumentServer:
    """Потоковый TCP-сервер совместного редактирования документа."""

    def __init__(self, host: str = "127.0.0.1", port: int = 12346, logger: logging.Logger | None = None) -> None:
        """Создать сервер с пустым документом и ACL."""
        self.host, self.port = host, port
        self.logger = logger or logging.getLogger("shared_document.server")
        self.document = ""
        self.version = 0
        self.comments: list[dict[str, Any]] = []
        self.sessions: dict[str, Session] = {}
        self.roles: dict[str, str] = {}
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.server_socket: socket.socket | None = None

    def start(self) -> None:
        """Запустить сервер и принимать клиентов."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(32)
        self.port = int(self.server_socket.getsockname()[1])
        self.ready_event.set()
        self.logger.info("SharedDocumentServer запущен на %s:%s", self.host, self.port)
        while not self.stop_event.is_set():
            try:
                self.server_socket.settimeout(0.5)
                sock, address = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self.handle_client, args=(sock, address), name=f"DocumentClient-{address[1]}", daemon=True).start()

    def stop(self) -> None:
        """Остановить сервер и закрыть клиентские соединения."""
        self.stop_event.set()
        if self.server_socket:
            self.server_socket.close()
        with self.lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for session in sessions:
            try:
                session.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            session.sock.close()

    def handle_client(self, sock: socket.socket, _address: tuple[str, int]) -> None:
        """Обрабатывать команды клиента в отдельном потоке."""
        username: str | None = None
        buffer = ""
        try:
            while username is None:
                data = sock.recv(4096)
                if not data:
                    return
                buffer += data.decode("utf-8")
                if "\n" not in buffer:
                    continue
                line, buffer = buffer.split("\n", 1)
                username = self.register(json.loads(line), sock)
                if username is None:
                    return
            while not self.stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.handle_message(username, json.loads(line))
        except (OSError, ConnectionError, json.JSONDecodeError) as exc:
            self.logger.warning("Ошибка клиента %s: %s", username or "unknown", exc)
        finally:
            if username:
                self.unregister(username)
            sock.close()

    def register(self, request: dict[str, Any], sock: socket.socket) -> str | None:
        """Зарегистрировать клиента и назначить первую роль admin."""
        username = str(request.get("username", "")).strip()
        if not 1 <= len(username) <= 24 or "\n" in username:
            send_json(sock, {"type": "error", "message": "Некорректное имя"}, threading.Lock())
            return None
        with self.lock:
            if username in self.sessions:
                send_json(sock, {"type": "error", "message": "Имя уже занято"}, threading.Lock())
                return None
            role = "admin" if not self.roles else self.roles.get(username, "viewer")
            self.roles[username] = role
            session = Session(username, sock, threading.Lock(), role)
            self.sessions[username] = session
            state = self.state()
        send_json(sock, {"type": "welcome", "username": username, "role": role, **state}, session.send_lock)
        self.broadcast({"type": "presence", "message": f"{username} подключился", "timestamp": timestamp()})
        self.broadcast_state()
        return username

    def unregister(self, username: str) -> None:
        """Удалить клиента, сохранив его назначенную роль."""
        with self.lock:
            self.sessions.pop(username, None)
        self.broadcast({"type": "presence", "message": f"{username} отключился", "timestamp": timestamp()})
        self.broadcast_state()

    def handle_message(self, username: str, message: dict[str, Any]) -> None:
        """Обработать edit, comment, set_role или state."""
        kind = message.get("type")
        if kind == "edit":
            self.edit(username, message)
        elif kind == "comment":
            self.comment(username, message)
        elif kind == "set_role":
            self.set_role(username, message)
        elif kind == "state":
            self.send_to(username, {"type": "state", **self.state()})

    def edit(self, username: str, message: dict[str, Any]) -> None:
        """Принять полную версию документа при совпадении version."""
        with self.lock:
            role = self.roles.get(username, "viewer")
            if role not in {"admin", "editor"}:
                self.send_to(username, {"type": "error", "message": "У вас нет прав на редактирование"})
                return
            if int(message.get("base_version", -1)) != self.version:
                self.send_to(username, {"type": "conflict", **self.state()})
                return
            content = str(message.get("content", ""))
            if len(content) > 1_000_000:
                self.send_to(username, {"type": "error", "message": "Документ слишком большой"})
                return
            self.document = content
            self.version += 1
            event = {"type": "document", "content": self.document, "version": self.version, "author": username, "timestamp": timestamp()}
        self.broadcast(event)

    def comment(self, username: str, message: dict[str, Any]) -> None:
        """Добавить комментарий пользователю с подходящей ролью."""
        with self.lock:
            if self.roles.get(username) not in {"admin", "editor", "commenter"}:
                self.send_to(username, {"type": "error", "message": "У вас нет прав на комментарии"})
                return
            text = str(message.get("text", "")).strip()
            if not text:
                return
            item = {"id": len(self.comments) + 1, "author": username, "line": int(message.get("line", 1)), "text": text[:500], "timestamp": timestamp()}
            self.comments.append(item)
        self.broadcast({"type": "comment", "comment": item})

    def set_role(self, username: str, message: dict[str, Any]) -> None:
        """Изменить роль пользователя только по команде администратора."""
        target, role = str(message.get("username", "")), str(message.get("role", ""))
        with self.lock:
            if self.roles.get(username) != "admin":
                self.send_to(username, {"type": "error", "message": "Только admin может менять права"})
                return
            if target not in self.roles or role not in ROLES or target == username:
                self.send_to(username, {"type": "error", "message": "Некорректная цель или роль"})
                return
            self.roles[target] = role
            if target in self.sessions:
                self.sessions[target].role = role
        self.broadcast({"type": "role", "username": target, "role": role})
        self.broadcast_state()

    def state(self) -> dict[str, Any]:
        """Сформировать согласованное состояние документа и ACL."""
        with self.lock:
            return {"content": self.document, "version": self.version, "comments": list(self.comments), "users": [{"username": name, "role": role} for name, role in self.roles.items()]}

    def broadcast_state(self) -> None:
        """Разослать состояние ACL и активных пользователей."""
        self.broadcast({"type": "users", "users": self.state()["users"]})

    def send_to(self, username: str, payload: dict[str, Any]) -> None:
        """Отправить событие одному пользователю."""
        with self.lock:
            session = self.sessions.get(username)
        if session:
            try:
                send_json(session.sock, payload, session.send_lock)
            except OSError:
                self.unregister(username)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Разослать событие всем активным клиентам."""
        with self.lock:
            sessions = list(self.sessions.values())
        for session in sessions:
            try:
                send_json(session.sock, payload, session.send_lock)
            except OSError:
                self.unregister(session.username)
