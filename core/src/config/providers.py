#!/usr/bin/env python3
"""
数据提供者配置整合模块

整合所有数据提供者的配置,提供统一的访问接口
"""

from typing import Any, Dict, Optional
from .settings import get_settings

# 导入提供者特定配置
try:
    from ..providers.tushare.config import TushareConfig, TushareErrorMessages, TushareFields
    from ..providers.akshare.config import AkShareConfig, AkShareFields, AkShareNotes
except ImportError:
    # 如果无法相对导入,尝试绝对导入
    from providers.tushare.config import TushareConfig, TushareErrorMessages, TushareFields
    from providers.akshare.config import AkShareConfig, AkShareFields, AkShareNotes


class ProviderConfigManager:
    """
    数据提供者配置管理器

    统一管理所有数据提供者的配置,并与全局设置集成
    """

    def __init__(self):
        """初始化配置管理器"""
        self.settings = get_settings()
        self._configs = {}

    def get_provider_name(self) -> str:
        """
        获取当前配置的数据提供者名称

        Returns:
            数据提供者名称 ('tushare', 'akshare' 等)
        """
        return self.settings.data_source.provider

    def get_tushare_config(self) -> Dict[str, Any]:
        """
        获取 Tushare 提供者配置

        Returns:
            Tushare 配置字典,包含 token 和其他配置常量
        """
        if 'tushare' not in self._configs:
            self._configs['tushare'] = {
                'token': self.settings.data_source.tushare_token,
                'timeout': TushareConfig.DEFAULT_TIMEOUT,
                'retry_count': TushareConfig.DEFAULT_RETRY_COUNT,
                'retry_delay': TushareConfig.DEFAULT_RETRY_DELAY,
                'request_delay': TushareConfig.DEFAULT_REQUEST_DELAY,
                'config_class': TushareConfig,
                'error_messages': TushareErrorMessages,
                'fields': TushareFields,
            }
        return self._configs['tushare']

    def get_akshare_config(self) -> Dict[str, Any]:
        """
        获取 AkShare 提供者配置

        Returns:
            AkShare 配置字典和配置常量
        """
        if 'akshare' not in self._configs:
            self._configs['akshare'] = {
                'timeout': AkShareConfig.DEFAULT_TIMEOUT,
                'retry_count': AkShareConfig.DEFAULT_RETRY_COUNT,
                'retry_delay': AkShareConfig.DEFAULT_RETRY_DELAY,
                'request_delay': AkShareConfig.DEFAULT_REQUEST_DELAY,
                'config_class': AkShareConfig,
                'fields': AkShareFields,
                'notes': AkShareNotes,
            }
        return self._configs['akshare']

    def get_current_provider_config(self) -> Dict[str, Any]:
        """
        获取当前配置的提供者配置

        Returns:
            当前提供者的配置字典

        Raises:
            ValueError: 如果提供者不支持
        """
        provider = self.get_provider_name()

        if provider == 'tushare':
            return self.get_tushare_config()
        elif provider == 'akshare':
            return self.get_akshare_config()
        else:
            raise ValueError(f"不支持的数据提供者: {provider}")

    def has_tushare_token(self) -> bool:
        """
        检查是否配置了 Tushare Token

        Returns:
            是否已配置 Token
        """
        return self.settings.data_source.has_tushare

    def get_provider_info(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        获取提供者信息摘要

        Args:
            provider: 提供者名称,None 表示当前提供者

        Returns:
            提供者信息字典
        """
        provider = provider or self.get_provider_name()

        if provider == 'tushare':
            return {
                'name': 'Tushare Pro',
                'description': '专业金融数据接口,需要积分和Token',
                'has_token': self.has_tushare_token(),
                'free': False,
                'data_quality': 'high',
                'rate_limit': 'based_on_points',
            }
        elif provider == 'akshare':
            return {
                'name': 'AkShare',
                'description': '开源免费的数据接口,基于网络爬虫',
                'has_token': True,  # 不需要token
                'free': True,
                'data_quality': 'medium',
                'rate_limit': 'ip_based',
            }
        else:
            raise ValueError(f"未知的数据提供者: {provider}")


# 全局配置管理器单例
_provider_config_manager: Optional[ProviderConfigManager] = None


def get_provider_config_manager() -> ProviderConfigManager:
    """
    获取全局提供者配置管理器单例

    Returns:
        ProviderConfigManager 实例
    """
    global _provider_config_manager
    if _provider_config_manager is None:
        _provider_config_manager = ProviderConfigManager()
    return _provider_config_manager


# 便捷函数

def get_current_provider() -> str:
    """获取当前数据提供者名称"""
    return get_provider_config_manager().get_provider_name()


def get_current_provider_config() -> Dict[str, Any]:
    """获取当前提供者配置"""
    return get_provider_config_manager().get_current_provider_config()


def get_tushare_config() -> Dict[str, Any]:
    """获取 Tushare 配置"""
    return get_provider_config_manager().get_tushare_config()


def get_akshare_config() -> Dict[str, Any]:
    """获取 AkShare 配置"""
    return get_provider_config_manager().get_akshare_config()


# 导出所有公共接口
__all__ = [
    'ProviderConfigManager',
    'get_provider_config_manager',
    'get_current_provider',
    'get_current_provider_config',
    'get_tushare_config',
    'get_akshare_config',
    # 导出提供者特定配置类
    'TushareConfig',
    'TushareErrorMessages',
    'TushareFields',
    'AkShareConfig',
    'AkShareFields',
    'AkShareNotes',
]
