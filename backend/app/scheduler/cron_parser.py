"""
Cron表达式解析器
提供Cron表达式解析和验证功能
"""

from celery.schedules import crontab
from typing import Optional
from loguru import logger


class CronParser:
    """Cron表达式解析器"""

    @staticmethod
    def parse(cron_expr: str) -> Optional[crontab]:
        """
        解析Cron表达式为Celery crontab对象

        Args:
            cron_expr: Cron表达式，格式: "分 时 日 月 周"
                      例如: "30 17 * * 1-5" 表示周一到周五的17:30

        Returns:
            celery.schedules.crontab对象，解析失败返回None

        Examples:
            >>> parser = CronParser()
            >>> parser.parse("30 17 * * 1-5")
            crontab(minute='30', hour='17', day_of_month='*',
                    month_of_year='*', day_of_week='1-5')
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                logger.warning(f"⚠️  Cron表达式格式错误: {cron_expr} (需要5个字段)")
                return None

            minute, hour, day_of_month, month_of_year, day_of_week = parts

            return crontab(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week
            )
        except Exception as e:
            logger.error(f"❌ 解析Cron表达式失败 '{cron_expr}': {e}")
            return None

    @staticmethod
    def validate(cron_expr: str) -> bool:
        """
        验证Cron表达式是否有效

        Args:
            cron_expr: Cron表达式

        Returns:
            是否有效
        """
        return CronParser.parse(cron_expr) is not None

    @staticmethod
    def parse_with_validation(cron_expr: str) -> tuple[Optional[crontab], Optional[str]]:
        """
        解析Cron表达式并返回错误信息

        Args:
            cron_expr: Cron表达式

        Returns:
            (crontab对象或None, 错误信息或None)
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return None, f"Cron表达式格式错误: {cron_expr} (需要5个字段)"

            minute, hour, day_of_month, month_of_year, day_of_week = parts

            schedule = crontab(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week
            )
            return schedule, None

        except Exception as e:
            return None, f"解析失败: {str(e)}"
