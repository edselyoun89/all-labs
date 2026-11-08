"""ЛР1, вариант 22: метод Якоби, MPI и подтверждённый OpenMP Numba."""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

# Выбор backend должен предшествовать первой компиляции parallel=True.
os.environ['NUMBA_THREADING_LAYER'] = 'omp'
os.environ.setdefault('NUMBA_NUM_THREADS', str(os.cpu_count() or 2))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import numpy as np
import numba
from mpi4py import MPI
from numba import njit, prange

ROOT = Path(__file__).resolve().parent


def generate_data(n: int, seed: int = 22) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Создать строго диагонально преобладающую СЛАУ с известным решением."""
    if n < 1:
        raise ValueError('N должен быть положительным')
    rng = np.random.default_rng(seed)
    a = rng.uniform(-1.0, 1.0, (n, n))
    np.fill_diagonal(a, 0.0)
    np.fill_diagonal(a, np.abs(a).sum(axis=1) + 1.0)
    exact = rng.uniform(-1.0, 1.0, n)
    b = a @ exact
    return a, b, exact


@njit(cache=True)
def sequential_kernel(a, b, iterations):
    """Выполнить заданное число итераций Якоби одним потоком."""
    n = len(b)
    x = np.zeros(n)
    new = np.empty(n)
    for _ in range(iterations):
        for i in range(n):
            total = 0.0
            for j in range(n):
                if j != i:
                    total += a[i, j] * x[j]
            new[i] = (b[i] - total) / a[i, i]
        x, new = new, x
    return x


@njit(parallel=True, cache=True)
def jacobi_rows(a, b, old, new, offset):
    """Обновить независимые строки блока через OpenMP prange."""
    for i in prange(len(b)):
        global_i = offset + i
        total = 0.0
        for j in range(len(old)):
            if j != global_i:
                total += a[i, j] * old[j]
        new[i] = (b[i] - total) / a[i, global_i]


def sequential_computation(data, iterations: int = 100):
    """Последовательно решить СЛАУ тем же арифметическим ядром."""
    a, b = data[:2]
    return sequential_kernel(a, b, iterations)


def parallel_computation(data, comm, iterations: int = 100):
    """Scatter строк, локальный Якоби, Allgather нового x на каждом шаге."""
    rank, p = comm.Get_rank(), comm.Get_size()
    n = comm.bcast(len(data[1]) if rank == 0 else None, root=0)
    if n < p or n % p:
        raise ValueError('N должен делиться на число MPI-процессов и быть не меньше p')
    rows = n // p
    a = np.empty((rows, n), dtype=np.float64)
    b = np.empty(rows, dtype=np.float64)
    comm.Scatter(data[0] if rank == 0 else None, a, root=0)
    comm.Scatter(data[1] if rank == 0 else None, b, root=0)
    x = np.zeros(n, dtype=np.float64)
    local_x = np.empty(rows, dtype=np.float64)
    for _ in range(iterations):
        # Все строки используют x только предыдущей итерации.
        jacobi_rows(a, b, x, local_x, rank * rows)
        comm.Allgather(local_x, x)
    return x


def check_result(seq_result, par_result, eps: float = 1e-9) -> bool:
    """Сравнить векторы, отвергая NaN и бесконечности."""
    return bool(np.isfinite(par_result).all() and
                np.allclose(seq_result, par_result, rtol=eps, atol=eps))


def run_measurements(n: int, iterations: int, repeats: int, comm):
    """Усреднить замеры; Tp включает распределение данных и все обмены."""
    rank, p = comm.Get_rank(), comm.Get_size()
    data = generate_data(n) if rank == 0 else None
    # Прогреть оба JIT-ядра на малом входе, вне измерений.
    small = generate_data(8 * p) if rank == 0 else None
    if rank == 0:
        sequential_computation(small, 1)
    parallel_computation(small, comm, 1)
    seq_times, par_times = [], []
    for repeat in range(repeats):
        comm.Barrier()
        if rank == 0:
            start = time.perf_counter()
            seq = sequential_computation(data, iterations)
            seq_times.append(time.perf_counter() - start)
        comm.Barrier()
        start = MPI.Wtime()
        par = parallel_computation(data, comm, iterations)
        elapsed = MPI.Wtime() - start
        # Время всего задания определяется самым медленным rank.
        par_times.append(comm.allreduce(elapsed, op=MPI.MAX))
    if rank != 0:
        return None
    a, b, exact = data
    t1, tp = float(np.mean(seq_times)), float(np.mean(par_times))
    speedup = t1 / tp
    relative_residual = float(np.linalg.norm(a @ par - b, ord=np.inf) /
                              np.linalg.norm(b, ord=np.inf))
    error = float(np.max(np.abs(par - exact)))
    correct = check_result(seq, par) and error < 1e-8 and relative_residual < 1e-9
    return dict(n=n, iterations=iterations, processes=p,
                threads_per_process=numba.get_num_threads(),
                total_threads=p * numba.get_num_threads(),
                threading_layer=numba.threading_layer(),
                t1_seconds=t1, tp_seconds=tp, speedup=speedup,
                efficiency=speedup / p,
                efficiency_total_threads=speedup / (p * numba.get_num_threads()),
                serial_fraction_b=(1 / speedup - 1 / p) / (1 - 1 / p) if p > 1 else None,
                max_abs_error=error, relative_residual=relative_residual,
                correct=correct, repeats=repeats,
                sequential_samples=seq_times, parallel_samples=par_times,
                python=platform.python_version(), numpy=np.__version__,
                numba=numba.__version__, mpi_library=MPI.Get_library_version().strip())


def main():
    """Разобрать CLI, проверить параметры и сохранить измерения в JSON."""
    parser = argparse.ArgumentParser(description='ЛР1, вариант 22: метод Якоби')
    parser.add_argument('--n', type=int, default=2000)
    parser.add_argument('--sizes', nargs='+', type=int)
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    comm = MPI.COMM_WORLD
    try:
        sizes = args.sizes or [args.n]
        if args.iterations < 1 or args.repeats < 3 or args.threads < 2:
            raise ValueError('Нужны iterations >= 1, repeats >= 3, threads >= 2')
        if any(n < comm.size or n % comm.size for n in sizes):
            raise ValueError('Каждый N должен быть положительным и делиться на p')
        numba.set_num_threads(args.threads)
        results = []
        for n in sizes:
            result = run_measurements(n, args.iterations, args.repeats, comm)
            if comm.rank == 0:
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                if not result['correct']:
                    raise RuntimeError('Проверка результата: ОШИБКА')
        if comm.rank == 0 and args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        if comm.rank == 0:
            print(f'ОШИБКА: {exc}', flush=True)
        comm.Abort(1)


if __name__ == '__main__':
    main()
