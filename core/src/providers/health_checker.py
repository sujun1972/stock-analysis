"""
数据源健康检查器

监控数据源的健康状态，提供：
- 健康分数计算
- 成功/失败记录
- 自动降级判断
- 健康恢复检测
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from src.database.db_manager import DatabaseManager, get_database
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataSourceHealthChecker:
    """
    数据源健康检查器

    健康分数计算规则：
    - 基础分数: 100分
    - 每次失败: -10分
    - 每次成功: +5分（最高100分）
    - 连续失败3次以上: 标记为不可用
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        failure_penalty: float = 10.0,
        success_reward: float = 5.0,
        consecutive_failure_threshold: int = 3,
        recovery_time_seconds: int = 300
    ):
        """
        初始化健康检查器

        Args:
            db_manager: 数据库管理器
            failure_penalty: 失败惩罚分数
            success_reward: 成功奖励分数
            consecutive_failure_threshold: 连续失败阈值
            recovery_time_seconds: 恢复检测时间（秒）
        """
        self.db = db_manager if db_manager else get_database()
        self.failure_penalty = failure_penalty
        self.success_reward = success_reward
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.recovery_time_seconds = recovery_time_seconds

    def record_success(self, provider_name: str) -> float:
        """
        记录成功调用

        Args:
            provider_name: 数据源名称

        Returns:
            更新后的健康分数
        """
        try:
            # 确保数据源记录存在
            self._ensure_provider_exists(provider_name)

            # 更新统计
            sql = """
                UPDATE data_source_health
                SET total_requests = total_requests + 1,
                    success_count = success_count + 1,
                    consecutive_failures = 0,
                    last_success_at = CURRENT_TIMESTAMP,
                    health_score = LEAST(health_score + %s, 100.0),
                    is_available = TRUE
                WHERE provider_name = %s
                RETURNING health_score
            """

            rows = self.db.execute_query(sql, (self.success_reward, provider_name))
            health_score = rows[0]['health_score'] if rows else 100.0

            logger.debug(f"数据源 {provider_name} 调用成功, 健康分数: {health_score:.1f}")

            # 记录事件
            self._log_event(provider_name, 'success', health_score, "调用成功")

            return float(health_score)

        except Exception as e:
            logger.error(f"记录成功失败: {provider_name}, 错误: {e}")
            return 100.0

    def record_failure(self, provider_name: str, error_message: Optional[str] = None) -> float:
        """
        记录失败调用

        Args:
            provider_name: 数据源名称
            error_message: 错误信息

        Returns:
            更新后的健康分数
        """
        try:
            # 确保数据源记录存在
            self._ensure_provider_exists(provider_name)

            # 更新统计
            sql = """
                UPDATE data_source_health
                SET total_requests = total_requests + 1,
                    failure_count = failure_count + 1,
                    consecutive_failures = consecutive_failures + 1,
                    last_failure_at = CURRENT_TIMESTAMP,
                    last_error_message = %s,
                    health_score = GREATEST(health_score - %s, 0.0)
                WHERE provider_name = %s
                RETURNING health_score, consecutive_failures
            """

            rows = self.db.execute_query(
                sql,
                (error_message, self.failure_penalty, provider_name)
            )

            if not rows:
                return 0.0

            health_score = float(rows[0]['health_score'])
            consecutive_failures = rows[0]['consecutive_failures']

            logger.warning(
                f"数据源 {provider_name} 调用失败 (连续失败{consecutive_failures}次), "
                f"健康分数: {health_score:.1f}, 错误: {error_message}"
            )

            # 检查是否需要降级
            if consecutive_failures >= self.consecutive_failure_threshold:
                self._mark_unavailable(provider_name)
                self._log_event(
                    provider_name,
                    'degraded',
                    health_score,
                    f"连续失败{consecutive_failures}次，标记为不可用"
                )
            else:
                self._log_event(provider_name, 'failure', health_score, error_message or "调用失败")

            return health_score

        except Exception as e:
            logger.error(f"记录失败失败: {provider_name}, 错误: {e}")
            return 0.0

    def check_health(self, provider_name: str) -> bool:
        """
        检查数据源是否健康

        Args:
            provider_name: 数据源名称

        Returns:
            是否健康（可用）
        """
        try:
            sql = """
                SELECT is_available, health_score, consecutive_failures, last_failure_at
                FROM data_source_health
                WHERE provider_name = %s
            """
            rows = self.db.execute_query(sql, (provider_name,))

            if not rows:
                logger.warning(f"数据源不存在: {provider_name}")
                return True  # 默认可用

            row = rows[0]
            is_available = row['is_available']
            last_failure_at = row['last_failure_at']

            # 如果标记为不可用，检查是否到了恢复时间
            if not is_available and last_failure_at:
                elapsed = (datetime.now() - last_failure_at).total_seconds()
                if elapsed >= self.recovery_time_seconds:
                    logger.info(f"数据源 {provider_name} 到达恢复时间，尝试恢复")
                    self._attempt_recovery(provider_name)
                    return True

            return is_available

        except Exception as e:
            logger.error(f"检查健康失败: {provider_name}, 错误: {e}")
            return True  # 出错时默认可用

    def get_health_score(self, provider_name: str) -> float:
        """
        获取健康分数

        Args:
            provider_name: 数据源名称

        Returns:
            健康分数 (0-100)
        """
        try:
            sql = "SELECT health_score FROM data_source_health WHERE provider_name = %s"
            rows = self.db.execute_query(sql, (provider_name,))

            if rows:
                return float(rows[0]['health_score'])

            return 100.0  # 默认满分

        except Exception as e:
            logger.error(f"获取健康分数失败: {provider_name}, 错误: {e}")
            return 100.0

    def get_all_health_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有数据源的健康统计

        Returns:
            数据源健康统计字典
        """
        try:
            sql = "SELECT * FROM data_source_health ORDER BY health_score DESC"
            rows = self.db.execute_query(sql)

            stats = {}
            for row in rows:
                stats[row['provider_name']] = {
                    'health_score': float(row['health_score']),
                    'is_available': row['is_available'],
                    'total_requests': row['total_requests'],
                    'success_count': row['success_count'],
                    'failure_count': row['failure_count'],
                    'consecutive_failures': row['consecutive_failures'],
                    'success_rate': row['success_count'] / max(1, row['total_requests']),
                    'last_success_at': row['last_success_at'],
                    'last_failure_at': row['last_failure_at'],
                    'last_error_message': row['last_error_message']
                }

            return stats

        except Exception as e:
            logger.error(f"获取健康统计失败: {e}")
            return {}

    def reset_provider(self, provider_name: str) -> bool:
        """
        重置数据源健康状态

        Args:
            provider_name: 数据源名称

        Returns:
            是否重置成功
        """
        try:
            sql = """
                UPDATE data_source_health
                SET health_score = 100.0,
                    consecutive_failures = 0,
                    is_available = TRUE,
                    last_error_message = NULL
                WHERE provider_name = %s
            """
            self.db.execute_query(sql, (provider_name,))

            logger.info(f"数据源 {provider_name} 健康状态已重置")
            self._log_event(provider_name, 'recovered', 100.0, "手动重置健康状态")
            return True

        except Exception as e:
            logger.error(f"重置数据源失败: {provider_name}, 错误: {e}")
            return False

    def _ensure_provider_exists(self, provider_name: str):
        """确保数据源记录存在"""
        try:
            sql = """
                INSERT INTO data_source_health (provider_name, health_score, is_available)
                VALUES (%s, 100.0, TRUE)
                ON CONFLICT (provider_name) DO NOTHING
            """
            self.db.execute_query(sql, (provider_name,))

        except Exception as e:
            logger.error(f"创建数据源记录失败: {provider_name}, 错误: {e}")

    def _mark_unavailable(self, provider_name: str):
        """标记数据源为不可用"""
        try:
            sql = """
                UPDATE data_source_health
                SET is_available = FALSE
                WHERE provider_name = %s
            """
            self.db.execute_query(sql, (provider_name,))

            logger.warning(f"数据源 {provider_name} 已标记为不可用")

        except Exception as e:
            logger.error(f"标记不可用失败: {provider_name}, 错误: {e}")

    def _attempt_recovery(self, provider_name: str):
        """尝试恢复数据源"""
        try:
            sql = """
                UPDATE data_source_health
                SET is_available = TRUE,
                    consecutive_failures = 0,
                    health_score = 50.0
                WHERE provider_name = %s
            """
            self.db.execute_query(sql, (provider_name,))

            logger.info(f"数据源 {provider_name} 尝试恢复，健康分数重置为50")
            self._log_event(provider_name, 'recovered', 50.0, "自动恢复尝试")

        except Exception as e:
            logger.error(f"尝试恢复失败: {provider_name}, 错误: {e}")

    def _log_event(
        self,
        provider_name: str,
        event_type: str,
        health_score: float,
        message: Optional[str] = None
    ):
        """记录健康事件"""
        try:
            sql = """
                INSERT INTO data_source_health_events (
                    provider_name, event_type, health_score, message
                ) VALUES (%s, %s, %s, %s)
            """
            self.db.execute_query(sql, (provider_name, event_type, health_score, message))

        except Exception as e:
            logger.error(f"记录事件失败: {provider_name}, {event_type}, 错误: {e}")
