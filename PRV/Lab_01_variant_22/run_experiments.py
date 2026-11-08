"""Основная серия N=2000 и дискретный поиск N_min для E >= 0.7."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def write_csv(path, rows):
    """Сохранить плоские поля измерений в CSV."""
    fields = [k for k, v in rows[0].items() if not isinstance(v, list)]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Запустить четыре MPI-серии с тем же интерпретатором Python."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--sizes', type=int, nargs='+', default=[128, 256, 512, 1000, 2000, 3000, 4000])
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--refine-only', action='store_true', help='Использовать уже сохранённые основные измерения')
    args = parser.parse_args()
    if args.threads < 2 or any(n < 8 or n % 8 for n in args.sizes):
        parser.error('Нужны threads >= 2 и размеры N >= 8, кратные 8')
    sizes = sorted(set([2000] + args.sizes))
    mpiexec = os.environ.get('MPIEXEC') or shutil.which('mpiexec')
    if not mpiexec:
        parser.error('Не найден mpiexec: установите Microsoft MPI или задайте MPIEXEC')
    output = ROOT / 'results'
    output.mkdir(exist_ok=True)
    rows = []
    for p in (1, 2, 4, 8):
        target = output / f'raw_p{p}.json'
        env = dict(os.environ, NUMBA_THREADING_LAYER='omp', NUMBA_NUM_THREADS=str(args.threads),
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        command = [mpiexec, '-n', str(p), sys.executable, str(ROOT / 'main.py'),
                   '--sizes', *map(str, sizes), '--threads', str(args.threads), '--output', str(target)]
        if not args.refine_only:
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                       encoding='utf-8', errors='replace', timeout=300)
            (output / f'mpi_p{p}.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
            if completed.returncode:
                raise RuntimeError(f'MPI p={p}: {completed.stderr}\n{completed.stdout}')
        batch = json.loads(target.read_text(encoding='utf-8'))
        rows.extend(batch)
        print(f'p={p}: {len(batch)} размеров, все correct={all(r["correct"] for r in batch)}', flush=True)
    # После грубой сетки проверяем ВСЕ допустимые N ниже первой удачной точки.
    # Это экспериментальный минимум для данной серии, а не аппаратная константа.
    for p in (2, 4, 8):
        passed = [r for r in rows if r['processes'] == p and r['efficiency'] >= .7]
        if not passed:
            continue
        first = min(r['n'] for r in passed)
        known = {r['n'] for r in rows if r['processes'] == p}
        candidates = [n for n in range(p, first, p) if n not in known]
        if not candidates:
            continue
        target = output / f'refinement_p{p}.json'
        env = dict(os.environ, NUMBA_THREADING_LAYER='omp', NUMBA_NUM_THREADS=str(args.threads),
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        command = [mpiexec, '-n', str(p), sys.executable, str(ROOT / 'main.py'), '--sizes',
                   *map(str, candidates), '--threads', str(args.threads), '--output', str(target)]
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=300)
        (output / f'refinement_p{p}.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
        if completed.returncode:
            raise RuntimeError(f'Уточнение p={p}: {completed.stdout}\n{completed.stderr}')
        rows.extend(json.loads(target.read_text(encoding='utf-8')))
        print(f'p={p}: уточнено {len(candidates)} размеров ниже N={first}', flush=True)
    rows.sort(key=lambda r: (r['processes'], r['n']))
    write_csv(ROOT / 'results.csv', [r for r in rows if r['n'] == 2000])
    write_csv(ROOT / 'scalability.csv', rows)
    thresholds = []
    for p in (2, 4, 8):
        tested = sorted((r for r in rows if r['processes'] == p), key=lambda r: r['n'])
        passed = [r for r in tested if r['efficiency'] >= 0.7]
        thresholds.append(dict(processes=p, target_efficiency=0.7,
                               first_tested_n=passed[0]['n'] if passed else None,
                               status='experimental_minimum_over_admissible_sizes' if passed else 'not_reached_in_tested_range',
                               tested_sizes=[r['n'] for r in tested],
                               max_tested_n=tested[-1]['n']))
    (output / 'thresholds.json').write_text(json.dumps(thresholds, ensure_ascii=False, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'plot_graphs.py')], check=True)


if __name__ == '__main__':
    main()
