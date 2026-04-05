"""
Celery 信号处理器
用于自动更新任务执行历史

功能说明:
1. task_prerun: 任务开始执行时，更新 started_at 和 status='running'
2. task_success: 任务成功完成时，更新 completed_at、duration_ms、result 和 status='success'
3. task_failure: 任务失败时，更新 completed_at、duration_ms、error 和 status='failure'
4. task_revoked: 任务被撤销时，标记为 status='failure'

注意事项:
- 使用本地时间 datetime.now() 而非 UTC 时间
- 每次信号处理时创建新的数据库连接，避免 fork pool worker 中的连接共享问题
- Celery 5.x 中 task_id 需要从 sender.request.id 获取
"""

from celery import signals
from datetime import datetime
from loguru import logger
import json
import psycopg2

from app.core.config import settings


def _get_direct_conn():
    """
    创建独立的 psycopg2 直连，供信号处理器专用。

    信号处理器（task_prerun / task_success / task_failure）与任务函数
    在同一 ForkPoolWorker 进程中执行，但执行时机不同：
    - task_prerun  在任务函数体之前触发，此时单例连接池可能是 fork 前的旧连接（已损坏）
    - task_success 在任务函数之后触发，此时任务函数内部可能已调用 reset_instance() 重建了池

    使用独立直连，完全不依赖单例池，无论池处于何种状态都能正常写入。
    每次信号触发时新建连接，用完立即关闭，不影响业务连接池。
    """
    return psycopg2.connect(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        dbname=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        connect_timeout=5
    )


def _execute_direct(sql: str, params: tuple) -> None:
    """执行一条 SQL，使用独立直连，用后关闭。"""
    conn = None
    try:
        conn = _get_direct_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _query_direct(sql: str, params: tuple) -> list:
    """查询并返回结果行列表，使用独立直连，用后关闭。"""
    conn = None
    try:
        conn = _get_direct_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, **kwargs):
    """
    任务开始执行时的回调
    更新任务的started_at时间和状态为running
    """
    try:
        if not task_id:
            return

        started_at = datetime.now()
        _execute_direct(
            """
            UPDATE celery_task_history
            SET status = 'running', started_at = %s
            WHERE celery_task_id = %s
            """,
            (started_at, task_id)
        )
        logger.info(f"任务 {task_id[:8]}... 开始执行")

    except Exception as e:
        logger.error(f"更新任务开始状态失败: {e}")


@signals.task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """
    任务成功完成时的回调
    自动更新任务历史状态为成功

    Celery task_success 信号参数:
    - sender: 任务实例
    - result: 任务返回结果
    - kwargs: 包含 request (TaskRequest对象)
    """
    db = None
    task_id = None
    try:
        # 从 Celery 信号参数中获取 task_id
        # Celery 5.x 中，task_id 位于 sender.request.id
        task_id = kwargs.get('task_id')  # 旧版本兼容
        if not task_id and 'request' in kwargs:
            request = kwargs.get('request')
            if request and hasattr(request, 'id'):
                task_id = request.id

        if not task_id and hasattr(sender, 'request'):
            task_id = sender.request.id

        if not task_id:
            logger.warning(f"task_success 信号未获取到 task_id，跳过处理")
            return

        records = _query_direct(
            "SELECT id, started_at FROM celery_task_history WHERE celery_task_id = %s",
            (task_id,)
        )

        if not records:
            logger.warning(f"任务 {task_id[:8]}... 在数据库中未找到记录")
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()

        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        result_json = result if isinstance(result, dict) else {'value': str(result)}

        _execute_direct(
            """
            UPDATE celery_task_history
            SET status = 'success', completed_at = %s, result = %s, duration_ms = %s
            WHERE celery_task_id = %s
            """,
            (completed_at, json.dumps(result_json), duration_ms, task_id)
        )
        logger.info(f"任务 {task_id[:8]}... 执行成功，耗时 {duration_ms}ms")

    except Exception as e:
        logger.error(f"更新任务成功状态失败: {e} (task_id={task_id[:8] if task_id else 'None'})")
        import traceback
        logger.error(traceback.format_exc())


@signals.task_failure.connect
def task_failure_handler(sender=None, exception=None, traceback=None, **kwargs):
    """
    任务失败时的回调
    自动更新任务历史状态为失败
    """
    db = None
    try:
        task_id = kwargs.get('task_id')
        if not task_id:
            return

        records = _query_direct(
            "SELECT id, started_at FROM celery_task_history WHERE celery_task_id = %s",
            (task_id,)
        )

        if not records:
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()

        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        error_msg = "Unknown error"
        if exception:
            try:
                error_msg = str(exception)
            except Exception:
                error_msg = f"Error type: {type(exception).__name__}"

        if not exception and 'einfo' in kwargs:
            try:
                einfo = kwargs.get('einfo')
                if einfo:
                    error_msg = str(einfo)
            except Exception:
                pass

        _execute_direct(
            """
            UPDATE celery_task_history
            SET status = 'failure', completed_at = %s, error = %s, duration_ms = %s
            WHERE celery_task_id = %s
            """,
            (completed_at, error_msg, duration_ms, task_id)
        )
        logger.error(f"任务 {task_id[:8]}... 执行失败: {error_msg}")

    except Exception as e:
        logger.error(f"更新任务失败状态失败: {e}")


@signals.worker_process_init.connect
def worker_process_init_handler(**kwargs):
    """
    每个 Fork Pool Worker 进程启动时重置 DatabaseManager 单例。

    问题：Celery 使用 fork() 创建 worker 进程，子进程继承父进程的
    DatabaseManager 单例（包含已损坏的连接池），导致第一次查询时报
    "server closed the connection unexpectedly"。

    解决：在 worker 进程初始化时重置单例，强制子进程在首次使用时
    重新创建自己的连接池。
    """
    try:
        from src.database.db_manager import DatabaseManager
        DatabaseManager.reset_instance()
        logger.info("✅ Fork worker 已重置 DatabaseManager 单例（连接池将在首次使用时重建）")
    except Exception as e:
        logger.warning(f"重置 DatabaseManager 单例失败（无害）: {e}")


@signals.task_revoked.connect
def task_revoked_handler(sender=None, **kwargs):
    """
    任务被撤销时的回调
    """
    db = None
    try:
        task_id = kwargs.get('task_id')
        if not task_id:
            return

        records = _query_direct(
            "SELECT id, started_at FROM celery_task_history WHERE celery_task_id = %s",
            (task_id,)
        )

        if not records:
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()

        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        _execute_direct(
            """
            UPDATE celery_task_history
            SET status = 'failure', completed_at = %s, error = 'Task revoked', duration_ms = %s
            WHERE celery_task_id = %s
            """,
            (completed_at, duration_ms, task_id)
        )
        logger.warning(f"任务 {task_id[:8]}... 已被撤销")

    except Exception as e:
        logger.error(f"更新任务撤销状态失败: {e}")
