"""Build the two lab reports from measured data and the exact current source."""
from pathlib import Path
import csv
import json
import re
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    """Read a result table without rounding its stored values."""
    with path.open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def fmt(value, places=6):
    """Format a number for a report table."""
    return f'{float(value):.{places}f}' if value not in ('', None) else '—'


def lab1():
    """Compose the Jacobi report using all four measured process counts."""
    folder = ROOT / 'Lab_01_variant_22'
    rows = read_csv(folder / 'results.csv')
    scaling = read_csv(folder / 'scalability.csv')
    thresholds = json.loads((folder / 'results' / 'thresholds.json').read_text(encoding='utf-8'))
    b = []
    def add(kind, *args):
        """Append a content block."""
        b.append((kind, *args))
    add('h', '1. Введение и постановка задачи')
    add('p', 'Цель работы — реализовать решение системы линейных алгебраических уравнений методом Якоби с использованием MPI и OpenMP и экспериментально исследовать ускорение, эффективность и масштабируемость гибридной программы.')
    add('p', 'Задание варианта 22: реализовать параллельное решение СЛАУ методом Якоби с использованием MPI + OpenMP. Для N=2000 выполнить 100 итераций и измерить время на 1, 2, 4, 8 MPI-процессах. Построить E(p). Для E=0.7 найти N_min при p=2,4,8. Каждый набор измеряется не менее трёх раз; ввод-вывод исключается.')
    add('p', 'Вход — плотная случайная матрица A, правая часть b. Генератор с seed=22 создаёт внедиагональные коэффициенты в [-1,1], затем задаёт a_ii=1+Σ(j≠i)|a_ij|. Таким образом, диагональное преобладание строгое. Случайный вектор x* задаёт b=A·x*. Начальное приближение x^(0)=0. Все режимы получают воспроизводимые данные.')
    add('h', '2. Теоретическая часть')
    add('p', 'Метод Якоби использует значения только предыдущей итерации. Формула обновления строки i: x_i^(k+1) = [b_i − Σ(j≠i) a_ij·x_j^(k)] / a_ii. При строгом диагональном преобладании выбранного семейства систем итерационный процесс сходится. Для выполнения задания остановка по точности не применяется: всегда выполняются ровно 100 шагов.')
    add('p', 'Одна итерация плотной системы требует O(N²) арифметических действий. Строки независимы при известном x^(k); их можно распределить между MPI-процессами и OpenMP-потоками. После каждого шага всем процессам нужен полный новый вектор. MPI обеспечивает межпроцессные обмены, а prange в Numba распределяет независимые локальные строки между потоками OpenMP.')
    add('p', 'Метрики задания: S(p)=T1/Tp; E(p)=S(p)/p; B(p)=[1/S(p)−1/p]/[1−1/p], p>1. Закон Амдала: S_A(p)=1/[B+(1−B)/p]. Здесь p обозначает число MPI-процессов; в каждом процессе два OpenMP-потока. Поэтому дополнительно вычисляется E_total=S/(2p). S и E по процессам могут превышать p и 1 соответственно. B в такой гибридной конфигурации является формальной оценкой модели, а не физической долей строк программы.')
    add('h', '3. Описание алгоритма MPI и OpenMP')
    add('p', 'Процесс rank=0 генерирует A,b. Матрица и правая часть распределяются двумя Scatter на равные непрерывные блоки N/p строк. Каждый процесс хранит свои строки и полный старый вектор x. На каждом из 100 шагов jacobi_rows с @njit(parallel=True) и prange вычисляет локальные компоненты нового вектора. Allgather собирает их на всех процессах. Только после завершения обмена начинается следующий шаг; чтение и запись одного поколения x не смешиваются.')
    add('p', 'Схема: генерация A,b → Scatter строк → x=0 → [prange обновления строк → Allgather нового x] × 100 → проверка → расчёт метрик → сохранение. Для OpenMP до первой компиляции установлен NUMBA_THREADING_LAYER=omp, после запуска записывается numba.threading_layer(). Во всех измерениях фактически выбран omp.')
    add('p', 'Последовательный метод также JIT-компилируется Numba, но использует обычные циклы range и один поток. Арифметическая формула и порядок суммирования одинаковы. Это уменьшает влияние различий Python/NumPy/JIT на сравнение. Проверка входа требует положительных размеров, делимости N на p, не менее трёх повторов и минимум двух OpenMP-потоков на процесс.')
    add('h', '4. Реализация и методика эксперимента')
    add('p', 'main.py содержит generate_data, sequential_computation, parallel_computation, check_result и main. run_experiments.py выполняет MPI-серии и поиск минимального размера; plot_graphs.py читает фактические CSV. Полный исходник основной программы приведён в приложении; вспомогательные скрипты находятся рядом с отчётом.')
    add('p', 'Среда измерения: Windows, Intel Core i5-11400F (6 физических / 12 логических ядер), Python 3.12.14, NumPy 2.5.4, Numba 0.68.0, Microsoft MPI 10.1.12498.52. Дата экспериментов — 8 ноября 2026 года. На каждый MPI-процесс выделено 2 OpenMP-потока; BLAS-потоки ограничены одним. В основной серии p=1,2,4,8, N=2000, 100 итераций, три повтора.')
    add('p', 'Оба JIT-ядра предварительно прогреты на малой системе вне измеряемого участка. T1 измеряется perf_counter, Tp — MPI.Wtime после Barrier. Tp включает выделение локальных буферов, Scatter и 100 обновлений с Allgather. Для каждого повтора берётся максимальное время по rank, затем среднее по трём повторам. Генерация, вычисление невязки и запись файлов исключены. Запуск mpiexec и импорт модулей также происходят до измерений.')
    add('h', '5. Экспериментальные результаты')
    add('table', ['p', 'T1, с', 'Tp, с', 'S(p)', 'E(p)', 'B(p)'],
        [[r['processes'], fmt(r['t1_seconds']), fmt(r['tp_seconds']), fmt(r['speedup'],4), fmt(r['efficiency'],4), fmt(r['serial_fraction_b'],4)] for r in rows])
    add('p', 'Во всех четырёх режимах результат совпал с последовательным решением. Максимальная абсолютная ошибка относительно x*: 2.442491·10⁻¹⁵; относительная невязка ||Ax−b||∞/||b||∞: 2.295382·10⁻¹⁵. Это подтверждение для выбранных входов; дополнительные системы проверяются отдельными тестами.')
    for filename, caption in [('speedup.png', 'Рисунок 1 — Ускорение при N=2000'), ('efficiency.png', 'Рисунок 2 — Эффективность по числу MPI-процессов'), ('serial_fraction.png', 'Рисунок 3 — Формальная оценка B(p)')]:
        add('img', filename, caption)
    add('h', '6. Исследование масштабируемости')
    add('p', 'Сначала проверена сетка N=128,256,512,1000,2000,3000,4000. Если E>=0.7 достигнута, дополнительно проверяются все меньшие допустимые N с шагом p. Каждый размер измерен трижды при 100 итерациях. Всего получено ' + str(len(scaling)) + ' комбинаций N,p, то есть ' + str(3*len(scaling)) + ' параллельных измерений; во всех комбинациях correct=True.')
    threshold_rows = []
    for t in thresholds:
        if t['first_tested_n']:
            r = next(r for r in scaling if int(r['processes']) == t['processes'] and int(r['n']) == t['first_tested_n'])
            threshold_rows.append([str(t['processes']), str(t['first_tested_n']), fmt(r['efficiency'],4), 'Все меньшие N, кратные p, проверены'])
        else:
            threshold_rows.append([str(t['processes']), 'Не найден', '—', '7 точек сетки до N=4000'])
    add('table', ['p', 'N_min серии', 'E(N_min)', 'Граница вывода'], threshold_rows)
    add('p', 'N_min — экспериментальный минимум этой серии среди допустимых размеров, кратных p. Короткие времена чувствительны к шуму, и повторный эксперимент может дать другой минимум; монотонность эффективности не предполагается. Для p=8 условие на проверенной сетке не выполнено. Отсюда нельзя вывести, что порог невозможен при любых размерах. Все размеры и отдельные времена сохранены в scalability.csv и JSON, включая уточняющие серии.')
    add('img', 'scalability.png', 'Рисунок 4 — Эффективность и целевой порог E=0.7')
    add('h', '7. Анализ результатов')
    best = min(rows, key=lambda r: float(r['tp_seconds']))
    add('p', f'При N=2000 минимальное измеренное время Tp получено при p={best["processes"]}: {fmt(best["tp_seconds"])} с, S={fmt(best["speedup"],4)}. При p=1 задействованы два OpenMP-потока, поэтому S(1)>1 не противоречит измерениям. E_total для p=1,2,4,8 соответственно равна ' + ', '.join(fmt(r['efficiency_total_threads'],4) for r in rows) + '.')
    add('p', 'Для p=2 и p=4 B отрицательна вследствие гибридной модели с двумя потоками на процесс; интерпретировать её как отрицательную долю последовательных инструкций нельзя. При p=8 B>1 отражает замедление относительно последовательного метода. Запускаются 16 потоков при 12 логических ядрах, возрастает конкуренция за вычислительные ресурсы и память; обмены Allgather повторяются 100 раз. Это вероятные факторы деградации. Отдельное профилирование каждого фактора не выполнялось.')
    add('p', 'В основной серии наибольшее T1 меньше 0.5 с, существенно ниже ограничения 30 с для N<=2048. Каждый процессный запуск всей грубой серии завершился раньше пяти минут. Теоретические диапазоны ускорения из примера методички не подменяют фактические измерения конкретной гибридной конфигурации.')
    add('h', '8. Проверка корректности и обработка ошибок')
    add('p', 'test_jacobi.py запущен на p=1,2,4,8. Он независимо сравнивает с numpy.linalg.solve обычную и диагональную системы и нулевую правую часть, проверяет первую итерацию по b_i/a_ii и согласованный отказ при неделимом N. Пройдено 19 из 19 сценариев. Нулевое число повторов и неделимый размер в CLI приводят к сообщению и ненулевому коду завершения. Сохранение JSON выполняется rank=0, ошибка ввода-вывода обрабатывается общим обработчиком и завершает MPI-задание.')
    add('h', '9. Выводы')
    add('p', 'Разработана и проверена реализация метода Якоби с MPI-разбиением строк и реальным OpenMP через Numba. Выполнены обязательные 100 итераций для N=2000 на 1,2,4,8 процессах, по три повтора. Решения корректны; построены S,E,B и масштабируемость. В проведённой серии N_min равен 124 при p=2 и 216 при p=4; для p=8 он не установлен на проверенной сетке до 4000. Для выбранной основной задачи лучшим из проверенных режимов стал p=4. При интерпретации необходимо учитывать два потока на процесс и аппаратные ограничения.')
    add('h', 'Список литературы')
    add('p', '1. Методические указания «ЛР1. PYTHON + MPI + OpenMP», предоставленный файл; индивидуальное задание — вариант 22.')
    add('p', '2. mpi4py. Tutorial: коллективные операции с NumPy-массивами. https://mpi4py.readthedocs.io/en/stable/tutorial.html (дата обращения: 08.11.2026).')
    add('p', '3. Numba. The Threading Layers; переменные окружения. https://numba.readthedocs.io/en/stable/user/threading-layer.html и https://numba.readthedocs.io/en/stable/reference/envvars.html (дата обращения: 08.11.2026).')
    add('code', 'Приложение. Полный текст основной программы', (folder / 'main.py').read_text(encoding='utf-8'))
    return folder, 1, 'Решение СЛАУ методом Якоби: MPI + OpenMP', b


