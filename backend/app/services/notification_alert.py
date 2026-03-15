"""
通知系统失败告警服务

Phase 3: 自动检测并告警通知系统异常
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from loguru import logger

from app.services.notification_monitor import NotificationMonitor
from app.models.notification_setting import InAppNotification
from app.models.user import User


class NotificationAlert:
    """通知系统告警服务"""

    def __init__(self, db: Session):
        self.db = db
        self.monitor = NotificationMonitor(db)

    # ==================== 告警阈值配置 ====================

    # 成功率告警阈值
    SUCCESS_RATE_WARNING_THRESHOLD = 90.0  # 成功率低于 90% 发出警告
    SUCCESS_RATE_CRITICAL_THRESHOLD = 70.0  # 成功率低于 70% 发出严重告警

    # 失败率告警阈值
    FAILURE_RATE_WARNING_THRESHOLD = 10.0  # 失败率高于 10% 发出警告
    FAILURE_RATE_CRITICAL_THRESHOLD = 20.0  # 失败率高于 20% 发出严重告警

    # 积压告警阈值
    PENDING_WARNING_THRESHOLD = 100  # 待发送积压超过 100 条发出警告
    PENDING_CRITICAL_THRESHOLD = 500  # 待发送积压超过 500 条发出严重告警

    # 连续失败告警阈值
    CONSECUTIVE_FAILURES_THRESHOLD = 5  # 连续失败 5 次发出告警

    # ==================== 健康检查与告警触发 ====================

    def check_and_alert(self) -> Dict[str, Any]:
        """
        执行健康检查并触发告警

        Returns:
            {
                'health_status': '健康状态',
                'alerts_triggered': [已触发的告警],
                'admin_notified': 是否通知管理员
            }
        """
        try:
            logger.info("开始通知系统健康检查...")

            # 执行健康检查
            health_check = self.monitor.health_check()

            alerts_triggered = []

            # 检查成功率
            success_rate = health_check.get('success_rate_24h', 100)
            if success_rate < self.SUCCESS_RATE_CRITICAL_THRESHOLD:
                alert = self._create_alert(
                    level='critical',
                    title='通知系统成功率严重偏低',
                    message=f"最近 24 小时通知成功率仅为 {success_rate}%，低于临界阈值 {self.SUCCESS_RATE_CRITICAL_THRESHOLD}%",
                    details=health_check
                )
                alerts_triggered.append(alert)

            elif success_rate < self.SUCCESS_RATE_WARNING_THRESHOLD:
                alert = self._create_alert(
                    level='warning',
                    title='通知系统成功率偏低',
                    message=f"最近 24 小时通知成功率为 {success_rate}%，低于警告阈值 {self.SUCCESS_RATE_WARNING_THRESHOLD}%",
                    details=health_check
                )
                alerts_triggered.append(alert)

            # 检查失败率
            failure_rate = health_check.get('failure_rate', 0)
            if failure_rate > self.FAILURE_RATE_CRITICAL_THRESHOLD:
                alert = self._create_alert(
                    level='critical',
                    title='通知系统失败率严重过高',
                    message=f"最近 24 小时通知失败率高达 {failure_rate}%，超过临界阈值 {self.FAILURE_RATE_CRITICAL_THRESHOLD}%",
                    details=health_check
                )
                alerts_triggered.append(alert)

            elif failure_rate > self.FAILURE_RATE_WARNING_THRESHOLD:
                alert = self._create_alert(
                    level='warning',
                    title='通知系统失败率过高',
                    message=f"最近 24 小时通知失败率为 {failure_rate}%，超过警告阈值 {self.FAILURE_RATE_WARNING_THRESHOLD}%",
                    details=health_check
                )
                alerts_triggered.append(alert)

            # 检查待发送积压
            pending_count = health_check.get('pending_count', 0)
            if pending_count > self.PENDING_CRITICAL_THRESHOLD:
                alert = self._create_alert(
                    level='critical',
                    title='通知系统严重积压',
                    message=f"当前待发送通知积压 {pending_count} 条，超过临界阈值 {self.PENDING_CRITICAL_THRESHOLD} 条",
                    details={'pending_count': pending_count}
                )
                alerts_triggered.append(alert)

            elif pending_count > self.PENDING_WARNING_THRESHOLD:
                alert = self._create_alert(
                    level='warning',
                    title='通知系统积压预警',
                    message=f"当前待发送通知积压 {pending_count} 条，超过警告阈值 {self.PENDING_WARNING_THRESHOLD} 条",
                    details={'pending_count': pending_count}
                )
                alerts_triggered.append(alert)

            # 检查渠道异常
            channel_alerts = self._check_channel_anomalies()
            alerts_triggered.extend(channel_alerts)

            # 如果有告警，通知管理员
            admin_notified = False
            if alerts_triggered:
                admin_notified = self._notify_admins(alerts_triggered)

            logger.info(f"健康检查完成，触发 {len(alerts_triggered)} 条告警")

            return {
                'health_status': health_check.get('status', 'unknown'),
                'alerts_triggered': alerts_triggered,
                'admin_notified': admin_notified,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"健康检查执行失败: {e}", exc_info=True)
            return {
                'health_status': 'critical',
                'error': str(e),
                'alerts_triggered': [],
                'admin_notified': False
            }

    def _create_alert(
        self,
        level: str,
        title: str,
        message: str,
        details: Dict = None
    ) -> Dict[str, Any]:
        """创建告警对象"""
        return {
            'level': level,  # 'warning' | 'critical'
            'title': title,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }

    # ==================== 渠道异常检测 ====================

    def _check_channel_anomalies(self) -> List[Dict[str, Any]]:
        """检查各渠道异常"""
        alerts = []

        try:
            # 获取最近 24 小时渠道性能
            yesterday = datetime.now() - timedelta(hours=24)
            channel_performance = self.monitor.get_channel_performance(
                start_date=yesterday.date(),
                end_date=datetime.now().date()
            )

            for channel, stats in channel_performance.items():
                success_rate = stats.get('success_rate', 0)

                # 渠道成功率过低
                if success_rate < 80:
                    alert = self._create_alert(
                        level='critical' if success_rate < 60 else 'warning',
                        title=f'{channel.upper()} 渠道成功率异常',
                        message=f"{channel} 渠道最近 24 小时成功率仅为 {success_rate}%",
                        details=stats
                    )
                    alerts.append(alert)

                # 平均送达时间过长
                avg_delivery_time = stats.get('avg_delivery_time', 0)
                if avg_delivery_time > 300:  # 超过 5 分钟
                    alert = self._create_alert(
                        level='warning',
                        title=f'{channel.upper()} 渠道送达延迟',
                        message=f"{channel} 渠道平均送达时间为 {avg_delivery_time:.2f} 秒，存在延迟",
                        details=stats
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"检查渠道异常失败: {e}", exc_info=True)

        return alerts

    # ==================== 管理员通知 ====================

    def _notify_admins(self, alerts: List[Dict]) -> bool:
        """通知所有管理员"""
        try:
            # 查询所有超级管理员
            admins = self.db.query(User).filter(User.role == 'superadmin').all()

            if not admins:
                logger.warning("未找到超级管理员，无法发送告警通知")
                return False

            # 生成告警摘要
            alert_summary = self._generate_alert_summary(alerts)

            # 为每个管理员创建站内消息
            for admin in admins:
                try:
                    notification = InAppNotification(
                        user_id=admin.id,
                        title='⚠️ 通知系统异常告警',
                        content=alert_summary,
                        notification_type='system_alert',
                        priority='high'
                    )
                    self.db.add(notification)

                except Exception as e:
                    logger.error(f"通知管理员 {admin.id} 失败: {e}")

            self.db.commit()
            logger.info(f"已通知 {len(admins)} 名管理员")

            return True

        except Exception as e:
            logger.error(f"通知管理员失败: {e}", exc_info=True)
            return False

    def _generate_alert_summary(self, alerts: List[Dict]) -> str:
        """生成告警摘要"""
        lines = []
        lines.append(f"【时间】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"【告警数量】{len(alerts)} 条")
        lines.append("")

        critical_alerts = [a for a in alerts if a['level'] == 'critical']
        warning_alerts = [a for a in alerts if a['level'] == 'warning']

        if critical_alerts:
            lines.append("【严重告警】")
            for alert in critical_alerts:
                lines.append(f"- {alert['title']}")
                lines.append(f"  {alert['message']}")
            lines.append("")

        if warning_alerts:
            lines.append("【警告告警】")
            for alert in warning_alerts:
                lines.append(f"- {alert['title']}")
                lines.append(f"  {alert['message']}")
            lines.append("")

        lines.append("请登录管理后台查看详细监控数据。")

        return "\n".join(lines)

    # ==================== 失败原因分析与建议 ====================

    def analyze_failures_and_suggest(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        分析失败原因并提供优化建议

        Args:
            days: 分析天数

        Returns:
            {
                'failure_summary': [...],
                'suggestions': [...],
                'trend': 'improving' | 'worsening' | 'stable'
            }
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # 获取失败原因汇总
            failure_summary = self.monitor.get_failure_reasons_summary(
                start_date=start_date,
                end_date=end_date
            )

            # 生成优化建议
            suggestions = self._generate_suggestions(failure_summary)

            # 趋势分析
            trend = self._analyze_trend(days)

            return {
                'period_days': days,
                'failure_summary': failure_summary,
                'suggestions': suggestions,
                'trend': trend,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"失败分析失败: {e}", exc_info=True)
            return {}

    def _generate_suggestions(self, failure_summary: List[Dict]) -> List[str]:
        """根据失败原因生成优化建议"""
        suggestions = []

        for item in failure_summary[:5]:  # 只分析 Top 5
            reason = item['reason'].lower()
            count = item['count']

            # SMTP 相关错误
            if 'smtp' in reason or 'email' in reason:
                if 'timeout' in reason:
                    suggestions.append(
                        f"SMTP 超时错误出现 {count} 次，建议检查 SMTP 服务器配置或增加超时时间"
                    )
                elif 'authentication' in reason or 'auth' in reason:
                    suggestions.append(
                        f"SMTP 认证失败出现 {count} 次，请检查 SMTP 用户名和密码配置"
                    )
                elif 'connection' in reason:
                    suggestions.append(
                        f"SMTP 连接失败出现 {count} 次，建议检查网络连接和 SMTP 服务器可用性"
                    )

            # Telegram 相关错误
            elif 'telegram' in reason or 'bot' in reason:
                if 'token' in reason:
                    suggestions.append(
                        f"Telegram Bot Token 错误出现 {count} 次，请检查 Bot Token 配置"
                    )
                elif 'chat_id' in reason:
                    suggestions.append(
                        f"Telegram Chat ID 错误出现 {count} 次，请提醒用户正确配置 Chat ID"
                    )

            # 超时错误
            elif 'timeout' in reason:
                suggestions.append(
                    f"超时错误出现 {count} 次，建议增加重试次数或延长超时时间"
                )

            # 网络错误
            elif 'network' in reason or 'connection' in reason:
                suggestions.append(
                    f"网络连接错误出现 {count} 次，建议检查服务器网络环境和防火墙设置"
                )

        if not suggestions:
            suggestions.append("暂无明确的优化建议，请联系技术支持分析详细日志")

        return suggestions

    def _analyze_trend(self, days: int) -> str:
        """分析失败趋势"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # 获取每日趋势
            daily_trend = self.monitor.get_daily_trend(
                start_date=start_date,
                end_date=end_date
            )

            if len(daily_trend) < 3:
                return 'insufficient_data'

            # 计算最近 3 天和之前的平均失败率
            recent_3_days = daily_trend[:3]
            earlier_days = daily_trend[3:]

            recent_failure_rate = sum(
                (day['failed'] / day['total'] * 100) if day['total'] > 0 else 0
                for day in recent_3_days
            ) / len(recent_3_days)

            earlier_failure_rate = sum(
                (day['failed'] / day['total'] * 100) if day['total'] > 0 else 0
                for day in earlier_days
            ) / len(earlier_days) if earlier_days else recent_failure_rate

            # 判断趋势
            if recent_failure_rate < earlier_failure_rate - 2:
                return 'improving'
            elif recent_failure_rate > earlier_failure_rate + 2:
                return 'worsening'
            else:
                return 'stable'

        except Exception as e:
            logger.error(f"分析趋势失败: {e}")
            return 'unknown'

    # ==================== 单条通知失败告警 ====================

    def alert_on_critical_notification_failure(
        self,
        notification_log_id: int,
        user_id: int,
        notification_type: str,
        failed_reason: str
    ):
        """
        针对重要通知失败发送即时告警

        Args:
            notification_log_id: 通知日志ID
            user_id: 用户ID
            notification_type: 通知类型
            failed_reason: 失败原因
        """
        try:
            # 判断是否为关键通知（可根据业务需求自定义）
            critical_types = ['backtest_result', 'strategy_alert', 'system_alert']

            if notification_type in critical_types:
                # 通知管理员
                admins = self.db.query(User).filter(User.role == 'superadmin').all()

                for admin in admins:
                    notification = InAppNotification(
                        user_id=admin.id,
                        title='⚠️ 关键通知发送失败',
                        content=f"""
用户 ID: {user_id}
通知类型: {notification_type}
失败原因: {failed_reason}
日志 ID: {notification_log_id}

请及时处理该告警。
                        """.strip(),
                        notification_type='system_alert',
                        priority='high'
                    )
                    self.db.add(notification)

                self.db.commit()
                logger.warning(
                    f"关键通知发送失败已告警: user_id={user_id}, "
                    f"type={notification_type}, log_id={notification_log_id}"
                )

        except Exception as e:
            logger.error(f"告警关键通知失败失败: {e}", exc_info=True)
