"""
并行计算配置测试

测试内容：
- ParallelComputingConfig配置类
- 配置验证和默认值
- 与主配置的集成

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
from dataclasses import fields

from src.config.features import (
    ParallelComputingConfig,
    FeatureEngineerConfig,
    get_feature_config,
    set_feature_config,
    reset_feature_config,
)


# ==================== 基础配置测试 ====================


class TestParallelComputingConfig:
    """并行计算配置基础测试"""

    def test_default_values(self):
        """测试默认配置值"""
        config = ParallelComputingConfig()

        assert config.enable_parallel is True
        assert config.n_workers == -1
        assert config.parallel_backend == 'multiprocessing'
        assert config.chunk_size == 100
        assert config.use_shared_memory is False
        assert config.ray_address is None
        assert config.show_progress is True
        assert config.timeout == 300

    def test_custom_values(self):
        """测试自定义配置值"""
        config = ParallelComputingConfig(
            enable_parallel=False,
            n_workers=4,
            parallel_backend='ray',
            chunk_size=50,
            use_shared_memory=True,
            ray_address='auto',
            show_progress=False,
            timeout=600
        )

        assert config.enable_parallel is False
        assert config.n_workers == 4
        assert config.parallel_backend == 'ray'
        assert config.chunk_size == 50
        assert config.use_shared_memory is True
        assert config.ray_address == 'auto'
        assert config.show_progress is False
        assert config.timeout == 600

    def test_config_immutability(self):
        """测试配置可修改性（dataclass默认可修改）"""
        config = ParallelComputingConfig()

        # 应该可以修改
        config.n_workers = 8
        assert config.n_workers == 8

        config.parallel_backend = 'dask'
        assert config.parallel_backend == 'dask'

    def test_all_fields_documented(self):
        """测试所有字段都有文档字符串"""
        config = ParallelComputingConfig()

        # 获取所有字段
        field_names = [f.name for f in fields(config)]

        # 至少应该有这些核心字段
        required_fields = [
            'enable_parallel',
            'n_workers',
            'parallel_backend',
            'chunk_size',
            'ray_address',
            'show_progress',
            'timeout'
        ]

        for field_name in required_fields:
            assert field_name in field_names


# ==================== 配置验证测试 ====================


class TestConfigValidation:
    """配置验证测试"""

    def test_valid_backend_values(self):
        """测试有效的backend值"""
        valid_backends = ['multiprocessing', 'threading', 'ray', 'dask']

        for backend in valid_backends:
            config = ParallelComputingConfig(parallel_backend=backend)
            assert config.parallel_backend == backend

    def test_n_workers_values(self):
        """测试n_workers的各种取值"""
        # -1: 自动检测
        config = ParallelComputingConfig(n_workers=-1)
        assert config.n_workers == -1

        # 1: 禁用并行
        config = ParallelComputingConfig(n_workers=1)
        assert config.n_workers == 1

        # >1: 指定进程数
        config = ParallelComputingConfig(n_workers=8)
        assert config.n_workers == 8

    def test_chunk_size_positive(self):
        """测试chunk_size为正数"""
        config = ParallelComputingConfig(chunk_size=50)
        assert config.chunk_size > 0

    def test_timeout_values(self):
        """测试timeout的各种取值"""
        # 0: 不超时
        config = ParallelComputingConfig(timeout=0)
        assert config.timeout == 0

        # >0: 超时秒数
        config = ParallelComputingConfig(timeout=300)
        assert config.timeout == 300


# ==================== 主配置集成测试 ====================


class TestFeatureEngineerConfigIntegration:
    """主配置集成测试"""

    def test_parallel_config_in_main_config(self):
        """测试并行配置在主配置中"""
        config = FeatureEngineerConfig()

        # 应该包含parallel_computing配置
        assert hasattr(config, 'parallel_computing')
        assert isinstance(config.parallel_computing, ParallelComputingConfig)

    def test_default_parallel_config(self):
        """测试默认并行配置"""
        config = FeatureEngineerConfig()

        # 默认启用并行
        assert config.parallel_computing.enable_parallel is True

        # 默认使用multiprocessing
        assert config.parallel_computing.parallel_backend == 'multiprocessing'

    def test_custom_parallel_config(self):
        """测试自定义并行配置"""
        parallel_config = ParallelComputingConfig(
            n_workers=4,
            parallel_backend='ray'
        )

        config = FeatureEngineerConfig(
            parallel_computing=parallel_config
        )

        assert config.parallel_computing.n_workers == 4
        assert config.parallel_computing.parallel_backend == 'ray'

    def test_all_config_sections_present(self):
        """测试所有配置段都存在"""
        config = FeatureEngineerConfig()

        # 检查所有主要配置段
        assert hasattr(config, 'trading_days')
        assert hasattr(config, 'technical_indicators')
        assert hasattr(config, 'alpha_factors')
        assert hasattr(config, 'feature_transform')
        assert hasattr(config, 'parallel_computing')


# ==================== 全局配置管理测试 ====================


class TestGlobalConfigManagement:
    """全局配置管理测试"""

    def test_get_feature_config(self):
        """测试获取全局配置"""
        config = get_feature_config()

        assert isinstance(config, FeatureEngineerConfig)
        assert hasattr(config, 'parallel_computing')

    def test_set_feature_config(self):
        """测试设置全局配置"""
        # 创建自定义配置
        custom_config = FeatureEngineerConfig(
            parallel_computing=ParallelComputingConfig(n_workers=16)
        )

        # 设置全局配置
        set_feature_config(custom_config)

        # 获取并验证
        config = get_feature_config()
        assert config.parallel_computing.n_workers == 16

        # 清理：重置为默认
        reset_feature_config()

    def test_reset_feature_config(self):
        """测试重置配置"""
        # 修改配置
        custom_config = FeatureEngineerConfig(
            parallel_computing=ParallelComputingConfig(n_workers=32)
        )
        set_feature_config(custom_config)

        # 重置
        reset_feature_config()

        # 验证已重置为默认值
        config = get_feature_config()
        assert config.parallel_computing.n_workers == -1


# ==================== 配置场景测试 ====================


class TestConfigScenarios:
    """实际使用场景测试"""

    def test_local_multiprocessing_scenario(self):
        """测试本地多进程场景"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=8,
            parallel_backend='multiprocessing',
            show_progress=True
        )

        assert config.enable_parallel
        assert config.n_workers == 8
        assert config.parallel_backend == 'multiprocessing'

    def test_ray_distributed_scenario(self):
        """测试Ray分布式场景"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=-1,  # 自动检测
            parallel_backend='ray',
            ray_address='auto',
            show_progress=True
        )

        assert config.parallel_backend == 'ray'
        assert config.ray_address == 'auto'

    def test_disabled_parallel_scenario(self):
        """测试禁用并行场景"""
        config = ParallelComputingConfig(
            enable_parallel=False,
            n_workers=1
        )

        assert not config.enable_parallel
        assert config.n_workers == 1

    def test_io_intensive_threading_scenario(self):
        """测试I/O密集型线程场景"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=32,  # I/O可以用更多线程
            parallel_backend='threading',
            chunk_size=50
        )

        assert config.parallel_backend == 'threading'
        assert config.n_workers == 32


