"""GUI-клиент геолокационного чата на Tkinter."""

from __future__ import annotations

import json
import queue
import socket
import threading
import urllib.parse
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable


class ChatClient:
    """Потокобезопасный JSON-lines TCP-клиент."""

    def __init__(self, host: str, port: int, on_message: Callable[[dict[str, Any]], None]) -> None:
        """Создать клиент с адресом сервера и callback входящих сообщений."""
        self.host, self.port = host, port
        self.on_message = on_message
        self.sock: socket.socket | None = None
        self.send_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.listener: threading.Thread | None = None

    def connect(self, username: str) -> None:
        """Подключиться к серверу и отправить hello."""
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.settimeout(None)
        self.listener = threading.Thread(target=self._listen, name="ChatListener", daemon=True)
        self.listener.start()
        self.send({"type": "hello", "username": username})

    def _listen(self) -> None:
        """Читать JSON-события сервера до закрытия соединения."""
        assert self.sock is not None
        buffer = ""
        try:
            while not self.stop_event.is_set():
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.on_message(json.loads(line))
        except (ConnectionError, OSError, json.JSONDecodeError) as exc:
            self.on_message({"type": "error", "message": f"Соединение закрыто: {exc}"})

    def send(self, payload: dict[str, Any]) -> None:
        """Отправить JSON-команду серверу."""
        if self.sock is None:
            raise RuntimeError("Клиент не подключён")
        data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        with self.send_lock:
            self.sock.sendall(data)

    def close(self) -> None:
        """Закрыть соединение и поток чтения."""
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()