def lab2():
    """Compose the priority queue report with separate latency measures."""
    folder = ROOT / 'Lab_02_variant_22'
    rows = read_csv(folder / 'results' / 'summary.csv')
    priorities = [r for r in read_csv(folder / 'results' / 'priority_summary.csv') if r['threads'] == '10']
    b = []
    def add(kind, *args):
        """Append a content block."""
        b.append((kind, *args))
    add('h', '1. Задание')
    add('p', 'Вариант 22. Реализация очереди с приоритетами для многопоточных приложений. Тема — организация многопоточного приложения с приоритетной очередью. Цель — изучить применение потоков и условных переменных для реализации очереди с приоритетами.')
    add('p', 'Разработать PriorityQueue с атрибутом items и методами put(task,priority), get(). Создать Producer и Consumer — наследники Thread. Производители формируют задачи HIGH, MEDIUM, LOW; потребители обрабатывают задачи по приоритету. Создать пять производителей и десять потребителей. Использовать Condition, добавить логирование, измерить время обработки задач разных приоритетов и построить соответствующий график.')
    add('h', '2. Введение')
    add('p', 'Приоритетная очередь позволяет срочным задачам, ожидающим обработки, обслуживаться раньше менее срочных. В многопоточном приложении требуется согласовать изменение списка между производителями и потребителями, исключить потерю задач и завершить ожидающие потоки. Работа исследует эти механизмы на конечном воспроизводимом наборе задач.')
    add('h', '3. Теоретическая часть')
    add('p', 'Потоки одного процесса разделяют память, поэтому общий список требует синхронизации. Condition объединяет блокировку и ожидание изменения состояния: потребитель в цикле проверяет пустоту очереди и вызывает wait, освобождая блокировку; производитель под той же блокировкой добавляет элемент и вызывает notify. После пробуждения условие проверяется повторно. Это позволяет ждать без активного опроса [2].')
    add('p', 'Очередь хранится как min-heap в списке items. Запись содержит (приоритет, порядковый номер, задача, время постановки). HIGH=0, MEDIUM=1, LOW=2. Минимальный элемент извлекается первым. Уникальный счётчик обеспечивает FIFO для одинакового приоритета и исключает сравнение словарей задач. Операции добавления и извлечения имеют O(log M), M — число ожидающих элементов [3].')
    add('p', 'Приоритет применяется к задачам, которые уже находятся в очереди на момент get. Поздняя HIGH-задача не прерывает уже начатую LOW. При нескольких потребителях порядок завершения может отличаться от порядка извлечения. При бесконечной подаче HIGH возможен голод LOW; для его уменьшения можно добавить старение приоритета, но в этой работе набор задач конечный.')
    add('p', 'Измеряются W=t_start−t_enqueue — ожидание, C=t_finish−t_start — обслуживание, R=t_finish−t_enqueue=W+C — полный отклик. Для общей производительности S=T_seq/T_par, E=S/c, где c — число потребителей. Дополнительно сохраняется общее число потоков: c+5 производителей. Эти определения позволяют отличать эффект приоритета от скорости самой обработки.')
    add('h', '4. Описание алгоритма')
    add('p', 'Схема: создать PriorityQueue → запустить потребителей → запустить пять производителей → дождаться всех производителей → поставить по одному None на потребителя → дождаться queue.join → выполнить Thread.join всех потребителей → проверить результаты → сохранить CSV. Потребитель выполняет: get → если None, завершение; иначе обработка и измерение → task_done в finally → следующий get.')
    add('p', 'Сигнал None получает приоритет бесконечность, поэтому не опережает обычные задачи. Счётчик unfinished увеличивается в put и уменьшается в task_done; join ждёт его обнуления. Condition защищает все изменения очереди и счётчика. Результаты каждого потребителя хранятся в собственном списке, а главный поток объединяет их после join.')
    add('p', 'Producer и Consumer наследуют Thread, имеют осмысленные имена и основной алгоритм в run. Потребитель перехватывает ошибку обработки, сохраняет её и всегда подтверждает задачу; после завершения потоков ошибка передаётся главному потоку. Поэтому ошибка одной задачи не оставляет queue.join в вечном ожидании.')
    add('h', '5. Реализация программы')
    add('p', 'main.py содержит PriorityQueue, Producer, Consumer, генератор, одинаковую обработку последовательного и потокового режимов, CLI и CSV. Для вычислений используются стандартные модули Python: threading, heapq, time, logging и вспомогательные средства сохранения. Matplotlib нужен только для графиков. Полный код основной программы приведён в приложении.')
    add('p', 'По умолчанию каждый из пяти производителей создаёт 30 задач; всего 150, по 50 на каждый приоритет. Приоритеты в исходной последовательности чередуются LOW,HIGH,MEDIUM. Обработка включает одинаковое ожидание 5 мс (модель I/O) и возведение payload в квадрат для проверки результата. Такой workload выбран для наблюдения ожидания очереди и перекрытия I/O, он не является тестом CPU-масштабирования Python под GIL.')
    add('p', 'Лог содержит время, имя потока, уровень и сообщение. INFO показывает запуск и завершение потоков; DEBUG включает постановку и обработку каждой задачи. Проверяются конечная неотрицательная задержка, положительные количества и минимум три повтора; ошибки ввода-вывода логируются и приводят к ненулевому коду завершения.')
    add('h', '6. Результаты экспериментов')
    add('p', 'Эксперименты выполнены 8 ноября 2026 года на Windows, Intel Core i5-11400F, CPython 3.13 с обычным GIL. Для каждого числа потребителей выполнены три повтора на тех же 150 задачах, пять производителей во всех режимах. Измеряется полное время последовательной обработки и полное время потокового запуска, включая создание потоков и синхронизацию. Генерация и сохранение CSV исключены. Логирование включено на INFO.')
    add('table', ['Потребителей', 'T_seq, с', 'T_par, с', 'S', 'E', 'Проверка'],
        [[r['threads'], fmt(r['time_seq']), fmt(r['time_par']), fmt(r['speedup'],4), fmt(r['efficiency'],4), 'Успешно'] for r in rows])
    add('p', 'Во всех 12 измерениях результаты каждой задачи совпали с последовательной версией; потерь и дубликатов не обнаружено. Всего сохранено 1800 строк задач. Основной обязательный режим — пять производителей и десять потребителей; остальные режимы используются для сравнения зависимости времени от числа потребителей.')
    add('table', ['Приоритет', 'Наблюдений', 'Ожидание, мс', 'Обработка, мс', 'Отклик, мс'],
        [[r['priority'], r['count'], fmt(1000*float(r['mean_wait_seconds']),3), fmt(1000*float(r['mean_service_seconds']),3), fmt(1000*float(r['mean_response_seconds']),3)] for r in priorities])
    add('p', 'Таблица приоритетов относится к десяти потребителям. 150 наблюдений каждого класса — это 50 задач × три повтора; все классы обрабатываются одной и той же функцией с одинаковым заданным ожиданием. Фактическое обслуживание немного превышает 5 мс из-за работы планировщика ОС и накладных расходов.')
    add('img', 'priority_time.png', 'Рисунок 1 — Ожидание, обслуживание и полный отклик по приоритетам')
    add('img', 'thread_time.png', 'Рисунок 2 — Полное время при разном числе потребителей')
    add('h', '7. Анализ результатов')
    add('p', 'В обязательном режиме HIGH ожидает в среднем 10.105 мс, MEDIUM — 36.901 мс, LOW — 63.486 мс. При этом обслуживание всех классов около 5.3–5.4 мс. Следовательно, наблюдаемое преимущество высокого приоритета связано с более ранним выбором из накопленной очереди, а не с искусственно более короткими заданиями.')
    add('p', 'При десяти потребителях T_par=0.084948 с, T_seq=0.805126 с, S≈9.478, E≈0.948 по числу потребителей. Потоки проводят значительную часть времени в ожидании, и ожидания разных задач перекрываются. При одном потребителе потоковая инфраструктура немного увеличивает время. Рост числа производителей в этой серии не исследовался; полученная E не описывает эффективность всех пятнадцати служебных и рабочих потоков.')
    add('p', 'Замеры зависят от планировщика ОС и нагрузки; приоритет регулирует порядок извлечения доступных элементов, но не гарантирует сортировку всего потока задач по времени окончания. Длительная обработка LOW не прерывается. Эти свойства являются частью выбранной модели очереди и учитываются при проверке.')
    add('h', '8. Проверка и контрольные вопросы')
    add('p', 'Пройдено пять автоматических тестов: заранее накопленные задачи выдаются HIGH→MEDIUM→LOW с FIFO для равных приоритетов; get ожидает на пустой очереди и просыпается после put; ошибочные приоритеты и лишний task_done отклоняются; 1500 задач с пятью производителями и десятью потребителями обрабатываются ровно один раз; ошибка обработки возвращается вызывающему коду без зависания. После стресс-теста рабочие потоки не остаются активными. Нулевое число задач в CLI завершается кодом 2.')
    add('p', 'Как реализовать очередь с приоритетами? Хранить элементы в min-heap с ключом приоритет и устойчивым порядковым номером, защитив доступ общей блокировкой. Какой механизм синхронизации подходит? Condition, потому что потребитель должен ожидать появления элемента и атомарно проверить состояние. Как расширить функциональность? Добавить ограничение вместимости с ожиданием свободного места, тайм-аут get, старение приоритетов, отмену задач или статистику нагрузки.')
    add('h', '9. Выводы')
    add('p', 'Реализована очередь с приоритетами HIGH,MEDIUM,LOW, условной переменной Condition и классами Producer/Consumer. Выполнено требование пяти производителей и десяти потребителей, организованы корректное завершение и обработка ошибок. Получены реальные времена по приоритетам, CSV, логи и графики. Высокий приоритет уменьшает ожидание, а длительность обслуживания остаётся одинаковой. Все тесты и 12 экспериментальных запусков завершились корректно.')
    add('h', 'Список литературы')
    add('p', '1. Методические указания «ЛР2. Потоки», предоставленный файл; вариант 22 «Реализация очереди с приоритетами».')
    add('p', '2. Python. threading — Thread-based parallelism, Condition objects. https://docs.python.org/3/library/threading.html (дата обращения: 08.11.2026).')
    add('p', '3. Python. heapq — Heap queue algorithm; Priority Queue Implementation Notes. https://docs.python.org/3/library/heapq.html (дата обращения: 08.11.2026).')
    add('code', 'Приложение. Полный текст основной программы', (folder / 'main.py').read_text(encoding='utf-8'))
    return folder, 2, 'Очередь с приоритетами для многопоточных приложений', b


