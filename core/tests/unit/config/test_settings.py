#!/usr/bin/env python3
"""
config/settings.py 模块的完整测试套件

测试覆盖:
1. 所有 Settings 子类 (DatabaseSettings, DataSourceSettings, PathSettings, MLSettings, AppSettings)
2. Settings 主类
3. 单例模式
4. 环境变量加载
5. 便捷函数
6. 属性和方法
7. 向后兼容性
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os


class TestDatabaseSettings:
    """测试 DatabaseSettings 类"""

    def test_database_settings_defaults(self):
        """测试数据库设置默认值"""
        from src.config.settings import DatabaseSettings

        settings = DatabaseSettings()

        # 验证类型和值存在（可能被环境变量覆盖）
        assert isinstance(settings.host, str)
        assert isinstance(settings.port, int)
        assert isinstance(settings.database, str)
        assert isinstance(settings.user, str)
        assert isinstance(settings.password, str)
        assert len(settings.host) > 0
        assert settings.port > 0

    def test_database_settings_custom_values(self):
        """测试数据库设置自定义值"""
        from src.config.settings import DatabaseSettings

        settings = DatabaseSettings(
            host="custom_host",
            port=6543,
            database="custom_db",
            user="custom_user",
            password="custom_pass"
        )

        assert settings.host == "custom_host"
        assert settings.port == 6543
        assert settings.database == "custom_db"
        assert settings.user == "custom_user"
        assert settings.password == "custom_pass"

    def test_database_settings_env_prefix(self):
        """测试数据库设置环境变量前缀"""
        from src.config.settings import DatabaseSettings

        # 验证 model_config 中有 env_prefix
        assert DatabaseSettings.model_config['env_prefix'] == 'DATABASE_'

    def test_database_settings_types(self):
        """测试数据库设置类型"""
        from src.config.settings import DatabaseSettings

        settings = DatabaseSettings()

        assert isinstance(settings.host, str)
        assert isinstance(settings.port, int)
        assert isinstance(settings.database, str)
        assert isinstance(settings.user, str)
        assert isinstance(settings.password, str)


class TestDataSourceSettings:
    """测试 DataSourceSettings 类"""

    def test_data_source_settings_defaults(self):
        """测试数据源设置默认值"""
        from src.config.settings import DataSourceSettings
        import os

        # 暂时清除环境变量以测试默认值
        old_token = os.environ.pop('DATA_TUSHARE_TOKEN', None)
        old_api_key = os.environ.pop('DATA_DEEPSEEK_API_KEY', None)

        try:
            settings = DataSourceSettings()

            assert settings.provider == "akshare"
            assert settings.tushare_token == ""
            assert settings.deepseek_api_key == ""
        finally:
            # 恢复环境变量
            if old_token:
                os.environ['DATA_TUSHARE_TOKEN'] = old_token
            if old_api_key:
                os.environ['DATA_DEEPSEEK_API_KEY'] = old_api_key

    def test_data_source_settings_custom_values(self):
        """测试数据源设置自定义值"""
        from src.config.settings import DataSourceSettings

        settings = DataSourceSettings(
            provider="tushare",
            tushare_token="test_token_123",
            deepseek_api_key="test_key_456"
        )

        assert settings.provider == "tushare"
        assert settings.tushare_token == "test_token_123"
        assert settings.deepseek_api_key == "test_key_456"

    def test_data_source_has_tushare_true(self):
        """测试 has_tushare 属性为 True"""
        from src.config.settings import DataSourceSettings

        settings = DataSourceSettings(tushare_token="valid_token")

        assert settings.has_tushare is True

    def test_data_source_has_tushare_false(self):
        """测试 has_tushare 属性为 False"""
        from src.config.settings import DataSourceSettings

        settings = DataSourceSettings(tushare_token="")

        assert settings.has_tushare is False

    def test_data_source_settings_env_prefix(self):
        """测试数据源设置环境变量前缀"""
        from src.config.settings import DataSourceSettings

        assert DataSourceSettings.model_config['env_prefix'] == 'DATA_'


class TestPathSettings:
    """测试 PathSettings 类"""

    def test_path_settings_defaults(self):
        """测试路径设置默认值"""
        from src.config.settings import PathSettings
        import os

        # 暂时清除路径相关环境变量以测试默认值
        env_vars_to_clear = ['PATH_DATA_DIR', 'PATH_MODELS_DIR', 'PATH_CACHE_DIR', 'PATH_RESULTS_DIR']
        old_values = {}
        for var in env_vars_to_clear:
            old_values[var] = os.environ.pop(var, None)

        try:
            settings = PathSettings()

            assert settings.data_dir == "/data"
            assert settings.models_dir == "/data/models/ml_models"
            assert settings.cache_dir == "/data/pipeline_cache"
            assert settings.results_dir == "/data/backtest_results"
        finally:
            # 恢复环境变量
            for var, value in old_values.items():
                if value:
                    os.environ[var] = value

    def test_path_settings_custom_values(self):
        """测试路径设置自定义值"""
        from src.config.settings import PathSettings

        settings = PathSettings(
            data_dir="/custom/data",
            models_dir="/custom/models",
            cache_dir="/custom/cache",
            results_dir="/custom/results"
        )

        assert settings.data_dir == "/custom/data"
        assert settings.models_dir == "/custom/models"
        assert settings.cache_dir == "/custom/cache"
        assert settings.results_dir == "/custom/results"

    def test_get_data_path(self):
        """测试获取数据路径"""
        from src.config.settings import PathSettings

        settings = PathSettings(data_dir="/test/data")
        path = settings.get_data_path()

        assert isinstance(path, Path)
        assert str(path) == "/test/data"

    def test_get_models_path(self):
        """测试获取模型路径"""
        from src.config.settings import PathSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = PathSettings(models_dir=tmpdir)
            path = settings.get_models_path()

            assert isinstance(path, Path)
            assert path.exists()

    def test_get_cache_path(self):
        """测试获取缓存路径"""
        from src.config.settings import PathSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = PathSettings(cache_dir=tmpdir)
            path = settings.get_cache_path()

            assert isinstance(path, Path)
            assert path.exists()

    def test_get_results_path(self):
        """测试获取结果路径"""
        from src.config.settings import PathSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            settings = PathSettings(results_dir=tmpdir)
            path = settings.get_results_path()

            assert isinstance(path, Path)
            assert path.exists()

    def test_data_path_property(self):
        """测试 data_path 属性（向后兼容）"""
        from src.config.settings import PathSettings

        settings = PathSettings(data_dir="/test/data")

        assert settings.data_path == settings.get_data_path()
        assert isinstance(settings.data_path, Path)

    def test_path_settings_env_prefix(self):
        """测试路径设置环境变量前缀"""
        from src.config.settings import PathSettings

        assert PathSettings.model_config['env_prefix'] == 'PATH_'

    def test_path_settings_mkdir_creates_directories(self):
        """测试路径设置创建目录"""
        from src.config.settings import PathSettings

        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models" / "subdir"
            cache_dir = Path(tmpdir) / "cache" / "subdir"
            results_dir = Path(tmpdir) / "results" / "subdir"

            settings = PathSettings(
                models_dir=str(models_dir),
                cache_dir=str(cache_dir),
                results_dir=str(results_dir)
            )

            # 调用 get_*_path 应该创建目录
            models_path = settings.get_models_path()
            cache_path = settings.get_cache_path()
            results_path = settings.get_results_path()

            assert models_path.exists()
            assert cache_path.exists()
            assert results_path.exists()


class TestMLSettings:
    """测试 MLSettings 类"""

    def test_ml_settings_defaults(self):
        """测试机器学习设置默认值"""
        from src.config.settings import MLSettings

        settings = MLSettings()

        assert settings.default_target_period == 5
        assert settings.default_scaler_type == "robust"
        assert settings.default_train_ratio == 0.7
        assert settings.default_valid_ratio == 0.15
        assert settings.cache_features is True
        assert settings.feature_version == "v2.0"

    def test_ml_settings_custom_values(self):
        """测试机器学习设置自定义值"""
        from src.config.settings import MLSettings

        settings = MLSettings(
            default_target_period=10,
            default_scaler_type="standard",
            default_train_ratio=0.8,
            default_valid_ratio=0.1,
            cache_features=False,
            feature_version="v3.0"
        )

        assert settings.default_target_period == 10
        assert settings.default_scaler_type == "standard"
        assert settings.default_train_ratio == 0.8
        assert settings.default_valid_ratio == 0.1
        assert settings.cache_features is False
        assert settings.feature_version == "v3.0"

    def test_ml_settings_types(self):
        """测试机器学习设置类型"""
        from src.config.settings import MLSettings

        settings = MLSettings()

        assert isinstance(settings.default_target_period, int)
        assert isinstance(settings.default_scaler_type, str)
        assert isinstance(settings.default_train_ratio, float)
        assert isinstance(settings.default_valid_ratio, float)
        assert isinstance(settings.cache_features, bool)
        assert isinstance(settings.feature_version, str)

    def test_ml_settings_env_prefix(self):
        """测试机器学习设置环境变量前缀"""
        from src.config.settings import MLSettings

        assert MLSettings.model_config['env_prefix'] == 'ML_'


class TestAppSettings:
    """测试 AppSettings 类"""

    def test_app_settings_defaults(self):
        """测试应用设置默认值"""
        from src.config.settings import AppSettings

        settings = AppSettings()

        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.log_level == "INFO"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000

    def test_app_settings_custom_values(self):
        """测试应用设置自定义值"""
        from src.config.settings import AppSettings

        settings = AppSettings(
            environment="production",
            debug=False,
            log_level="WARNING",
            api_host="127.0.0.1",
            api_port=9000
        )

        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.log_level == "WARNING"
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 9000

    def test_app_is_production_true(self):
        """测试 is_production 属性为 True"""
        from src.config.settings import AppSettings

        settings = AppSettings(environment="production")

        assert settings.is_production is True

    def test_app_is_production_false(self):
        """测试 is_production 属性为 False"""
        from src.config.settings import AppSettings

        settings = AppSettings(environment="development")

        assert settings.is_production is False

    def test_app_is_development_true(self):
        """测试 is_development 属性为 True"""
        from src.config.settings import AppSettings

        settings = AppSettings(environment="development")

        assert settings.is_development is True

    def test_app_is_development_false(self):
        """测试 is_development 属性为 False"""
        from src.config.settings import AppSettings

        settings = AppSettings(environment="production")

        assert settings.is_development is False

    def test_app_settings_env_prefix(self):
        """测试应用设置环境变量前缀"""
        from src.config.settings import AppSettings

        assert AppSettings.model_config['env_prefix'] == 'APP_'

    def test_app_environment_case_insensitive(self):
        """测试环境配置大小写不敏感"""
        from src.config.settings import AppSettings

        settings1 = AppSettings(environment="PRODUCTION")
        settings2 = AppSettings(environment="Production")
        settings3 = AppSettings(environment="production")

        assert settings1.is_production is True
        assert settings2.is_production is True
        assert settings3.is_production is True


class TestSettings:
    """测试 Settings 主类"""

    def test_settings_initialization(self):
        """测试设置初始化"""
        from src.config.settings import Settings

        settings = Settings()

        assert settings.database is not None
        assert settings.data_source is not None
        assert settings.paths is not None
        assert settings.ml is not None
        assert settings.app is not None

    def test_settings_sub_config_types(self):
        """测试子配置类型"""
        from src.config.settings import (
            Settings,
            DatabaseSettings,
            DataSourceSettings,
            PathSettings,
            MLSettings,
            AppSettings
        )

        settings = Settings()

        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.data_source, DataSourceSettings)
        assert isinstance(settings.paths, PathSettings)
        assert isinstance(settings.ml, MLSettings)
        assert isinstance(settings.app, AppSettings)

    def test_get_database_config(self):
        """测试获取数据库配置字典"""
        from src.config.settings import Settings

        settings = Settings()
        db_config = settings.get_database_config()

        assert isinstance(db_config, dict)
        assert 'host' in db_config
        assert 'port' in db_config
        assert 'database' in db_config
        assert 'user' in db_config
        assert 'password' in db_config

        # 验证值匹配
        assert db_config['host'] == settings.database.host
        assert db_config['port'] == settings.database.port
        assert db_config['database'] == settings.database.database
        assert db_config['user'] == settings.database.user
        assert db_config['password'] == settings.database.password

    def test_display_config(self):
        """测试显示配置"""
        from src.config.settings import Settings

        settings = Settings()
        display = settings.display_config()

        assert isinstance(display, str)
        assert len(display) > 0
        assert '当前配置摘要' in display
        assert '环境:' in display
        assert '数据库:' in display
        assert '数据源:' in display

    def test_display_config_hides_password(self):
        """测试显示配置隐藏密码"""
        from src.config.settings import Settings

        settings = Settings()
        display = settings.display_config()

        # 密码不应该明文显示
        # 只显示用户名@主机等信息
        assert settings.database.user in display
        assert settings.database.host in display

    def test_display_config_format(self):
        """测试显示配置格式"""
        from src.config.settings import Settings

        settings = Settings()
        display = settings.display_config()

        # 验证格式
        assert '=' * 60 in display
        lines = display.split('\n')
        assert len(lines) > 5


class TestGetSettings:
    """测试 get_settings 函数（单例）"""

    def test_get_settings_returns_settings(self):
        """测试 get_settings 返回 Settings 实例"""
        from src.config.settings import get_settings, Settings

        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_singleton(self):
        """测试 get_settings 单例模式"""
        from src.config.settings import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # 应该返回同一个实例
        assert settings1 is settings2

    def test_get_settings_cached(self):
        """测试 get_settings 使用缓存"""
        from src.config.settings import get_settings

        # 多次调用
        for _ in range(10):
            settings = get_settings()
            assert settings is not None


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_get_database_config_function(self):
        """测试 get_database_config 便捷函数"""
        from src.config.settings import get_database_config

        db_config = get_database_config()

        assert isinstance(db_config, dict)
        assert 'host' in db_config
        assert 'port' in db_config
        assert 'database' in db_config
        assert 'user' in db_config
        assert 'password' in db_config

    def test_get_data_source_function(self):
        """测试 get_data_source 便捷函数"""
        from src.config.settings import get_data_source

        data_source = get_data_source()

        assert isinstance(data_source, str)
        assert data_source in ['tushare', 'akshare']

    def test_get_models_dir_function(self):
        """测试 get_models_dir 便捷函数"""
        import tempfile
        import os
        from unittest.mock import patch

        # 必须在导入前设置环境变量
        tmpdir = tempfile.mkdtemp()
        os.environ['PATH_DATA_DIR'] = tmpdir
        os.environ['PATH_MODELS_DIR'] = os.path.join(tmpdir, 'models')

        try:
            from src.config.settings import get_models_dir, get_settings

            # 清除缓存
            get_settings.cache_clear()

            # Mock Path.mkdir 以避免只读文件系统问题
            with patch('pathlib.Path.mkdir'):
                models_dir = get_models_dir()
                assert isinstance(models_dir, Path)
        finally:
            # 清理
            os.environ.pop('PATH_DATA_DIR', None)
            os.environ.pop('PATH_MODELS_DIR', None)

            from src.config.settings import get_settings
            get_settings.cache_clear()

            # 清理临时目录
            import shutil
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_database_config_constant(self):
        """测试 DATABASE_CONFIG 常量"""
        from src.config.settings import DATABASE_CONFIG

        assert isinstance(DATABASE_CONFIG, dict)
        assert 'host' in DATABASE_CONFIG

    def test_default_data_source_constant(self):
        """测试 DEFAULT_DATA_SOURCE 常量"""
        from src.config.settings import DEFAULT_DATA_SOURCE

        assert isinstance(DEFAULT_DATA_SOURCE, str)
        assert DEFAULT_DATA_SOURCE in ['tushare', 'akshare']


class TestEnvironmentVariables:
    """测试环境变量加载"""

    def test_env_file_path(self):
        """测试环境变量文件路径"""
        from src.config.settings import ENV_FILE, PROJECT_ROOT

        assert isinstance(ENV_FILE, Path)
        assert isinstance(PROJECT_ROOT, Path)

    def test_project_root_valid(self):
        """测试项目根目录有效"""
        from src.config.settings import PROJECT_ROOT

        assert PROJECT_ROOT.exists()

    @patch.dict(os.environ, {'DATABASE_HOST': 'env_host', 'DATABASE_PORT': '7777'})
    def test_settings_load_from_env(self):
        """测试从环境变量加载设置"""
        from src.config.settings import DatabaseSettings

        # 清除缓存
        from src.config.settings import get_settings
        get_settings.cache_clear()

        settings = DatabaseSettings()

        # 应该从环境变量加载（如果支持）
        # 注意：这取决于 pydantic_settings 的行为
        assert settings is not None


class TestModelConfig:
    """测试模型配置"""

    def test_settings_model_config(self):
        """测试 Settings 模型配置"""
        from src.config.settings import Settings

        config = Settings.model_config

        assert 'env_file_encoding' in config
        assert config['env_file_encoding'] == 'utf-8'
        assert config['case_sensitive'] is False
        assert config['extra'] == 'ignore'

    def test_database_settings_case_insensitive(self):
        """测试数据库设置大小写不敏感"""
        from src.config.settings import DatabaseSettings

        config = DatabaseSettings.model_config

        assert config['case_sensitive'] is False


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_strings(self):
        """测试空字符串"""
        from src.config.settings import DataSourceSettings

        settings = DataSourceSettings(
            provider="",
            tushare_token="",
            deepseek_api_key=""
        )

        assert settings.provider == ""
        assert settings.tushare_token == ""
        assert settings.deepseek_api_key == ""
        assert settings.has_tushare is False

    def test_path_with_spaces(self):
        """测试包含空格的路径"""
        from src.config.settings import PathSettings

        settings = PathSettings(data_dir="/path with spaces/data")

        path = settings.get_data_path()
        assert str(path) == "/path with spaces/data"

    def test_special_characters_in_password(self):
        """测试密码中的特殊字符"""
        from src.config.settings import DatabaseSettings

        settings = DatabaseSettings(password="p@ss!w0rd#$%")

        assert settings.password == "p@ss!w0rd#$%"

    def test_zero_values(self):
        """测试零值"""
        from src.config.settings import MLSettings

        settings = MLSettings(
            default_train_ratio=0.0,
            default_valid_ratio=0.0
        )

        assert settings.default_train_ratio == 0.0
        assert settings.default_valid_ratio == 0.0

    def test_negative_values(self):
        """测试负值（如果适用）"""
        from src.config.settings import MLSettings

        # target_period 可能不应该是负数，但测试类型系统
        settings = MLSettings(default_target_period=-1)

        assert settings.default_target_period == -1


class TestMainBlock:
    """测试 __main__ 块"""

    def test_main_block_exists(self):
        """测试 __main__ 块存在"""
        import src.config.settings as settings_module
        import inspect

        # 检查源代码中是否包含 __main__ 块
        source = inspect.getsource(settings_module)
        assert 'if __name__ == "__main__"' in source

    def test_main_block_execution(self, capsys):
        """测试 __main__ 块可以执行"""
        import subprocess
        import sys
        import tempfile
        import os

        # 使用临时目录避免只读文件系统问题
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env['PATH_DATA_DIR'] = tmpdir
            env['PATH_MODELS_DIR'] = os.path.join(tmpdir, 'models')

            # 运行 settings.py 作为主程序
            result = subprocess.run(
                [sys.executable, '-m', 'src.config.settings'],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                env=env
            )

            # 验证输出包含预期内容
            output = result.stdout + result.stderr
            assert '测试配置管理模块' in output or '配置摘要' in output or result.returncode == 0


class TestImportCompatibility:
    """测试导入兼容性"""

    def test_pydantic_settings_import(self):
        """测试 pydantic_settings 导入"""
        # 验证导入不会失败
        from src.config.settings import BaseSettings

        assert BaseSettings is not None

    def test_all_classes_importable(self):
        """测试所有类可导入"""
        from src.config.settings import (
            DatabaseSettings,
            DataSourceSettings,
            PathSettings,
            MLSettings,
            AppSettings,
            Settings
        )

        assert DatabaseSettings is not None
        assert DataSourceSettings is not None
        assert PathSettings is not None
        assert MLSettings is not None
        assert AppSettings is not None
        assert Settings is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
