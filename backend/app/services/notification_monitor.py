"""
通知发送监控服务

Phase 3: 提供发送成功率统计、失败分析、渠道性能监控
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case, desc, text
from datetime import datetime, date, timedelta
from loguru import logger

from app.models.notification_setting import NotificationLog, InAppNotification


class NotificationMonitor:
    """通知发送监控服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 发送成功率统计 ====================

    def get_success_rate_statistics(
        self,
        start_date: date,
        end_date: date,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取通知发送成功率统计

        Args:
            start_date: 开始日期
            end_date: 结束日期
            channel: 指定渠道 ('email', 'telegram', 'in_app')，为 None 时统计所有渠道

        Returns:
            {
                'total': 总发送数,
                'sent': 成功数,
                'failed': 失败数,
                'pending': 待发送数,
                'success_rate': 成功率,
                'failure_rate': 失败率,
                'avg_retry_count': 平均重试次数,
                'by_channel': {
                    'email': {...},
                    'telegram': {...},
                    'in_app': {...}
                }
            }
        """
        try:
            # 基础查询
            query = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.created_at >= start_date,
                    NotificationLog.created_at < end_date + timedelta(days=1)
                )
            )

            if channel:
                query = query.filter(NotificationLog.channel == channel)

            logs = query.all()

            if not logs:
                return self._empty_statistics()

            # 统计数据
            total = len(logs)
            sent = sum(1 for log in logs if log.status == 'sent')
            failed = sum(1 for log in logs if log.status == 'failed')
            pending = sum(1 for log in logs if log.status == 'pending')
            skipped = sum(1 for log in logs if log.status == 'skipped')

            success_rate = (sent / total * 100) if total > 0 else 0
            failure_rate = (failed / total * 100) if total > 0 else 0

            # 平均重试次数（仅统计失败的记录）
            failed_logs = [log for log in logs if log.status == 'failed']
            avg_retry_count = (
                sum(log.retry_count for log in failed_logs) / len(failed_logs)
                if failed_logs else 0
            )

            result = {
                'total': total,
                'sent': sent,
                'failed': failed,
                'pending': pending,
                'skipped': skipped,
                'success_rate': round(success_rate, 2),
                'failure_rate': round(failure_rate, 2),
                'avg_retry_count': round(avg_retry_count, 2)
            }

            # 如果没有指定渠道，按渠道分组统计
            if not channel:
                result['by_channel'] = self._statistics_by_channel(logs)

            return result

        except Exception as e:
            logger.error(f"获取成功率统计失败: {e}", exc_info=True)
            return self._empty_statistics()

    def _statistics_by_channel(self, logs: List[NotificationLog]) -> Dict[str, Dict]:
        """按渠道分组统计"""
        channel_stats = {}

        for channel_name in ['email', 'telegram', 'in_app']:
            channel_logs = [log for log in logs if log.channel == channel_name]

            if not channel_logs:
                continue

            total = len(channel_logs)
            sent = sum(1 for log in channel_logs if log.status == 'sent')
            failed = sum(1 for log in channel_logs if log.status == 'failed')
            pending = sum(1 for log in channel_logs if log.status == 'pending')

            success_rate = (sent / total * 100) if total > 0 else 0

            channel_stats[channel_name] = {
                'total': total,
                'sent': sent,
                'failed': failed,
                'pending': pending,
                'success_rate': round(success_rate, 2)
            }

        return channel_stats

    def _empty_statistics(self) -> Dict:
        """空统计结果"""
        return {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'pending': 0,
            'skipped': 0,
            'success_rate': 0,
            'failure_rate': 0,
            'avg_retry_count': 0,
            'by_channel': {}
        }

    # ==================== 失败记录分析 ====================

    def get_failure_analysis(
        self,
        start_date: date,
        end_date: date,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取失败记录分析

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数

        Returns:
            失败记录列表，包含失败原因和统计
        """
        try:
            failed_logs = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.status == 'failed',
                    NotificationLog.created_at >= start_date,
                    NotificationLog.created_at < end_date + timedelta(days=1)
                )
            ).order_by(desc(NotificationLog.created_at)).limit(limit).all()

            results = []
            for log in failed_logs:
                results.append({
                    'id': log.id,
                    'user_id': log.user_id,
                    'channel': log.channel,
                    'notification_type': log.notification_type,
                    'title': log.title,
                    'failed_reason': log.failed_reason,
                    'retry_count': log.retry_count,
                    'created_at': log.created_at.isoformat(),
                    'business_date': str(log.business_date) if log.business_date else None
                })

            return results

        except Exception as e:
            logger.error(f"获取失败分析失败: {e}", exc_info=True)
            return []

    def get_failure_reasons_summary(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        失败原因统计汇总

        Returns:
            [
                {'reason': '原因', 'count': 次数, 'percentage': 百分比},
                ...
            ]
        """
        try:
            # 统计失败原因
            result = self.db.query(
                NotificationLog.failed_reason,
                func.count(NotificationLog.id).label('count')
            ).filter(
                and_(
                    NotificationLog.status == 'failed',
                    NotificationLog.created_at >= start_date,
                    NotificationLog.created_at < end_date + timedelta(days=1)
                )
            ).group_by(NotificationLog.failed_reason).all()

            total = sum(r.count for r in result)

            summary = []
            for row in result:
                reason = row.failed_reason or '未知原因'
                count = row.count
                percentage = (count / total * 100) if total > 0 else 0

                summary.append({
                    'reason': reason,
                    'count': count,
                    'percentage': round(percentage, 2)
                })

            # 按数量降序排序
            summary.sort(key=lambda x: x['count'], reverse=True)

            return summary

        except Exception as e:
            logger.error(f"获取失败原因汇总失败: {e}", exc_info=True)
            return []

    # ==================== 渠道性能分析 ====================

    def get_channel_performance(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Dict[str, Any]]:
        """
        获取各渠道性能分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {
                'email': {
                    'total': 总数,
                    'success_rate': 成功率,
                    'avg_delivery_time': 平均送达时间（秒）,
                    'failure_reasons': [...],
                    'peak_hours': [...]  # 发送高峰时段
                },
                ...
            }
        """
        try:
            channel_performance = {}

            for channel_name in ['email', 'telegram', 'in_app']:
                # 基础统计
                logs = self.db.query(NotificationLog).filter(
                    and_(
                        NotificationLog.channel == channel_name,
                        NotificationLog.created_at >= start_date,
                        NotificationLog.created_at < end_date + timedelta(days=1)
                    )
                ).all()

                if not logs:
                    continue

                total = len(logs)
                sent = sum(1 for log in logs if log.status == 'sent')
                success_rate = (sent / total * 100) if total > 0 else 0

                # 计算平均送达时间（从创建到发送成功的时间）
                sent_logs = [log for log in logs if log.status == 'sent' and log.sent_at]
                if sent_logs:
                    delivery_times = [
                        (log.sent_at - log.created_at).total_seconds()
                        for log in sent_logs
                    ]
                    avg_delivery_time = sum(delivery_times) / len(delivery_times)
                else:
                    avg_delivery_time = 0

                # 失败原因 Top 5
                failed_logs = [log for log in logs if log.status == 'failed']
                failure_reasons = {}
                for log in failed_logs:
                    reason = log.failed_reason or '未知原因'
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

                top_failures = sorted(
                    failure_reasons.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]

                # 发送高峰时段（按小时统计）
                hourly_counts = {}
                for log in logs:
                    hour = log.created_at.hour
                    hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

                peak_hours = sorted(
                    hourly_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]

                channel_performance[channel_name] = {
                    'total': total,
                    'success_rate': round(success_rate, 2),
                    'avg_delivery_time': round(avg_delivery_time, 2),
                    'failure_reasons': [
                        {'reason': reason, 'count': count}
                        for reason, count in top_failures
                    ],
                    'peak_hours': [
                        {'hour': hour, 'count': count}
                        for hour, count in peak_hours
                    ]
                }

            return channel_performance

        except Exception as e:
            logger.error(f"获取渠道性能分析失败: {e}", exc_info=True)
            return {}

    # ==================== 趋势分析 ====================

    def get_daily_trend(
        self,
        start_date: date,
        end_date: date,
        channel: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取每日发送趋势

        Args:
            start_date: 开始日期
            end_date: 结束日期
            channel: 指定渠道

        Returns:
            [
                {
                    'date': '2026-03-15',
                    'total': 100,
                    'sent': 95,
                    'failed': 3,
                    'pending': 2,
                    'success_rate': 95.0
                },
                ...
            ]
        """
        try:
            # 使用原生 SQL 查询（效率更高）
            sql = text("""
                SELECT
                    DATE(created_at) as send_date,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM notification_logs
                WHERE created_at >= :start_date
                  AND created_at < :end_date
                  AND (:channel IS NULL OR channel = :channel)
                GROUP BY DATE(created_at)
                ORDER BY send_date DESC
            """)

            result = self.db.execute(
                sql,
                {
                    'start_date': start_date,
                    'end_date': end_date + timedelta(days=1),
                    'channel': channel
                }
            )

            trends = []
            for row in result:
                total = row.total
                sent = row.sent
                success_rate = (sent / total * 100) if total > 0 else 0

                trends.append({
                    'date': str(row.send_date),
                    'total': total,
                    'sent': sent,
                    'failed': row.failed,
                    'pending': row.pending,
                    'success_rate': round(success_rate, 2)
                })

            return trends

        except Exception as e:
            logger.error(f"获取每日趋势失败: {e}", exc_info=True)
            return []

    # ==================== 用户通知统计 ====================

    def get_user_notification_stats(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户通知统计

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            用户通知统计数据
        """
        try:
            start_date = datetime.now() - timedelta(days=days)

            logs = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.user_id == user_id,
                    NotificationLog.created_at >= start_date
                )
            ).all()

            total = len(logs)
            sent = sum(1 for log in logs if log.status == 'sent')
            failed = sum(1 for log in logs if log.status == 'failed')

            # 按通知类型统计
            by_type = {}
            for log in logs:
                ntype = log.notification_type
                if ntype not in by_type:
                    by_type[ntype] = {'total': 0, 'sent': 0}
                by_type[ntype]['total'] += 1
                if log.status == 'sent':
                    by_type[ntype]['sent'] += 1

            # 按渠道统计
            by_channel = {}
            for log in logs:
                channel = log.channel
                if channel not in by_channel:
                    by_channel[channel] = {'total': 0, 'sent': 0}
                by_channel[channel]['total'] += 1
                if log.status == 'sent':
                    by_channel[channel]['sent'] += 1

            return {
                'user_id': user_id,
                'period_days': days,
                'total': total,
                'sent': sent,
                'failed': failed,
                'success_rate': round((sent / total * 100) if total > 0 else 0, 2),
                'by_type': by_type,
                'by_channel': by_channel
            }

        except Exception as e:
            logger.error(f"获取用户通知统计失败: {e}", exc_info=True)
            return {}

    # ==================== 实时监控 ====================

    def get_realtime_stats(self) -> Dict[str, Any]:
        """
        获取实时监控数据

        Returns:
            {
                'last_24h': {...},
                'last_hour': {...},
                'pending_count': 待发送数,
                'recent_failures': [...]
            }
        """
        try:
            now = datetime.now()
            yesterday = now - timedelta(hours=24)
            last_hour = now - timedelta(hours=1)

            # 最近 24 小时统计
            last_24h_stats = self.get_success_rate_statistics(
                start_date=yesterday.date(),
                end_date=now.date()
            )

            # 最近 1 小时统计
            last_hour_logs = self.db.query(NotificationLog).filter(
                NotificationLog.created_at >= last_hour
            ).all()

            last_hour_stats = {
                'total': len(last_hour_logs),
                'sent': sum(1 for log in last_hour_logs if log.status == 'sent'),
                'failed': sum(1 for log in last_hour_logs if log.status == 'failed')
            }

            # 待发送数量
            pending_count = self.db.query(NotificationLog).filter(
                NotificationLog.status == 'pending'
            ).count()

            # 最近失败记录（最近 10 条）
            recent_failures = self.get_failure_analysis(
                start_date=(now - timedelta(days=1)).date(),
                end_date=now.date(),
                limit=10
            )

            return {
                'last_24h': last_24h_stats,
                'last_hour': last_hour_stats,
                'pending_count': pending_count,
                'recent_failures': recent_failures,
                'timestamp': now.isoformat()
            }

        except Exception as e:
            logger.error(f"获取实时监控数据失败: {e}", exc_info=True)
            return {}

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """
        通知系统健康检查

        Returns:
            {
                'status': 'healthy' | 'warning' | 'critical',
                'success_rate_24h': 成功率,
                'pending_alert': 是否有积压,
                'failure_rate_alert': 失败率是否过高,
                'details': {...}
            }
        """
        try:
            now = datetime.now()
            yesterday = now - timedelta(hours=24)

            # 最近 24 小时统计
            stats = self.get_success_rate_statistics(
                start_date=yesterday.date(),
                end_date=now.date()
            )

            # 待发送积压检查
            pending_count = self.db.query(NotificationLog).filter(
                and_(
                    NotificationLog.status == 'pending',
                    NotificationLog.created_at < now - timedelta(hours=1)
                )
            ).count()

            # 健康状态评估
            status = 'healthy'
            alerts = []

            # 成功率检查
            if stats['success_rate'] < 90:
                status = 'warning'
                alerts.append(f"成功率低于 90% ({stats['success_rate']}%)")

            if stats['success_rate'] < 70:
                status = 'critical'
                alerts.append(f"成功率严重偏低 ({stats['success_rate']}%)")

            # 积压检查
            if pending_count > 100:
                status = 'warning' if status == 'healthy' else status
                alerts.append(f"待发送积压: {pending_count} 条")

            if pending_count > 500:
                status = 'critical'
                alerts.append(f"待发送严重积压: {pending_count} 条")

            # 失败率检查
            if stats['failure_rate'] > 10:
                status = 'warning' if status == 'healthy' else status
                alerts.append(f"失败率过高: {stats['failure_rate']}%")

            return {
                'status': status,
                'success_rate_24h': stats['success_rate'],
                'pending_count': pending_count,
                'failure_rate': stats['failure_rate'],
                'alerts': alerts,
                'details': stats,
                'timestamp': now.isoformat()
            }

        except Exception as e:
            logger.error(f"健康检查失败: {e}", exc_info=True)
            return {
                'status': 'critical',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
