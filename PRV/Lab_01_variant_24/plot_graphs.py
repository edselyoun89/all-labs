"""Построение графиков по results.csv."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent


def main() -> None:
    rows = np.genfromtxt(ROOT / "results.csv", delimiter=",", names=True)
    p = rows["processes"]
    for field, title, ylabel, filename in [
        ("efficiency", "Эффективность E(p)", "E(p)", "efficiency.png"),
        ("speedup", "Ускорение S(p)", "S(p)", "speedup.png"),
        ("serial_fraction_b", "Оценка доли последовательного кода", "B(p)", "serial_fraction.png"),
    ]:
        plt.figure(figsize=(8, 5))
        plt.plot(p, rows[field], "o-", label=field)
        plt.xlabel("Число MPI-процессов p")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.xticks(p)
        plt.legend()
        plt.tight_layout()
        plt.savefig(ROOT / filename, dpi=160)
        plt.close()


if __name__ == "__main__":
    main()
