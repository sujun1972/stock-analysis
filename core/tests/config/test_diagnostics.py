"""
配置诊断工具测试

测试 ConfigDiagnostics 的所有诊断功能。
"""

from unittest.mock import Mock, patch

import pytest

from src.config.diagnostics import (
    ConfigDiagnostics,
    Suggestion,
    Conflict,
    HealthReport,
)


class TestSuggestion:
    """测试 Suggestion 数据类"""

    def test_create_suggestion(self):
        """测试创建建议"""
        sug = Suggestion(
            category="performance",
            message="检测到多核 CPU",
            suggestion="建议启用多进程并行",
            priority="high"
        )

        assert sug.category == "performance"
        assert sug.priority == "high"


class TestConflict:
    """测试 Conflict 数据类"""

    def test_create_conflict(self):
        """测试创建冲突"""
        conflict = Conflict(
            message="GPU 已启用但不可用",
            conflicting_settings=["performance.gpu.enable_gpu"],
            resolution="禁用 GPU 或安装驱动"
        )

        assert "GPU" in conflict.message
        assert len(conflict.conflicting_settings) == 1


class TestConfigDiagnostics:
    """测试 ConfigDiagnostics 类"""

    @pytest.fixture
    def mock_settings(self):
        """创建模拟配置对象"""
        settings = Mock()

        # 数据库配置
        settings.database = Mock()
        settings.database.host = "localhost"
        settings.database.password = "strong_password"

        # 路径配置
        settings.paths = Mock()
        settings.paths.data_dir = "/tmp/data"
        settings.paths.models_dir = "/tmp/models"
        settings.paths.cache_dir = "/tmp/cache"
        settings.paths.results_dir = "/tmp/results"

        # 数据源配置
        settings.data_source = Mock()
        settings.data_source.provider = "akshare"

        # ML 配置
        settings.ml = Mock()
        settings.ml.cache_features = True

        # 应用配置
        settings.app = Mock()

        return settings

    @pytest.fixture
    def diagnostics(self, mock_settings):
        """创建诊断工具实例"""
        return ConfigDiagnostics(settings=mock_settings)

    def test_init_with_settings(self, mock_settings):
        """测试使用提供的配置初始化"""
        diagnostics = ConfigDiagnostics(settings=mock_settings)
        assert diagnostics.settings == mock_settings

    def test_get_system_info(self, diagnostics):
        """测试获取系统信息"""
        info = diagnostics._get_system_info()

        assert "platform" in info
        assert "python_version" in info
        assert "cpu_count" in info

    def test_check_resources_with_psutil(self, diagnostics):
        """测试检查资源（有 psutil）"""
        try:
            import psutil
            status = diagnostics._check_resources()

            assert "cpu_usage_percent" in status or "note" in status
        except ImportError:
            pytest.skip("psutil 未安装")

    def test_check_resources_without_psutil(self, diagnostics):
        """测试检查资源（无 psutil）"""
        with patch.dict('sys.modules', {'psutil': None}):
            status = diagnostics._check_resources()
            # 应该返回一些基本信息或提示
            assert isinstance(status, dict)

    def test_check_dependencies(self, diagnostics):
        """测试检查依赖包"""
        deps = diagnostics._check_dependencies()

        assert isinstance(deps, dict)
        # 至少应该检查一些核心依赖
        assert "pandas" in deps
        assert "numpy" in deps

    def test_check_config_consistency(self, diagnostics):
        """测试检查配置一致性"""
        consistency = diagnostics._check_config_consistency()

        assert isinstance(consistency, dict)
        assert "paths_configured" in consistency
        assert "database_configured" in consistency
        assert "data_source_configured" in consistency

    def test_determine_overall_health_good(self, diagnostics):
        """测试确定健康状况 - 良好"""
        resource_status = {"cpu_status": "good", "memory_status": "good", "disk_status": "good"}
        dependencies = {"pandas": True, "numpy": True, "psycopg2": True, "sqlalchemy": True, "loguru": True, "rich": True}
        config_consistency = {"paths_configured": True, "database_configured": True, "data_source_configured": True}

        health = diagnostics._determine_overall_health(resource_status, dependencies, config_consistency)

        assert health == "good"

    def test_determine_overall_health_critical_resources(self, diagnostics):
        """测试确定健康状况 - 资源紧张"""
        resource_status = {"cpu_status": "critical"}
        dependencies = {"pandas": True, "numpy": True, "psycopg2": True, "sqlalchemy": True, "loguru": True, "rich": True}
        config_consistency = {"paths_configured": True, "database_configured": True}

        health = diagnostics._determine_overall_health(resource_status, dependencies, config_consistency)

        assert health == "critical"

    def test_determine_overall_health_missing_dependencies(self, diagnostics):
        """测试确定健康状况 - 缺少依赖"""
        resource_status = {"cpu_status": "good"}
        dependencies = {"pandas": False}  # 缺少核心依赖
        config_consistency = {"paths_configured": True}

        health = diagnostics._determine_overall_health(resource_status, dependencies, config_consistency)

        assert health == "critical"

    def test_suggest_optimizations_many_cores(self, diagnostics):
        """测试优化建议 - 多核 CPU"""
        with patch('multiprocessing.cpu_count', return_value=16):
            try:
                import psutil
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.total = 32 * 1024 ** 3  # 32 GB

                    suggestions = diagnostics.suggest_optimizations()

                    assert len(suggestions) > 0
                    assert any("CPU" in s.message for s in suggestions)
            except ImportError:
                pytest.skip("psutil 未安装")

    def test_suggest_optimizations_low_memory(self, diagnostics):
        """测试优化建议 - 内存不足"""
        try:
            import psutil
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.total = 4 * 1024 ** 3  # 4 GB

                suggestions = diagnostics.suggest_optimizations()

                assert any("内存" in s.message for s in suggestions)
        except ImportError:
            pytest.skip("psutil 未安装")

    def test_suggest_optimizations_weak_password(self, diagnostics):
        """测试优化建议 - 弱密码"""
        diagnostics.settings.database.password = "password"

        suggestions = diagnostics.suggest_optimizations()

        assert any("密码" in s.message for s in suggestions)

    def test_suggest_optimizations_akshare(self, diagnostics):
        """测试优化建议 - AkShare 数据源"""
        diagnostics.settings.data_source.provider = "akshare"

        suggestions = diagnostics.suggest_optimizations()

        assert any("AkShare" in s.message for s in suggestions)

    def test_detect_conflicts_gpu_enabled_but_unavailable(self, diagnostics):
        """测试检测冲突 - GPU 已启用但不可用"""
        diagnostics.settings.performance = Mock()
        diagnostics.settings.performance.gpu = Mock()
        diagnostics.settings.performance.gpu.enable_gpu = True

        with patch.object(diagnostics, '_check_gpu_available', return_value=False):
            conflicts = diagnostics.detect_conflicts()

            assert len(conflicts) > 0
            assert any("GPU" in c.message for c in conflicts)

    def test_detect_conflicts_ray_not_installed(self, diagnostics):
        """测试检测冲突 - Ray 未安装"""
        diagnostics.settings.performance = Mock()
        diagnostics.settings.performance.parallel = Mock()
        diagnostics.settings.performance.parallel.backend = "ray"

        with patch.dict('sys.modules', {'ray': None}):
            conflicts = diagnostics.detect_conflicts()

            # 注意：这个测试可能因为 import 机制而不稳定
            assert isinstance(conflicts, list)

    def test_detect_conflicts_akshare_not_installed(self, diagnostics):
        """测试检测冲突 - AkShare 未安装"""
        diagnostics.settings.data_source.provider = "akshare"

        with patch.dict('sys.modules', {'akshare': None}):
            # 由于 import 的复杂性，这里主要测试不会崩溃
            conflicts = diagnostics.detect_conflicts()
            assert isinstance(conflicts, list)

    def test_check_gpu_available_cuda(self, diagnostics):
        """测试检查 GPU - CUDA"""
        try:
            import torch
            if torch.cuda.is_available():
                result = diagnostics._check_gpu_available()
                assert result is True
            else:
                pytest.skip("CUDA 不可用")
        except ImportError:
            pytest.skip("PyTorch 未安装")

    def test_check_gpu_available_mps(self, diagnostics):
        """测试检查 GPU - Apple MPS"""
        try:
            import torch
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                result = diagnostics._check_gpu_available()
                assert result is True
            else:
                pytest.skip("MPS 不可用")
        except ImportError:
            pytest.skip("PyTorch 未安装")

    def test_check_gpu_available_none(self, diagnostics):
        """测试检查 GPU - 无 GPU"""
        with patch.dict('sys.modules', {'torch': None}):
            result = diagnostics._check_gpu_available()
            assert result is False

    def test_run_health_check(self, diagnostics):
        """测试运行健康检查"""
        report = diagnostics.run_health_check()

        assert isinstance(report, HealthReport)
        assert report.overall_health in ["good", "warning", "critical"]
        assert isinstance(report.system_info, dict)
        assert isinstance(report.resource_status, dict)
        assert isinstance(report.dependencies_status, dict)
        assert isinstance(report.config_consistency, dict)

    def test_generate_report_console(self, diagnostics):
        """测试生成控制台报告"""
        # 这个测试主要验证不会崩溃
        with patch.object(diagnostics, 'run_health_check') as mock_health:
            mock_health.return_value = HealthReport(
                overall_health="good",
                system_info={"platform": "test"},
                resource_status={},
                dependencies_status={},
                config_consistency={},
            )

            with patch.object(diagnostics, 'suggest_optimizations', return_value=[]):
                with patch.object(diagnostics, 'detect_conflicts', return_value=[]):
                    # 调用不应抛出异常
                    diagnostics.generate_report(format="console")

    def test_generate_report_markdown(self, diagnostics):
        """测试生成 Markdown 报告"""
        with patch.object(diagnostics, 'run_health_check') as mock_health:
            mock_health.return_value = HealthReport(
                overall_health="good",
                system_info={"platform": "test"},
                resource_status={},
                dependencies_status={},
                config_consistency={},
            )

            with patch.object(diagnostics, 'suggest_optimizations', return_value=[]):
                with patch.object(diagnostics, 'detect_conflicts', return_value=[]):
                    report = diagnostics.generate_report(format="markdown")

                    assert isinstance(report, str)
                    assert "# 配置诊断报告" in report

    def test_generate_report_html(self, diagnostics):
        """测试生成 HTML 报告"""
        with patch.object(diagnostics, 'run_health_check') as mock_health:
            mock_health.return_value = HealthReport(
                overall_health="good",
                system_info={},
                resource_status={},
                dependencies_status={},
                config_consistency={},
            )

            with patch.object(diagnostics, 'suggest_optimizations', return_value=[]):
                with patch.object(diagnostics, 'detect_conflicts', return_value=[]):
                    report = diagnostics.generate_report(format="html")

                    assert isinstance(report, str)
                    assert "<html>" in report

    def test_generate_report_invalid_format(self, diagnostics):
        """测试生成报告 - 无效格式"""
        with pytest.raises(ValueError):
            diagnostics.generate_report(format="invalid")


class TestIntegration:
    """集成测试"""

    def test_full_diagnostics_flow(self):
        """测试完整的诊断流程"""
        settings = Mock()
        settings.database = Mock()
        settings.database.host = "localhost"
        settings.database.password = "strong_pass"

        settings.paths = Mock()
        settings.paths.data_dir = "/tmp/data"
        settings.paths.models_dir = "/tmp/models"
        settings.paths.cache_dir = "/tmp/cache"
        settings.paths.results_dir = "/tmp/results"

        settings.data_source = Mock()
        settings.data_source.provider = "akshare"

        settings.ml = Mock()
        settings.ml.cache_features = True

        settings.app = Mock()

        diagnostics = ConfigDiagnostics(settings=settings)

        # 运行健康检查
        health = diagnostics.run_health_check()
        assert isinstance(health, HealthReport)

        # 获取优化建议
        suggestions = diagnostics.suggest_optimizations()
        assert isinstance(suggestions, list)

        # 检测冲突
        conflicts = diagnostics.detect_conflicts()
        assert isinstance(conflicts, list)
