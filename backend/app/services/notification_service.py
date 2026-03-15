"""
通知服务层

核心业务逻辑：订阅用户查询、报告内容渲染、通知日志管理
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, date
from loguru import logger
import json

from app.models.notification_setting import (
    UserNotificationSetting,
    NotificationLog,
    InAppNotification
)
from app.models.notification_channel_config import NotificationChannelConfig


class NotificationService:
    """通知服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 用户配置管理 ====================

    def get_user_settings(self, user_id: int) -> Optional[UserNotificationSetting]:
        """获取用户通知配置"""
        return self.db.query(UserNotificationSetting).filter(
            UserNotificationSetting.user_id == user_id
        ).first()

    def update_user_settings(
        self,
        user_id: int,
        settings_data: Dict[str, Any]
    ) -> UserNotificationSetting:
        """更新用户通知配置"""
        settings = self.get_user_settings(user_id)

        if not settings:
            # 创建新配置
            settings = UserNotificationSetting(user_id=user_id)
            self.db.add(settings)

        # 更新字段
        for key, value in settings_data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    # ==================== 订阅用户查询 ====================

    def get_subscribers(self, report_type: str) -> List[Dict]:
        """
        获取订阅指定报告类型的用户列表

        Args:
            report_type: 'sentiment_report', 'premarket_report', 'backtest_result'

        Returns:
            用户配置列表
        """
        # 根据报告类型确定订阅字段
        subscription_field_map = {
            'sentiment_report': UserNotificationSetting.subscribe_sentiment_report,
            'premarket_report': UserNotificationSetting.subscribe_premarket_report,
            'backtest_result': UserNotificationSetting.subscribe_backtest_report
        }

        subscription_field = subscription_field_map.get(report_type)
        if not subscription_field:
            logger.warning(f"未知报告类型: {report_type}")
            return []

        # 查询订阅用户
        settings_list = self.db.query(UserNotificationSetting).filter(
            subscription_field == True
        ).all()

        subscribers = []
        for settings in settings_list:
            enabled_channels = []

            # 检查各渠道是否启用
            if settings.email_enabled and settings.email_address:
                enabled_channels.append('email')
            if settings.telegram_enabled and settings.telegram_chat_id:
                enabled_channels.append('telegram')
            if settings.in_app_enabled:
                enabled_channels.append('in_app')

            if not enabled_channels:
                continue

            subscribers.append({
                'user_id': settings.user_id,
                'email_address': settings.email_address,
                'telegram_chat_id': settings.telegram_chat_id,
                'report_format': settings.report_format,
                'enabled_channels': enabled_channels
            })

        logger.info(f"找到 {len(subscribers)} 个订阅 {report_type} 的用户")
        return subscribers

    # ==================== 报告内容渲染 ====================

    def render_report(
        self,
        report_type: str,
        report_data: Dict[str, Any],
        user_preferences: Dict
    ) -> Dict[str, str]:
        """
        渲染报告内容

        Args:
            report_type: 报告类型
            report_data: 原始报告数据
            user_preferences: 用户偏好

        Returns:
            {
                'title': '标题',
                'content': '纯文本内容',
                'email_html': 'HTML格式邮件内容',
                'telegram_markdown': 'Telegram Markdown格式'
            }
        """
        if report_type == 'sentiment_report':
            return self._render_sentiment_report(report_data, user_preferences)
        elif report_type == 'premarket_report':
            return self._render_premarket_report(report_data, user_preferences)
        elif report_type == 'backtest_result':
            return self._render_backtest_report(report_data, user_preferences)
        else:
            logger.error(f"未知报告类型: {report_type}")
            return {
                'title': '报告生成失败',
                'content': '未知报告类型',
                'email_html': '<p>未知报告类型</p>',
                'telegram_markdown': '未知报告类型'
            }

    def _render_sentiment_report(
        self,
        report_data: Dict,
        user_preferences: Dict
    ) -> Dict[str, str]:
        """渲染盘后情绪报告"""
        trade_date = report_data.get('trade_date', '')
        full_report = report_data.get('full_report', '')
        tomorrow_tactics = report_data.get('tomorrow_tactics', {})
        report_format = user_preferences.get('report_format', 'full')

        if report_format == 'action_only':
            # 仅行动指令
            content = self._format_tactics_summary(tomorrow_tactics)
            title = f"【明日战术】{trade_date}"
        elif report_format == 'summary':
            # 摘要版
            content = self._format_sentiment_summary(report_data)
            title = f"【盘后情绪摘要】{trade_date}"
        else:
            # 完整报告
            content = full_report
            title = f"【盘后情绪深度分析】{trade_date}"

        return {
            'title': title,
            'content': content,
            'email_html': self._convert_to_html(title, content),
            'telegram_markdown': self._convert_to_telegram_markdown(title, content)
        }

    def _render_premarket_report(
        self,
        report_data: Dict,
        user_preferences: Dict
    ) -> Dict[str, str]:
        """渲染盘前碰撞报告"""
        trade_date = report_data.get('trade_date', '')
        action_command = report_data.get('action_command', '')
        report_format = user_preferences.get('report_format', 'full')

        if report_format == 'action_only':
            content = action_command
            title = f"【盘前行动指令】{trade_date}"
        else:
            # 完整报告
            macro_tone = report_data.get('macro_tone', {})
            content = f"""【盘前碰撞分析】{trade_date}

一、宏观定调
开盘预期: {macro_tone.get('direction', '未知')}
置信度: {macro_tone.get('confidence', '?')}

═══════════════════
【极简行动指令】
{action_command}
"""
            title = f"【盘前碰撞分析】{trade_date}"

        return {
            'title': title,
            'content': content,
            'email_html': self._convert_to_html(title, content),
            'telegram_markdown': self._convert_to_telegram_markdown(title, content)
        }

    def _render_backtest_report(
        self,
        report_data: Dict,
        user_preferences: Dict
    ) -> Dict[str, str]:
        """渲染回测结果报告"""
        strategy_name = report_data.get('strategy_name', '未知策略')
        total_return = report_data.get('total_return', 0)

        title = f"【回测完成】{strategy_name}"
        content = f"""策略回测已完成！

策略名称: {strategy_name}
总收益率: {total_return:.2f}%
年化收益: {report_data.get('annual_return', 0):.2f}%
夏普比率: {report_data.get('sharpe_ratio', 0):.2f}
最大回撤: {report_data.get('max_drawdown', 0):.2f}%

请登录系统查看详细报告。
"""

        return {
            'title': title,
            'content': content,
            'email_html': self._convert_to_html(title, content),
            'telegram_markdown': self._convert_to_telegram_markdown(title, content)
        }

    def _format_tactics_summary(self, tactics: Dict) -> str:
        """格式化战术摘要"""
        if not tactics:
            return "暂无明日战术"

        call_auction = tactics.get('call_auction_tactics', {})
        buy_conditions = tactics.get('buy_conditions', [])
        stop_loss = tactics.get('stop_loss_conditions', [])

        lines = []
        lines.append("【集合竞价】")
        lines.append(f"参与条件: {call_auction.get('participate_conditions', '无')}")
        lines.append(f"回避条件: {call_auction.get('avoid_conditions', '无')}")
        lines.append("")
        lines.append("【买入条件】")
        for i, cond in enumerate(buy_conditions, 1):
            lines.append(f"{i}. {cond}")
        lines.append("")
        lines.append("【止损条件】")
        for i, cond in enumerate(stop_loss, 1):
            lines.append(f"{i}. {cond}")

        return "\n".join(lines)

    def _format_sentiment_summary(self, report_data: Dict) -> str:
        """格式化情绪分析摘要"""
        space = report_data.get('space_analysis', {})
        sentiment = report_data.get('sentiment_analysis', {})
        capital = report_data.get('capital_flow_analysis', {})

        lines = []
        lines.append(f"【空间】{space.get('space_level', '未知')}")
        lines.append(f"【情绪】{sentiment.get('money_making_effect', '未知')}")
        lines.append(f"【策略】{sentiment.get('strategy', '未知')}")
        lines.append(f"【资金】{capital.get('capital_consensus', '未知')}")

        return "\n".join(lines)

    def _convert_to_html(self, title: str, content: str) -> str:
        """转换为HTML邮件格式"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <pre>{content}</pre>
    <hr>
    <p style="color: #7f8c8d; font-size: 12px;">此邮件由股票分析系统自动发送，请勿回复。</p>
</body>
</html>
"""
        return html

    def _convert_to_telegram_markdown(self, title: str, content: str) -> str:
        """转换为Telegram Markdown格式"""
        # Telegram 支持的 Markdown 格式
        return f"*{title}*\n\n```\n{content}\n```"

    # ==================== 通知日志管理 ====================

    def create_notification_logs(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        content: str,
        business_date: str,
        channels: List[str]
    ) -> Dict[str, int]:
        """
        创建通知日志记录

        Returns:
            {'email': log_id, 'telegram': log_id, ...}
        """
        log_ids = {}

        for channel in channels:
            log = NotificationLog(
                user_id=user_id,
                notification_type=notification_type,
                content_type='full',
                title=title,
                content=content[:5000],  # 限制长度
                channel=channel,
                business_date=business_date,
                status='pending'
            )
            self.db.add(log)
            self.db.flush()
            log_ids[channel] = log.id

        self.db.commit()
        return log_ids

    def update_notification_log(
        self,
        log_id: int,
        status: str,
        failed_reason: str = None,
        retry_count: int = None
    ):
        """更新通知日志状态"""
        log = self.db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
        if not log:
            logger.warning(f"通知日志不存在: {log_id}")
            return

        log.status = status
        if status == 'sent':
            log.sent_at = datetime.now()
        if failed_reason:
            log.failed_reason = failed_reason
        if retry_count is not None:
            log.retry_count = retry_count

        self.db.commit()

    # ==================== 站内消息管理 ====================

    def create_in_app_notification(
        self,
        user_id: int,
        title: str,
        content: str,
        notification_type: str,
        business_date: str = None,
        reference_id: str = None,
        metadata: Dict = None,
        priority: str = 'normal'
    ):
        """创建站内消息"""
        notification = InAppNotification(
            user_id=user_id,
            title=title,
            content=content,
            notification_type=notification_type,
            business_date=business_date,
            reference_id=reference_id,
            metadata=metadata,
            priority=priority
        )
        self.db.add(notification)
        self.db.commit()

    def get_in_app_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[InAppNotification]:
        """获取站内消息列表"""
        query = self.db.query(InAppNotification).filter(
            InAppNotification.user_id == user_id
        )

        if unread_only:
            query = query.filter(InAppNotification.is_read == False)

        query = query.order_by(desc(InAppNotification.created_at))
        query = query.limit(limit).offset(offset)

        return query.all()

    def mark_as_read(self, notification_id: int, user_id: int):
        """标记消息为已读"""
        notification = self.db.query(InAppNotification).filter(
            and_(
                InAppNotification.id == notification_id,
                InAppNotification.user_id == user_id
            )
        ).first()

        if notification:
            notification.is_read = True
            notification.read_at = datetime.now()
            self.db.commit()

    def mark_all_as_read(self, user_id: int) -> int:
        """全部标记为已读"""
        count = self.db.query(InAppNotification).filter(
            and_(
                InAppNotification.user_id == user_id,
                InAppNotification.is_read == False
            )
        ).update({
            'is_read': True,
            'read_at': datetime.now()
        })
        self.db.commit()
        return count

    def get_unread_count(self, user_id: int) -> int:
        """获取未读消息数量"""
        return self.db.query(InAppNotification).filter(
            and_(
                InAppNotification.user_id == user_id,
                InAppNotification.is_read == False
            )
        ).count()

    def get_notification_logs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[NotificationLog]:
        """获取通知发送历史"""
        return self.db.query(NotificationLog).filter(
            NotificationLog.user_id == user_id
        ).order_by(desc(NotificationLog.created_at)).limit(limit).offset(offset).all()

    # ==================== 渠道配置管理 ====================

    def get_channel_config(self, channel_type: str) -> Optional[Dict]:
        """获取渠道配置"""
        channel = self.db.query(NotificationChannelConfig).filter(
            and_(
                NotificationChannelConfig.channel_type == channel_type,
                NotificationChannelConfig.is_enabled == True
            )
        ).first()

        if not channel:
            return None

        return channel.config
