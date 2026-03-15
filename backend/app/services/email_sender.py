"""
Email 发送器

使用 SMTP 协议发送邮件通知
"""

import smtplib
from email.message import EmailMessage
from typing import Dict
from loguru import logger


class EmailSender:
    """邮件发送器"""

    def __init__(self, config: Dict):
        """
        初始化邮件发送器

        Args:
            config: SMTP 配置字典
            {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "user@example.com",
                "smtp_password": "password",
                "smtp_use_tls": true,
                "from_email": "noreply@example.com",
                "from_name": "股票分析系统"
            }
        """
        self.config = config

    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 格式邮件内容

        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            # 验证必要配置
            if not all([
                self.config.get('smtp_host'),
                self.config.get('smtp_port'),
                self.config.get('smtp_username'),
                self.config.get('smtp_password'),
                self.config.get('from_email')
            ]):
                logger.error("SMTP 配置不完整")
                return False

            # 构建邮件消息
            message = EmailMessage()
            from_name = self.config.get('from_name', '系统')
            message['From'] = f"{from_name} <{self.config['from_email']}>"
            message['To'] = to_email
            message['Subject'] = subject
            message.set_content(html_content, subtype='html')

            # 发送邮件（同步方式，适用于 Celery Worker）
            if self.config.get('smtp_use_tls', True):
                # TLS 加密连接（端口通常为 587）
                with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'], timeout=30) as server:
                    server.starttls()
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                    server.send_message(message)
            else:
                # SSL 加密连接（端口通常为 465）
                with smtplib.SMTP_SSL(self.config['smtp_host'], self.config['smtp_port'], timeout=30) as server:
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                    server.send_message(message)

            logger.info(f"邮件发送成功: {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 认证失败: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 发送失败: {e}")
            return False
        except Exception as e:
            logger.error(f"邮件发送异常: {e}", exc_info=True)
            return False

    def test_connection(self) -> tuple[bool, str]:
        """
        测试 SMTP 连接

        Returns:
            (是否成功, 消息)
        """
        try:
            # 验证配置
            if not all([
                self.config.get('smtp_host'),
                self.config.get('smtp_port'),
                self.config.get('smtp_username'),
                self.config.get('smtp_password')
            ]):
                return False, "SMTP 配置不完整"

            # 测试连接
            if self.config.get('smtp_use_tls', True):
                with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'], timeout=10) as server:
                    server.starttls()
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
            else:
                with smtplib.SMTP_SSL(self.config['smtp_host'], self.config['smtp_port'], timeout=10) as server:
                    server.login(self.config['smtp_username'], self.config['smtp_password'])

            logger.info("SMTP 连接测试成功")
            return True, "SMTP 连接测试成功"

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP 认证失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP 连接失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"连接测试异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