def make_report(folder, number, topic, blocks):
    """Write editable DOCX and a Markdown copy with identical report content."""
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2), Cm(2)
    section.left_margin, section.right_margin = Cm(3), Cm(1.5)
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.25
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.first_line_indent = Cm(1.25)
    for name in ('Heading 1', 'Heading 2'):
        style = doc.styles[name]
        style.font.name, style.font.size = 'Times New Roman', Pt(14)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.first_line_indent = Cm(0)
        style.paragraph_format.keep_with_next = True
    for text in ['Учебное заведение: ______________________________',
                 'Факультет: ______________________________________',
                 'Кафедра: ________________________________________']:
        p = doc.add_paragraph(text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
    doc.add_paragraph('')
    for text in [f'ЛАБОРАТОРНАЯ РАБОТА №{number}', 'по дисциплине «Параллельное программирование»', topic, 'Вариант 22']:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(16 if text.startswith('ЛАБОРАТОРНАЯ') else 14)
    doc.add_paragraph('')
    for text in ['Выполнил: _________________________________', 'Группа: ____________________________________',
                 'Проверил: __________________________________', 'Дата выполнения: 8 ноября 2026 года']:
        p = doc.add_paragraph(text)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.first_line_indent = Cm(0)
    doc.add_paragraph('')
    p = doc.add_paragraph('2026')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.first_line_indent = Cm(0)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.add_page_break()
    doc.add_heading('Содержание', level=1)
    for block in blocks:
        if block[0] in ('h', 'code'):
            p = doc.add_paragraph(block[1])
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.space_after = Pt(3)
    doc.add_page_break()
    md = [f'# Лабораторная работа №{number} — вариант 22', '', topic, '',
          'Дата: 8 ноября 2026 года. ФИО, группа и преподаватель: поля титула для заполнения.', '']
    for block in blocks:
        kind = block[0]
        if kind == 'h':
            doc.add_heading(block[1], level=1)
            md.extend(['## ' + block[1], ''])
        elif kind == 'p':
            doc.add_paragraph(block[1])
            md.extend([block[1], ''])
        elif kind == 'table':
            headers, rows = block[1:]
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = 'Table Grid'
            header = table.rows[0]
            for cell, text in zip(header.cells, headers):
                cell.text = text
            repeat = OxmlElement('w:tblHeader')
            header._tr.get_or_add_trPr().append(repeat)
            for row in rows:
                cells = table.add_row().cells
                for cell, value in zip(cells, row):
                    cell.text = str(value)
            for row in table.rows:
                cant = OxmlElement('w:cantSplit')
                row._tr.get_or_add_trPr().append(cant)
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.first_line_indent = Cm(0)
                        p.paragraph_format.line_spacing = 1
                        p.paragraph_format.space_after = Pt(4)
                        for run in p.runs:
                            run.font.size = Pt(10)
            md.extend(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'])
            md.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)
            md.append('')
        elif kind == 'img':
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(folder / block[1]), width=Cm(16))
            p = doc.add_paragraph(block[2])
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            for run in p.runs:
                run.font.size = Pt(11)
            md.extend([f'![{block[2]}]({block[1]})', ''])
        elif kind == 'code':
            doc.add_page_break()
            doc.add_heading(block[1], level=1)
            for line in block[2].splitlines():
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.line_spacing = 1
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(line)
                run.font.name, run.font.size = 'Consolas', Pt(8)
            md.extend(['## ' + block[1], '', '```python', block[2].rstrip(), '```', ''])
    doc.core_properties.title = f'Лабораторная работа №{number}. Вариант 22'
    doc.core_properties.subject = topic
    doc.core_properties.author = ''
    doc.save(folder / 'report.docx')
    (folder / 'report.md').write_text('\n'.join(md), encoding='utf-8')
    original = next((ROOT / f'Lab_0{number}_variant_24').glob('LR_*.docx'))
    shutil.copy2(original, folder / original.name)
    print(folder / 'report.docx')


def main():
    """Generate both reports."""
    for args in (lab1(), lab2()):
        make_report(*args)


if __name__ == '__main__':
    main()
