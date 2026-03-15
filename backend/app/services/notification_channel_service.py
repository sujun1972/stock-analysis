"""
通知渠道配置服务层

管理员管理通知渠道配置（SMTP、Telegram Bot 等）
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from loguru import logger
import copy

from app.models.notification_channel_config import NotificationChannelConfig
from app.services.email_sender import EmailSender


class NotificationChannelService:
    """通知渠道配置服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_channels(self) -> List[NotificationChannelConfig]:
        """获取所有通知渠道配置"""
        channels = self.db.query(NotificationChannelConfig).all()

        # 脱敏处理
        for channel in channels:
            channel.config = self._mask_sensitive_data(channel.config, channel.channel_type)

        return channels

    def get_channel_by_type(self, channel_type: str) -> Optional[NotificationChannelConfig]:
        """获取指定渠道配置"""
        channel = self.db.query(NotificationChannelConfig).filter(
            NotificationChannelConfig.channel_type == channel_type
        ).first()

        if channel:
            channel.config = self._mask_sensitive_data(channel.config, channel.channel_type)

        return channel

    def update_channel(
        self,
        channel_type: str,
        update_data: Dict[str, Any]
    ) -> NotificationChannelConfig:
        """更新渠道配置"""
        channel = self.db.query(NotificationChannelConfig).filter(
            NotificationChannelConfig.channel_type == channel_type
        ).first()

        if not channel:
            raise ValueError(f"渠道不存在: {channel_type}")

        # 更新启用状态
        if 'is_enabled' in update_data:
            channel.is_enabled = update_data['is_enabled']

        # 更新描述
        if 'description' in update_data:
            channel.description = update_data['description']

        # 更新配置（处理敏感信息）
        if 'config' in update_data and update_data['config']:
            new_config = update_data['config']

            # 处理密码/Token（留空表示不修改）
            if channel_type == 'email':
                if not new_config.get('smtp_password'):
                    # 保留原密码
                    new_config['smtp_password'] = channel.config.get('smtp_password', '')

            elif channel_type == 'telegram':
                if not new_config.get('bot_token'):
                    # 保留原 Token
                    new_config['bot_token'] = channel.config.get('bot_token', '')

            channel.config = new_config

        self.db.commit()
        self.db.refresh(channel)

        # 返回时脱敏
        channel.config = self._mask_sensitive_data(channel.config, channel.channel_type)
        return channel

    def toggle_channel(self, channel_type: str) -> NotificationChannelConfig:
        """启用/禁用渠道"""
        channel = self.db.query(NotificationChannelConfig).filter(
            NotificationChannelConfig.channel_type == channel_type
        ).first()

        if not channel:
            raise ValueError(f"渠道不存在: {channel_type}")

        channel.is_enabled = not channel.is_enabled
        self.db.commit()
        self.db.refresh(channel)

        # 返回时脱敏
        channel.config = self._mask_sensitive_data(channel.config, channel.channel_type)
        return channel

    async def test_channel(
        self,
        channel_type: str,
        test_target: str
    ) -> Dict[str, Any]:
        """测试渠道连接"""
        channel = self.db.query(NotificationChannelConfig).filter(
            NotificationChannelConfig.channel_type == channel_type
        ).first()

        if not channel:
            return {
                "success": False,
                "message": f"渠道不存在: {channel_type}",
                "test_time": datetime.now()
            }

        test_time = datetime.now()

        try:
            if channel_type == 'email':
                success, message = await self._test_email(channel.config, test_target)
            elif channel_type == 'telegram':
                success, message = await self._test_telegram(channel.config, test_target)
            else:
                success = False
                message = f"不支持的渠道类型: {channel_type}"

            # 更新测试状态
            channel.last_test_at = test_time
            channel.last_test_status = 'success' if success else 'failed'
            channel.last_test_message = message
            self.db.commit()

            return {
                "success": success,
                "message": message,
                "test_time": test_time
            }

        except Exception as e:
            logger.error(f"测试渠道失败: {e}", exc_info=True)

            # 更新测试状态为失败
            channel.last_test_at = test_time
            channel.last_test_status = 'failed'
            channel.last_test_message = str(e)
            self.db.commit()

            return {
                "success": False,
                "message": f"测试失败: {str(e)}",
                "test_time": test_time
            }

    async def _test_email(self, config: Dict, test_email: str) -> tuple[bool, str]:
        """测试 Email 渠道"""
        sender = EmailSender(config)

        # 发送测试邮件
        test_subject = "【测试邮件】股票分析系统通知测试"
        test_content = f"""
        <h2>这是一封测试邮件</h2>
        <p>如果您收到此邮件，说明 SMTP 配置正确。</p>
        <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>收件地址: {test_email}</p>
        """

        success = sender.send(test_email, test_subject, test_content)

        if success:
            return True, f"测试邮件已成功发送到 {test_email}"
        else:
            return False, "测试邮件发送失败，请检查 SMTP 配置"

    async def _test_telegram(self, config: Dict, chat_id: str) -> tuple[bool, str]:
        """测试 Telegram 渠道"""
        # TODO: 实现 Telegram Bot 测试（Phase 2）
        return False, "Telegram Bot 测试功能尚未实现（Phase 2 开发）"

    def _mask_sensitive_data(self, config: Dict, channel_type: str) -> Dict:
        """脱敏敏感信息（密码、Token）"""
        if not config:
            return config

        config_copy = copy.deepcopy(config)

        if channel_type == 'email':
            # 脱敏密码
            password = config_copy.get('smtp_password', '')
            if password:
                config_copy['smtp_password'] = '****'

        elif channel_type == 'telegram':
            # 脱敏 Bot Token
            token = config_copy.get('bot_token', '')
            if token:
                parts = token.split(':')
                if len(parts) == 2:
                    config_copy['bot_token'] = f"{parts[0][:10]}****"
                else:
                    config_copy['bot_token'] = '****'

        return config_copy
