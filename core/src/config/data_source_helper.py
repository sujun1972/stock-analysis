"""
Core层数据源配置辅助工具

用于Core层代码获取Backend的数据源配置
支持直接从数据库读取配置，避免硬编码数据源
"""

from typing import Dict, Optional
from loguru import logger

try:
    from src.database.db_manager import DatabaseManager
except ImportError:
    DatabaseManager = None


class DataSourceConfigHelper:
    """
    数据源配置辅助工具

    提供Core层代码获取数据源配置的能力
    """

    _instance = None
    _config_cache: Optional[Dict] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化"""
        if not hasattr(self, '_initialized'):
            self.db_manager = None
            self._initialized = True

    def _ensure_db_manager(self) -> DatabaseManager:
        """确保DatabaseManager已初始化"""
        if self.db_manager is None:
            if DatabaseManager is None:
                raise ImportError("DatabaseManager 未安装")
            self.db_manager = DatabaseManager()
        return self.db_manager

    def get_data_source_config(self, use_cache: bool = True) -> Dict:
        """
        获取数据源配置

        Args:
            use_cache: 是否使用缓存（默认True）

        Returns:
            Dict: 包含 data_source、minute_data_source、realtime_data_source 和 tushare_token
        """
        # 使用缓存
        if use_cache and self._config_cache is not None:
            return self._config_cache

        try:
            db = self._ensure_db_manager()

            # 直接查询配置表
            query = """
                SELECT config_key, config_value
                FROM config
                WHERE config_key IN ('data_source', 'minute_data_source', 'realtime_data_source', 'tushare_token')
            """

            results = db.execute_query(query)

            # 转换为字典
            config_dict = {row['config_key']: row['config_value'] for row in results}

            # 填充默认值
            config = {
                "data_source": config_dict.get("data_source") or "akshare",
                "minute_data_source": config_dict.get("minute_data_source") or "akshare",
                "realtime_data_source": config_dict.get("realtime_data_source") or "akshare",
                "limit_up_data_source": config_dict.get("limit_up_data_source") or "tushare",  # 默认tushare（用户有5000积分）
                "top_list_data_source": config_dict.get("top_list_data_source") or "tushare",  # 默认tushare
                "premarket_data_source": config_dict.get("premarket_data_source") or "akshare",  # 默认akshare（外盘数据）
                "tushare_token": config_dict.get("tushare_token") or "",
            }

            # 缓存配置
            self._config_cache = config

            logger.debug(f"✓ 获取数据源配置: {config['data_source']}")
            return config

        except Exception as e:
            logger.warning(f"从数据库获取配置失败，使用默认值: {e}")
            # 返回默认配置
            return {
                "data_source": "akshare",
                "minute_data_source": "akshare",
                "realtime_data_source": "akshare",
                "limit_up_data_source": "tushare",
                "top_list_data_source": "tushare",
                "premarket_data_source": "akshare",
                "tushare_token": "",
            }

    def get_data_source(self) -> str:
        """获取主数据源"""
        config = self.get_data_source_config()
        return config["data_source"]

    def get_minute_data_source(self) -> str:
        """获取分时数据源"""
        config = self.get_data_source_config()
        return config["minute_data_source"]

    def get_realtime_data_source(self) -> str:
        """获取实时数据源"""
        config = self.get_data_source_config()
        return config["realtime_data_source"]

    def get_tushare_token(self) -> str:
        """获取Tushare Token"""
        config = self.get_data_source_config()
        return config["tushare_token"]

    def clear_cache(self):
        """清除配置缓存"""
        self._config_cache = None
        logger.debug("✓ 配置缓存已清除")

    def create_provider(self, source_type: str = "data"):
        """
        创建数据提供者实例

        Args:
            source_type: 数据源类型
                - "data": 主数据源（用于日线、股票列表等）
                - "minute": 分时数据源
                - "realtime": 实时数据源
                - "limit_up": 涨停板池数据源
                - "top_list": 龙虎榜数据源
                - "premarket": 盘前数据源
                - "concept": 概念数据源

        Returns:
            数据提供者实例
        """
        try:
            from src.providers import DataProviderFactory
        except ImportError:
            raise ImportError("DataProviderFactory 未安装")

        config = self.get_data_source_config()

        # 根据类型选择数据源
        if source_type == "minute":
            source = config["minute_data_source"]
        elif source_type == "realtime":
            source = config["realtime_data_source"]
        elif source_type == "limit_up":
            source = config["limit_up_data_source"]
        elif source_type == "top_list":
            source = config["top_list_data_source"]
        elif source_type == "premarket":
            source = config["premarket_data_source"]
        elif source_type == "concept":
            source = config.get("concept_data_source", config["data_source"])  # 概念数据源，如果未配置则使用主数据源
        else:
            source = config["data_source"]

        # 创建Provider
        provider = DataProviderFactory.create_provider(
            source=source,
            token=config["tushare_token"],
            retry_count=3
        )

        logger.info(f"✓ 创建数据提供者: {source} ({source_type})")
        return provider


# 全局单例
_helper = DataSourceConfigHelper()


def get_data_source_config(use_cache: bool = True) -> Dict:
    """获取数据源配置（便捷函数）"""
    return _helper.get_data_source_config(use_cache)


def get_data_source() -> str:
    """获取主数据源（便捷函数）"""
    return _helper.get_data_source()


def get_minute_data_source() -> str:
    """获取分时数据源（便捷函数）"""
    return _helper.get_minute_data_source()


def get_realtime_data_source() -> str:
    """获取实时数据源（便捷函数）"""
    return _helper.get_realtime_data_source()


def get_concept_data_source() -> str:
    """获取概念数据源（便捷函数）"""
    config = _helper.get_data_source_config()
    return config.get("concept_data_source", config["data_source"])


def get_tushare_token() -> str:
    """获取Tushare Token（便捷函数）"""
    return _helper.get_tushare_token()


def create_provider(source_type: str = "data"):
    """创建数据提供者（便捷函数）"""
    return _helper.create_provider(source_type)


def clear_config_cache():
    """清除配置缓存（便捷函数）"""
    _helper.clear_cache()
