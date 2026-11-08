"""Reproducible checks of the new variant and focused probes of existing labs."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
MPIEXEC = os.environ.get('MPIEXEC', r'C:\Program Files\Microsoft MPI\Bin\mpiexec.exe')


def run(name, folder, args, mpi=None):
    """Run a bounded check and preserve its actual output."""
    command = [PYTHON, *args]
    if mpi is not None:
        command = [MPIEXEC, '-n', str(mpi), *command]
    result = subprocess.run(command, cwd=ROOT / folder, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=90,
                            env=dict(os.environ, PYTHONUTF8='1', NUMBA_NUM_THREADS='2',
                                     OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'))
    row = dict(name=name, folder=folder, command=command, exit_code=result.returncode,
               stdout=result.stdout, stderr=result.stderr)
    print(name, result.returncode, result.stdout.strip()[-350:], flush=True)
    return row


def main():
    """Verify MPI correctness, queues and existing network functionality."""
    checks = []
    for p in (1, 2, 4, 8):
        checks.append(run(f'jacobi_p{p}', 'Lab_01_variant_22', ['test_jacobi.py'], mpi=p))
    checks.append(run('priority_queue_tests', 'Lab_02_variant_22', ['-m', 'unittest', '-v', 'test_priority_queue.py']))
    checks.append(run('lab1_invalid_size', 'Lab_01_variant_22', ['main.py', '--n', '17'], mpi=2))
    checks.append(run('lab1_invalid_repeats', 'Lab_01_variant_22', ['main.py', '--repeats', '0'], mpi=1))
    checks.append(run('lab2_invalid_tasks', 'Lab_02_variant_22', ['main.py', '--tasks', '0']))
    checks.append(run('lab3_smoke', 'Lab_03_variant_24', ['main.py', '--single']))
    for folder in ('Lab_05_variant_24', 'Lab_06_variant_24', 'Lab_07_variant_24'):
        # LR7 integration writes demonstration files: preserve original bytes.
        paths = list((ROOT / folder / 'results').glob('parsed_data.*'))
        backups = {p: p.read_bytes() for p in paths}
        try:
            checks.append(run(folder + '_integration', folder, ['integration_test.py']))
        finally:
            for path, content in backups.items():
                path.write_bytes(content)
    checks.append(run('lab4_source_zero', 'Lab_04_variant_24', ['main.py', '--n', '32'], mpi=2))
    checks.append(run('lab4_source_one_probe', 'Lab_04_variant_24', ['main.py', '--n', '32', '--source', '1'], mpi=2))
    checks.append(run('lab1_old_pivot_probe', 'Lab_01_variant_24', ['-c',
        'import numpy as np; from mpi4py import MPI; from main import sequential_computation, parallel_computation, check_result; '
        'a=np.array([[0.,1.],[1.,0.]]); s=sequential_computation(a); p=parallel_computation(a,MPI.COMM_WORLD); '
        'print({"sequential":s,"parallel":p,"correct":check_result(s,p)})'], mpi=1))
    checks.append(run('lab7_nested_html_probe', 'Lab_07_variant_24', ['-c',
        'from parser import SiteParser; p=SiteParser(); p.feed("<p>Hello <b>nested</b> world</p>"); '
        'print({"expected":["Hello nested world"],"actual":p.paragraphs})']))
    (ROOT / 'analysis' / 'verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
