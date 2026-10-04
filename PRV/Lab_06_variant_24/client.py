"""GUI-клиент совместного документа."""

from __future__ import annotations

import json
import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable


class DocumentClient:
    """JSON-lines клиент с фоновым потоком приёма событий."""

    def __init__(self, host: str, port: int, callback: Callable[[dict[str, Any]], None]) -> None:
        """Создать клиент общего документа."""
        self.host, self.port, self.callback = host, port, callback
        self.sock: socket.socket | None = None
        self.version = 0
        self.role = "viewer"
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    def connect(self, username: str) -> None:
        """Подключиться и запросить начальное состояние."""
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.sock.settimeout(None)
        threading.Thread(target=self.listen, name="DocumentListener", daemon=True).start()
        self.send({"type": "hello", "username": username})

    def listen(self) -> None:
        """Читать серверные события и передавать их GUI callback."""
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
                        self.callback(json.loads(line))
        except (OSError, ConnectionError, json.JSONDecodeError) as exc:
            self.callback({"type": "error", "message": str(exc)})

    def send(self, payload: dict[str, Any]) -> None:
        """Отправить команду серверу."""
        if self.sock is None:
            raise RuntimeError("Клиент не подключён")
        with self.lock:
            self.sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))

    def close(self) -> None:
        """Остановить поток приёма и закрыть сокет."""
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()


