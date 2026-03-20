"""
Cron 表达式工具服务

职责：
- Cron 表达式验证
- 计算下次执行时间
- Cron 表达式解析
"""

from typing import Optional
from datetime import datetime
from loguru import logger


class CronService:
    """
    Cron 表达式工具服务

    提供 Cron 表达式的验证和解析功能
    """

    @staticmethod
    def validate_cron_expression(cron_expr: str) -> bool:
        """
        验证 Cron 表达式是否有效

        Args:
            cron_expr: Cron 表达式，格式: "分 时 日 月 周"

        Returns:
            是否有效

        Examples:
            >>> service = CronService()
            >>> service.validate_cron_expression("0 9 * * *")  # True
            >>> service.validate_cron_expression("invalid")    # False
        """
        try:
            from croniter import croniter
            croniter(cron_expr, datetime.now())
            return True
        except Exception:
            # croniter 不可用或表达式无效，使用简单验证
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return False
            # 简单检查每个字段是否符合基本格式
            return all(part for part in parts)

    @staticmethod
    def calculate_next_run_time(cron_expr: str) -> Optional[datetime]:
        """
        计算下次执行时间

        Args:
            cron_expr: Cron 表达式

        Returns:
            下次执行时间，解析失败返回 None

        Examples:
            >>> service = CronService()
            >>> next_time = service.calculate_next_run_time("0 9 * * *")
            >>> print(next_time)  # 下一个9:00
        """
        try:
            from croniter import croniter
            cron = croniter(cron_expr, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.warning(f"计算下次执行时间失败: {e}")
            return None

    @staticmethod
    def format_datetime(dt: Optional[datetime]) -> Optional[str]:
        """
        格式化 datetime 为字符串

        Args:
            dt: datetime 对象

        Returns:
            格式化后的字符串 (YYYY-MM-DD HH:MM:SS)，None 则返回 None
        """
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def validate_and_get_next_run(self, cron_expression: str) -> dict:
        """
        验证 Cron 表达式并返回下次执行时间

        Args:
            cron_expression: Cron 表达式

        Returns:
            验证结果字典

        Examples:
            >>> service = CronService()
            >>> result = service.validate_and_get_next_run("0 9 * * *")
            >>> print(result['valid'])  # True
            >>> print(result['next_run_at'])  # "2026-03-21 09:00:00"
        """
        is_valid = self.validate_cron_expression(cron_expression)

        if not is_valid:
            return {
                "valid": False,
                "error": "格式应为: 分 时 日 月 周 (例: 0 9 * * 1-5)"
            }

        next_run = self.calculate_next_run_time(cron_expression)

        return {
            "valid": True,
            "next_run_at": self.format_datetime(next_run) if next_run else None,
            "cron_expression": cron_expression
        }
