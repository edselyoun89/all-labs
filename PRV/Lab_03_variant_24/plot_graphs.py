"""Построение графиков времени поиска."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Создать графики зависимости времени от числа запросов и процессов."""
    query_data = np.genfromtxt(ROOT / "results" / "results.csv", delimiter=",", names=True)
    plt.figure(figsize=(8, 5))
    plt.plot(query_data["queries"], query_data["time_seq"] * 1000, "o-", label="Последовательно")
    plt.plot(query_data["queries"], query_data["time_par"] * 1000, "s-", label="Pool")
    plt.xlabel("Количество поисковых запросов")
    plt.ylabel("Время, мс")
    plt.title("Время поиска в зависимости от числа запросов")
    plt.grid(True, alpha=0.3)
    plt.xticks(query_data["queries"])
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / "query_time.png", dpi=160)
    plt.close()

    process_data = np.genfromtxt(ROOT / "results" / "process_scaling.csv", delimiter=",", names=True)
    plt.figure(figsize=(8, 5))
    plt.plot(process_data["processes"], process_data["time_par"] * 1000, "o-", label="Pool")
    plt.xlabel("Количество процессов")
    plt.ylabel("Время поиска 10 запросов, мс")
    plt.title("Масштабирование поиска по числу процессов")
    plt.grid(True, alpha=0.3)
    plt.xticks(process_data["processes"])
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / "process_time.png", dpi=160)
    plt.close()


if __name__ == "__main__":
    main()
