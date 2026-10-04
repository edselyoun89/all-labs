"""Запуск варианта 24 для p=1,2,4,8 и расчёт N_min при E>=0.5."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "main.py"
MPIEXEC = os.environ.get("MPIEXEC", r"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe")
N_VALUES = [256, 512, 768, 1000, 1280, 1536, 1792, 2048]


def run(p: int, n: int, repeats: int = 3) -> dict:
    command = [MPIEXEC, "-n", str(p), sys.executable, str(MAIN), "--n", str(n), "--repeats", str(repeats)]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    lines = [line for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        raise RuntimeError(f"Не найден JSON-результат. stdout={completed.stdout!r}, stderr={completed.stderr!r}")
    return json.loads(lines[-1])


def main() -> None:
    rows = []
    for p in (1, 2, 4, 8):
        result = run(p, 1000)
        rows.append(result)
        print(f"p={p}: T1={result['t1_seconds']:.6f}, Tp={result['tp_seconds']:.6f}, "
              f"S={result['speedup']:.3f}, E={result['efficiency']:.3f}, "
              f"correct={'УСПЕШНО' if result['correct'] else 'ОШИБКА'}")

    with (ROOT / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    scaling = []
    for p in (2, 4, 8):
        found = None
        for n in N_VALUES:
            if n % p:
                continue
            result = run(p, n, repeats=3)
            scaling.append(result)
            print(f"scale p={p}, N={n}: E={result['efficiency']:.3f}")
            if result["efficiency"] >= 0.5:
                found = n
                break
        if found is None:
            found = "не найдено в диапазоне"
        print(f"N_min для p={p}, E>=0.5: {found}")

    with (ROOT / "scalability.csv").open("w", newline="", encoding="utf-8") as handle:
        if scaling:
            writer = csv.DictWriter(handle, fieldnames=scaling[0].keys())
            writer.writeheader()
            writer.writerows(scaling)

    subprocess.run([sys.executable, str(ROOT / "plot_graphs.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
