"""Построить графики из фактических измерений Якоби."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    """Сохранить S, E, B и зависимость E от размера СЛАУ."""
    with (ROOT / 'results.csv').open(encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    for field, label, filename in [('speedup', 'Ускорение S(p)', 'speedup.png'),
                                   ('efficiency', 'Эффективность E(p) = S(p) / p_MPI', 'efficiency.png'),
                                   ('serial_fraction_b', 'Оценка B(p)', 'serial_fraction.png')]:
        selected = [r for r in rows if r[field]]
        plt.figure(figsize=(8, 4.5))
        plt.plot([int(r['processes']) for r in selected], [float(r[field]) for r in selected], 'o-')
        plt.xlabel('Число MPI-процессов (2 OpenMP-потока на процесс)')
        plt.ylabel(label)
        plt.title('Метод Якоби: N = 2000, 100 итераций')
        plt.grid(alpha=.3)
        plt.tight_layout()
        plt.savefig(ROOT / filename, dpi=150)
        plt.close()
    with (ROOT / 'scalability.csv').open(encoding='utf-8', newline='') as file:
        scaling = list(csv.DictReader(file))
    plt.figure(figsize=(8, 4.5))
    for p in (2, 4, 8):
        chosen = [r for r in scaling if int(r['processes']) == p]
        plt.plot([int(r['n']) for r in chosen], [float(r['efficiency']) for r in chosen], 'o-', label=f'p = {p}')
    plt.axhline(.7, ls='--', color='black', label='E = 0.7')
    plt.xlabel('Размер СЛАУ N')
    plt.ylabel('E(p) = S(p) / p_MPI')
    plt.legend()
    plt.grid(alpha=.3)
    plt.tight_layout()
    plt.savefig(ROOT / 'scalability.png', dpi=150)
    plt.close()


if __name__ == '__main__':
    main()
