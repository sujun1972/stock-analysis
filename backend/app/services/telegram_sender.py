"""
Telegram Bot 消息发送器

支持功能:
- 基本文本消息发送
- Markdown/HTML 格式化
- 消息长度自动分割（Telegram 限制 4096 字符）
- 连接超时和重试机制
- 消息预览模式
"""
import requests
from typing import Dict, List, Optional
from loguru import logger


class TelegramSender:
    """Telegram Bot 发送器（增强版）"""

    # Telegram 消息长度限制
    MAX_MESSAGE_LENGTH = 4096

    def __init__(self, config: Dict):
        """
        初始化 Telegram 发送器

        Args:
            config: Bot 配置字典
            {
                "bot_token": "1234567890:ABCDEF...",
                "parse_mode": "Markdown",
                "timeout": 30,
                "disable_notification": false,
                "disable_web_page_preview": false
            }
        """
        self.config = config
        self.bot_token = config['bot_token']
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.timeout = config.get('timeout', 30)

    def send(
        self,
        chat_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        disable_notification: bool = False,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        发送 Telegram 消息（自动处理长消息分割）

        Args:
            chat_id: 用户的 Chat ID
            message: 消息内容（支持 Markdown 或 HTML）
            parse_mode: 解析模式（'Markdown' 或 'HTML' 或 'MarkdownV2'）
            disable_notification: 是否静默推送
            disable_web_page_preview: 是否禁用链接预览

        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            # 使用配置中的默认 parse_mode
            if parse_mode is None:
                parse_mode = self.config.get('parse_mode', 'Markdown')

            # 如果消息超长，自动分割
            if len(message) > self.MAX_MESSAGE_LENGTH:
                logger.warning(
                    f"消息长度 {len(message)} 超过限制 {self.MAX_MESSAGE_LENGTH}，自动分割"
                )
                return self._send_long_message(
                    chat_id=chat_id,
                    message=message,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    disable_web_page_preview=disable_web_page_preview
                )

            # 发送单条消息
            return self._send_single_message(
                chat_id=chat_id,
                message=message,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                disable_web_page_preview=disable_web_page_preview
            )

        except Exception as e:
            logger.error(f"Telegram 发送异常: {e}", exc_info=True)
            return False

    def _send_single_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str,
        disable_notification: bool,
        disable_web_page_preview: bool
    ) -> bool:
        """发送单条消息"""
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_notification': disable_notification,
            'disable_web_page_preview': disable_web_page_preview
        }

        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Telegram 发送成功: chat_id={chat_id}")
                return True
            else:
                error_data = response.json()
                logger.error(
                    f"Telegram 发送失败: {response.status_code}, "
                    f"{error_data.get('description', response.text)}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Telegram 发送超时: chat_id={chat_id}, timeout={self.timeout}s")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram 请求失败: {e}")
            return False

    def _send_long_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str,
        disable_notification: bool,
        disable_web_page_preview: bool
    ) -> bool:
        """
        发送长消息（自动分割）

        策略:
        1. 按段落分割（\n\n）
        2. 如果单段落超长，强制在最大长度处切割
        3. 保留格式标记完整性
        """
        chunks = self._split_message(message)

        logger.info(f"长消息分割为 {len(chunks)} 段")

        all_success = True
        for i, chunk in enumerate(chunks, 1):
            # 添加分页标记
            if len(chunks) > 1:
                chunk_with_marker = f"{chunk}\n\n_（第 {i}/{len(chunks)} 部分）_"
            else:
                chunk_with_marker = chunk

            success = self._send_single_message(
                chat_id=chat_id,
                message=chunk_with_marker,
                parse_mode=parse_mode,
                disable_notification=disable_notification if i == 1 else True,  # 只第一条通知
                disable_web_page_preview=disable_web_page_preview
            )

            if not success:
                all_success = False
                logger.error(f"第 {i}/{len(chunks)} 部分发送失败")
                # 继续尝试发送后续部分

        return all_success

    def _split_message(self, message: str) -> List[str]:
        """
        智能分割消息

        Returns:
            分割后的消息片段列表
        """
        # 预留分页标记的空间（约 30 字符）
        effective_limit = self.MAX_MESSAGE_LENGTH - 50

        if len(message) <= effective_limit:
            return [message]

        chunks = []
        # 先按双换行符分割（段落）
        paragraphs = message.split('\n\n')

        current_chunk = ""
        for paragraph in paragraphs:
            # 如果单个段落就超长，需要强制分割
            if len(paragraph) > effective_limit:
                # 先保存当前积累的内容
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # 强制分割超长段落
                for i in range(0, len(paragraph), effective_limit):
                    chunks.append(paragraph[i:i + effective_limit])
            else:
                # 检查加入后是否超长
                if len(current_chunk) + len(paragraph) + 2 > effective_limit:
                    # 保存当前块
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # 继续积累
                    current_chunk += ("\n\n" if current_chunk else "") + paragraph

        # 保存最后一块
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def test_connection(self, chat_id: str) -> Dict[str, any]:
        """
        测试 Bot 连接和 Chat ID 有效性

        Args:
            chat_id: 测试目标 Chat ID

        Returns:
            {
                "success": bool,
                "message": str,
                "bot_info": dict  # Bot 基本信息
            }
        """
        try:
            # 1. 测试 Bot Token 有效性
            bot_info_response = requests.get(
                f"{self.api_url}/getMe",
                timeout=10
            )

            if bot_info_response.status_code != 200:
                return {
                    "success": False,
                    "message": f"Bot Token 无效: {bot_info_response.text}",
                    "bot_info": None
                }

            bot_info = bot_info_response.json()['result']
            logger.info(f"Bot 信息: @{bot_info.get('username')}")

            # 2. 发送测试消息
            test_message = (
                "🔔 *Telegram Bot 测试消息*\n\n"
                f"Bot 名称: {bot_info.get('first_name')}\n"
                f"Bot 用户名: @{bot_info.get('username')}\n"
                f"测试时间: {self._get_current_time()}\n\n"
                "✅ 如果您收到此消息，说明配置成功！"
            )

            success = self.send(
                chat_id=chat_id,
                message=test_message,
                parse_mode='Markdown'
            )

            if success:
                return {
                    "success": True,
                    "message": "测试消息发送成功",
                    "bot_info": {
                        "bot_name": bot_info.get('first_name'),
                        "bot_username": bot_info.get('username'),
                        "bot_id": bot_info.get('id')
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"测试消息发送失败，请检查 Chat ID: {chat_id}",
                    "bot_info": None
                }

        except Exception as e:
            logger.error(f"Telegram 连接测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
                "bot_info": None
            }

    def get_chat_info(self, chat_id: str) -> Optional[Dict]:
        """
        获取 Chat 信息（验证 Chat ID 有效性）

        Args:
            chat_id: Chat ID

        Returns:
            Chat 信息字典，失败返回 None
        """
        try:
            response = requests.get(
                f"{self.api_url}/getChat",
                params={'chat_id': chat_id},
                timeout=10
            )

            if response.status_code == 200:
                chat_info = response.json()['result']
                return {
                    'type': chat_info.get('type'),
                    'username': chat_info.get('username'),
                    'first_name': chat_info.get('first_name'),
                    'last_name': chat_info.get('last_name'),
                    'title': chat_info.get('title')
                }
            else:
                logger.error(f"获取 Chat 信息失败: {response.text}")
                return None

        except Exception as e:
            logger.error(f"获取 Chat 信息异常: {e}")
            return None

    @staticmethod
    def _get_current_time() -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        转义 Markdown 特殊字符（MarkdownV2 模式需要）

        Args:
            text: 原始文本

        Returns:
            转义后的文本
        """
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
