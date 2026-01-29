#!/usr/bin/env python3
"""
config/__init__.py 模块的完整测试套件

测试覆盖:
1. 所有导入是否正确
2. 向后兼容性常量
3. get_config_summary() 函数
4. validate_config() 函数
5. 全局配置访问
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


class TestConfigImports:
    """测试 config 模块的导入功能"""

    def test_import_core_settings(self):
        """测试核心设置导入"""
        from src.config import (
            get_settings,
            Settings,
            DatabaseSettings,
            DataSourceSettings,
            PathSettings,
            MLSettings,
            AppSettings,
            get_database_config,
            get_data_source,
            get_models_dir,
        )

        assert get_settings is not None
        assert Settings is not None
        assert DatabaseSettings is not None
        assert DataSourceSettings is not None
        assert PathSettings is not None
        assert MLSettings is not None
        assert AppSettings is not None
        assert get_database_config is not None
        assert get_data_source is not None
        assert get_models_dir is not None

    def test_import_trading_rules(self):
        """测试交易规则导入"""
        from src.config import (
            TradingHours,
            T_PLUS_N,
            PriceLimitRules,
            TradingCosts,
            TradingUnits,
            StockFilterRules,
            MarketType,
            DataQualityRules,
            AdjustType,
        )

        assert TradingHours is not None
        assert T_PLUS_N is not None
        assert PriceLimitRules is not None
        assert TradingCosts is not None
        assert TradingUnits is not None
        assert StockFilterRules is not None
        assert MarketType is not None
        assert DataQualityRules is not None
        assert AdjustType is not None

    def test_import_providers(self):
        """测试提供者配置导入"""
        from src.config import (
            ProviderConfigManager,
            get_provider_config_manager,
            get_current_provider,
            get_current_provider_config,
            get_tushare_config,
            get_akshare_config,
            TushareConfig,
            TushareErrorMessages,
            TushareFields,
            AkShareConfig,
            AkShareFields,
            AkShareNotes,
        )

        assert ProviderConfigManager is not None
        assert get_provider_config_manager is not None
        assert get_current_provider is not None
        assert get_current_provider_config is not None
        assert get_tushare_config is not None
        assert get_akshare_config is not None
        assert TushareConfig is not None
        assert TushareErrorMessages is not None
        assert TushareFields is not None
        assert AkShareConfig is not None
        assert AkShareFields is not None
        assert AkShareNotes is not None

    def test_import_pipeline(self):
        """测试流水线配置导入"""
        from src.config import (
            PipelineConfig,
            DEFAULT_CONFIG,
            QUICK_TRAINING_CONFIG,
            BALANCED_TRAINING_CONFIG,
            LONG_TERM_CONFIG,
            PRODUCTION_CONFIG,
            create_config,
        )

        assert PipelineConfig is not None
        assert DEFAULT_CONFIG is not None
        assert QUICK_TRAINING_CONFIG is not None
        assert BALANCED_TRAINING_CONFIG is not None
        assert LONG_TERM_CONFIG is not None
        assert PRODUCTION_CONFIG is not None
        assert create_config is not None

    def test_import_features(self):
        """测试特征工程配置导入"""
        from src.config import (
            FeatureEngineerConfig,
            TradingDaysConfig,
            TechnicalIndicatorConfig,
            AlphaFactorConfig,
            FeatureTransformConfig,
            DEFAULT_FEATURE_CONFIG,
            QUICK_FEATURE_CONFIG,
            FULL_FEATURE_CONFIG,
            DEBUG_FEATURE_CONFIG,
            get_feature_config,
            set_feature_config,
            reset_feature_config,
        )

        assert FeatureEngineerConfig is not None
        assert TradingDaysConfig is not None
        assert TechnicalIndicatorConfig is not None
        assert AlphaFactorConfig is not None
        assert FeatureTransformConfig is not None
        assert DEFAULT_FEATURE_CONFIG is not None
        assert QUICK_FEATURE_CONFIG is not None
        assert FULL_FEATURE_CONFIG is not None
        assert DEBUG_FEATURE_CONFIG is not None
        assert get_feature_config is not None
        assert set_feature_config is not None
        assert reset_feature_config is not None

    def test_import_convenience_functions(self):
        """测试便捷函数导入"""
        from src.config import get_config_summary, validate_config

        assert get_config_summary is not None
        assert validate_config is not None


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_data_path_constant(self):
        """测试 DATA_PATH 常量"""
        from src.config import DATA_PATH

        assert DATA_PATH is not None
        assert isinstance(DATA_PATH, str)

    def test_tushare_token_constant(self):
        """测试 TUSHARE_TOKEN 常量"""
        from src.config import TUSHARE_TOKEN

        assert TUSHARE_TOKEN is not None
        assert isinstance(TUSHARE_TOKEN, str)

    def test_database_config_constant(self):
        """测试 DATABASE_CONFIG 常量"""
        from src.config import DATABASE_CONFIG

        assert DATABASE_CONFIG is not None
        assert isinstance(DATABASE_CONFIG, dict)
        assert 'host' in DATABASE_CONFIG
        assert 'port' in DATABASE_CONFIG
        assert 'database' in DATABASE_CONFIG
        assert 'user' in DATABASE_CONFIG
        assert 'password' in DATABASE_CONFIG

    def test_default_data_source_constant(self):
        """测试 DEFAULT_DATA_SOURCE 常量"""
        from src.config import DEFAULT_DATA_SOURCE

        assert DEFAULT_DATA_SOURCE is not None
        assert isinstance(DEFAULT_DATA_SOURCE, str)
        assert DEFAULT_DATA_SOURCE in ['tushare', 'akshare']


class TestGetConfigSummary:
    """测试 get_config_summary() 函数"""

    def test_get_config_summary_basic(self):
        """测试基本配置摘要"""
        from src.config import get_config_summary

        summary = get_config_summary()

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert '配置系统摘要' in summary

    def test_config_summary_contains_all_sections(self):
        """测试配置摘要包含所有必要部分"""
        from src.config import get_config_summary

        summary = get_config_summary()

        # 验证包含所有配置部分
        assert '【应用配置】' in summary
        assert '【数据库配置】' in summary
        assert '【数据源配置】' in summary
        assert '【路径配置】' in summary
        assert '【机器学习配置】' in summary
        assert '【特征工程配置】' in summary

    def test_config_summary_contains_environment(self):
        """测试配置摘要包含环境信息"""
        from src.config import get_config_summary, get_settings

        settings = get_settings()
        summary = get_config_summary()

        assert f'环境: {settings.app.environment}' in summary
        assert f'调试模式: {settings.app.debug}' in summary
        assert f'日志级别: {settings.app.log_level}' in summary

    def test_config_summary_contains_database_info(self):
        """测试配置摘要包含数据库信息"""
        from src.config import get_config_summary, get_settings

        settings = get_settings()
        summary = get_config_summary()

        assert settings.database.user in summary
        assert settings.database.database in summary
        assert str(settings.database.port) in summary

    def test_config_summary_contains_provider_info(self):
        """测试配置摘要包含提供者信息"""
        from src.config import get_config_summary, get_provider_config_manager

        provider_manager = get_provider_config_manager()
        summary = get_config_summary()

        assert f'当前提供者: {provider_manager.get_provider_name()}' in summary

        # 验证 token 状态
        if provider_manager.has_tushare_token():
            assert 'Tushare Token: 已配置' in summary
        else:
            assert 'Tushare Token: 未配置' in summary

    def test_config_summary_contains_path_info(self):
        """测试配置摘要包含路径信息"""
        from src.config import get_config_summary, get_settings

        settings = get_settings()
        summary = get_config_summary()

        assert f'数据目录: {settings.paths.data_dir}' in summary
        assert f'模型目录: {settings.paths.models_dir}' in summary
        assert f'缓存目录: {settings.paths.cache_dir}' in summary
        assert f'结果目录: {settings.paths.results_dir}' in summary

    def test_config_summary_contains_ml_info(self):
        """测试配置摘要包含机器学习配置"""
        from src.config import get_config_summary, get_settings

        settings = get_settings()
        summary = get_config_summary()

        assert f'特征版本: {settings.ml.feature_version}' in summary
        assert f'默认预测周期: {settings.ml.default_target_period}天' in summary
        assert f'默认缩放类型: {settings.ml.default_scaler_type}' in summary

    def test_config_summary_contains_feature_info(self):
        """测试配置摘要包含特征工程配置"""
        from src.config import get_config_summary, get_feature_config

        feature_config = get_feature_config()
        summary = get_config_summary()

        assert f'年交易日数: {feature_config.trading_days.annual_trading_days}' in summary
        assert f'MA周期: {feature_config.technical_indicators.ma_periods}' in summary

    def test_config_summary_separator_lines(self):
        """测试配置摘要包含分隔线"""
        from src.config import get_config_summary

        summary = get_config_summary()

        # 验证包含分隔线
        assert '=' * 70 in summary


class TestValidateConfig:
    """测试 validate_config() 函数"""

    def test_validate_config_success(self):
        """测试配置验证成功"""
        from src.config import validate_config

        result = validate_config()

        # 应该返回布尔值
        assert isinstance(result, bool)

    def test_validate_config_checks_database_host(self):
        """测试验证数据库主机配置"""
        from src.config import validate_config, get_settings

        settings = get_settings()

        # 正常情况应该通过
        if settings.database.host:
            result = validate_config()
            assert result is True

    def test_validate_config_checks_database_name(self):
        """测试验证数据库名称配置"""
        from src.config import validate_config, get_settings

        settings = get_settings()

        # 正常情况应该通过
        if settings.database.database:
            result = validate_config()
            assert result is True

    @patch('src.config.get_settings')
    def test_validate_config_missing_host(self, mock_get_settings):
        """测试缺少数据库主机时的验证"""
        mock_settings = MagicMock()
        mock_settings.database.host = ""
        mock_settings.database.database = "test_db"
        mock_get_settings.return_value = mock_settings

        from src.config import validate_config

        result = validate_config()
        assert result is False

    @patch('src.config.get_settings')
    def test_validate_config_missing_database(self, mock_get_settings):
        """测试缺少数据库名称时的验证"""
        mock_settings = MagicMock()
        mock_settings.database.host = "localhost"
        mock_settings.database.database = ""
        mock_get_settings.return_value = mock_settings

        from src.config import validate_config

        result = validate_config()
        assert result is False

    @patch('src.config.get_settings')
    def test_validate_config_warns_missing_tushare_token(self, mock_get_settings, capsys):
        """测试缺少 Tushare Token 时的警告"""
        mock_settings = MagicMock()
        mock_settings.database.host = "localhost"
        mock_settings.database.database = "test_db"
        mock_settings.data_source.provider = 'tushare'
        mock_settings.data_source.tushare_token = ''
        mock_settings.paths.data_dir = '/tmp'
        mock_get_settings.return_value = mock_settings

        from src.config import validate_config

        validate_config()
        captured = capsys.readouterr()
        assert '警告' in captured.out
        assert 'Tushare' in captured.out

    @patch('src.config.get_settings')
    def test_validate_config_checks_data_path(self, mock_get_settings, capsys):
        """测试验证数据路径"""
        import tempfile
        from pathlib import Path

        # 使用一个不存在的路径
        non_existent_path = '/tmp/this_path_does_not_exist_123456789'

        mock_settings = MagicMock()
        mock_settings.database.host = "localhost"
        mock_settings.database.database = "test_db"
        mock_settings.data_source.provider = 'akshare'
        mock_settings.paths.data_dir = non_existent_path
        mock_get_settings.return_value = mock_settings

        from src.config import validate_config

        validate_config()
        captured = capsys.readouterr()
        assert '警告' in captured.out
        assert '不存在' in captured.out

    @patch('src.config.get_settings')
    def test_validate_config_exception_handling(self, mock_get_settings, capsys):
        """测试验证配置时的异常处理"""
        mock_get_settings.side_effect = Exception("Test error")

        from src.config import validate_config

        result = validate_config()

        assert result is False
        captured = capsys.readouterr()
        assert '配置验证失败' in captured.out


class TestConfigIntegration:
    """测试配置模块的集成功能"""

    def test_all_exported_in_all(self):
        """测试 __all__ 包含所有必要的导出"""
        from src.config import __all__

        assert '__all__' is not None
        assert isinstance(__all__, list)
        assert len(__all__) > 0

        # 验证核心导出
        assert 'get_settings' in __all__
        assert 'get_config_summary' in __all__
        assert 'validate_config' in __all__

    def test_settings_singleton(self):
        """测试 Settings 是单例模式"""
        from src.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # 应该是同一个实例
        assert settings1 is settings2

    def test_provider_manager_singleton(self):
        """测试 ProviderConfigManager 是单例模式"""
        from src.config import get_provider_config_manager

        manager1 = get_provider_config_manager()
        manager2 = get_provider_config_manager()

        # 应该是同一个实例
        assert manager1 is manager2

    def test_feature_config_access(self):
        """测试特征配置访问"""
        from src.config import get_feature_config, set_feature_config, reset_feature_config

        # 获取默认配置
        config1 = get_feature_config()
        assert config1 is not None

        # 重置配置
        reset_feature_config()
        config2 = get_feature_config()
        assert config2 is not None

    def test_config_types(self):
        """测试配置类型正确性"""
        import tempfile
        import os
        from unittest.mock import patch, MagicMock

        # 必须在导入前设置环境变量
        tmpdir = tempfile.mkdtemp()
        os.environ['PATH_DATA_DIR'] = tmpdir
        os.environ['PATH_MODELS_DIR'] = os.path.join(tmpdir, 'models')

        try:
            from src.config import (
                get_settings,
                get_database_config,
                get_data_source,
                get_models_dir,
            )

            # 清除缓存，强制重新加载
            get_settings.cache_clear()

            settings = get_settings()
            assert hasattr(settings, 'database')
            assert hasattr(settings, 'data_source')
            assert hasattr(settings, 'paths')
            assert hasattr(settings, 'ml')
            assert hasattr(settings, 'app')

            db_config = get_database_config()
            assert isinstance(db_config, dict)

            data_source = get_data_source()
            assert isinstance(data_source, str)

            # Mock Path.mkdir 以避免只读文件系统问题
            with patch('pathlib.Path.mkdir'):
                models_dir = get_models_dir()
                assert isinstance(models_dir, Path)
        finally:
            # 清理环境变量和临时目录
            os.environ.pop('PATH_DATA_DIR', None)
            os.environ.pop('PATH_MODELS_DIR', None)

            # 清除缓存
            from src.config import get_settings
            get_settings.cache_clear()

            # 清理临时目录
            import shutil
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)


class TestConfigModuleCoverage:
    """测试 config 模块的边界情况和覆盖率"""

    def test_module_docstring(self):
        """测试模块文档字符串"""
        import src.config as config_module

        assert config_module.__doc__ is not None

    def test_import_all_exports(self):
        """测试导入所有导出的内容"""
        from src.config import __all__
        import src.config as config_module

        for name in __all__:
            assert hasattr(config_module, name), f"Missing export: {name}"

    def test_convenience_functions_work(self):
        """测试便捷函数正常工作"""
        from src.config import (
            get_current_provider,
            get_current_provider_config,
            get_tushare_config,
            get_akshare_config,
        )

        # 测试所有便捷函数
        provider = get_current_provider()
        assert provider in ['tushare', 'akshare']

        provider_config = get_current_provider_config()
        assert isinstance(provider_config, dict)

        tushare_config = get_tushare_config()
        assert isinstance(tushare_config, dict)

        akshare_config = get_akshare_config()
        assert isinstance(akshare_config, dict)

    def test_backward_compatibility_constants_accessible(self):
        """测试向后兼容常量可访问"""
        import src.config as config_module

        # 所有向后兼容常量
        assert hasattr(config_module, 'DATA_PATH')
        assert hasattr(config_module, 'TUSHARE_TOKEN')
        assert hasattr(config_module, 'DATABASE_CONFIG')
        assert hasattr(config_module, 'DEFAULT_DATA_SOURCE')

        # 访问这些常量不会抛出异常
        _ = config_module.DATA_PATH
        _ = config_module.TUSHARE_TOKEN
        _ = config_module.DATABASE_CONFIG
        _ = config_module.DEFAULT_DATA_SOURCE


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
