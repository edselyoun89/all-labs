"""CLI приложения для парсинга сайтов и сохранения результата."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from parser import parse_with_error_logging, publish_to_shared_document, save_results


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Распарсить URL, сохранить файлы и при необходимости опубликовать результат."""
    parser = argparse.ArgumentParser(description="Лабораторная работа 7: парсинг сайтов")
    parser.add_argument("url", help="URL сайта или file:// HTML-файла")
    parser.add_argument("--keyword", default="", help="Фильтр по ключевому слову")
    parser.add_argument("--tag", choices=["all", "headings", "paragraphs", "links"], default="all")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--shared-host", default=None)
    parser.add_argument("--shared-port", type=int, default=12346)
    parser.add_argument("--username", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    try:
        data = parse_with_error_logging(args.url, keyword=args.keyword, tag=args.tag, limit=args.limit)
        paths = save_results(data, args.output_dir)
        logging.info("Извлечено элементов: %s", data["total_items"])
        logging.info("Сохранено: %s", ", ".join(str(path) for path in paths))
        if args.shared_host:
            if not args.username:
                raise ValueError("Для публикации в общий документ нужен --username")
            publish_to_shared_document(data, args.shared_host, args.shared_port, args.username)
            logging.info("Данные опубликованы в общем документе")
    except (RuntimeError, OSError, PermissionError, ValueError) as exc:
        logging.error("Ошибка: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