class ChatWindow:
    """Графическое окно чата с картой и маркерами пользователей."""

    def __init__(self, root: tk.Tk, host: str, port: int, username: str) -> None:
        """Создать виджеты и подключить клиента."""
        self.root = root
        self.root.title(f"GeoChat — {username}")
        self.root.geometry("1100x700")
        self.client = ChatClient(host, port, lambda message: root.after(0, self.handle_message, message))
        self.users: list[dict[str, Any]] = []
        self._build_ui()
        try:
            self.client.connect(username)
            self.status.set(f"Подключено к {host}:{port}")
        except OSError as exc:
            messagebox.showerror("Ошибка подключения", str(exc))
            self.status.set("Не подключено")
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        """Собрать панели сообщений, пользователей, карты и управления."""
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.status = tk.StringVar(value="Подключение...")
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(main, width=280)
        right.pack(side="right", fill="y", padx=(8, 0))

        self.messages = tk.Text(left, state="disabled", wrap="word", height=25)
        self.messages.pack(fill="both", expand=True)
        compose = ttk.Frame(left)
        compose.pack(fill="x", pady=(8, 0))
        self.message_entry = ttk.Entry(compose)
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", lambda _event: self.send_chat())
        ttk.Button(compose, text="Отправить", command=self.send_chat).pack(side="right", padx=(8, 0))

        ttk.Label(right, text="Активные пользователи").pack(anchor="w")
        self.user_listbox = tk.Listbox(right, height=8)
        self.user_listbox.pack(fill="x", pady=(4, 8))
        coords = ttk.LabelFrame(right, text="Моё местоположение", padding=6)
        coords.pack(fill="x")
        self.latitude = ttk.Entry(coords)
        self.longitude = ttk.Entry(coords)
        self.label = ttk.Entry(coords)
        for title, widget in (("Широта", self.latitude), ("Долгота", self.longitude), ("Метка", self.label)):
            ttk.Label(coords, text=title).pack(anchor="w")
            widget.pack(fill="x", pady=(0, 4))
        ttk.Button(coords, text="Отправить координаты", command=self.send_location).pack(fill="x")
        ttk.Button(coords, text="Открыть OpenStreetMap", command=self.open_map).pack(fill="x", pady=(4, 0))
        ttk.Label(coords, text="Поиск адреса").pack(anchor="w", pady=(6, 0))
        self.address = ttk.Entry(coords)
        self.address.pack(fill="x")
        ttk.Button(coords, text="Найти адрес", command=self.search_address).pack(fill="x", pady=(4, 0))
        search = ttk.LabelFrame(right, text="Ближайшие пользователи", padding=6)
        search.pack(fill="x", pady=(8, 0))
        self.radius = ttk.Entry(search)
        self.radius.insert(0, "50")
        ttk.Label(search, text="Радиус, км").pack(anchor="w")
        self.radius.pack(fill="x")
        ttk.Button(search, text="Найти рядом", command=self.find_nearby).pack(fill="x", pady=(4, 0))
        ttk.Button(search, text="Обновить список", command=lambda: self.client.send({"type": "users"})).pack(fill="x", pady=(4, 0))
        self.map_canvas = tk.Canvas(right, height=220, background="#e8f1f7", highlightthickness=0)
        self.map_canvas.pack(fill="x", pady=(8, 0))
        ttk.Label(right, textvariable=self.status).pack(anchor="w", pady=(8, 0))

    def handle_message(self, message: dict[str, Any]) -> None:
        """Обработать серверное событие в GUI-потоке."""
        message_type = message.get("type")
        if message_type == "users":
            self.users = message.get("users", [])
            self.user_listbox.delete(0, tk.END)
            for user in self.users:
                marker = "📍" if user.get("latitude") is not None else "○"
                self.user_listbox.insert(tk.END, f"{marker} {user['username']}")
            self.draw_map()
        elif message_type == "chat":
            self.append_message(f"[{message.get('timestamp', '')}] {message['username']}: {message['text']}")
        elif message_type == "system":
            self.append_message(f"* {message['message']}")
        elif message_type == "location":
            self.append_message(f"📍 {message['username']} отправил координаты: {message['latitude']}, {message['longitude']}")
        elif message_type == "nearby":
            items = message.get("users", [])
            text = "Ближайшие: " + (", ".join(f"{item['username']} ({item['distance_km']} км)" for item in items) if items else "никого не найдено")
            self.append_message(text)
        elif message_type == "error":
            self.append_message(f"Ошибка: {message.get('message', '')}")
            self.status.set(message.get("message", "Ошибка"))

    def append_message(self, text: str) -> None:
        """Добавить строку в область сообщений."""
        self.messages.configure(state="normal")
        self.messages.insert(tk.END, text + "\n")
        self.messages.see(tk.END)
        self.messages.configure(state="disabled")

    def send_chat(self) -> None:
        """Отправить текстовое сообщение."""
        text = self.message_entry.get().strip()
        if text:
            self.client.send({"type": "chat", "text": text})
            self.message_entry.delete(0, tk.END)

    def send_location(self) -> None:
        """Проверить и отправить координаты текущего пользователя."""
        try:
            latitude, longitude = float(self.latitude.get()), float(self.longitude.get())
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Координаты", "Введите широту от -90 до 90 и долготу от -180 до 180")
            return
        self.client.send({"type": "location", "latitude": latitude, "longitude": longitude, "label": self.label.get()})

    def find_nearby(self) -> None:
        """Запросить пользователей в радиусе от своих координат."""
        try:
            latitude, longitude, radius = float(self.latitude.get()), float(self.longitude.get()), float(self.radius.get())
        except ValueError:
            messagebox.showwarning("Поиск", "Укажите корректные координаты и радиус")
            return
        self.client.send({"type": "nearby", "latitude": latitude, "longitude": longitude, "radius_km": radius})

    def draw_map(self) -> None:
        """Нарисовать схематичную карту мира с маркерами."""
        self.map_canvas.delete("all")
        width, height = max(self.map_canvas.winfo_width(), 260), 220
        self.map_canvas.create_text(width // 2, 12, text="Схематичная карта пользователей", fill="#29465b")
        self.map_canvas.create_line(8, height // 2, width - 8, height // 2, fill="#b3c9d6")
        self.map_canvas.create_line(width // 2, 24, width // 2, height - 8, fill="#b3c9d6")
        for user in self.users:
            if user.get("latitude") is None:
                continue
            x = 8 + (float(user["longitude"]) + 180) / 360 * (width - 16)
            y = height - 8 - (float(user["latitude"]) + 90) / 180 * (height - 32)
            self.map_canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#e34f4f", outline="white")
            self.map_canvas.create_text(x + 8, y, text=user["username"], anchor="w", fill="#22313a")

    def open_map(self) -> None:
        """Открыть координаты текущего пользователя в OpenStreetMap."""
        try:
            latitude, longitude = float(self.latitude.get()), float(self.longitude.get())
        except ValueError:
            messagebox.showwarning("Карта", "Сначала укажите координаты")
            return
        query = urllib.parse.urlencode({"mlat": latitude, "mlon": longitude})
        webbrowser.open(f"https://www.openstreetmap.org/?{query}#map=12/{latitude}/{longitude}")

    def search_address(self) -> None:
        """Найти адрес через публичный Nominatim API и заполнить координаты."""
        address = self.address.get().strip()
        if not address:
            messagebox.showwarning("Адрес", "Введите адрес для поиска")
            return
        try:
            query = urllib.parse.urlencode({"q": address, "format": "jsonv2", "limit": 1})
            request = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?{query}",
                headers={"User-Agent": "GeoChat-Lab5/1.0"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                results = json.loads(response.read().decode("utf-8"))
            if not results:
                raise ValueError("Адрес не найден")
            self.latitude.delete(0, tk.END)
            self.latitude.insert(0, results[0]["lat"])
            self.longitude.delete(0, tk.END)
            self.longitude.insert(0, results[0]["lon"])
            self.label.delete(0, tk.END)
            self.label.insert(0, results[0].get("display_name", address)[:80])
            self.status.set("Адрес найден; координаты заполнены")
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showwarning("Поиск адреса", str(exc))

    def close(self) -> None:
        """Закрыть клиент и окно."""
        self.client.close()
        self.root.destroy()


def run_gui(host: str, port: int, username: str | None = None) -> None:
    """Запустить GUI-клиент."""
    root = tk.Tk()
    username = username or simpledialog.askstring("GeoChat", "Имя пользователя:", parent=root)
    if not username:
        root.destroy()
        return
    ChatWindow(root, host, port, username)
    root.mainloop()
