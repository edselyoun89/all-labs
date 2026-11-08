"""Графики времени по приоритету и числу потребителей из CSV."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    """Показать отдельно ожидание, обслуживание и время до завершения."""
    with (ROOT / 'results' / 'priority_summary.csv').open(encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    n = max(int(r['threads']) for r in rows)
    selected = {r['priority']: r for r in rows if int(r['threads']) == n}
    names = [k for k in ('HIGH', 'MEDIUM', 'LOW') if k in selected]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, field, title in zip(axes, ['mean_wait_seconds', 'mean_service_seconds', 'mean_response_seconds'],
                               ['Ожидание в очереди', 'Обработка задачи', 'От постановки до завершения']):
        ax.bar(names, [1000 * float(selected[k][field]) for k in names], color=['#c43b48', '#d9a126', '#377cb8'][:len(names)])
        ax.set_title(title)
        ax.set_ylabel('Время, мс')
        ax.grid(axis='y', alpha=.3)
    fig.suptitle(f'Очередь с приоритетами: 5 производителей, {n} потребителей')
    fig.tight_layout()
    fig.savefig(ROOT / 'priority_time.png', dpi=150)
    plt.close(fig)
    with (ROOT / 'results' / 'summary.csv').open(encoding='utf-8', newline='') as file:
        rows = list(csv.DictReader(file))
    plt.figure(figsize=(8, 4.5))
    for field, label in [('time_seq', 'Последовательно'), ('time_par', 'Потоки')]:
        plt.plot([int(r['threads']) for r in rows], [float(r[field]) for r in rows], 'o-', label=label)
    plt.xlabel('Число потребителей')
    plt.ylabel('Полное время, с')
    plt.title('Одинаковые задачи: имитация I/O по 5 мс')
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROOT / 'thread_time.png', dpi=150)
    plt.close()


if __name__ == '__main__':
    main()
