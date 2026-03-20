"""
Backtest History Service
回测历史管理服务
"""

from typing import Dict, Any, Optional
from loguru import logger

from app.repositories import StrategyExecutionRepository


class BacktestHistoryService:
    """回测历史管理服务"""

    def __init__(self):
        self.execution_repo = StrategyExecutionRepository()
        logger.debug("✓ BacktestHistoryService initialized")

    def get_user_history(
        self,
        username: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        strategy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取用户回测历史（分页）

        Args:
            username: 用户名
            page: 页码（从1开始）
            page_size: 每页数量
            status_filter: 状态筛选（可选）
            strategy_id: 策略ID筛选（可选）

        Returns:
            包含 total, page, page_size, items 的字典
        """
        logger.info(
            f"查询用户回测历史: username={username}, page={page}, "
            f"page_size={page_size}, status={status_filter}, strategy_id={strategy_id}"
        )

        # 调用 Repository 获取数据
        result = self.execution_repo.list_by_user_with_pagination(
            username=username,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            strategy_id=strategy_id
        )

        # 格式化返回数据
        items = []
        for item in result['items']:
            # 提取关键指标
            metrics = item['metrics'] or {}
            execution_params = item['execution_params'] or {}

            formatted_item = {
                "id": item['id'],
                "execution_type": item['execution_type'],
                "status": item['status'],
                "metrics": {
                    "total_return": metrics.get("total_return", 0.0),
                    "annual_return": metrics.get("annual_return", 0.0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                    "max_drawdown": metrics.get("max_drawdown", 0.0),
                    "win_rate": metrics.get("win_rate", 0.0),
                    "total_trades": metrics.get("total_trades", 0),
                },
                "execution_params": {
                    "stock_pool": execution_params.get("stock_pool", []),
                    "start_date": execution_params.get("start_date"),
                    "end_date": execution_params.get("end_date"),
                    "initial_capital": execution_params.get("initial_capital", 1000000),
                },
                "error_message": item['error_message'],
                "execution_duration_ms": item['execution_duration_ms'],
                "started_at": item['started_at'],
                "completed_at": item['completed_at'],
                "created_at": item['created_at'],
                "strategy": item['strategy'],
            }
            items.append(formatted_item)

        return {
            "total": result['total'],
            "page": page,
            "page_size": page_size,
            "items": items
        }

    def get_backtest_detail(
        self,
        execution_id: int,
        username: str
    ) -> Dict[str, Any]:
        """
        获取回测详情（包含权限校验）

        Args:
            execution_id: 执行记录 ID
            username: 当前用户名

        Returns:
            回测详情字典

        Raises:
            ValueError: 记录不存在或无权访问
        """
        logger.info(f"查询回测详情: execution_id={execution_id}, username={username}")

        # 查询记录
        detail = self.execution_repo.get_by_id_with_strategy(execution_id)

        if not detail:
            raise ValueError("回测记录不存在")

        # 权限校验：只能查看自己的回测记录
        if detail['executed_by'] != username:
            raise ValueError("无权查看此回测记录")

        # 格式化结果数据
        result = detail['result'] or {}

        formatted_detail = {
            "id": detail['id'],
            "execution_type": detail['execution_type'],
            "status": detail['status'],
            "metrics": detail['metrics'],
            "execution_params": detail['execution_params'],
            "result": {
                "equity_curve": result.get("equity_curve", []),
                "trades": result.get("trades", []),
                "stock_charts": result.get("stock_charts", {}),
            },
            "error_message": detail['error_message'],
            "execution_duration_ms": detail['execution_duration_ms'],
            "started_at": detail['started_at'],
            "completed_at": detail['completed_at'],
            "created_at": detail['created_at'],
            "executed_by": detail['executed_by'],
            "strategy": detail['strategy'],
        }

        return formatted_detail

    def delete_backtest_record(
        self,
        execution_id: int,
        username: str
    ) -> None:
        """
        删除回测记录（包含权限校验）

        Args:
            execution_id: 执行记录 ID
            username: 当前用户名

        Raises:
            ValueError: 记录不存在或无权删除
        """
        logger.info(f"删除回测记录: execution_id={execution_id}, username={username}")

        # 先查询记录（检查是否存在且有权限）
        record = self.execution_repo.get_by_id(execution_id)

        if not record:
            raise ValueError("回测记录不存在")

        # 权限校验：只能删除自己的回测记录
        if record['executed_by'] != username:
            raise ValueError("无权删除此回测记录")

        # 执行删除
        deleted = self.execution_repo.delete_by_id(execution_id)

        if deleted == 0:
            raise ValueError("删除失败")

        logger.info(f"✓ 已删除回测记录: execution_id={execution_id}")
