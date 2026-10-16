"""评测队列：自定义运行的并发闸（名额上限、超时泄载、名额归还）与评测线程的数据库连接回收。"""
import threading
import time
from unittest import mock, skipUnless

from django.db import connection, connections
from django.test import SimpleTestCase, TransactionTestCase

from judge.services import judge_queue
from judge.services.judge_queue import RunQueueBusy

from .base import OJTestCase


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


def kill_current_connection():
    """
    在服务端掐断本线程的数据库连接，客户端对象仍以为自己连着——
    与 MySQL 空闲超时（wait_timeout）断开、或 MySQL 重启后的状态一致。
    """
    with connection.cursor() as c:
        c.execute('SELECT CONNECTION_ID()')
        conn_id = c.fetchone()[0]
    other = connections.create_connection('default')
    try:
        with other.cursor() as c:
            c.execute('KILL CONNECTION %s', [conn_id])
    finally:
        other.close()


@skipUnless(connection.vendor == 'mysql', '依赖 MySQL 的 CONNECTION_ID() 与断线行为，SQLite 下跳过')
class JudgeTaskConnectionTests(TransactionTestCase):
    """
    评测池的线程常驻复用，Django 不会像处理请求那样替它回收数据库连接。连接一旦被
    MySQL 断开，这条线程之后的每次评测都会失败，提交永远停在 Pending。

    必须用 TransactionTestCase：TestCase 把每个测试包在事务里，事务中途关闭连接会直接报错。
    """

    def setUp(self):
        user = OJTestCase.make_user('conn_tester')
        self.problem = OJTestCase.make_problem()
        self.sub = OJTestCase.make_submission(user, self.problem, status='Pending', score=0)
        # 测试失败时连接可能还是断的；收尾前换掉，免得清库和后续测试跟着报错
        self.addCleanup(connection.close)

    @staticmethod
    def _judge_ok(sub, prob):
        """替代真实评测：只写库，不起沙箱。"""
        sub.status = 'AC'
        sub.save(update_fields=['status'])

    def _run_task(self, judge):
        with mock.patch('judge.services.judger.judge_submission', side_effect=judge):
            judge_queue._judge_task(self.sub.id, self.problem.id)

    def test_recovers_after_connection_dropped_while_idle(self):
        """线程空闲期间连接被 MySQL 断开，下一次评测照常完成。"""
        kill_current_connection()
        self._run_task(self._judge_ok)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'AC')

    def test_releases_connection_after_task(self):
        """评测结束就归还连接，线程不再长期攥着一条连接。"""
        self._run_task(self._judge_ok)
        self.assertIsNone(connection.connection)

    def test_fallback_result_written_when_connection_drops_mid_task(self):
        """评测中途数据库断开：换一条连接写入兜底的 RE，前端不会一直轮询。"""
        def judge_then_lose_db(sub, prob):
            kill_current_connection()
            self._judge_ok(sub, prob)       # 连接已断，这里抛 OperationalError

        with mock.patch.object(judge_queue.logger, 'exception') as log_exception:
            self._run_task(judge_then_lose_db)
        log_exception.assert_called_once()
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'RE')
        self.assertEqual(self.sub.error_info, 'Internal judge error')
