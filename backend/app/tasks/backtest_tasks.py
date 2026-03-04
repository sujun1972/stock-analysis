"""
回测异步任务
用于在后台执行耗时的回测任务
"""

import sys
import traceback
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

from celery import Task
from loguru import logger

from app.celery_app import celery_app
from app.repositories.strategy_execution_repository import StrategyExecutionRepository


# 添加 core 路径
if Path("/app/core").exists():
    core_path = Path("/app/core")
else:
    core_path = Path(__file__).parent.parent.parent.parent / "core"

if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))


class CallbackTask(Task):
    """任务失败时记录到数据库的回调任务基类"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"任务失败: task_id={task_id}, error={str(exc)}")

        # 更新数据库中的任务状态
        try:
            repo = StrategyExecutionRepository()

            # 通过 task_id 查找执行记录
            execution = repo.get_by_task_id(task_id)
            if execution:
                error_message = f"{str(exc)}\n\nTraceback:\n{einfo}"
                repo.update_status(
                    execution['id'],
                    'failed',
                    error_message=error_message[:2000]  # 限制错误消息长度
                )
                logger.info(f"已更新执行记录状态为failed: execution_id={execution['id']}")
        except Exception as e:
            logger.error(f"更新任务失败状态时出错: {e}")


@celery_app.task(base=CallbackTask, bind=True, name='app.tasks.backtest_tasks.run_backtest_async')
def run_backtest_async(self, execution_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    异步执行回测任务

    Args:
        execution_id: 执行记录ID
        params: 回测参数
            - strategy_id: 策略ID
            - stock_pool: 股票代码列表
            - start_date: 开始日期
            - end_date: 结束日期
            - initial_capital: 初始资金
            - rebalance_freq: 调仓频率
            - commission_rate: 佣金费率
            - stamp_tax_rate: 印花税率
            - min_commission: 最小佣金
            - slippage: 滑点
            - strict_mode: 严格模式
            - strategy_params: 策略参数
            - exit_strategy_ids: 离场策略ID列表

    Returns:
        回测结果字典
    """
    logger.info(f"开始执行异步回测任务: execution_id={execution_id}, task_id={self.request.id}")

    try:
        # 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 11, 'status': '初始化...'}
        )

        # 初始化仓库
        execution_repo = StrategyExecutionRepository()

        # 更新执行状态为 running
        execution_repo.update_status(execution_id, 'running')
        logger.info(f"已更新执行记录状态为running: execution_id={execution_id}")

        # 导入回测执行函数
        from app.api.endpoints.backtest import execute_backtest_core

        # 定义进度回调函数
        def progress_callback(current: int, total: int, status: str):
            """回测进度回调"""
            self.update_state(
                state='PROGRESS',
                meta={'current': current, 'total': total, 'status': status}
            )

        # 执行实际的回测逻辑
        logger.info(f"调用核心回测函数: execution_id={execution_id}")
        result_data = execute_backtest_core(
            params=params,
            execution_id=execution_id,
            progress_callback=progress_callback
        )

        # result_data 包含:
        # - strategy_info
        # - metrics
        # - equity_curve
        # - trades
        # - stock_charts
        # - backtest_params
        # - execution_time_ms

        logger.info(f"回测完成，正在保存结果: execution_id={execution_id}")

        # 提取关键数据用于保存到数据库
        metrics = result_data.get('metrics', {})

        # 保存到数据库的result字段（完整数据，包括strategy_info等）
        db_result = {
            'strategy_info': result_data.get('strategy_info'),
            'equity_curve': result_data.get('equity_curve'),
            'trades': result_data.get('trades'),
            'stock_charts': result_data.get('stock_charts'),
            'backtest_params': result_data.get('backtest_params'),
            'metrics': metrics,
        }

        execution_repo.update_result(
            execution_id=execution_id,
            result=db_result,
            metrics=metrics
        )

        # 更新状态为 completed
        execution_repo.update_status(execution_id, 'completed')

        logger.info(f"异步回测任务完成: execution_id={execution_id}, total_return={metrics.get('total_return', 0):.2%}")

        return {
            'success': True,
            'execution_id': execution_id,
            'data': result_data
        }

    except Exception as e:
        error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(f"异步回测任务失败: execution_id={execution_id}, error={error_msg}")

        # 更新执行状态为 failed
        try:
            execution_repo = StrategyExecutionRepository()
            execution_repo.update_status(
                execution_id,
                'failed',
                error_message=error_msg[:2000]
            )
        except Exception as update_error:
            logger.error(f"更新失败状态时出错: {update_error}")

        # 重新抛出异常让 Celery 记录
        raise


@celery_app.task(name='app.tasks.backtest_tasks.cancel_backtest')
def cancel_backtest(execution_id: int) -> Dict[str, Any]:
    """
    取消回测任务

    Args:
        execution_id: 执行记录ID

    Returns:
        操作结果
    """
    logger.info(f"取消回测任务: execution_id={execution_id}")

    try:
        execution_repo = StrategyExecutionRepository()

        # 更新状态为 cancelled
        execution_repo.update_status(execution_id, 'cancelled')

        return {
            'success': True,
            'message': f'回测任务已取消: execution_id={execution_id}'
        }

    except Exception as e:
        logger.error(f"取消回测任务失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }
