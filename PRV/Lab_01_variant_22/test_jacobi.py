"""Запускать через mpiexec: независимый эталон и проверки нескольких СЛАУ."""
import json
import numpy as np
from mpi4py import MPI
from main import generate_data, sequential_computation, parallel_computation, check_result
import numba


def main():
    """Проверить известное решение, нулевую правую часть, одну итерацию и ошибки N."""
    comm = MPI.COMM_WORLD
    numba.set_num_threads(2)
    checks = []
    n = 8 * comm.size
    for mode in ('random', 'diagonal', 'zero_rhs', 'one_iteration'):
        if comm.rank == 0:
            a, b, exact = generate_data(n)
            if mode == 'diagonal':
                a = np.diag(np.arange(1, n + 1, dtype=float))
                b = a @ exact
            if mode == 'zero_rhs':
                b = np.zeros(n)
                exact = np.zeros(n)
            data = a, b, exact
        else:
            data = None
        iterations = 1 if mode == 'one_iteration' else 100
        par = parallel_computation(data, comm, iterations)
        if comm.rank == 0:
            seq = sequential_computation(data, iterations)
            expected = b / np.diag(a) if mode == 'one_iteration' else np.linalg.solve(a, b)
            checks.append(check_result(seq, par) and check_result(expected, par))
    # Ошибка размеров должна быть одинаково распознана всеми rank.
    if comm.size > 1:
        bad = generate_data(n + 1) if comm.rank == 0 else None
        try:
            parallel_computation(bad, comm, 1)
            valid = False
        except ValueError:
            valid = True
        flags = comm.allgather(valid)
        if comm.rank == 0:
            checks.append(all(flags))
    if comm.rank == 0:
        result = dict(processes=comm.size, passed=sum(checks), total=len(checks),
                      openmp=numba.threading_layer(), correct=all(checks))
        print(json.dumps(result), flush=True)
        if not all(checks):
            comm.Abort(1)


if __name__ == '__main__':
    main()
