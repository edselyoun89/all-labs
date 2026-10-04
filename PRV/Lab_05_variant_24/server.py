"""TCP-сервер геолокационного чата, вариант 24."""

from __future__ import annotations

import json
import logging
import math
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_timestamp() -> str:
    """Вернуть текущее UTC-время в ISO-формате."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def send_json(sock: socket.socket, payload: dict[str, Any], lock: threading.Lock | None = None) -> None:
    """Отправить одну JSON-строку через TCP-сокет."""
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    if lock is None:
        sock.sendall(data)
    else:
        with lock:
            sock.sendall(data)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычислить расстояние между координатами по формуле гаверсинуса."""
    radius = 6371.0088
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    value = math.sin(d_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(value))


@dataclass
class ClientSession:
    """Состояние подключённого пользователя."""

    username: str
    sock: socket.socket
    address: tuple[str, int]
    send_lock: threading.Lock
    latitude: float | None = None
    longitude: float | None = None
    label: str = ""


class ChatServer:
    """Многопользовательский сервер геолокационного чата."""

    def __init__(self, host: str = "127.0.0.1", port: int = 12345, logger: logging.Logger | None = None) -> None:
        """Создать сервер с адресом и портом прослушивания."""
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger("geo_chat.server")
        self.clients: dict[str, ClientSession] = {}
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.server_socket: socket.socket | None = None

    def start(self) -> None:
        """Запустить accept-loop и потоки обработки клиентов."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(32)
        self.port = int(self.server_socket.getsockname()[1])
        self.ready_event.set()
        self.logger.info("Сервер запущен на %s:%s", self.host, self.port)
        while not self.stop_event.is_set():
            try:
                self.server_socket.settimeout(0.5)
                client_socket, address = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            thread = threading.Thread(target=self.handle_client, args=(client_socket, address), name=f"Client-{address[0]}:{address[1]}", daemon=True)
            thread.start()

    def stop(self) -> None:
        """Остановить сервер и закрыть все клиентские соединения."""
        self.stop_event.set()
        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass
        with self.lock:
            sessions = list(self.clients.values())
            self.clients.clear()
        for session in sessions:
            try:
                session.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            session.sock.close()
        self.logger.info("Сервер остановлен")

    def handle_client(self, client_socket: socket.socket, address: tuple[str, int]) -> None:
        """Обработать JSON-команды одного клиента в отдельном потоке."""
        username: str | None = None
        buffer = ""
        try:
            client_socket.settimeout(30.0)
            while username is None:
                data = client_socket.recv(4096)
                if not data:
                    return
                buffer += data.decode("utf-8")
                if "\n" not in buffer:
                    continue
                line, buffer = buffer.split("\n", 1)
                request = json.loads(line)
                username = self._register(request, client_socket, address)
                if username is None:
                    return
            client_socket.settimeout(None)
            while not self.stop_event.is_set():
                data = client_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._handle_message(username, json.loads(line))
        except (ConnectionError, OSError, json.JSONDecodeError) as exc:
            self.logger.warning("Соединение %s завершено: %s", address, exc)
        finally:
            if username is not None:
                self._unregister(username)
            client_socket.close()

    def _register(self, request: dict[str, Any], sock: socket.socket, address: tuple[str, int]) -> str | None:
        """Зарегистрировать пользователя после hello-команды."""
        username = str(request.get("username", "")).strip()
        if not 1 <= len(username) <= 24 or "\n" in username:
            send_json(sock, {"type": "error", "message": "Имя пользователя должно содержать 1–24 символа"})
            return None
        with self.lock:
            if username in self.clients:
                send_json(sock, {"type": "error", "message": "Это имя уже занято"})
                return None
            self.clients[username] = ClientSession(username, sock, address, threading.Lock())
        send_json(sock, {"type": "welcome", "username": username}, self.clients[username].send_lock)
        self.broadcast({"type": "system", "message": f"{username} подключился", "timestamp": utc_timestamp()})
        self.broadcast_users()
        self.logger.info("Подключён пользователь %s", username)
        return username

    def _unregister(self, username: str) -> None:
        """Удалить пользователя и уведомить остальных."""
        with self.lock:
            session = self.clients.pop(username, None)
        if session is not None:
            self.broadcast({"type": "system", "message": f"{username} отключился", "timestamp": utc_timestamp()})
            self.broadcast_users()
            self.logger.info("Отключён пользователь %s", username)

    def _handle_message(self, username: str, message: dict[str, Any]) -> None:
        """Маршрутизировать чат-команду, координаты или запрос nearby."""
        message_type = message.get("type")
        if message_type == "chat":
            text = str(message.get("text", "")).strip()
            if text:
                self.broadcast({"type": "chat", "username": username, "text": text, "timestamp": utc_timestamp()})
        elif message_type == "location":
            try:
                latitude = float(message["latitude"])
                longitude = float(message["longitude"])
                if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                self.send_to(username, {"type": "error", "message": "Некорректные координаты"})
                return
            with self.lock:
                session = self.clients.get(username)
                if session:
                    session.latitude, session.longitude = latitude, longitude
                    session.label = str(message.get("label", ""))[:80]
            self.broadcast({"type": "location", "username": username, "latitude": latitude, "longitude": longitude, "label": message.get("label", ""), "timestamp": utc_timestamp()})
            self.broadcast_users()
        elif message_type == "users":
            self.send_to(username, {"type": "users", "users": self.user_list()})
        elif message_type == "nearby":
            self._send_nearby(username, message)

    def _send_nearby(self, username: str, message: dict[str, Any]) -> None:
        """Найти пользователей в радиусе от заданной точки."""
        try:
            latitude = float(message["latitude"])
            longitude = float(message["longitude"])
            radius = max(0.0, min(float(message.get("radius_km", 50)), 20_000.0))
        except (KeyError, TypeError, ValueError):
            self.send_to(username, {"type": "error", "message": "Некорректный радиус или координаты"})
            return
        nearby = []
        with self.lock:
            sessions = list(self.clients.values())
        for session in sessions:
            if session.latitude is None or session.longitude is None:
                continue
            distance = haversine_km(latitude, longitude, session.latitude, session.longitude)
            if distance <= radius:
                nearby.append({"username": session.username, "latitude": session.latitude, "longitude": session.longitude, "label": session.label, "distance_km": round(distance, 3)})
        nearby.sort(key=lambda item: item["distance_km"])
        self.send_to(username, {"type": "nearby", "users": nearby})

    def user_list(self) -> list[dict[str, Any]]:
        """Получить безопасный список активных пользователей и координат."""
        with self.lock:
            return [{"username": session.username, "latitude": session.latitude, "longitude": session.longitude, "label": session.label} for session in self.clients.values()]

    def broadcast_users(self) -> None:
        """Разослать текущий список пользователей всем клиентам."""
        self.broadcast({"type": "users", "users": self.user_list()})

    def send_to(self, username: str, payload: dict[str, Any]) -> None:
        """Отправить сообщение конкретному пользователю."""
        with self.lock:
            session = self.clients.get(username)
        if session:
            try:
                send_json(session.sock, payload, session.send_lock)
            except OSError:
                self._unregister(username)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Разослать JSON-событие всем подключённым клиентам."""
        with self.lock:
            sessions = list(self.clients.values())
        for session in sessions:
            try:
                send_json(session.sock, payload, session.send_lock)
            except OSError:
                self._unregister(session.username)


def create_logger() -> logging.Logger:
    """Создать консольный logger для standalone-сервера."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    return logging.getLogger("geo_chat.server")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TCP-сервер геолокационного чата")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12345)
    args = parser.parse_args()
    server = ChatServer(args.host, args.port, create_logger())
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