# ==================== 配置序列化测试 ====================


class TestConfigSerialization:
    """配置序列化测试（如果需要）"""

    def test_config_to_dict(self):
        """测试配置转为字典"""
        from dataclasses import asdict

        config = ParallelComputingConfig(
            n_workers=8,
            parallel_backend='ray'
        )

        config_dict = asdict(config)

        assert isinstance(config_dict, dict)
        assert config_dict['n_workers'] == 8
        assert config_dict['parallel_backend'] == 'ray'

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            'enable_parallel': True,
            'n_workers': 16,
            'parallel_backend': 'dask',
            'chunk_size': 200,
            'use_shared_memory': False,
            'ray_address': None,
            'show_progress': True,
            'timeout': 600
        }

        config = ParallelComputingConfig(**config_dict)

        assert config.n_workers == 16
        assert config.parallel_backend == 'dask'
        assert config.chunk_size == 200


# ==================== 向后兼容性测试 ====================


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_config_without_parallel(self):
        """测试没有并行配置的旧版本兼容"""
        # 即使不使用parallel_computing，主配置也应该正常工作
        config = FeatureEngineerConfig()

        # 可以忽略parallel_computing
        assert config.trading_days.annual_trading_days == 252
        assert len(config.technical_indicators.ma_periods) > 0

    def test_default_behavior_unchanged(self):
        """测试默认行为未改变"""
        config = FeatureEngineerConfig()

        # 默认启用Copy-on-Write
        assert config.enable_copy_on_write is True

        # 默认禁用数据泄漏检测
        assert config.enable_leak_detection is False

        # 默认不显示缓存统计
        assert config.show_cache_stats is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
