"""Построение графиков времени MPI-подходов."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Построить средние времена трёх подходов по числу процессов."""
    data = np.genfromtxt(ROOT / "results" / "results.csv", delimiter=",", names=True)
    processes = sorted(set(data["processes"]))
    means = {name: [np.mean(data[name][data["processes"] == p]) * 1000 for p in processes]
             for name in ("point_to_point_seconds", "collective_seconds", "cartesian_seconds")}
    labels = {
        "point_to_point_seconds": "Send/Recv + Дейкстра",
        "collective_seconds": "Bcast/Reduce + Дейкстра",
        "cartesian_seconds": "Декартова топология + Флойд",
    }
    plt.figure(figsize=(9, 5))
    for name, values in means.items():
        plt.plot(processes, values, "o-", label=labels[name])
    plt.xlabel("Число MPI-процессов")
    plt.ylabel("Среднее время, мс")
    plt.title("Сравнение MPI-подходов к поиску кратчайшего пути")
    plt.grid(True, alpha=0.3)
    plt.xticks(processes)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / "mpi_methods_time.png", dpi=160)
    plt.close()
