"""Лабораторная работа №3, вариант 24: параллельный поиск в базе данных."""

from __future__ import annotations

import argparse
import csv
import logging
import multiprocessing as mp
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
LOG_FILE = RESULTS_DIR / "logs.log"
_WORKER_DATABASE: list[dict[str, Any]] = []


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Настроить логирование в файл и в консоль."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lab3.database_search")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level))
    formatter = logging.Formatter("%(asctime)s - %(processName)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    stream_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def generate_database(size: int = 10_000) -> list[dict[str, Any]]:
    """Создать детерминированную базу данных заданного размера."""
    categories = ["science", "history", "technology", "art", "medicine"]
    database = []
    for record_id in range(size):
        category = categories[record_id % len(categories)]
        database.append({
            "id": record_id,
            "title": f"Record {record_id:05d}",
            "category": category,
            "text": f"Document {record_id} about {category} topic-{record_id % 10} tag-{record_id % 20}",
        })
    return database


def build_queries() -> list[str]:
    """Вернуть десять воспроизводимых поисковых запросов."""
    return [f"topic-{index}" for index in range(10)]


def search_database(database: list[dict[str, Any]], query: str) -> list[int]:
    """Последовательно найти идентификаторы записей, содержащих query."""
    normalized = query.casefold()
    return [
        int(record["id"])
        for record in database
        if normalized in f"{record['title']} {record['category']} {record['text']}".casefold()
    ]


def initialize_worker(database: list[dict[str, Any]]) -> None:
    """Передать копию базы данных каждому процессу пула."""
    global _WORKER_DATABASE
    _WORKER_DATABASE = database


def worker_search(query: str) -> tuple[str, list[int]]:
    """Выполнить один поисковый запрос внутри процесса Pool."""
    return query, search_database(_WORKER_DATABASE, query)


def sequential_search(database: list[dict[str, Any]], queries: list[str]) -> dict[str, list[int]]:
    """Выполнить набор запросов последовательно."""
    return {query: search_database(database, query) for query in queries}


def parallel_search(database: list[dict[str, Any]], queries: list[str], processes: int) -> dict[str, list[int]]:
    """Выполнить набор запросов через multiprocessing.Pool."""
    with mp.Pool(processes=processes, initializer=initialize_worker, initargs=(database,)) as pool:
        pairs = pool.map(worker_search, queries)
    return dict(pairs)


def measure_case(database: list[dict[str, Any]], queries: list[str], processes: int, repeats: int) -> dict[str, Any]:
    """Усреднить последовательные и параллельные замеры для набора запросов."""
    sequential_times: list[float] = []
    parallel_times: list[float] = []
    correct_values: list[bool] = []
    for _ in range(repeats):
        start = time.perf_counter()
        sequential = sequential_search(database, queries)
        sequential_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        parallel = parallel_search(database, queries, processes)
        parallel_times.append(time.perf_counter() - start)
        correct_values.append(sequential == parallel)
    time_seq = sum(sequential_times) / repeats
    time_par = sum(parallel_times) / repeats
    speedup = time_seq / time_par if time_par else 0.0
    return {
        "records": len(database),
        "queries": len(queries),
        "processes": processes,
        "time_seq": time_seq,
        "time_par": time_par,
        "speedup": speedup,
        "efficiency": speedup / processes if processes else 0.0,
        "correct": all(correct_values),
        "total_matches": sum(len(ids) for ids in sequential.values()),
        "repeats": repeats,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Записать список результатов с заголовком в CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Разобрать параметры командной строки."""
    parser = argparse.ArgumentParser(description="Параллельный поиск в базе данных, вариант 24")
    parser.add_argument("--records", type=int, default=10_000, help="Размер базы данных")
    parser.add_argument("--repeats", type=int, default=3, help="Число повторов каждого измерения")
    parser.add_argument("--processes", type=int, default=4, help="Размер Pool")
    parser.add_argument("--log", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--single", action="store_true", help="Один smoke-test вместо полного benchmark")
    return parser.parse_args()


def main() -> None:
    """Создать базу, провести эксперименты и сохранить результаты."""
    args = parse_args()
    if args.records <= 0 or args.repeats <= 0 or args.processes <= 0:
        raise SystemExit("records, repeats и processes должны быть положительными")
    logger = setup_logging(args.log)
    database = generate_database(args.records)
    all_queries = build_queries()
    query_counts = [1, 2, 5, 10]
    if args.single:
        result = measure_case(database, all_queries[:2], min(args.processes, 2), 1)
        logger.info("Smoke-test: %s", result)
        print(result)
        return

    query_rows = []
    for query_count in query_counts:
        logger.info("Запуск серии для %d запросов", query_count)
        query_rows.append(measure_case(database, all_queries[:query_count], args.processes, args.repeats))

    process_counts = [1, 2, 4, 8]
    process_rows = []
    for process_count in process_counts:
        logger.info("Запуск серии для %d процессов", process_count)
        process_rows.append(measure_case(database, all_queries, process_count, args.repeats))

    write_csv(RESULTS_DIR / "results.csv", query_rows)
    write_csv(RESULTS_DIR / "process_scaling.csv", process_rows)
    for row in query_rows:
        print(row)
    print("--- process scaling ---")
    for row in process_rows:
        print(row)


if __name__ == "__main__":
    mp.freeze_support()
    main()
