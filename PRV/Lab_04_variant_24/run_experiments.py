"""Запуск MPI-экспериментов для p=1,2,4,8 и трёх повторов."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MPIEXEC = os.environ.get("MPIEXEC", r"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe")


def run_once(processes: int, n: int = 128) -> dict:
    """Запустить один MPI-эксперимент и извлечь JSON-результат."""
    command = [MPIEXEC, "-n", str(processes), sys.executable, str(ROOT / "main.py"), "--n", str(n), "--log", "WARNING"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    lines = [line for line in completed.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        raise RuntimeError(f"MPI не вернул JSON: {completed.stdout!r} {completed.stderr!r}")
    return json.loads(lines[-1])


def main() -> None:
    """Собрать три повтора для каждого числа процессов."""
    rows = []
    for processes in (1, 2, 4, 8):
        for repeat in range(1, 4):
            row = run_once(processes)
            row["repeat"] = repeat
            rows.append(row)
            print(row)
    with (ROOT / "results" / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
