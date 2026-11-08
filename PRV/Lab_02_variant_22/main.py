"""ЛР2, вариант 22: очередь с приоритетами, 5 производителей и 10 потребителей."""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import logging
import threading
import time
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
HIGH, MEDIUM, LOW = 0, 1, 2
PRIORITY_NAMES = {HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW'}


class PriorityQueue:
    """Потокобезопасная min-heap: меньший номер означает больший приоритет."""

    def __init__(self):
        """Создать очередь, условную переменную и счётчик незавершённых задач."""
        self.items = []
        self.condition = threading.Condition()
        self.sequence = 0
        self.unfinished = 0
        self.history = []

    def put(self, task, priority):
        """Добавить задачу; None с бесконечным приоритетом завершает потребителя."""
        if task is not None and priority not in PRIORITY_NAMES:
            raise ValueError('Допустимы приоритеты HIGH=0, MEDIUM=1, LOW=2')
        if task is None and priority != float('inf'):
            raise ValueError('Сигнал None должен иметь priority=inf')
        with self.condition:
            enqueued = time.perf_counter()
            heapq.heappush(self.items, (priority, self.sequence, task, enqueued))
            self.sequence += 1
            self.unfinished += 1
            self.condition.notify()

    def get(self):
        """Ожидать задачу в цикле; вернуть task, priority, момент enqueue и номер извлечения."""
        with self.condition:
            while not self.items:
                self.condition.wait()
            priority, sequence, task, enqueued = heapq.heappop(self.items)
            order = len(self.history)
            # История фиксируется под той же блокировкой, что извлечение.
            self.history.append((priority, sequence, None if task is None else task['id']))
            return task, priority, enqueued, order

    def task_done(self):
        """Подтвердить завершение ровно одной полученной задачи."""
        with self.condition:
            if self.unfinished <= 0:
                raise ValueError('task_done вызван слишком много раз')
            self.unfinished -= 1
            if self.unfinished == 0:
                self.condition.notify_all()

    def join(self):
        """Дождаться подтверждения всех поставленных задач и сигналов завершения."""
        with self.condition:
            while self.unfinished:
                self.condition.wait()


def process_task(task):
    """Смоделировать одинаковую I/O-задержку и вычислить проверяемый результат."""
    time.sleep(task['service_seconds'])
    return task['payload'] ** 2


class Producer(threading.Thread):
    """Именованный производитель задач трёх приоритетов."""

    def __init__(self, number, tasks, queue, logger):
        """Передать производителю его детерминированный набор задач."""
        super().__init__(name=f'Producer-{number}')
        self.tasks, self.queue, self.logger = tasks, queue, logger
        self.error = None

    def run(self):
        """Поместить задачи в очередь и сохранить исключение для главного потока."""
        self.logger.info('Начало генерации %d задач', len(self.tasks))
        try:
            for task in self.tasks:
                self.queue.put(task, task['priority'])
                self.logger.debug('Поставлена задача %s, %s', task['id'], PRIORITY_NAMES[task['priority']])
        except Exception as exc:
            self.error = str(exc)
            self.logger.exception('Ошибка производителя')
        self.logger.info('Производитель завершён')


class Consumer(threading.Thread):
    """Именованный потребитель, завершающийся после сигнала None."""

    def __init__(self, number, queue, logger):
        """Создать независимый журнал результатов потока."""
        super().__init__(name=f'Consumer-{number}')
        self.queue, self.logger = queue, logger
        self.records = []
        self.errors = []

    def run(self):
        """Извлекать по приоритету, измерять ожидание и обработку, подтверждать задачи."""
        self.logger.info('Потребитель запущен')
        while True:
            task, priority, enqueued, order = self.queue.get()
            try:
                if task is None:
                    break
                started = time.perf_counter()
                result = process_task(task)
                finished = time.perf_counter()
                self.records.append(dict(task_id=task['id'], priority=PRIORITY_NAMES[priority],
                                         consumer=self.name, dequeue_order=order,
                                         wait_seconds=started - enqueued,
                                         service_seconds=finished - started,
                                         response_seconds=finished - enqueued, result=result))
                self.logger.debug('Обработана задача %s, %s', task['id'], PRIORITY_NAMES[priority])
            except Exception as exc:
                self.errors.append(str(exc))
                self.logger.exception('Ошибка обработки задачи %s', task['id'])
            finally:
                self.queue.task_done()
        self.logger.info('Потребитель завершён')


def create_tasks(producers=5, tasks_per_producer=30, service_seconds=.005):
    """Создать воспроизводимые задачи LOW, HIGH, MEDIUM одинаковой длительности."""
    return [[dict(id=f'{p + 1}-{i + 1}', priority=(LOW, HIGH, MEDIUM)[i % 3],
                  payload=p * tasks_per_producer + i + 1, service_seconds=service_seconds)
             for i in range(tasks_per_producer)] for p in range(producers)]


def sequential_computation(groups):
    """Обработать те же задачи одним потоком с устойчивой сортировкой по приоритету."""
    tasks = sorted((task for group in groups for task in group), key=lambda t: t['priority'])
    return {task['id']: process_task(task) for task in tasks}


def parallel_computation(groups, consumers, logger):
    """Создать потоки, дождаться производителей, затем завершить потребителей сигналами."""
    queue = PriorityQueue()
    workers = [Consumer(i + 1, queue, logger) for i in range(consumers)]
    producers = [Producer(i + 1, group, queue, logger) for i, group in enumerate(groups)]
    started_threads = []
    try:
        for thread in workers + producers:
            thread.start()
            started_threads.append(thread)
    finally:
        # Даже при частичном отказе запуска сначала завершаем живых производителей.
        for thread in started_threads:
            if isinstance(thread, Producer):
                thread.join()
        live_workers = [thread for thread in started_threads if isinstance(thread, Consumer)]
        for _ in live_workers:
            queue.put(None, float('inf'))
        if live_workers:
            queue.join()
        for thread in live_workers:
            thread.join()
    errors = [p.error for p in producers if p.error] + [e for w in workers for e in w.errors]
    if errors:
        raise RuntimeError('; '.join(errors))
    records = sorted((r for worker in workers for r in worker.records), key=lambda r: r['dequeue_order'])
    return records


def setup_logging(level):
    """Настроить время, имя потока, уровень и запись в файл и консоль."""
    (ROOT / 'results').mkdir(exist_ok=True)
    logger = logging.getLogger('lab2.priority_queue')
    logger.setLevel(getattr(logging, level))
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
    for handler in (logging.FileHandler(ROOT / 'results' / 'logs.log', mode='w', encoding='utf-8'),
                    logging.StreamHandler()):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def write_csv(path, rows):
    """Сохранить измерения с заголовком."""
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Провести не менее трёх повторов и сохранить общие и приоритетные метрики."""
    parser = argparse.ArgumentParser(description='ЛР2, вариант 22: приоритетная очередь')
    parser.add_argument('--producers', type=int, default=5)
    parser.add_argument('--threads', '--consumers', dest='threads', type=int, default=10)
    parser.add_argument('--tasks', type=int, default=30, help='Число задач на одного производителя')
    parser.add_argument('--service-ms', type=float, default=5.)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--benchmark', action='store_true', help='Проверить 1, 2, 4 и 10 потребителей')
    parser.add_argument('--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    args = parser.parse_args()
    if min(args.producers, args.threads, args.tasks) < 1 or args.repeats < 3 or not 0 <= args.service_ms < float('inf'):
        parser.error('Нужны положительные количества, repeats >= 3 и конечный service-ms >= 0')
    logger = setup_logging(args.log)
    try:
        groups = create_tasks(args.producers, args.tasks, args.service_ms / 1000)
        raw, details, summaries, priorities = [], [], [], []
        counts = sorted(set([1, 2, 4, args.threads])) if args.benchmark else [args.threads]
        for consumers in counts:
            cases = []
            for repeat in range(1, args.repeats + 1):
                start = time.perf_counter()
                seq = sequential_computation(groups)
                t1 = time.perf_counter() - start
                start = time.perf_counter()
                records = parallel_computation(groups, consumers, logger)
                tp = time.perf_counter() - start
                correct = len(records) == len(seq) and len({r['task_id'] for r in records}) == len(seq) and \
                          {r['task_id']: r['result'] for r in records} == seq
                if not correct:
                    raise RuntimeError('Проверка результатов: ОШИБКА')
                row = dict(threads=consumers, producers=args.producers, total_threads=consumers + args.producers,
                           tasks=len(seq), repeat=repeat, time_seq=t1, time_par=tp,
                           speedup=t1 / tp, efficiency=t1 / tp / consumers, correct=correct)
                raw.append(row)
                cases.append(row)
                details.extend(dict(threads=consumers, repeat=repeat, **r) for r in records)
            t1, tp = mean(r['time_seq'] for r in cases), mean(r['time_par'] for r in cases)
            summaries.append(dict(threads=consumers, producers=args.producers, tasks=len(seq), repeats=args.repeats,
                                  time_seq=t1, time_par=tp, speedup=t1 / tp,
                                  efficiency=t1 / tp / consumers, correct=True))
            for priority in PRIORITY_NAMES.values():
                selected = [r for r in details if r['threads'] == consumers and r['priority'] == priority]
                if selected:
                    priorities.append(dict(threads=consumers, priority=priority, count=len(selected),
                                           mean_wait_seconds=mean(r['wait_seconds'] for r in selected),
                                           mean_service_seconds=mean(r['service_seconds'] for r in selected),
                                           mean_response_seconds=mean(r['response_seconds'] for r in selected)))
            print(json.dumps(summaries[-1], ensure_ascii=False), flush=True)
        for name, rows in [('results', raw), ('summary', summaries), ('tasks', details), ('priority_summary', priorities)]:
            write_csv(ROOT / 'results' / f'{name}.csv', rows)
        (ROOT / 'results' / 'parameters.json').write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding='utf-8')
    except (OSError, RuntimeError, ValueError) as exc:
        logger.exception('Ошибка эксперимента: %s', exc)
        raise SystemExit(1) from exc


if __name__ == '__main__':
    main()
