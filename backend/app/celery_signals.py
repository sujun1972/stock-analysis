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

from src.database.db_manager import DatabaseManager


def get_db():
    """
    获取数据库管理器实例

    每次信号处理时创建新实例，避免 fork 子进程共享数据库连接
    """
    return DatabaseManager()


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, **kwargs):
    """
    任务开始执行时的回调
    更新任务的started_at时间和状态为running
    """
    db = None
    try:
        if not task_id:
            return

        db = get_db()
        started_at = datetime.now()

        # 更新任务状态为 running 并设置 started_at
        update_sql = """
            UPDATE celery_task_history
            SET status = 'running',
                started_at = %s
            WHERE celery_task_id = %s
        """
        db._execute_update(update_sql, (started_at, task_id))

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

        db = get_db()

        # 查询任务记录
        query_sql = """
            SELECT id, started_at FROM celery_task_history
            WHERE celery_task_id = %s
        """
        records = db._execute_query(query_sql, (task_id,))

        if not records:
            logger.warning(f"任务 {task_id[:8]}... 在数据库中未找到记录")
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()  # 使用本地时间

        # 计算耗时（毫秒）
        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # 处理结果
        result_json = result if isinstance(result, dict) else {'value': str(result)}

        # 更新任务状态为成功
        update_sql = """
            UPDATE celery_task_history
            SET status = 'success',
                completed_at = %s,
                result = %s,
                duration_ms = %s
            WHERE celery_task_id = %s
        """
        db._execute_update(
            update_sql,
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

        db = get_db()

        # 先查询任务记录
        query_sql = """
            SELECT id, started_at FROM celery_task_history
            WHERE celery_task_id = %s
        """
        records = db._execute_query(query_sql, (task_id,))

        if not records:
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()

        # 计算耗时（毫秒）
        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # 获取错误信息
        error_msg = "Unknown error"
        if exception:
            try:
                error_msg = str(exception)
            except Exception:
                error_msg = f"Error type: {type(exception).__name__}"

        # 如果没有exception参数，尝试从einfo获取
        if not exception and 'einfo' in kwargs:
            try:
                einfo = kwargs.get('einfo')
                if einfo:
                    error_msg = str(einfo)
            except Exception:
                pass

        # 更新任务状态
        update_sql = """
            UPDATE celery_task_history
            SET status = 'failure',
                completed_at = %s,
                error = %s,
                duration_ms = %s
            WHERE celery_task_id = %s
        """
        db._execute_update(
            update_sql,
            (completed_at, error_msg, duration_ms, task_id)
        )

        logger.error(f"任务 {task_id[:8]}... 执行失败: {error_msg}")

    except Exception as e:
        logger.error(f"更新任务失败状态失败: {e}")


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

        db = get_db()

        # 先查询任务记录
        query_sql = """
            SELECT id, started_at FROM celery_task_history
            WHERE celery_task_id = %s
        """
        records = db._execute_query(query_sql, (task_id,))

        if not records:
            return

        record_id, started_at = records[0]
        completed_at = datetime.now()

        # 计算耗时（毫秒）
        duration_ms = None
        if started_at:
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # 更新任务状态
        update_sql = """
            UPDATE celery_task_history
            SET status = 'failure',
                completed_at = %s,
                error = 'Task revoked',
                duration_ms = %s
            WHERE celery_task_id = %s
        """
        db._execute_update(
            update_sql,
            (completed_at, duration_ms, task_id)
        )

        logger.warning(f"任务 {task_id[:8]}... 已被撤销")

    except Exception as e:
        logger.error(f"更新任务撤销状态失败: {e}")
