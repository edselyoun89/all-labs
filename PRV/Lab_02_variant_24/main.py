"""Лабораторная работа №2, вариант 24: таймер с отложенным запуском."""

from __future__ import annotations

import argparse
import csv
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from typing import Callable


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
LOG_FILE = RESULTS_DIR / "logs.log"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Настроить запись событий в файл и в консоль."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lab2.scheduler")
    logger.setLevel(getattr(logging, level))
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    stream_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


@dataclass
class Task:
    """Описание задачи, запускаемой после заданной задержки."""

    name: str
    delay: float
    function: Callable[[], None]
    scheduled_at: float | None = None
    executed_at: float | None = None
    cancelled: bool = False
    timer: threading.Timer | None = field(default=None, repr=False)
    done: threading.Event = field(default_factory=threading.Event, repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def mark_executed(self, timestamp: float) -> None:
        """Зафиксировать фактическое время запуска задачи."""
        with self.lock:
            self.executed_at = timestamp
            self.done.set()


class Scheduler:
    """Планировщик отложенных задач на базе threading.Timer."""

    def __init__(self, logger: logging.Logger) -> None:
        """Создать пустой планировщик."""
        self.tasks: list[Task] = []
        self.lock = threading.RLock()
        self.logger = logger

    def schedule(self, task: Task, delay: float | None = None) -> Task:
        """Запланировать задачу и запустить её Timer-поток."""
        actual_delay = task.delay if delay is None else delay
        task.delay = actual_delay
        task.scheduled_at = time.perf_counter()

        def execute() -> None:
            """Выполнить функцию задачи и сообщить о завершении."""
            with task.lock:
                if task.cancelled:
                    task.done.set()
                    return
            started_at = time.perf_counter()
            self.logger.info("Задача %s начала выполнение", task.name)
            try:
                task.function()
                task.mark_executed(started_at)
                self.logger.info("Задача %s завершена", task.name)
            except Exception:
                self.logger.exception("Ошибка выполнения задачи %s", task.name)
                task.mark_executed(started_at)

        with self.lock:
            task.timer = threading.Timer(actual_delay, execute)
            task.timer.name = f"Timer-{task.name}"
            task.timer.daemon = True
            self.tasks.append(task)
            self.logger.info("Задача %s запланирована на %.3f с", task.name, actual_delay)
            task.timer.start()
        return task

    def run(self) -> None:
        """Дождаться завершения всех незапланированно отменённых задач."""
        with self.lock:
            tasks = list(self.tasks)
        for task in tasks:
            task.done.wait()

    def cancel(self, task: Task) -> bool:
        """Отменить задачу до её запуска и вернуть успешность отмены."""
        with self.lock:
            if task not in self.tasks or task.executed_at is not None:
                return False
            with task.lock:
                task.cancelled = True
                if task.timer is not None:
                    task.timer.cancel()
                task.done.set()
            self.logger.info("Задача %s отменена", task.name)
            return True


class LoadWorker(threading.Thread):
    """Фоновый поток, создающий управляемую вычислительную нагрузку."""

    def __init__(self, stop_event: threading.Event, worker_id: int) -> None:
        """Создать поток нагрузки."""
        super().__init__(name=f"LoadWorker-{worker_id}", daemon=True)
        self.stop_event = stop_event

    def run(self) -> None:
        """Выполнять короткие CPU-блоки до получения сигнала остановки."""
        value = 0.0
        while not self.stop_event.is_set():
            for index in range(20_000):
                value += math.sin(index * 0.001) ** 2
            if value > 1.0e12:
                value = 0.0


def create_tasks(task_count: int, max_delay: int, logger: logging.Logger) -> list[Task]:
    """Создать задачи с задержками от 1 до max_delay секунд."""
    if task_count != 10 or max_delay != 10:
        logger.warning("Для полного варианта 24 рекомендуется 10 задач и задержки 1..10 секунд")
    tasks = []
    for index in range(task_count):
        delay = float(1 + (index % max_delay))
        tasks.append(Task(f"task-{index + 1:02d}", delay, lambda: None))
    return tasks


def run_case(task_count: int, max_delay: int, load_threads: int, logger: logging.Logger) -> dict[str, float | int | bool]:
    """Провести один эксперимент с указанной фоновой нагрузкой."""
    scheduler = Scheduler(logger)
    tasks = create_tasks(task_count, max_delay, logger)
    stop_event = threading.Event()
    workers = [LoadWorker(stop_event, index + 1) for index in range(load_threads)]
    for worker in workers:
        worker.start()

    started = time.perf_counter()
    for task in tasks:
        scheduler.schedule(task)
    cancelled = scheduler.cancel(tasks[-1])
    scheduler.run()
    elapsed = time.perf_counter() - started

    stop_event.set()
    for worker in workers:
        worker.join(timeout=2.0)

    executed = [task for task in tasks if not task.cancelled and task.executed_at is not None]
    errors = [abs((task.executed_at - task.scheduled_at) - task.delay) for task in executed]
    requested_total = sum(task.delay for task in tasks)
    sequential_time = requested_total
    speedup = sequential_time / elapsed if elapsed else 0.0
    return {
        "load_threads": load_threads,
        "tasks": task_count,
        "cancelled": cancelled,
        "executed_tasks": len(executed),
        "time_seq": sequential_time,
        "time_par": elapsed,
        "speedup": speedup,
        "efficiency": speedup / max(1, load_threads),
        "mean_error_seconds": mean(errors) if errors else 0.0,
        "max_error_seconds": max(errors) if errors else 0.0,
        "correct": len(executed) == task_count - 1,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Записать результаты экспериментов в CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Разобрать параметры командной строки."""
    parser = argparse.ArgumentParser(description="Timer с отложенным запуском, вариант 24")
    parser.add_argument("--tasks", type=int, default=10, help="Количество задач")
    parser.add_argument("--max-delay", type=int, default=10, help="Максимальная задержка в секундах")
    parser.add_argument("--repeats", type=int, default=3, help="Повторы каждого набора параметров")
    parser.add_argument("--loads", nargs="+", type=int, default=[0, 2, 4, 8], help="Числа потоков нагрузки")
    parser.add_argument("--log", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--single", action="store_true", help="Выполнить один эксперимент без benchmark-цикла")
    return parser.parse_args()


def main() -> None:
    """Запустить демонстрацию или полный эксперимент и сохранить результаты."""
    args = parse_args()
    if args.tasks <= 0 or args.max_delay <= 0 or args.repeats <= 0 or any(load < 0 for load in args.loads):
        raise SystemExit("Параметры tasks, max-delay и repeats должны быть положительными, load неотрицателен")
    logger = setup_logging(args.log)
    if args.single:
        result = run_case(args.tasks, args.max_delay, args.loads[0], logger)
        print(result)
        return

    raw_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for load in args.loads:
        repeats = [run_case(args.tasks, args.max_delay, load, logger) for _ in range(args.repeats)]
        raw_rows.extend(repeats)
        summary_rows.append({
            "load_threads": load,
            "tasks": args.tasks,
            "repeats": args.repeats,
            "time_seq": mean(row["time_seq"] for row in repeats),
            "time_par": mean(row["time_par"] for row in repeats),
            "speedup": mean(row["speedup"] for row in repeats),
            "efficiency": mean(row["efficiency"] for row in repeats),
            "mean_error_seconds": mean(row["mean_error_seconds"] for row in repeats),
            "max_error_seconds": mean(row["max_error_seconds"] for row in repeats),
            "correct": all(row["correct"] for row in repeats),
        })
    write_csv(RESULTS_DIR / "results.csv", raw_rows)
    write_csv(RESULTS_DIR / "summary.csv", summary_rows)
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
