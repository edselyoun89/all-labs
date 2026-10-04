"""Лабораторная работа №1, вариант 24.

Параллельное вычисление определителя матрицы методом Гаусса:
MPI распределяет строки, а Numba prange распараллеливает исключение
внутри каждого MPI-процесса.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI
from numba import njit, prange


ROOT = Path(__file__).resolve().parent
EPS = 1.0e-12


@njit(parallel=True, cache=True)
def eliminate_rows(block: np.ndarray, pivot: np.ndarray, pivot_column: int, global_start: int) -> None:
    """Обнулить текущий столбец в строках блока после pivot_column."""
    for local_i in prange(block.shape[0]):
        global_i = global_start + local_i
        if global_i > pivot_column:
            factor = block[local_i, pivot_column] / pivot[pivot_column]
            block[local_i, pivot_column] = 0.0
            for column in range(pivot_column + 1, block.shape[1]):
                block[local_i, column] -= factor * pivot[column]


def validate_process_count(size: int) -> None:
    if size not in (1, 2, 4, 8):
        raise ValueError("Для варианта 24 допустимы только p = 1, 2, 4, 8.")


def generate_data(n: int, seed: int = 20261003) -> np.ndarray:
    """Сгенерировать воспроизводимую невырожденную матрицу."""
    rng = np.random.default_rng(seed)
    matrix = rng.uniform(-1.0, 1.0, size=(n, n)).astype(np.float64)
    matrix += np.eye(n, dtype=np.float64) * n
    return matrix


def sequential_computation(data: np.ndarray) -> tuple[float, float]:
    """Последовательное вычисление det(A) методом Гаусса с выбором pivot."""
    matrix = np.array(data, dtype=np.float64, copy=True)
    n = matrix.shape[0]
    sign = 1.0
    for k in range(n):
        pivot = k + int(np.argmax(np.abs(matrix[k:, k])))
        if abs(matrix[pivot, k]) < EPS:
            return 0.0, -math.inf
        if pivot != k:
            matrix[[k, pivot]] = matrix[[pivot, k]]
            sign = -sign
        if k + 1 < n:
            factors = matrix[k + 1 :, k] / matrix[k, k]
            matrix[k + 1 :, k] = 0.0
            matrix[k + 1 :, k + 1 :] -= factors[:, None] * matrix[k, k + 1 :]
    diagonal = np.diag(matrix)
    determinant_sign = sign * float(np.prod(np.sign(diagonal)))
    log_abs = float(np.log(np.abs(diagonal)).sum())
    return determinant_sign, log_abs


def _owner(global_row: int, rows_per_process: int) -> int:
    return global_row // rows_per_process


def parallel_computation(data: np.ndarray | None, comm: MPI.Comm) -> tuple[float, float]:
    """Распределённое вычисление det(A) методом Гаусса."""
    rank = comm.Get_rank()
    size = comm.Get_size()
    n = data.shape[0] if rank == 0 and data is not None else None
    n = comm.bcast(n, root=0)
    if n % size != 0:
        raise ValueError("Размер матрицы должен делиться на число MPI-процессов.")

    rows_per_process = n // size
    local = np.empty((rows_per_process, n), dtype=np.float64)
    if rank == 0:
        sendbuf = np.ascontiguousarray(data, dtype=np.float64)
    else:
        sendbuf = None
    comm.Scatter(sendbuf, local, root=0)

    sign = 1.0
    for k in range(n):
        local_row = k - rank * rows_per_process
        candidate = (-1.0, -1)
        if 0 <= local_row < rows_per_process:
            value = abs(local[local_row, k])
            candidate = (float(value), k)
        candidates = comm.allgather(candidate)
        pivot_value, pivot_row = max(candidates, key=lambda item: item[0])
        if pivot_value < EPS:
            return 0.0, -math.inf

        owner_k = _owner(k, rows_per_process)
        owner_pivot = _owner(pivot_row, rows_per_process)
        if pivot_row != k:
            if owner_k == owner_pivot:
                if rank == owner_k:
                    row_k = k - rank * rows_per_process
                    row_p = pivot_row - rank * rows_per_process
                    local[[row_k, row_p]] = local[[row_p, row_k]]
            elif rank in (owner_k, owner_pivot):
                partner = owner_pivot if rank == owner_k else owner_k
                row_index = k if rank == owner_k else pivot_row
                row = np.ascontiguousarray(local[row_index - rank * rows_per_process].copy())
                received = np.empty_like(row)
                comm.Sendrecv(row, dest=partner, sendtag=k, recvbuf=received, source=partner, recvtag=k)
                local[row_index - rank * rows_per_process] = received
            sign = -sign

        pivot = np.empty(n, dtype=np.float64)
        if rank == owner_k:
            pivot[:] = local[k - rank * rows_per_process]
        comm.Bcast(pivot, root=owner_k)
        eliminate_rows(local, pivot, k, rank * rows_per_process)

    local_diag = np.array([local[i, rank * rows_per_process + i] for i in range(rows_per_process)])
    local_sign = float(np.prod(np.sign(local_diag)))
    local_log_abs = float(np.log(np.abs(local_diag)).sum())
    determinant_sign = sign * comm.allreduce(local_sign, op=MPI.PROD)
    log_abs = comm.allreduce(local_log_abs, op=MPI.SUM)
    return float(determinant_sign), float(log_abs)


def check_result(seq_result: tuple[float, float], par_result: tuple[float, float], rtol: float = 1e-8, atol: float = 1e-8) -> bool:
    return bool(seq_result[0] == par_result[0] and np.isclose(seq_result[1], par_result[1], rtol=rtol, atol=atol))


def run_measurements(n: int, repeats: int, comm: MPI.Comm) -> dict[str, float | int | bool]:
    rank = comm.Get_rank()
    size = comm.Get_size()
    if n % size != 0:
        raise ValueError("Размер матрицы должен делиться на число MPI-процессов.")
    data = generate_data(n) if rank == 0 else None

    # Прогрев Numba выполняется до измерений, чтобы JIT-компиляция не
    # искажала Tp. Этот вызов также проверяет MPI-обмены до эксперимента.
    parallel_computation(data, comm)
    comm.Barrier()

    seq_times: list[float] = []
    seq_result = None
    if rank == 0:
        for _ in range(repeats):
            started = time.perf_counter()
            seq_result = sequential_computation(data)
            seq_times.append(time.perf_counter() - started)
    t1 = float(np.mean(seq_times)) if rank == 0 else None
    t1 = comm.bcast(t1, root=0)

    parallel_times: list[float] = []
    par_result = None
    for _ in range(repeats):
        comm.Barrier()
        started = MPI.Wtime()
        par_result = parallel_computation(data, comm)
        parallel_times.append(MPI.Wtime() - started)
    tp = float(np.mean(parallel_times))
    par_result = comm.bcast(par_result, root=0)
    seq_result = comm.bcast(seq_result, root=0)
    correct = check_result(seq_result, par_result)
    speedup = t1 / tp if tp > 0 else math.inf
    efficiency = speedup / size
    b_fraction = (1.0 / speedup - 1.0 / size) / (1.0 - 1.0 / size) if size > 1 else 0.0
    return {
        "n": n,
        "processes": size,
        "t1_seconds": t1,
        "tp_seconds": tp,
        "speedup": speedup,
        "efficiency": efficiency,
        "serial_fraction_b": b_fraction,
        "determinant_sign": float(par_result[0]),
        "log10_abs_determinant": float(par_result[1] / math.log(10.0)),
        "correct": correct,
        "repeats": repeats,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    try:
        validate_process_count(comm.Get_size())
        result = run_measurements(args.n, args.repeats, comm)
        if rank == 0:
            print(json.dumps(result, ensure_ascii=False))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        if rank == 0:
            print(f"ОШИБКА: {exc}")
        comm.Abort(1)


if __name__ == "__main__":
    main()
