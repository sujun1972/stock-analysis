"""
Celery 通知任务

异步发送邮件、Telegram 和站内消息
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from typing import Dict, Any, List
from datetime import datetime

from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.services.email_sender import EmailSender

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification_task(
    self,
    user_id: int,
    email_address: str,
    subject: str,
    html_content: str,
    notification_log_id: int
):
    """
    发送邮件通知

    Args:
        user_id: 用户ID
        email_address: 收件人邮箱
        subject: 邮件主题
        html_content: HTML 格式邮件内容
        notification_log_id: 通知日志ID

    重试策略: 3次，指数退避 (60s, 120s, 240s)
    """
    db = None
    try:
        logger.info(f"开始发送邮件: user_id={user_id}, email={email_address}")

        # 获取数据库会话
        db = next(get_db())
        service = NotificationService(db)

        # 查询 SMTP 配置
        smtp_config = service.get_channel_config('email')

        if not smtp_config or not smtp_config.get('smtp_host'):
            raise ValueError("SMTP 配置不存在或未启用")

        # 发送邮件
        email_sender = EmailSender(smtp_config)
        success = email_sender.send(
            to_email=email_address,
            subject=subject,
            html_content=html_content
        )

        if success:
            # 更新日志状态为成功
            service.update_notification_log(notification_log_id, 'sent')
            logger.info(f"邮件发送成功: log_id={notification_log_id}")
        else:
            raise Exception("邮件发送失败")

    except Exception as exc:
        logger.error(f"邮件发送失败: {exc}")

        # 更新日志状态为失败
        if db:
            try:
                service = NotificationService(db)
                service.update_notification_log(
                    notification_log_id,
                    'failed',
                    failed_reason=str(exc),
                    retry_count=self.request.retries
                )
            except Exception as e:
                logger.error(f"更新日志失败: {e}")

        # 指数退避重试
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            logger.warning(f"准备重试 ({self.request.retries + 1}/{self.max_retries})，延迟 {countdown}s")
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(f"邮件最终发送失败: log_id={notification_log_id}")

    finally:
        if db:
            db.close()


@shared_task
def send_in_app_notification_task(
    user_id: int,
    title: str,
    content: str,
    notification_type: str,
    business_date: str = None,
    reference_id: str = None,
    metadata: Dict = None,
    priority: str = 'normal'
):
    """
    发送站内消息

    Args:
        user_id: 用户ID
        title: 消息标题
        content: 消息内容
        notification_type: 通知类型
        business_date: 关联的交易日
        reference_id: 关联的业务ID
        metadata: 额外元数据
        priority: 优先级

    注意: 站内消息直接写库，无需重试
    """
    db = None
    try:
        logger.info(f"创建站内消息: user_id={user_id}, type={notification_type}")

        db = next(get_db())
        service = NotificationService(db)

        service.create_in_app_notification(
            user_id=user_id,
            title=title,
            content=content,
            notification_type=notification_type,
            business_date=business_date,
            reference_id=reference_id,
            metadata=metadata,
            priority=priority
        )

        logger.info(f"站内消息创建成功: user_id={user_id}, type={notification_type}")

    except Exception as e:
        logger.error(f"站内消息创建失败: {e}", exc_info=True)

    finally:
        if db:
            db.close()


@shared_task
def schedule_report_notification_task(
    report_type: str,
    trade_date: str,
    report_data: Dict[str, Any]
):
    """
    调度报告通知（批量生成发送任务）

    Args:
        report_type: 报告类型 ('sentiment_report', 'premarket_report', 'backtest_result')
        trade_date: 交易日期
        report_data: 报告原始数据

    流程:
    1. 查询订阅用户列表
    2. 为每个用户渲染报告内容
    3. 创建通知日志
    4. 异步发送到各渠道队列
    """
    db = None
    try:
        logger.info(f"开始调度 {report_type} 通知: date={trade_date}")

        db = next(get_db())
        service = NotificationService(db)

        # 1. 获取订阅用户列表
        subscribers = service.get_subscribers(report_type)
        logger.info(f"找到 {len(subscribers)} 个订阅 {report_type} 的用户")

        if not subscribers:
            logger.info(f"无订阅用户，跳过通知调度")
            return

        # 2. 为每个用户生成通知
        for user in subscribers:
            try:
                # 渲染报告内容
                rendered = service.render_report(
                    report_type=report_type,
                    report_data=report_data,
                    user_preferences=user
                )

                # 创建通知日志
                log_ids = service.create_notification_logs(
                    user_id=user['user_id'],
                    notification_type=report_type,
                    title=rendered['title'],
                    content=rendered['content'],
                    business_date=trade_date,
                    channels=user['enabled_channels']
                )

                # 3. 异步发送到各渠道
                if 'email' in user['enabled_channels']:
                    send_email_notification_task.delay(
                        user_id=user['user_id'],
                        email_address=user['email_address'],
                        subject=rendered['title'],
                        html_content=rendered['email_html'],
                        notification_log_id=log_ids['email']
                    )
                    logger.info(f"已推送邮件任务: user_id={user['user_id']}")

                if 'telegram' in user['enabled_channels']:
                    # TODO: Phase 2 实现 Telegram 发送
                    logger.warning(f"Telegram 发送功能尚未实现（Phase 2）")

                if 'in_app' in user['enabled_channels']:
                    send_in_app_notification_task.delay(
                        user_id=user['user_id'],
                        title=rendered['title'],
                        content=rendered['content'],
                        notification_type=report_type,
                        business_date=trade_date
                    )
                    logger.info(f"已推送站内消息任务: user_id={user['user_id']}")

            except Exception as e:
                logger.error(f"处理用户 {user['user_id']} 通知失败: {e}", exc_info=True)
                continue

        logger.info(f"{report_type} 通知调度完成，共处理 {len(subscribers)} 个用户")

    except Exception as e:
        logger.error(f"调度通知任务失败: {e}", exc_info=True)

    finally:
        if db:
            db.close()


@shared_task
def cleanup_expired_notifications_task():
    """
    清理过期的站内消息

    定时任务，每天凌晨执行
    清理 3 个月前的已读消息
    """
    db = None
    try:
        logger.info("开始清理过期的站内消息")

        db = next(get_db())

        # 使用原生 SQL 清理（效率更高）
        from sqlalchemy import text
        from datetime import timedelta

        three_months_ago = datetime.now() - timedelta(days=90)

        result = db.execute(
            text("""
                DELETE FROM in_app_notifications
                WHERE is_read = true
                  AND created_at < :cutoff_date
            """),
            {"cutoff_date": three_months_ago}
        )

        deleted_count = result.rowcount
        db.commit()

        logger.info(f"清理完成，删除 {deleted_count} 条过期消息")

    except Exception as e:
        logger.error(f"清理过期消息失败: {e}", exc_info=True)
        if db:
            db.rollback()

    finally:
        if db:
            db.close()
