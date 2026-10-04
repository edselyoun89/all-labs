"""Парсер HTML и публикация результата в общий документ LR_6."""

from __future__ import annotations

import csv
import html
import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class SiteParser(HTMLParser):
    """Извлекает заголовок, headings, ссылки и текстовые блоки HTML."""

    def __init__(self) -> None:
        """Создать пустое состояние HTML-парсера."""
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.headings: list[str] = []
        self.links: list[dict[str, str]] = []
        self.paragraphs: list[str] = []
        self._tag_stack: list[str] = []
        self._buffer: list[str] = []
        self._link_href = ""
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Запомнить открывающий тег и атрибуты ссылки."""
        self._tag_stack.append(tag)
        if tag == "a":
            self._link_href = dict(attrs).get("href", "") or ""
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        """Сохранить накопленный текст соответствующего блока."""
        text = " ".join(" ".join(self._buffer).split())
        if tag == "title" and text:
            self.title = text
        elif tag in {"h1", "h2", "h3", "h4"} and text:
            self.headings.append(text)
        elif tag == "p" and text:
            self.paragraphs.append(text)
        elif tag == "a" and self._link_href:
            self.links.append({"text": " ".join(self._link_text).strip(), "href": self._link_href})
            self._link_href, self._link_text = "", []
        if tag in self._tag_stack:
            self._tag_stack.pop()
        self._buffer = []

    def handle_data(self, data: str) -> None:
        """Накопить текст текущего HTML-блока."""
        cleaned = " ".join(data.split())
        if cleaned:
            self._buffer.append(cleaned)
            if "a" in self._tag_stack:
                self._link_text.append(cleaned)


def fetch_html(url: str, timeout: float = 10.0) -> tuple[str, str]:
    """Загрузить HTML и вернуть текст с фактическим URL."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https", "file"}:
        raise ValueError("URL должен начинаться с http://, https:// или file://")
    request = urllib.request.Request(url, headers={"User-Agent": "Lab7SiteParser/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), response.geturl()


def parse_site(url: str, keyword: str = "", tag: str = "all", limit: int = 100, timeout: float = 10.0) -> dict[str, Any]:
    """Загрузить сайт и извлечь данные по keyword/tag/limit."""
    if limit <= 0:
        raise ValueError("limit должен быть положительным")
    source, final_url = fetch_html(url, timeout=timeout)
    parser = SiteParser()
    parser.feed(source)
    normalized = keyword.casefold().strip()
    headings = [item for item in parser.headings if not normalized or normalized in item.casefold()]
    paragraphs = [item for item in parser.paragraphs if not normalized or normalized in item.casefold()]
    links = [item for item in parser.links if not normalized or normalized in f"{item['text']} {item['href']}".casefold()]
    if tag == "headings":
        paragraphs, links = [], []
    elif tag == "paragraphs":
        headings, links = [], []
    elif tag == "links":
        headings, paragraphs = [], []
    elif tag != "all":
        raise ValueError("tag должен быть all, headings, paragraphs или links")
    return {
        "source_url": url,
        "final_url": final_url,
        "keyword": keyword,
        "title": parser.title,
        "headings": headings[:limit],
        "paragraphs": paragraphs[:limit],
        "links": links[:limit],
        "total_items": len(headings) + len(paragraphs) + len(links),
    }


def save_results(data: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    """Сохранить результат парсинга в JSON, CSV и HTML."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "parsed_data.json"
    csv_path = output_dir / "parsed_data.csv"
    html_path = output_dir / "parsed_data.html"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["type", "text", "href"])
        writer.writerow(["title", data["title"], ""])
        for item in data["headings"]:
            writer.writerow(["heading", item, ""])
        for item in data["paragraphs"]:
            writer.writerow(["paragraph", item, ""])
        for item in data["links"]:
            writer.writerow(["link", item["text"], item["href"]])
    rows = [f"<h1>{html.escape(data['title'])}</h1>"]
    rows.extend(f"<h2>{html.escape(item)}</h2>" for item in data["headings"])
    rows.extend(f"<p>{html.escape(item)}</p>" for item in data["paragraphs"])
    rows.extend(f'<p><a href="{html.escape(item["href"])}">{html.escape(item["text"] or item["href"])}</a></p>' for item in data["links"])
    html_path.write_text("<!doctype html><meta charset='utf-8'>" + "\n".join(rows), encoding="utf-8")
    return json_path, csv_path, html_path


def publish_to_shared_document(data: dict[str, Any], host: str, port: int, username: str, timeout: float = 5.0) -> None:
    """Опубликовать Markdown-представление в сервере LR_6."""
    content = [f"# Результат парсинга: {data['title']}", f"Источник: {data['final_url']}", ""]
    content.extend(f"## {item}" for item in data["headings"])
    content.extend(data["paragraphs"])
    content.extend(f"- [{item['text'] or item['href']}]({item['href']})" for item in data["links"])
    payload = (json.dumps({"type": "hello", "username": username}, ensure_ascii=False) + "\n").encode()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        sock.settimeout(timeout)
        buffer = ""
        welcome: dict[str, Any] | None = None
        while welcome is None:
            buffer += sock.recv(4096).decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                event = json.loads(line)
                if event.get("type") == "welcome":
                    welcome = event
                if event.get("type") == "error":
                    raise RuntimeError(event.get("message", "Ошибка shared document"))
        if welcome["role"] not in {"admin", "editor"}:
            raise PermissionError("Пользователь не имеет права редактировать общий документ")
        edit = {"type": "edit", "content": "\n".join(content), "base_version": welcome["version"]}
        sock.sendall((json.dumps(edit, ensure_ascii=False) + "\n").encode())
        buffer = ""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("Сервер общего документа закрыл соединение до подтверждения редакции")
            buffer += chunk.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                event = json.loads(line)
                if event.get("type") == "document":
                    return
                if event.get("type") in {"error", "conflict"}:
                    raise RuntimeError(event.get("message", "Редакция общего документа не принята"))


def parse_with_error_logging(url: str, **kwargs: Any) -> dict[str, Any]:
    """Обёртка парсера с понятным исключением для CLI."""
    try:
        return parse_site(url, **kwargs)
    except (OSError, urllib.error.URLError, ValueError, UnicodeError) as exc:
        raise RuntimeError(f"Не удалось обработать сайт {url}: {exc}") from exc
