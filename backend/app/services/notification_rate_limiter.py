"""
通知频率限制服务

功能:
- 每日通知次数限制
- 每小时通知次数限制
- 渠道级别限制
- 自动重置机制
- 频率统计和监控
"""
from typing import Dict, Optional, List
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.models.notification_setting import UserNotificationSetting


class NotificationRateLimiter:
    """通知频率限制器"""

    # 默认限制配置
    DEFAULT_DAILY_LIMIT = 50  # 每日最大通知数
    DEFAULT_HOURLY_LIMIT = 10  # 每小时最大通知数

    def __init__(self, db: Session):
        self.db = db

    def check_rate_limit(
        self,
        user_id: int,
        channel: str = 'all'
    ) -> Dict[str, any]:
        """
        检查用户是否超过频率限制

        Args:
            user_id: 用户 ID
            channel: 渠道类型 ('email', 'telegram', 'in_app', 'all')

        Returns:
            {
                "allowed": bool,           # 是否允许发送
                "reason": str,             # 拒绝原因
                "remaining_quota": int,    # 剩余配额
                "reset_at": datetime       # 重置时间
            }
        """
        # 获取用户配置
        user_settings = self.db.query(UserNotificationSetting).filter(
            UserNotificationSetting.user_id == user_id
        ).first()

        if not user_settings:
            logger.warning(f"用户通知配置不存在: user_id={user_id}")
            return {
                "allowed": True,
                "reason": "",
                "remaining_quota": 999,
                "reset_at": None
            }

        # 检查是否启用频率限制
        if not user_settings.enable_rate_limit:
            return {
                "allowed": True,
                "reason": "",
                "remaining_quota": 999,
                "reset_at": None
            }

        # 检查是否需要重置计数器（跨天）
        today = date.today()
        if user_settings.last_reset_date != today:
            self._reset_daily_counter(user_id)
            user_settings = self.db.query(UserNotificationSetting).filter(
                UserNotificationSetting.user_id == user_id
            ).first()

        # 检查每日限制
        max_daily = user_settings.max_daily_notifications or self.DEFAULT_DAILY_LIMIT
        current_count = user_settings.daily_notification_count or 0

        if current_count >= max_daily:
            logger.warning(
                f"用户达到每日通知限制: user_id={user_id}, "
                f"count={current_count}, limit={max_daily}"
            )
            return {
                "allowed": False,
                "reason": f"已达到每日通知限制（{max_daily} 条）",
                "remaining_quota": 0,
                "reset_at": datetime.combine(today + timedelta(days=1), datetime.min.time())
            }

        # 检查每小时限制（可选，从 rate_limits 表查询）
        hourly_allowed = self._check_hourly_limit(user_id, channel)
        if not hourly_allowed['allowed']:
            return hourly_allowed

        # 允许发送
        return {
            "allowed": True,
            "reason": "",
            "remaining_quota": max_daily - current_count,
            "reset_at": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }

    def increment_counter(
        self,
        user_id: int,
        channel: str
    ) -> bool:
        """
        增加通知计数器

        Args:
            user_id: 用户 ID
            channel: 渠道类型

        Returns:
            是否成功
        """
        try:
            user_settings = self.db.query(UserNotificationSetting).filter(
                UserNotificationSetting.user_id == user_id
            ).first()

            if not user_settings:
                logger.error(f"用户通知配置不存在: user_id={user_id}")
                return False

            # 增加每日计数
            user_settings.daily_notification_count = (
                (user_settings.daily_notification_count or 0) + 1
            )

            self.db.commit()

            # 同时更新 rate_limits 表（详细统计）
            self._update_rate_limits_table(user_id, channel)

            logger.info(
                f"通知计数器已更新: user_id={user_id}, "
                f"count={user_settings.daily_notification_count}"
            )
            return True

        except Exception as e:
            logger.error(f"更新通知计数器失败: {e}", exc_info=True)
            self.db.rollback()
            return False

    def get_rate_limit_status(
        self,
        user_id: int
    ) -> Dict[str, any]:
        """
        获取用户频率限制状态

        Args:
            user_id: 用户 ID

        Returns:
            {
                "daily_limit": int,
                "daily_count": int,
                "remaining_quota": int,
                "hourly_counts": {},
                "last_reset_date": date
            }
        """
        user_settings = self.db.query(UserNotificationSetting).filter(
            UserNotificationSetting.user_id == user_id
        ).first()

        if not user_settings:
            return {
                "daily_limit": self.DEFAULT_DAILY_LIMIT,
                "daily_count": 0,
                "remaining_quota": self.DEFAULT_DAILY_LIMIT,
                "hourly_counts": {},
                "last_reset_date": date.today()
            }

        daily_limit = user_settings.max_daily_notifications or self.DEFAULT_DAILY_LIMIT
        daily_count = user_settings.daily_notification_count or 0

        return {
            "daily_limit": daily_limit,
            "daily_count": daily_count,
            "remaining_quota": max(0, daily_limit - daily_count),
            "hourly_counts": self._get_hourly_counts(user_id),
            "last_reset_date": user_settings.last_reset_date
        }

    def _reset_daily_counter(self, user_id: int):
        """重置每日计数器"""
        try:
            user_settings = self.db.query(UserNotificationSetting).filter(
                UserNotificationSetting.user_id == user_id
            ).first()

            if user_settings:
                user_settings.daily_notification_count = 0
                user_settings.last_reset_date = date.today()
                self.db.commit()
                logger.info(f"每日计数器已重置: user_id={user_id}")

        except Exception as e:
            logger.error(f"重置每日计数器失败: {e}")
            self.db.rollback()

    def _check_hourly_limit(
        self,
        user_id: int,
        channel: str
    ) -> Dict[str, any]:
        """
        检查每小时限制

        Args:
            user_id: 用户 ID
            channel: 渠道类型

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "remaining_quota": int
            }
        """
        # 查询最近 1 小时的发送记录
        one_hour_ago = datetime.now() - timedelta(hours=1)

        # 从 notification_logs 表统计
        from app.models.notification_log import NotificationLog

        hourly_count = self.db.query(func.count(NotificationLog.id)).filter(
            NotificationLog.user_id == user_id,
            NotificationLog.created_at >= one_hour_ago,
            NotificationLog.status.in_(['sent', 'pending'])
        ).scalar()

        if channel != 'all':
            # 特定渠道的小时限制
            hourly_count = self.db.query(func.count(NotificationLog.id)).filter(
                NotificationLog.user_id == user_id,
                NotificationLog.channel == channel,
                NotificationLog.created_at >= one_hour_ago,
                NotificationLog.status.in_(['sent', 'pending'])
            ).scalar()

        if hourly_count >= self.DEFAULT_HOURLY_LIMIT:
            logger.warning(
                f"用户达到每小时通知限制: user_id={user_id}, "
                f"count={hourly_count}, limit={self.DEFAULT_HOURLY_LIMIT}"
            )
            return {
                "allowed": False,
                "reason": f"每小时通知频率过高（{self.DEFAULT_HOURLY_LIMIT} 条/小时）",
                "remaining_quota": 0,
                "reset_at": one_hour_ago + timedelta(hours=1)
            }

        return {
            "allowed": True,
            "reason": "",
            "remaining_quota": self.DEFAULT_HOURLY_LIMIT - hourly_count
        }

    def _update_rate_limits_table(
        self,
        user_id: int,
        channel: str
    ):
        """
        更新 rate_limits 表（详细统计）

        Args:
            user_id: 用户 ID
            channel: 渠道类型
        """
        try:
            # 导入模型（避免循环导入）
            from app.models import NotificationRateLimit

            today = date.today()
            current_hour = datetime.now().hour

            # 查询或创建今日记录
            rate_limit = self.db.query(NotificationRateLimit).filter(
                NotificationRateLimit.user_id == user_id,
                NotificationRateLimit.notification_date == today
            ).first()

            if not rate_limit:
                rate_limit = NotificationRateLimit(
                    user_id=user_id,
                    notification_date=today,
                    email_count=0,
                    telegram_count=0,
                    in_app_count=0,
                    total_count=0,
                    hourly_counts={}
                )
                self.db.add(rate_limit)

            # 更新渠道计数
            if channel == 'email':
                rate_limit.email_count += 1
            elif channel == 'telegram':
                rate_limit.telegram_count += 1
            elif channel == 'in_app':
                rate_limit.in_app_count += 1

            rate_limit.total_count += 1

            # 更新每小时计数
            hourly_counts = rate_limit.hourly_counts or {}
            hour_key = str(current_hour).zfill(2)
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            rate_limit.hourly_counts = hourly_counts

            self.db.commit()

        except Exception as e:
            logger.error(f"更新 rate_limits 表失败: {e}")
            self.db.rollback()

    def _get_hourly_counts(self, user_id: int) -> Dict[str, int]:
        """获取今日每小时发送统计"""
        try:
            from app.models import NotificationRateLimit

            today = date.today()
            rate_limit = self.db.query(NotificationRateLimit).filter(
                NotificationRateLimit.user_id == user_id,
                NotificationRateLimit.notification_date == today
            ).first()

            if rate_limit and rate_limit.hourly_counts:
                return rate_limit.hourly_counts

            return {}

        except Exception as e:
            logger.error(f"获取每小时统计失败: {e}")
            return {}

    def get_global_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, any]:
        """
        获取全局通知统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {
                "total_notifications": int,
                "by_channel": {},
                "by_date": {},
                "top_users": []
            }
        """
        try:
            from app.models import NotificationRateLimit

            query = self.db.query(NotificationRateLimit)

            if start_date:
                query = query.filter(NotificationRateLimit.notification_date >= start_date)
            if end_date:
                query = query.filter(NotificationRateLimit.notification_date <= end_date)

            records = query.all()

            # 统计
            total = sum(r.total_count for r in records)
            by_channel = {
                'email': sum(r.email_count for r in records),
                'telegram': sum(r.telegram_count for r in records),
                'in_app': sum(r.in_app_count for r in records)
            }

            # 按日期统计
            by_date = {}
            for r in records:
                date_key = r.notification_date.strftime('%Y-%m-%d')
                by_date[date_key] = by_date.get(date_key, 0) + r.total_count

            # Top 用户
            user_totals = {}
            for r in records:
                user_totals[r.user_id] = user_totals.get(r.user_id, 0) + r.total_count

            top_users = sorted(
                user_totals.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            return {
                "total_notifications": total,
                "by_channel": by_channel,
                "by_date": by_date,
                "top_users": [{"user_id": u, "count": c} for u, c in top_users]
            }

        except Exception as e:
            logger.error(f"获取全局统计失败: {e}")
            return {
                "total_notifications": 0,
                "by_channel": {},
                "by_date": {},
                "top_users": []
            }
