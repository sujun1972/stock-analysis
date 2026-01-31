"""
配置验证器测试

测试 ConfigValidator 的所有验证功能。
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.config.validators import (
    ConfigValidator,
    ValidationReport,
    ValidationIssue,
    SeverityLevel,
    Category,
)


class TestValidationIssue:
    """测试 ValidationIssue 数据类"""

    def test_to_dict(self):
        """测试转换为字典"""
        issue = ValidationIssue(
            severity=SeverityLevel.ERROR,
            category=Category.DATABASE,
            code="DB001",
            message="数据库连接失败",
            suggestion="检查数据库配置",
            auto_fixable=False,
        )

        result = issue.to_dict()

        assert result["severity"] == "error"
        assert result["category"] == "database"
        assert result["code"] == "DB001"
        assert result["message"] == "数据库连接失败"
        assert result["suggestion"] == "检查数据库配置"
        assert result["auto_fixable"] is False


class TestValidationReport:
    """测试 ValidationReport 数据类"""

    def test_to_dict(self):
        """测试转换为字典"""
        issues = [
            ValidationIssue(
                severity=SeverityLevel.ERROR,
                category=Category.DATABASE,
                code="DB001",
                message="测试错误",
            )
        ]
        report = ValidationReport(
            passed=False,
            total_issues=1,
            issues_by_severity={"error": 1, "warning": 0, "critical": 0, "info": 0},
            issues=issues,
        )

        result = report.to_dict()

        assert result["passed"] is False
        assert result["total_issues"] == 1
        assert result["issues_by_severity"]["error"] == 1
        assert len(result["issues"]) == 1

    def test_to_json(self):
        """测试转换为 JSON"""
        report = ValidationReport(
            passed=True,
            total_issues=0,
            issues_by_severity={"error": 0, "warning": 0, "critical": 0, "info": 0},
            issues=[],
        )

        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["passed"] is True
        assert data["total_issues"] == 0

    def test_to_html(self):
        """测试生成 HTML 报告"""
        issues = [
            ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.PATHS,
                code="PATH001",
                message="路径不存在",
                suggestion="创建目录",
            )
        ]
        report = ValidationReport(
            passed=True,
            total_issues=1,
            issues_by_severity={"error": 0, "warning": 1, "critical": 0, "info": 0},
            issues=issues,
        )

        html = report.to_html()

        assert "<!DOCTYPE html>" in html
        assert "PATH001" in html
        assert "路径不存在" in html
        assert "创建目录" in html

    def test_to_console(self, capsys):
        """测试输出到控制台"""
        report = ValidationReport(
            passed=True,
            total_issues=0,
            issues_by_severity={"error": 0, "warning": 0, "critical": 0, "info": 0},
            issues=[],
        )

        report.to_console()
        captured = capsys.readouterr()

        # 验证输出包含关键信息（Rich 会添加 ANSI 转义码）
        assert "0" in captured.out  # total_issues


class TestConfigValidator:
    """测试 ConfigValidator 类"""

    @pytest.fixture
    def mock_settings(self):
        """创建模拟配置对象"""
        settings = Mock()

        # 数据库配置
        settings.database = Mock()
        settings.database.host = "localhost"
        settings.database.port = 5432
        settings.database.database = "test_db"
        settings.database.user = "test_user"
        settings.database.password = "strong_password_123"

        # 路径配置
        settings.paths = Mock()
        settings.paths.data_dir = "/tmp/data"
        settings.paths.models_dir = "/tmp/models"
        settings.paths.cache_dir = "/tmp/cache"
        settings.paths.results_dir = "/tmp/results"

        # 数据源配置
        settings.data_source = Mock()
        settings.data_source.provider = "akshare"
        settings.data_source.tushare_token = ""

        # ML 配置
        settings.ml = Mock()
        settings.ml.default_target_period = 5
        settings.ml.default_train_ratio = 0.8
        settings.ml.cache_features = True

        # 应用配置
        settings.app = Mock()
        settings.app.debug = False
        settings.app.environment = "development"

        return settings

    @pytest.fixture
    def validator(self, mock_settings):
        """创建验证器实例"""
        return ConfigValidator(settings=mock_settings)

    def test_init_with_settings(self, mock_settings):
        """测试使用提供的配置初始化"""
        validator = ConfigValidator(settings=mock_settings)
        assert validator.settings == mock_settings
        assert validator.issues == []

    def test_validate_database_success(self, validator):
        """测试数据库验证通过"""
        with patch.object(validator, '_test_db_connection') as mock_conn, \
             patch.object(validator, '_check_timescaledb_extension') as mock_timescale:
            # 模拟连接成功
            mock_conn.return_value = Mock()
            # 模拟TimescaleDB已安装
            mock_timescale.return_value = True

            issues = validator.validate_database()

            # 当连接成功且TimescaleDB已安装时，不应有任何issues
            assert len(issues) == 0

    def test_validate_database_missing_host(self, validator):
        """测试缺少数据库主机"""
        validator.settings.database.host = ""

        issues = validator.validate_database()

        assert len(issues) > 0
        assert any(issue.code == "DB001" for issue in issues)
        assert any(issue.severity == SeverityLevel.CRITICAL for issue in issues)

    def test_validate_database_connection_failed(self, validator):
        """测试数据库连接失败"""
        with patch.object(validator, '_test_db_connection') as mock_conn:
            mock_conn.side_effect = Exception("连接被拒绝")

            issues = validator.validate_database()

            assert len(issues) > 0
            assert any(issue.code == "DB002" for issue in issues)
            assert any(issue.severity == SeverityLevel.ERROR for issue in issues)

    def test_validate_database_timescaledb_not_installed(self, validator):
        """测试 TimescaleDB 扩展未安装"""
        with patch.object(validator, '_test_db_connection') as mock_conn:
            mock_conn.return_value = Mock()

        with patch.object(validator, '_check_timescaledb_extension') as mock_check:
            mock_check.return_value = False

            issues = validator.validate_database()

            assert any(issue.code == "DB003" for issue in issues)
            assert any(issue.severity == SeverityLevel.WARNING for issue in issues)

    def test_validate_paths_not_exist(self, validator):
        """测试路径不存在"""
        # 使用不存在的路径
        validator.settings.paths.data_dir = "/tmp/nonexistent_test_dir_12345"

        issues = validator.validate_paths()

        assert len(issues) > 0
        assert any(issue.code == "PATH001" for issue in issues)
        assert any(issue.severity == SeverityLevel.WARNING for issue in issues)

    def test_validate_paths_no_read_permission(self, validator):
        """测试路径无读权限"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()

            validator.settings.paths.data_dir = str(test_dir)

            with patch('os.access') as mock_access:
                # 模拟无读权限
                mock_access.return_value = False

                issues = validator.validate_paths()

                assert any(issue.code == "PATH002" for issue in issues)

    def test_validate_paths_no_write_permission(self, validator):
        """测试路径无写权限"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test"
            test_dir.mkdir()

            validator.settings.paths.data_dir = str(test_dir)

            def access_side_effect(path, mode):
                if mode == os.R_OK:
                    return True
                if mode == os.W_OK:
                    return False
                return True

            with patch('os.access', side_effect=access_side_effect):
                issues = validator.validate_paths()

                assert any(issue.code == "PATH003" for issue in issues)

    def test_validate_paths_low_disk_space(self, validator):
        """测试磁盘空间不足"""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator.settings.paths.data_dir = tmpdir

            mock_usage = Mock()
            mock_usage.free = 500 * 1024 * 1024  # 500 MB

            with patch('shutil.disk_usage', return_value=mock_usage):
                issues = validator.validate_paths()

                assert any(issue.code == "PATH004" for issue in issues)

    def test_validate_data_source_invalid_provider(self, validator):
        """测试无效的数据源"""
        validator.settings.data_source.provider = "invalid_provider"

        issues = validator.validate_data_sources()

        assert len(issues) > 0
        assert any(issue.code == "DS001" for issue in issues)
        assert any(issue.severity == SeverityLevel.ERROR for issue in issues)

    def test_validate_data_source_tushare_missing_token(self, validator):
        """测试 Tushare 缺少 Token"""
        validator.settings.data_source.provider = "tushare"
        validator.settings.data_source.tushare_token = ""

        issues = validator.validate_data_sources()

        assert any(issue.code == "DS002" for issue in issues)

    def test_validate_data_source_tushare_invalid_token(self, validator):
        """测试 Tushare Token 无效"""
        validator.settings.data_source.provider = "tushare"
        validator.settings.data_source.tushare_token = "invalid_token"

        with patch.object(validator, '_test_tushare_token') as mock_test:
            mock_test.return_value = False

            issues = validator.validate_data_sources()

            assert any(issue.code == "DS003" for issue in issues)

    def test_validate_data_source_connection_failed(self, validator):
        """测试数据源连接失败"""
        with patch.object(validator, '_test_data_source_connection') as mock_test:
            mock_test.side_effect = Exception("网络错误")

            issues = validator.validate_data_sources()

            assert any(issue.code == "DS004" for issue in issues)

    def test_validate_ml_config_invalid_target_period(self, validator):
        """测试无效的预测周期"""
        validator.settings.ml.default_target_period = 100  # 超出合理范围

        issues = validator.validate_ml_config()

        assert any(issue.code == "ML001" for issue in issues)

    def test_validate_ml_config_invalid_train_ratio(self, validator):
        """测试无效的训练集比例"""
        validator.settings.ml.default_train_ratio = 0.99  # 超出合理范围

        issues = validator.validate_ml_config()

        assert any(issue.code == "ML002" for issue in issues)

    def test_validate_ml_config_too_many_model_files(self, validator):
        """测试模型文件过多"""
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            validator.settings.paths.models_dir = str(models_dir)

            # 创建超过 100 个模型文件
            for i in range(105):
                (models_dir / f"model_{i}.pkl").touch()

            issues = validator.validate_ml_config()

            assert any(issue.code == "ML004" for issue in issues)

    def test_validate_performance_too_many_workers(self, validator):
        """测试 worker 数量超过 CPU 核心数"""
        validator.settings.performance = Mock()
        validator.settings.performance.n_workers = 1000  # 远超 CPU 核心数

        issues = validator.validate_performance()

        assert any(issue.code == "PERF001" for issue in issues)

    def test_validate_security_weak_password(self, validator):
        """测试使用弱密码"""
        validator.settings.database.password = "password"

        issues = validator.validate_security()

        assert any(issue.code == "SEC001" for issue in issues)

    def test_validate_security_production_debug_enabled(self, validator):
        """测试生产环境启用调试模式"""
        validator.settings.app.environment = "production"
        validator.settings.app.debug = True

        issues = validator.validate_security()

        assert any(issue.code == "SEC002" for issue in issues)
        assert any(issue.severity == SeverityLevel.ERROR for issue in issues)

    def test_validate_all(self, validator):
        """测试验证所有配置项"""
        with patch.object(validator, '_test_db_connection') as mock_conn:
            mock_conn.return_value = Mock()

            report = validator.validate_all()

            assert isinstance(report, ValidationReport)
            assert isinstance(report.passed, bool)
            assert isinstance(report.total_issues, int)
            assert isinstance(report.issues_by_severity, dict)

    def test_generate_report_passed(self, validator):
        """测试生成通过的报告"""
        validator.issues = []

        report = validator._generate_report()

        assert report.passed is True
        assert report.total_issues == 0

    def test_generate_report_with_warnings(self, validator):
        """测试生成包含警告的报告"""
        validator.issues = [
            ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.PATHS,
                code="PATH001",
                message="测试警告",
            )
        ]

        report = validator._generate_report()

        assert report.passed is True  # 警告不影响通过状态
        assert report.total_issues == 1
        assert report.issues_by_severity["warning"] == 1

    def test_generate_report_with_errors(self, validator):
        """测试生成包含错误的报告"""
        validator.issues = [
            ValidationIssue(
                severity=SeverityLevel.ERROR,
                category=Category.DATABASE,
                code="DB002",
                message="测试错误",
            )
        ]

        report = validator._generate_report()

        assert report.passed is False
        assert report.total_issues == 1
        assert report.issues_by_severity["error"] == 1

    def test_generate_report_with_critical(self, validator):
        """测试生成包含严重错误的报告"""
        validator.issues = [
            ValidationIssue(
                severity=SeverityLevel.CRITICAL,
                category=Category.DATABASE,
                code="DB001",
                message="测试严重错误",
            )
        ]

        report = validator._generate_report()

        assert report.passed is False
        assert report.issues_by_severity["critical"] == 1

    def test_test_db_connection_success(self, validator):
        """测试数据库连接成功"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn

            conn = validator._test_db_connection()

            assert conn == mock_conn
            mock_connect.assert_called_once()

    def test_test_db_connection_failed(self, validator):
        """测试数据库连接失败"""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("连接失败")

            with pytest.raises(Exception):
                validator._test_db_connection()

    def test_check_timescaledb_extension_installed(self, validator):
        """测试 TimescaleDB 扩展已安装"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [True]
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(validator, '_test_db_connection', return_value=mock_conn):
            result = validator._check_timescaledb_extension()

            assert result is True

    def test_check_timescaledb_extension_not_installed(self, validator):
        """测试 TimescaleDB 扩展未安装"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [False]
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(validator, '_test_db_connection', return_value=mock_conn):
            result = validator._check_timescaledb_extension()

            assert result is False

    def test_test_tushare_token_valid(self, validator):
        """测试 Tushare Token 有效"""
        validator.settings.data_source.tushare_token = "valid_token"

        mock_df = Mock()
        mock_df.empty = False

        with patch('tushare.set_token'):
            with patch('tushare.pro_api') as mock_pro_api:
                mock_api = Mock()
                mock_api.trade_cal.return_value = mock_df
                mock_pro_api.return_value = mock_api

                result = validator._test_tushare_token()

                assert result is True

    def test_test_data_source_connection_akshare_success(self, validator):
        """测试 AkShare 连接成功"""
        mock_df = Mock()
        mock_df.empty = False

        with patch('akshare.stock_zh_a_spot_em', return_value=mock_df):
            # 不应抛出异常
            validator._test_data_source_connection("akshare")

    def test_test_data_source_connection_akshare_failed(self, validator):
        """测试 AkShare 连接失败"""
        with patch('akshare.stock_zh_a_spot_em', side_effect=Exception("网络错误")):
            with pytest.raises(Exception):
                validator._test_data_source_connection("akshare")


class TestIntegration:
    """集成测试"""

    def test_full_validation_flow(self):
        """测试完整的验证流程"""
        # 创建临时配置
        settings = Mock()
        settings.database = Mock()
        settings.database.host = "localhost"
        settings.database.port = 5432
        settings.database.database = "test"
        settings.database.user = "user"
        settings.database.password = "strong_pass"

        settings.paths = Mock()
        settings.paths.data_dir = "/tmp/test"
        settings.paths.models_dir = "/tmp/models"
        settings.paths.cache_dir = "/tmp/cache"
        settings.paths.results_dir = "/tmp/results"

        settings.data_source = Mock()
        settings.data_source.provider = "akshare"
        settings.data_source.tushare_token = ""

        settings.ml = Mock()
        settings.ml.default_target_period = 5
        settings.ml.default_train_ratio = 0.8

        settings.app = Mock()
        settings.app.debug = False
        settings.app.environment = "development"

        validator = ConfigValidator(settings=settings)

        with patch.object(validator, '_test_db_connection', return_value=Mock()):
            report = validator.validate_all()

            assert isinstance(report, ValidationReport)
            assert report.total_issues >= 0
            assert all(key in report.issues_by_severity for key in ["critical", "error", "warning", "info"])
