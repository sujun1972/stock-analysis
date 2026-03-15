"""
Celery 通知任务

异步发送邮件、Telegram 和站内消息
Phase 2: 集成 Telegram、模板渲染、频率限制
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from typing import Dict, Any, List
from datetime import datetime

from app.core.database import get_db
from app.services.notification_service import NotificationService
from app.services.email_sender import EmailSender
from app.services.telegram_sender import TelegramSender  # Phase 2
from app.services.template_renderer import TemplateRenderer  # Phase 2
from app.services.notification_rate_limiter import NotificationRateLimiter  # Phase 2

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


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_notification_task(
    self,
    user_id: int,
    chat_id: str,
    message: str,
    notification_log_id: int,
    parse_mode: str = 'Markdown'
):
    """
    发送 Telegram 通知（Phase 2）

    Args:
        user_id: 用户ID
        chat_id: Telegram Chat ID
        message: 消息内容
        notification_log_id: 通知日志ID
        parse_mode: 解析模式（Markdown/HTML）

    重试策略: 3次，指数退避 (30s, 60s, 120s)
    """
    db = None
    try:
        logger.info(f"开始发送 Telegram: user_id={user_id}, chat_id={chat_id}")

        # 获取数据库会话
        db = next(get_db())
        service = NotificationService(db)

        # 查询 Telegram Bot 配置
        bot_config = service.get_channel_config('telegram')

        if not bot_config or not bot_config.get('bot_token'):
            raise ValueError("Telegram Bot 配置不存在或未启用")

        # 发送消息
        telegram_sender = TelegramSender(bot_config)
        success = telegram_sender.send(
            chat_id=chat_id,
            message=message,
            parse_mode=parse_mode
        )

        if success:
            # 更新日志状态为成功
            service.update_notification_log(notification_log_id, 'sent')
            logger.info(f"Telegram 发送成功: log_id={notification_log_id}")
        else:
            raise Exception("Telegram 发送失败")

    except Exception as exc:
        logger.error(f"Telegram 发送失败: {exc}")

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
            countdown = 30 * (2 ** self.request.retries)
            logger.warning(f"准备重试 ({self.request.retries + 1}/{self.max_retries})，延迟 {countdown}s")
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(f"Telegram 最终发送失败: log_id={notification_log_id}")

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
    调度报告通知（批量生成发送任务）- Phase 2 增强版

    Args:
        report_type: 报告类型 ('sentiment_report', 'premarket_report', 'backtest_result')
        trade_date: 交易日期
        report_data: 报告原始数据

    Phase 2 增强:
    1. 使用 Jinja2 模板渲染
    2. 检查频率限制
    3. 支持 Telegram 发送
    4. 批量发送优化
    """
    db = None
    try:
        logger.info(f"开始调度 {report_type} 通知: date={trade_date}")

        db = next(get_db())
        service = NotificationService(db)
        renderer = TemplateRenderer(db)  # Phase 2: 模板渲染器
        rate_limiter = NotificationRateLimiter(db)  # Phase 2: 频率限制器

        # 1. 获取订阅用户列表
        subscribers = service.get_subscribers(report_type)
        logger.info(f"找到 {len(subscribers)} 个订阅 {report_type} 的用户")

        if not subscribers:
            logger.info(f"无订阅用户，跳过通知调度")
            return

        # 统计数据
        sent_count = 0
        skipped_count = 0
        failed_count = 0

        # 2. 为每个用户生成通知
        for user in subscribers:
            user_id = user['user_id']

            try:
                # Phase 2: 检查频率限制
                rate_check = rate_limiter.check_rate_limit(user_id)
                if not rate_check['allowed']:
                    logger.warning(
                        f"用户 {user_id} 超过频率限制: {rate_check['reason']}"
                    )
                    skipped_count += 1
                    continue

                # 准备模板上下文
                context = {
                    'trade_date': trade_date,
                    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    **report_data  # 合并报告数据
                }

                # 获取用户配置的内容格式
                content_format = user.get('report_format', 'full')

                # 3. 异步发送到各渠道
                enabled_channels = user.get('enabled_channels', [])

                # Email 渠道
                if 'email' in enabled_channels and user.get('email_address'):
                    try:
                        # Phase 2: 使用模板渲染
                        email_render = renderer.render_notification(
                            notification_type=report_type,
                            channel='email',
                            context=context,
                            content_format=content_format
                        )

                        # 创建日志
                        log_id = service.create_notification_log(
                            user_id=user_id,
                            notification_type=report_type,
                            channel='email',
                            title=email_render['subject'],
                            content=email_render['content'],
                            content_type=content_format,
                            business_date=trade_date
                        )

                        # 异步发送
                        send_email_notification_task.delay(
                            user_id=user_id,
                            email_address=user['email_address'],
                            subject=email_render['subject'],
                            html_content=email_render['content'],
                            notification_log_id=log_id
                        )

                        # 增加计数器
                        rate_limiter.increment_counter(user_id, 'email')
                        logger.info(f"已推送邮件任务: user_id={user_id}")

                    except Exception as e:
                        logger.error(f"Email 任务创建失败: user_id={user_id}, {e}")

                # Telegram 渠道 (Phase 2)
                if 'telegram' in enabled_channels and user.get('telegram_chat_id'):
                    try:
                        # Phase 2: 使用模板渲染
                        telegram_render = renderer.render_notification(
                            notification_type=report_type,
                            channel='telegram',
                            context=context,
                            content_format=content_format
                        )

                        # 创建日志
                        log_id = service.create_notification_log(
                            user_id=user_id,
                            notification_type=report_type,
                            channel='telegram',
                            title=telegram_render['subject'],
                            content=telegram_render['content'],
                            content_type=content_format,
                            business_date=trade_date
                        )

                        # 异步发送
                        send_telegram_notification_task.delay(
                            user_id=user_id,
                            chat_id=user['telegram_chat_id'],
                            message=telegram_render['content'],
                            notification_log_id=log_id,
                            parse_mode='Markdown'
                        )

                        # 增加计数器
                        rate_limiter.increment_counter(user_id, 'telegram')
                        logger.info(f"已推送 Telegram 任务: user_id={user_id}")

                    except Exception as e:
                        logger.error(f"Telegram 任务创建失败: user_id={user_id}, {e}")

                # 站内消息渠道
                if 'in_app' in enabled_channels:
                    try:
                        # Phase 2: 使用模板渲染
                        in_app_render = renderer.render_notification(
                            notification_type=report_type,
                            channel='in_app',
                            context=context,
                            content_format='summary'  # 站内消息使用摘要版
                        )

                        # 异步发送
                        send_in_app_notification_task.delay(
                            user_id=user_id,
                            title=in_app_render['subject'],
                            content=in_app_render['content'],
                            notification_type=report_type,
                            business_date=trade_date
                        )

                        # 增加计数器
                        rate_limiter.increment_counter(user_id, 'in_app')
                        logger.info(f"已推送站内消息任务: user_id={user_id}")

                    except Exception as e:
                        logger.error(f"站内消息任务创建失败: user_id={user_id}, {e}")

                sent_count += 1

            except Exception as e:
                logger.error(f"处理用户 {user_id} 通知失败: {e}", exc_info=True)
                failed_count += 1
                continue

        logger.info(
            f"{report_type} 通知调度完成 - "
            f"总计: {len(subscribers)}, 成功: {sent_count}, "
            f"跳过: {skipped_count}, 失败: {failed_count}"
        )

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


