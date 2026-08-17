"""自定义运行的并发闸：名额上限、超时泄载、名额归还。"""
import threading
import time
from unittest import mock

from django.test import SimpleTestCase

from judge.services import judge_queue
from judge.services.judge_queue import RunQueueBusy


class RunSlotTests(SimpleTestCase):
    """_RUN_WORKERS / _RUN_QUEUE_WAIT 在模块导入时就读掉了，这里直接替换模块变量。"""

    WORKERS = 2

    def setUp(self):
        self._patches = [
            mock.patch.object(judge_queue, '_run_slots',
                              threading.BoundedSemaphore(self.WORKERS)),
            mock.patch.object(judge_queue, '_RUN_WORKERS', self.WORKERS),
            mock.patch.object(judge_queue, '_RUN_QUEUE_WAIT', 0.5),
            # 排队超时会 logger.warning，这里是预期行为，别刷测试输出
            mock.patch.object(judge_queue.logger, 'warning'),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self._patches])

    def test_concurrency_never_exceeds_limit(self):
        live = peak = busy = done = 0
        lock = threading.Lock()

        def worker():
            nonlocal live, peak, busy, done
            try:
                with judge_queue.run_slot():
                    with lock:
                        live += 1
                        peak = max(peak, live)
                    time.sleep(0.2)
                    with lock:
                        live -= 1
                        done += 1
            except RunQueueBusy:
                with lock:
                    busy += 1

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertLessEqual(peak, self.WORKERS, f'并发峰值 {peak} 超过上限')
        self.assertEqual(done + busy, 8)

    def test_sheds_load_instead_of_queueing_forever(self):
        """名额占满时应快速回 503，而不是把请求一直挂着。"""
        held = threading.Event()
        release = threading.Event()

        def hold():
            with judge_queue.run_slot():
                held.set()
                release.wait(timeout=5)

        holders = [threading.Thread(target=hold) for _ in range(self.WORKERS)]
        for t in holders:
            t.start()
        held.wait(timeout=2)
        time.sleep(0.05)

        started = time.monotonic()
        with self.assertRaises(RunQueueBusy):
            with judge_queue.run_slot():
                pass
        waited = time.monotonic() - started

        release.set()
        for t in holders:
            t.join()

        self.assertGreaterEqual(waited, 0.4, '应当真的等满配置的时间')
        self.assertLess(waited, 2.0, '不该无限期挂着')

    def test_slot_released_after_normal_exit(self):
        for _ in range(self.WORKERS * 3):
            with judge_queue.run_slot():
                pass

    def test_slot_released_after_exception(self):
        for _ in range(self.WORKERS * 3):
            with self.assertRaises(ValueError):
                with judge_queue.run_slot():
                    raise ValueError('沙箱异常')
        # 名额若没归还，这里会卡到超时后抛 RunQueueBusy
        with judge_queue.run_slot():
            pass
