# Лабораторная работа №4 — вариант 24

Комплексное исследование MPI на задаче поиска кратчайшего пути.

Реализованы три подхода:

1. явные `Send/Recv` и распределенный Дейкстра;
2. `Bcast`, `Reduce(MIN)`, `Allreduce` и Дейкстра;
3. декартова топология, обмен соседей и Флойд–Уоршелл.

## Запуск

```powershell
& 'C:\Program Files\Microsoft MPI\Bin\mpiexec.exe' -n 4 python main.py --n 128
python run_experiments.py
python plot_graphs.py
```

Размер графа по умолчанию — 128 вершин. Основные результаты сохраняются в `results/results.csv`, события — в `results/logs.log`.
