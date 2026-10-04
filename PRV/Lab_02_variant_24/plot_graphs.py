"""Построение графика точности таймера при разной загрузке."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Прочитать summary.csv и создать графики для отчёта."""
    data = np.genfromtxt(ROOT / "results" / "summary.csv", delimiter=",", names=True)
    load = data["load_threads"]
    mean_error_ms = data["mean_error_seconds"] * 1000.0
    max_error_ms = data["max_error_seconds"] * 1000.0
    plt.figure(figsize=(8, 5))
    plt.plot(load, mean_error_ms, "o-", label="Средняя абсолютная ошибка")
    plt.plot(load, max_error_ms, "s--", label="Максимальная абсолютная ошибка")
    plt.xlabel("Потоки фоновой нагрузки")
    plt.ylabel("Ошибка запуска, мс")
    plt.title("Точность Timer при разной загрузке системы")
    plt.grid(True, alpha=0.3)
    plt.xticks(load)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / "timer_accuracy.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.plot(load, data["time_par"], "o-", label="Время планировщика")
    plt.xlabel("Потоки фоновой нагрузки")
    plt.ylabel("Время, с")
    plt.title("Время выполнения эксперимента")
    plt.grid(True, alpha=0.3)
    plt.xticks(load)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / "timer_time.png", dpi=160)
    plt.close()


if __name__ == "__main__":
    main()