# ==================== Phase 3: 监控与告警任务 ====================

@shared_task
def notification_health_check_task():
    """
    通知系统健康检查任务

    定时任务，每小时执行一次
    检查发送成功率、失败率、积压情况，发现异常自动告警
    """
    db = None
    try:
        logger.info("开始通知系统健康检查...")

        db = next(get_db())
        from app.services.notification_alert import NotificationAlert

        alert_service = NotificationAlert(db)
        result = alert_service.check_and_alert()

        health_status = result.get('health_status', 'unknown')
        alerts_count = len(result.get('alerts_triggered', []))

        if alerts_count > 0:
            logger.warning(
                f"通知系统健康检查发现异常: status={health_status}, "
                f"alerts={alerts_count}"
            )
        else:
            logger.info(f"通知系统健康检查正常: status={health_status}")

        return result

    except Exception as e:
        logger.error(f"健康检查任务失败: {e}", exc_info=True)
        return {
            'health_status': 'critical',
            'error': str(e),
            'alerts_triggered': []
        }

    finally:
        if db:
            db.close()


@shared_task
def reset_daily_rate_limits_task():
    """
    重置每日频率限制计数器

    定时任务，每天凌晨执行
    重置所有用户的每日通知计数
    """
    db = None
    try:
        logger.info("开始重置每日频率限制...")

        db = next(get_db())
        from sqlalchemy import text

        # 批量重置计数器
        result = db.execute(
            text("""
                UPDATE user_notification_settings
                SET daily_notification_count = 0,
                    last_reset_date = CURRENT_DATE
                WHERE last_reset_date < CURRENT_DATE
            """)
        )

        reset_count = result.rowcount
        db.commit()

        logger.info(f"频率限制重置完成，共重置 {reset_count} 个用户")

    except Exception as e:
        logger.error(f"重置频率限制失败: {e}", exc_info=True)
        if db:
            db.rollback()

    finally:
        if db:
            db.close()
