"""
Email 发送器

Phase 3 优化: 使用 SMTP 连接池提升性能
"""

import smtplib
from email.message import EmailMessage
from typing import Dict, Optional
from loguru import logger
import threading
import queue
import time


class SMTPConnectionPool:
    """SMTP 连接池（线程安全）"""

    def __init__(self, config: Dict, pool_size: int = 5, timeout: int = 300):
        """
        初始化连接池

        Args:
            config: SMTP 配置
            pool_size: 连接池大小
            timeout: 连接超时时间（秒），超时后自动关闭连接
        """
        self.config = config
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool = queue.Queue(maxsize=pool_size)
        self.active_connections = 0
        self.lock = threading.Lock()

    def get_connection(self) -> Optional[smtplib.SMTP]:
        """获取可用连接"""
        try:
            # 尝试从池中获取连接
            if not self.pool.empty():
                conn = self.pool.get_nowait()
                # 检查连接是否有效
                try:
                    conn.noop()  # 发送 NOOP 命令测试连接
                    return conn
                except Exception:
                    # 连接已失效，创建新连接
                    logger.warning("连接池中的连接已失效，创建新连接")
                    return self._create_connection()
            else:
                # 池中无连接，创建新连接
                return self._create_connection()

        except Exception as e:
            logger.error(f"获取 SMTP 连接失败: {e}")
            return None

    def release_connection(self, conn: smtplib.SMTP):
        """释放连接回池"""
        try:
            if self.pool.qsize() < self.pool_size:
                self.pool.put_nowait(conn)
            else:
                # 池已满，关闭连接
                try:
                    conn.quit()
                except Exception:
                    pass

        except queue.Full:
            try:
                conn.quit()
            except Exception:
                pass

    def _create_connection(self) -> Optional[smtplib.SMTP]:
        """创建新的 SMTP 连接"""
        try:
            use_tls = self.config.get('smtp_use_tls', True)
            host = self.config['smtp_host']
            port = self.config['smtp_port']
            username = self.config['smtp_username']
            password = self.config['smtp_password']

            if use_tls:
                conn = smtplib.SMTP(host, port, timeout=30)
                conn.starttls()
            else:
                conn = smtplib.SMTP_SSL(host, port, timeout=30)

            conn.login(username, password)

            with self.lock:
                self.active_connections += 1

            logger.info(f"创建新 SMTP 连接 (当前活跃: {self.active_connections})")
            return conn

        except Exception as e:
            logger.error(f"创建 SMTP 连接失败: {e}")
            return None

    def close_all(self):
        """关闭所有连接"""
        closed_count = 0
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.quit()
                closed_count += 1
            except Exception:
                pass

        logger.info(f"连接池已关闭，共关闭 {closed_count} 个连接")


class EmailSender:
    """邮件发送器（Phase 3 优化版）"""

    # 全局连接池（按配置哈希缓存）
    _connection_pools: Dict[str, SMTPConnectionPool] = {}
    _pool_lock = threading.Lock()

    def __init__(self, config: Dict, use_pool: bool = True):
        """
        初始化邮件发送器

        Args:
            config: SMTP 配置字典
            use_pool: 是否使用连接池（默认启用，提升性能）
        """
        self.config = config
        self.use_pool = use_pool
        self._connection_pool: Optional[SMTPConnectionPool] = None

        if self.use_pool:
            # 获取或创建连接池
            pool_key = self._get_pool_key(config)
            with self._pool_lock:
                if pool_key not in self._connection_pools:
                    self._connection_pools[pool_key] = SMTPConnectionPool(config)
                self._connection_pool = self._connection_pools[pool_key]

    def _get_pool_key(self, config: Dict) -> str:
        """生成连接池键"""
        return f"{config['smtp_host']}:{config['smtp_port']}:{config['smtp_username']}"

    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        发送邮件（Phase 3 优化：使用连接池）

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

            # 使用连接池发送（性能优化）
            if self.use_pool and self._connection_pool:
                return self._send_with_pool(message, to_email)
            else:
                return self._send_direct(message, to_email)

        except Exception as e:
            logger.error(f"邮件发送异常: {e}", exc_info=True)
            return False

    def _send_with_pool(self, message: EmailMessage, to_email: str) -> bool:
        """使用连接池发送邮件（性能优化）"""
        conn = None
        try:
            conn = self._connection_pool.get_connection()
            if not conn:
                logger.error("无法获取 SMTP 连接")
                return False

            conn.send_message(message)
            logger.info(f"邮件发送成功（连接池）: {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP 认证失败: {e}")
            # 认证失败，关闭连接
            if conn:
                try:
                    conn.quit()
                except Exception:
                    pass
            return False

        except smtplib.SMTPException as e:
            logger.error(f"SMTP 发送失败: {e}")
            # 发送失败，关闭连接
            if conn:
                try:
                    conn.quit()
                except Exception:
                    pass
            return False

        except Exception as e:
            logger.error(f"邮件发送异常: {e}")
            return False

        finally:
            # 释放连接回池
            if conn:
                try:
                    self._connection_pool.release_connection(conn)
                except Exception as e:
                    logger.error(f"释放连接失败: {e}")

    def _send_direct(self, message: EmailMessage, to_email: str) -> bool:
        """直接发送邮件（不使用连接池）"""
        try:
            if self.config.get('smtp_use_tls', True):
                with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port'], timeout=30) as server:
                    server.starttls()
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                    server.send_message(message)
            else:
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