class DocumentWindow:
    """Окно редактора с ACL, комментариями и статусом версии."""

    def __init__(self, root: tk.Tk, host: str, port: int, username: str) -> None:
        """Создать GUI и подключиться к серверу."""
        self.root = root
        self.root.title(f"Shared Document — {username}")
        self.root.geometry("1050x700")
        self.client = DocumentClient(host, port, lambda event: root.after(0, self.handle_event, event))
        self.version = 0
        self.role = "viewer"
        self.local_change = False
        self.build_ui()
        self.client.connect(username)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self) -> None:
        """Создать редактор, панель пользователей и комментарии."""
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.status = tk.StringVar(value="Подключение...")
        self.version_label = tk.StringVar(value="Версия: 0")
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)
        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x")
        self.save_button = ttk.Button(toolbar, text="Сохранить изменения", command=self.save_document)
        self.save_button.pack(side="left")
        ttk.Button(toolbar, text="Обновить", command=lambda: self.client.send({"type": "state"})).pack(side="left", padx=6)
        ttk.Label(toolbar, textvariable=self.version_label).pack(side="left")
        ttk.Label(toolbar, textvariable=self.status).pack(side="right")
        body = ttk.Frame(main)
        body.pack(fill="both", expand=True, pady=(8, 0))
        self.editor = tk.Text(body, wrap="word", undo=True, font=("Segoe UI", 11))
        self.editor.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(body, width=300)
        side.pack(side="right", fill="y", padx=(8, 0))
        users_frame = ttk.LabelFrame(side, text="Пользователи и права", padding=6)
        users_frame.pack(fill="x")
        self.users = tk.Listbox(users_frame, height=8)
        self.users.pack(fill="x")
        self.role_user = ttk.Entry(users_frame)
        self.role_user.pack(fill="x", pady=(6, 2))
        self.role_choice = ttk.Combobox(users_frame, values=["admin", "editor", "commenter", "viewer"], state="readonly")
        self.role_choice.set("viewer")
        self.role_choice.pack(fill="x")
        ttk.Button(users_frame, text="Назначить роль", command=self.set_role).pack(fill="x", pady=(4, 0))
        comments = ttk.LabelFrame(side, text="Комментарии", padding=6)
        comments.pack(fill="both", expand=True, pady=(8, 0))
        self.comment_list = tk.Listbox(comments, height=12)
        self.comment_list.pack(fill="both", expand=True)
        self.comment_text = ttk.Entry(comments)
        self.comment_text.pack(fill="x", pady=(6, 2))
        self.comment_line = ttk.Entry(comments)
        self.comment_line.insert(0, "1")
        self.comment_line.pack(fill="x")
        ttk.Button(comments, text="Добавить комментарий", command=self.add_comment).pack(fill="x", pady=(4, 0))

    def handle_event(self, event: dict[str, Any]) -> None:
        """Обновить интерфейс по событию сервера."""
        kind = event.get("type")
        if kind == "welcome":
            self.role = event["role"]
            self.apply_state(event)
            self.status.set(f"Подключено; роль: {self.role}")
        elif kind in {"state", "conflict"}:
            self.apply_state(event)
            if kind == "conflict":
                self.status.set("Конфликт версии: загружена актуальная редакция")
        elif kind == "document":
            self.version = int(event["version"])
            self.set_editor_content(event["content"])
            self.version_label.set(f"Версия: {self.version}; автор: {event.get('author', '')}")
        elif kind == "users":
            self.fill_users(event["users"])
        elif kind == "comment":
            self.comment_list.insert(tk.END, f"#{event['comment']['id']} {event['comment']['author']}: {event['comment']['text']}")
        elif kind == "role":
            self.status.set(f"Роль {event['username']}: {event['role']}")
        elif kind == "presence":
            self.status.set(event["message"])
        elif kind == "error":
            self.status.set(event.get("message", "Ошибка"))
            messagebox.showwarning("Сервер", event.get("message", "Ошибка"))

    def apply_state(self, state: dict[str, Any]) -> None:
        """Применить полное состояние документа."""
        self.version = int(state.get("version", 0))
        self.set_editor_content(state.get("content", ""))
        self.version_label.set(f"Версия: {self.version}")
        self.comment_list.delete(0, tk.END)
        for comment in state.get("comments", []):
            self.comment_list.insert(tk.END, f"#{comment['id']} {comment['author']}: {comment['text']}")
        self.fill_users(state.get("users", []))
        self.update_permissions()

    def set_editor_content(self, content: str) -> None:
        """Безопасно заменить текст редактора серверной версией."""
        self.editor.configure(state="normal")
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.update_permissions()

    def fill_users(self, users: list[dict[str, Any]]) -> None:
        """Показать пользователей и роли."""
        self.users.delete(0, tk.END)
        for user in users:
            self.users.insert(tk.END, f"{user['username']} — {user['role']}")

    def update_permissions(self) -> None:
        """Заблокировать редактор для viewer/commenter."""
        editable = self.role in {"admin", "editor"}
        self.editor.configure(state="normal" if editable else "disabled")
        self.save_button.configure(state="normal" if editable else "disabled")

    def save_document(self) -> None:
        """Отправить полную редакцию документа с optimistic version check."""
        content = self.editor.get("1.0", "end-1c")
        self.client.send({"type": "edit", "content": content, "base_version": self.version})

    def add_comment(self) -> None:
        """Отправить комментарий к строке документа."""
        text = self.comment_text.get().strip()
        if not text:
            return
        try:
            line = max(1, int(self.comment_line.get()))
        except ValueError:
            messagebox.showwarning("Комментарий", "Строка должна быть числом")
            return
        self.client.send({"type": "comment", "line": line, "text": text})
        self.comment_text.delete(0, tk.END)

    def set_role(self) -> None:
        """Отправить admin-команду назначения роли."""
        self.client.send({"type": "set_role", "username": self.role_user.get().strip(), "role": self.role_choice.get()})

    def close(self) -> None:
        """Закрыть соединение и окно."""
        self.client.close()
        self.root.destroy()


def run_gui(host: str, port: int, username: str | None) -> None:
    """Запустить приложение клиента."""
    root = tk.Tk()
    username = username or simpledialog.askstring("Shared Document", "Имя пользователя", parent=root)
    if username:
        DocumentWindow(root, host, port, username)
        root.mainloop()
    else:
        root.destroy()
