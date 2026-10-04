"""Лабораторная работа №4, вариант 24: MPI и кратчайшие пути."""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI


ROOT = Path(__file__).resolve().parent


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Настроить логирование процесса-координатора."""
    logger = logging.getLogger("lab4.shortest_path")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level))
    handler = logging.FileHandler(ROOT / "results" / "logs.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(processName)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


def generate_graph(size: int, seed: int = 20261003) -> np.ndarray:
    """Создать воспроизводимый плотный ориентированный граф с весами."""
    rng = np.random.default_rng(seed)
    graph = rng.integers(1, 100, size=(size, size)).astype(np.float64)
    np.fill_diagonal(graph, 0.0)
    return graph


def dijkstra_sequential(graph: np.ndarray, source: int) -> np.ndarray:
    """Последовательно вычислить расстояния алгоритмом Дейкстры."""
    size = graph.shape[0]
    distances = np.full(size, np.inf)
    visited = np.zeros(size, dtype=bool)
    distances[source] = 0.0
    for _ in range(size):
        candidates = np.where(~visited, distances, np.inf)
        vertex = int(np.argmin(candidates))
        if not np.isfinite(candidates[vertex]):
            break
        visited[vertex] = True
        distances = np.minimum(distances, distances[vertex] + graph[vertex])
    return distances


def dijkstra_point_to_point(graph: np.ndarray | None, source: int, comm: MPI.Comm) -> np.ndarray | None:
    """Выполнить Дейкстру с явными Send/Recv и распределением строк графа."""
    rank, processes = comm.Get_rank(), comm.Get_size()
    size = graph.shape[0] if rank == 0 and graph is not None else None
    size = comm.bcast(size, root=0)
    if size % processes:
        raise ValueError("Размер графа должен делиться на число процессов")
    rows = size // processes
    local_graph = np.empty((rows, size), dtype=np.float64)
    started = MPI.Wtime()
    if rank == 0:
        local_graph[:] = graph[:rows]
        for target in range(1, processes):
            comm.Send(np.ascontiguousarray(graph[target * rows:(target + 1) * rows]), dest=target, tag=10)
    else:
        comm.Recv(local_graph, source=0, tag=10)

    distances = np.full(size, np.inf)
    visited = np.zeros(size, dtype=bool)
    distances[source] = 0.0
    if rank == 0:
        for target in range(1, processes):
            comm.Send(distances, dest=target, tag=20)
    else:
        comm.Recv(distances, source=0, tag=20)

    for iteration in range(size):
        local_candidates = np.where(~visited[rank * rows:(rank + 1) * rows], distances[rank * rows:(rank + 1) * rows], np.inf)
        local_offset = int(np.argmin(local_candidates))
        candidate = np.array([local_candidates[local_offset], rank * rows + local_offset], dtype=np.float64)
        if rank == 0:
            candidates = [candidate]
            for sender in range(1, processes):
                received = np.empty(2, dtype=np.float64)
                comm.Recv(received, source=sender, tag=100 + iteration)
                candidates.append(received)
            chosen = min(candidates, key=lambda item: (item[0], item[1]))
            chosen_vertex = int(chosen[1])
            chosen_distance = float(chosen[0])
        else:
            comm.Send(candidate, dest=0, tag=100 + iteration)
            chosen_vertex, chosen_distance = 0, 0.0

        if rank == 0:
            selection = np.array([chosen_vertex, chosen_distance], dtype=np.float64)
            for target in range(1, processes):
                comm.Send(selection, dest=target, tag=200 + iteration)
        else:
            selection = np.empty(2, dtype=np.float64)
            comm.Recv(selection, source=0, tag=200 + iteration)
            chosen_vertex, chosen_distance = int(selection[0]), float(selection[1])
        visited[chosen_vertex] = True

        owner = chosen_vertex // rows
        pivot_row = np.empty(size, dtype=np.float64)
        if rank == owner:
            pivot_row[:] = local_graph[chosen_vertex % rows]
            for target in range(processes):
                if target != owner:
                    comm.Send(pivot_row, dest=target, tag=250 + iteration)
        else:
            comm.Recv(pivot_row, source=owner, tag=250 + iteration)
        local_distances = distances[rank * rows:(rank + 1) * rows].copy()
        local_distances = np.minimum(
            local_distances,
            chosen_distance + pivot_row[rank * rows:(rank + 1) * rows],
        )
        if rank == 0:
            collected = distances.copy()
            collected[:rows] = local_distances
            for sender in range(1, processes):
                received = np.empty(rows, dtype=np.float64)
                comm.Recv(received, source=sender, tag=300 + iteration)
                collected[sender * rows:(sender + 1) * rows] = np.minimum(
                    collected[sender * rows:(sender + 1) * rows], received
                )
            distances = collected
            for target in range(1, processes):
                comm.Send(distances, dest=target, tag=400 + iteration)
                comm.Send(visited, dest=target, tag=500 + iteration)
        else:
            comm.Send(local_distances, dest=0, tag=300 + iteration)
            comm.Recv(distances, source=0, tag=400 + iteration)
            comm.Recv(visited, source=0, tag=500 + iteration)
    result = distances if rank == 0 else None
    elapsed = MPI.Wtime() - started
    return result, elapsed


def dijkstra_collective(graph: np.ndarray | None, source: int, comm: MPI.Comm) -> np.ndarray | None:
    """Выполнить Дейкстру с Bcast, Reduce(MIN) и Allreduce."""
    rank, processes = comm.Get_rank(), comm.Get_size()
    size = graph.shape[0] if rank == 0 and graph is not None else None
    size = comm.bcast(size, root=0)
    if size % processes:
        raise ValueError("Размер графа должен делиться на число процессов")
    started = MPI.Wtime()
    full_graph = np.empty((size, size), dtype=np.float64)
    if rank == 0:
        full_graph[:] = graph
    comm.Bcast(full_graph, root=0)
    rows = size // processes
    begin, end = rank * rows, (rank + 1) * rows
    distances = np.full(size, np.inf)
    distances[source] = 0.0
    visited = np.zeros(size, dtype=bool)
    for _ in range(size):
        local_values = np.where(~visited[begin:end], distances[begin:end], np.inf)
        local_min = float(np.min(local_values))
        global_min = comm.reduce(local_min, op=MPI.MIN, root=0)
        local_vertex = int(begin + np.argmin(local_values))
        vertices = comm.gather(local_vertex, root=0)
        if rank == 0:
            valid_vertices = [vertex for vertex in vertices if not visited[vertex] and np.isfinite(distances[vertex])]
            if not valid_vertices:
                raise RuntimeError("Не удалось выбрать непосещённую вершину")
            chosen_vertex = min(valid_vertices, key=lambda v: distances[v])
            selection = np.array([chosen_vertex, global_min], dtype=np.float64)
        else:
            selection = np.empty(2, dtype=np.float64)
        comm.Bcast(selection, root=0)
        chosen_vertex = int(selection[0])
        chosen_distance = float(selection[1])
        proposed = distances.copy()
        proposed[begin:end] = np.minimum(proposed[begin:end], chosen_distance + full_graph[chosen_vertex, begin:end])
        reduced_distances = np.empty_like(proposed)
        comm.Allreduce(proposed, reduced_distances, op=MPI.MIN)
        distances = reduced_distances
        visited[chosen_vertex] = True
    return distances if rank == 0 else None, MPI.Wtime() - started


def floyd_cartesian(graph: np.ndarray | None, comm: MPI.Comm) -> np.ndarray | None:
    """Выполнить Флойда-Уоршелла с одномерной декартовой топологией и обменом соседей."""
    rank, processes = comm.Get_rank(), comm.Get_size()
    size = graph.shape[0] if rank == 0 and graph is not None else None
    size = comm.bcast(size, root=0)
    if size % processes:
        raise ValueError("Размер графа должен делиться на число процессов")
    started = MPI.Wtime()
    full_graph = np.empty((size, size), dtype=np.float64)
    if rank == 0:
        full_graph[:] = graph
    comm.Bcast(full_graph, root=0)
    topology = comm.Create_cart([processes], periods=[True], reorder=False)
    left, right = topology.Shift(0, 1)
    local = np.ascontiguousarray(full_graph[rank::processes])
    for k in range(size):
        owner = k % processes
        token = local[k // processes].copy() if rank == owner else np.zeros(size, dtype=np.float64)
        flag = np.array([1 if rank == owner else 0], dtype=np.int32)
        for step in range(processes):
            received = np.empty(size, dtype=np.float64)
            received_flag = np.empty(1, dtype=np.int32)
            if processes == 1:
                received[:] = token
                received_flag[:] = flag
            else:
                topology.Sendrecv(token, dest=right, sendtag=600 + k, recvbuf=received, source=left, recvtag=600 + k)
                topology.Sendrecv(flag, dest=right, sendtag=700 + k, recvbuf=received_flag, source=left, recvtag=700 + k)
            if received_flag[0]:
                local = np.minimum(local, local[:, [k]] + received[None, :])
            token, flag = received, received_flag
    gathered = comm.gather(local, root=0)
    topology.Free()
    if rank == 0:
        all_pairs = np.empty((size, size), dtype=np.float64)
        for process_rank, block in enumerate(gathered):
            all_pairs[process_rank::processes] = block
        return all_pairs[0], MPI.Wtime() - started
    return None, MPI.Wtime() - started


def main() -> None:
    """Запустить и сравнить три MPI-подхода к кратчайшим путям."""
    parser = argparse.ArgumentParser(description="MPI shortest path, variant 24")
    parser.add_argument("--n", type=int, default=128, help="Размер графа")
    parser.add_argument("--source", type=int, default=0, help="Начальная вершина")
    parser.add_argument("--log", choices=["INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    if args.n <= 0 or not 0 <= args.source < args.n:
        raise SystemExit("Некорректные параметры графа")
    if rank == 0:
        (ROOT / "results").mkdir(parents=True, exist_ok=True)
        logger = setup_logging(args.log)
        graph = generate_graph(args.n)
    else:
        logger = logging.getLogger("lab4.shortest_path")
        graph = None
    expected = dijkstra_sequential(generate_graph(args.n), args.source) if rank == 0 else None
    point_result, point_time = dijkstra_point_to_point(graph, args.source, comm)
    collective_result, collective_time = dijkstra_collective(graph, args.source, comm)
    cart_result, cart_time = floyd_cartesian(graph, comm)
    if rank == 0:
        correct_point = bool(np.allclose(point_result, expected))
        correct_collective = bool(np.allclose(collective_result, expected))
        correct_cart = bool(np.allclose(cart_result, expected))
        result = {
            "n": args.n,
            "processes": comm.Get_size(),
            "point_to_point_seconds": point_time,
            "collective_seconds": collective_time,
            "cartesian_seconds": cart_time,
            "point_to_point_correct": correct_point,
            "collective_correct": correct_collective,
            "cartesian_correct": correct_cart,
            "all_correct": correct_point and correct_collective and correct_cart,
            "shortest_path_checksum": float(np.sum(expected)),
        }
        logger.info("Эксперимент завершён: %s", result)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
