"""Проверки приоритетов, ожидания, FIFO и отсутствия потерь при конкуренции."""
import logging
import threading
import unittest
from main import PriorityQueue, HIGH, MEDIUM, LOW, create_tasks, parallel_computation


class WaitingConsumer(threading.Thread):
    """Получатель для проверки блокирующего get на пустой очереди."""

    def __init__(self, queue):
        """Сохранить очередь и события теста."""
        super().__init__(daemon=True)
        self.queue = queue
        self.started = threading.Event()
        self.done = threading.Event()
        self.received = None

    def run(self):
        """Дождаться элемента и подтвердить его обработку."""
        self.started.set()
        self.received = self.queue.get()[0]
        self.queue.task_done()
        self.done.set()


class QueueTests(unittest.TestCase):
    """Проверить внешнее поведение очереди и жизненный цикл потоков."""

    def test_priorities_and_fifo(self):
        """Предварительно заполненная очередь выдаёт HIGH, MEDIUM, LOW и FIFO."""
        queue = PriorityQueue()
        for name, priority in [('low-1', LOW), ('high-1', HIGH), ('medium', MEDIUM),
                               ('high-2', HIGH), ('low-2', LOW)]:
            queue.put({'id': name}, priority)
        queue.put(None, float('inf'))
        actual = []
        for _ in range(6):
            task = queue.get()[0]
            actual.append(task['id'] if task else None)
            queue.task_done()
        queue.join()
        self.assertEqual(actual, ['high-1', 'high-2', 'medium', 'low-1', 'low-2', None])

    def test_wait_and_notification(self):
        """get блокируется до put и пробуждается через Condition.notify."""
        queue = PriorityQueue()
        thread = WaitingConsumer(queue)
        thread.start()
        self.assertTrue(thread.started.wait(1))
        self.assertFalse(thread.done.wait(.03))
        queue.put({'id': 'wake'}, HIGH)
        self.assertTrue(thread.done.wait(1))
        thread.join(1)
        self.assertEqual(thread.received['id'], 'wake')
        self.assertFalse(thread.is_alive())

    def test_validation_and_accounting(self):
        """Отклонить неправильные приоритеты и лишние подтверждения."""
        queue = PriorityQueue()
        with self.assertRaises(ValueError):
            queue.put({'id': 'bad'}, 42)
        with self.assertRaises(ValueError):
            queue.put(None, HIGH)
        with self.assertRaises(ValueError):
            queue.task_done()

    def test_concurrent_no_loss(self):
        """5 производителей и 10 потребителей обрабатывают 1500 задач ровно один раз."""
        logger = logging.getLogger('queue-test')
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL)
        groups = create_tasks(5, 300, 0)
        records = parallel_computation(groups, 10, logger)
        expected = {task['id']: task['payload'] ** 2 for group in groups for task in group}
        self.assertEqual(len(records), 1500)
        self.assertEqual({r['task_id']: r['result'] for r in records}, expected)
        self.assertFalse(any(t.name.startswith(('Producer-', 'Consumer-')) for t in threading.enumerate()))

    def test_worker_error_returns(self):
        """Ошибка функции обработки передаётся наверх без зависания join."""
        logger = logging.getLogger('queue-test')
        groups = [[dict(id='bad', priority=HIGH, payload=1, service_seconds=-1)]]
        with self.assertRaises(RuntimeError):
            parallel_computation(groups, 2, logger)


if __name__ == '__main__':
    unittest.main(verbosity=2)
