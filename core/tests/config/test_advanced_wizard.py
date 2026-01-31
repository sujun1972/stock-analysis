#!/usr/bin/env python3
"""
高级配置向导单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from config.advanced_wizard import (
    detect_system_info,
    configure_performance,
    configure_features,
    configure_strategies,
    configure_monitoring,
    save_advanced_config,
)


class TestSystemInfoDetection:
    """测试系统信息检测"""

    def test_detect_system_info(self):
        """测试系统信息检测"""
        info = detect_system_info()

        assert "cpu_count" in info
        assert "memory_gb" in info
        assert "disk_free_gb" in info
        assert "gpu_available" in info
        assert "platform" in info

        # CPU数量应该大于0
        assert info["cpu_count"] > 0

        # 内存应该大于0
        assert info["memory_gb"] > 0

    def test_system_info_types(self):
        """测试系统信息的数据类型"""
        info = detect_system_info()

        assert isinstance(info["cpu_count"], int)
        assert isinstance(info["memory_gb"], float)
        assert isinstance(info["disk_free_gb"], float)
        assert isinstance(info["gpu_available"], bool)
        assert isinstance(info["platform"], str)


class TestPerformanceConfiguration:
    """测试性能配置"""

    @patch('builtins.input')
    def test_configure_performance_multiprocessing(self, mock_input):
        """测试配置多进程并行"""
        # 模拟用户输入: 选择multiprocessing, 默认workers, 默认chunk_size, 不启用GPU, 启用流式处理, 默认内存限制
        mock_input.side_effect = ["1", "", "", "n", "y", ""]

        system_info = {
            "cpu_count": 8,
            "memory_gb": 16.0,
            "disk_free_gb": 100.0,
            "gpu_available": False,
            "platform": "Darwin",
        }

        config = configure_performance(system_info)

        assert "parallel" in config
        assert config["parallel"]["backend"] == "multiprocessing"
        assert config["parallel"]["n_workers"] > 0
        assert "gpu" in config
        assert "memory" in config

    @patch('builtins.input')
    def test_configure_performance_with_gpu(self, mock_input):
        """测试配置GPU加速"""
        mock_input.side_effect = ["1", "", "", "y", "", "y", "n"]

        system_info = {
            "cpu_count": 8,
            "memory_gb": 32.0,
            "disk_free_gb": 100.0,
            "gpu_available": True,
            "gpu_name": "NVIDIA RTX 3090",
            "platform": "Linux",
        }

        config = configure_performance(system_info)

        assert config["gpu"]["enable_gpu"] is True
        assert "device_id" in config["gpu"]


class TestFeaturesConfiguration:
    """测试特征工程配置"""

    @patch('builtins.input')
    def test_configure_features_all_indicators(self, mock_input):
        """测试启用所有技术指标"""
        # 启用所有指标, 使用默认MA周期, 启用所有Alpha因子, 使用默认动量周期
        mock_input.side_effect = ["y", "y", "y", "y"]

        config = configure_features()

        assert "technical_indicators" in config
        assert len(config["technical_indicators"]["enabled"]) > 0
        assert "alpha_factors" in config
        assert config["alpha_factors"]["enabled"] is True

    @patch('builtins.input')
    def test_configure_features_custom_indicators(self, mock_input):
        """测试自定义技术指标"""
        # 不启用所有, 自定义MA,EMA, 使用默认周期, 启用所有Alpha, 默认动量周期
        mock_input.side_effect = ["n", "MA,EMA", "y", "y", "y"]

        config = configure_features()

        assert "MA" in config["technical_indicators"]["enabled"]
        assert "EMA" in config["technical_indicators"]["enabled"]


class TestStrategiesConfiguration:
    """测试策略配置"""

    @patch('builtins.input')
    def test_configure_strategies_basic(self, mock_input):
        """测试基础策略配置"""
        # 默认初始资金, 默认手续费, 选择volume_based滑点, 默认风控参数, 不启用优化
        mock_input.side_effect = ["", "", "3", "", "", "", "n"]

        config = configure_strategies()

        assert "backtest" in config
        assert config["backtest"]["initial_capital"] == 1000000
        assert "risk" in config
        assert "optimization" in config
        assert config["optimization"]["enabled"] is False

    @patch('builtins.input')
    def test_configure_strategies_with_optimization(self, mock_input):
        """测试启用参数优化"""
        # 默认参数, 启用优化, 选择贝叶斯优化, 默认迭代次数
        mock_input.side_effect = ["", "", "3", "", "", "", "y", "3", ""]

        config = configure_strategies()

        assert config["optimization"]["enabled"] is True
        assert config["optimization"]["optimizer_type"] == "bayesian"


class TestMonitoringConfiguration:
    """测试监控配置"""

    @patch('builtins.input')
    def test_configure_monitoring_full(self, mock_input):
        """测试完整监控配置"""
        # INFO日志级别, 启用结构化日志, 启用指标收集, 默认间隔, 启用错误追踪
        mock_input.side_effect = ["2", "y", "y", "", "y"]

        config = configure_monitoring()

        assert config["logging"]["level"] == "INFO"
        assert config["logging"]["structured"] is True
        assert config["metrics"]["enabled"] is True
        assert config["error_tracking"]["enabled"] is True

    @patch('builtins.input')
    def test_configure_monitoring_minimal(self, mock_input):
        """测试最小监控配置"""
        # ERROR级别, 不启用结构化, 不启用指标, 不启用错误追踪
        mock_input.side_effect = ["4", "n", "n", "n"]

        config = configure_monitoring()

        assert config["logging"]["level"] == "ERROR"
        assert config["metrics"]["enabled"] is False
        assert config["error_tracking"]["enabled"] is False


class TestConfigSaving:
    """测试配置保存"""

    def test_save_advanced_config(self, tmp_path):
        """测试保存高级配置"""
        config = {
            "performance": {
                "parallel": {
                    "backend": "multiprocessing",
                    "n_workers": 7,
                }
            },
            "features": {
                "technical_indicators": {
                    "enabled": ["MA", "EMA"]
                }
            }
        }

        output_path = tmp_path / "config" / "advanced.yaml"
        saved_path = save_advanced_config(config, output_path)

        assert saved_path.exists()

        # 验证内容
        with open(saved_path, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config["performance"]["parallel"]["backend"] == "multiprocessing"
        assert loaded_config["features"]["technical_indicators"]["enabled"] == ["MA", "EMA"]

    def test_save_advanced_config_default_path(self, tmp_path, monkeypatch):
        """测试使用默认路径保存"""
        monkeypatch.chdir(tmp_path)

        config = {"test": "value"}
        saved_path = save_advanced_config(config)

        assert saved_path == tmp_path / "config" / "advanced.yaml"
        assert saved_path.exists()


class TestIntegration:
    """集成测试"""

    @patch('builtins.input')
    def test_full_configuration_flow(self, mock_input):
        """测试完整配置流程"""
        # 模拟完整的配置流程
        mock_input.side_effect = [
            # 性能配置
            "1", "7", "1000", "n", "y", "8",
            # 特征配置
            "y", "y", "y", "y",
            # 策略配置
            "", "", "3", "", "", "", "n",
            # 监控配置
            "2", "y", "y", "60", "y",
        ]

        system_info = detect_system_info()

        # 执行所有配置步骤
        perf_config = configure_performance(system_info)
        features_config = configure_features()
        strategies_config = configure_strategies()
        monitoring_config = configure_monitoring()

        # 验证所有配置都已生成
        assert perf_config is not None
        assert features_config is not None
        assert strategies_config is not None
        assert monitoring_config is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
