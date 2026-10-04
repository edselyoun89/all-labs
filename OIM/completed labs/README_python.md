# Запуск лабораторных без MATLAB

Используется [run_all_python.py](./run_all_python.py). Скрипт повторяет основные
вычисления первых четырёх лабораторных работ с помощью NumPy, Pillow, SciPy и
scikit-image.

Из корня проекта выполните в терминале VS Code:

```powershell
$env:PYTHONPATH = "C:/Users/nikit/Desktop/kipu/tmp/oim/deps"
& C:/Users/nikit/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe "C:/Users/nikit/Desktop/kipu/OIM/completed labs/run_all_python.py"
```

Результаты создаются в папках `Lab_01/results_python` ... `Lab_04/results_python`.
В `Lab_03/results_python/transform_checks.txt` записана проверка четырёх эталонных
изображений: все четыре результата совпали с эталонами (`different=0`, `MAE=0`).

Для лабораторной 4 Python-реализация использует аналогичные методы Canny, zero-crossing,
порог Отсу и probabilistic Hough transform; численные параметры могут немного отличаться
от MATLAB Image Processing Toolbox.
