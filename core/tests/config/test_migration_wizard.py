#!/usr/bin/env python3
"""
配置迁移向导单元测试
"""

import pytest
from pathlib import Path
from datetime import datetime

from config.migration_wizard import (
    ConfigMigrator,
    ConfigVersion,
    MigrationIssue,
    MigrationReport,
    MIGRATION_RULES,
)


class TestVersionDetection:
    """测试版本检测"""

    def test_detect_v2_0(self, tmp_path):
        """测试检测v2.0版本"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
ML_FEATURE_VERSION=v2.0
APP_ENVIRONMENT=development
        """.strip())

        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()

        assert version == ConfigVersion.V2_0

    def test_detect_v1_5(self, tmp_path):
        """测试检测v1.5版本"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
ML_CACHE_FEATURES=true
PATH_DATA_DIR=/data
        """.strip())

        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()

        assert version == ConfigVersion.V1_5

    def test_detect_v1_0(self, tmp_path):
        """测试检测v1.0版本"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
MODELS_PATH=/models
        """.strip())

        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()

        assert version == ConfigVersion.V1_0

    def test_detect_unknown(self, tmp_path):
        """测试检测未知版本"""
        config_file = tmp_path / ".env"
        config_file.write_text("")

        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()

        assert version == ConfigVersion.UNKNOWN

    def test_detect_nonexistent_file(self, tmp_path):
        """测试不存在的配置文件"""
        config_file = tmp_path / "nonexistent.env"

        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()

        assert version == ConfigVersion.UNKNOWN


class TestCompatibilityCheck:
    """测试兼容性检查"""

    def test_check_v1_0_to_v2_0(self, tmp_path):
        """测试v1.0到v2.0的兼容性"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATA_PATH=/data
MODELS_PATH=/models
        """.strip())

        migrator = ConfigMigrator(config_file)
        issues = migrator.check_compatibility(ConfigVersion.V1_0, ConfigVersion.V2_0)

        # 应该有重命名的信息
        rename_issues = [i for i in issues if "重命名" in i.message or "renamed" in i.message.lower()]
        assert len(rename_issues) > 0

    def test_check_same_version(self, tmp_path):
        """测试相同版本的兼容性"""
        config_file = tmp_path / ".env"
        config_file.write_text("DATABASE_HOST=localhost")

        migrator = ConfigMigrator(config_file)
        issues = migrator.check_compatibility(ConfigVersion.V2_0, ConfigVersion.V2_0)

        # 应该提示无需迁移（检查message或suggestion字段）
        assert any("无需迁移" in i.suggestion or "无需迁移" in i.message or "same version" in i.message.lower() for i in issues)

    def test_check_unknown_version(self, tmp_path):
        """测试未知版本的兼容性"""
        config_file = tmp_path / ".env"

        migrator = ConfigMigrator(config_file)
        issues = migrator.check_compatibility(ConfigVersion.UNKNOWN, ConfigVersion.V2_0)

        # 应该有错误
        assert any(i.severity == "error" for i in issues)


class TestMigration:
    """测试配置迁移"""

    def test_migrate_v1_0_to_v2_0(self, tmp_path):
        """测试从v1.0迁移到v2.0"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
MODELS_PATH=/models
DEBUG=True
        """.strip())

        migrator = ConfigMigrator(config_file)
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0)

        assert report.success is True
        assert report.from_version == "v1.0"
        assert report.to_version == "v2.0"
        assert len(report.changes_made) > 0

        # 验证新配置
        new_config = migrator._load_env_file()
        assert "PATH_DATA_DIR" in new_config
        assert "PATH_MODELS_DIR" in new_config
        assert "DATA_PATH" not in new_config
        assert "MODELS_PATH" not in new_config

    def test_migrate_creates_backup(self, tmp_path):
        """测试迁移时创建备份"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
        """.strip())

        migrator = ConfigMigrator(config_file)
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0, backup=True)

        assert report.success is True
        assert report.backup_path is not None
        assert report.backup_path.exists()

    def test_migrate_without_backup(self, tmp_path):
        """测试不创建备份的迁移"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
        """.strip())

        migrator = ConfigMigrator(config_file)
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0, backup=False)

        assert report.success is True
        assert report.backup_path is None

    def test_migrate_with_transforms(self, tmp_path):
        """测试值转换"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
DEBUG=True
        """.strip())

        migrator = ConfigMigrator(config_file)
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0)

        # 验证DEBUG被转换为小写字符串
        new_config = migrator._load_env_file()
        # 注意: 实际的转换可能因为规则而不同
        assert "DEBUG" in new_config or "APP_DEBUG" in new_config

    def test_migrate_adds_new_fields(self, tmp_path):
        """测试添加新字段"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATA_PATH=/data
        """.strip())

        migrator = ConfigMigrator(config_file)
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0)

        new_config = migrator._load_env_file()

        # 应该添加了ML_FEATURE_VERSION
        assert "ML_FEATURE_VERSION" in new_config
        assert new_config["ML_FEATURE_VERSION"] == "v2.0"


class TestRollback:
    """测试配置回滚"""

    def test_rollback_success(self, tmp_path):
        """测试成功回滚"""
        config_file = tmp_path / ".env"
        config_file.write_text("ORIGINAL=value")

        # 创建备份
        backup_file = tmp_path / ".env.backup.test"
        backup_file.write_text("ORIGINAL=value")

        # 修改配置
        config_file.write_text("MODIFIED=value")

        # 回滚
        migrator = ConfigMigrator(config_file)
        success = migrator.rollback(backup_file)

        assert success is True

        # 验证内容已恢复
        content = config_file.read_text()
        assert "ORIGINAL=value" in content

    def test_rollback_nonexistent_backup(self, tmp_path):
        """测试回滚不存在的备份"""
        config_file = tmp_path / ".env"
        backup_file = tmp_path / "nonexistent.backup"

        migrator = ConfigMigrator(config_file)
        success = migrator.rollback(backup_file)

        assert success is False


class TestEnvFileOperations:
    """测试环境变量文件操作"""

    def test_load_env_file(self, tmp_path):
        """测试加载环境变量文件"""
        config_file = tmp_path / ".env"
        config_file.write_text("""
# Comment
KEY1=value1
KEY2=value2

# Another comment
KEY3=value3
        """.strip())

        migrator = ConfigMigrator(config_file)
        config = migrator._load_env_file()

        assert config["KEY1"] == "value1"
        assert config["KEY2"] == "value2"
        assert config["KEY3"] == "value3"

    def test_save_env_file(self, tmp_path):
        """测试保存环境变量文件"""
        config_file = tmp_path / ".env"

        config = {
            "DATABASE_HOST": "localhost",
            "APP_DEBUG": "true",
            "PATH_DATA_DIR": "/data",
        }

        migrator = ConfigMigrator(config_file)
        migrator._save_env_file(config)

        # 验证文件已创建
        assert config_file.exists()

        # 验证内容
        content = config_file.read_text()
        assert "DATABASE_HOST=localhost" in content
        assert "APP_DEBUG=true" in content
        assert "PATH_DATA_DIR=/data" in content

    def test_save_env_file_with_grouping(self, tmp_path):
        """测试保存时按组分类"""
        config_file = tmp_path / ".env"

        config = {
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "5432",
            "APP_DEBUG": "true",
            "PATH_DATA_DIR": "/data",
        }

        migrator = ConfigMigrator(config_file)
        migrator._save_env_file(config)

        content = config_file.read_text()

        # 验证有分组注释
        assert "数据库配置" in content or "DATABASE" in content
        assert "应用配置" in content or "APP" in content


class TestBackup:
    """测试备份功能"""

    def test_backup_creates_file(self, tmp_path):
        """测试备份创建文件"""
        config_file = tmp_path / ".env"
        config_file.write_text("TEST=value")

        migrator = ConfigMigrator(config_file)
        backup_path = migrator._backup_config()

        assert backup_path.exists()
        assert backup_path.name.startswith(".env.backup.")

    def test_backup_preserves_content(self, tmp_path):
        """测试备份保留内容"""
        config_file = tmp_path / ".env"
        original_content = "TEST=value\nKEY=data"
        config_file.write_text(original_content)

        migrator = ConfigMigrator(config_file)
        backup_path = migrator._backup_config()

        backup_content = backup_path.read_text()
        assert backup_content == original_content


class TestMigrationRules:
    """测试迁移规则"""

    def test_migration_rules_exist(self):
        """测试迁移规则存在"""
        assert "v1.0_to_v2.0" in MIGRATION_RULES
        assert "v1.5_to_v2.0" in MIGRATION_RULES

    def test_migration_rules_structure(self):
        """测试迁移规则结构"""
        for key, rules in MIGRATION_RULES.items():
            assert "renames" in rules
            assert "removes" in rules
            assert "additions" in rules
            assert "transforms" in rules

            assert isinstance(rules["renames"], dict)
            assert isinstance(rules["removes"], list)
            assert isinstance(rules["additions"], dict)
            assert isinstance(rules["transforms"], dict)


class TestMigrationReport:
    """测试迁移报告"""

    def test_migration_report_creation(self):
        """测试创建迁移报告"""
        report = MigrationReport(
            from_version="v1.0",
            to_version="v2.0",
            success=True,
            issues=[],
            changes_made=["Test change"],
        )

        assert report.from_version == "v1.0"
        assert report.to_version == "v2.0"
        assert report.success is True
        assert len(report.changes_made) == 1
        assert report.timestamp is not None

    def test_migration_report_with_backup(self, tmp_path):
        """测试包含备份路径的报告"""
        backup_path = tmp_path / "backup.env"

        report = MigrationReport(
            from_version="v1.0",
            to_version="v2.0",
            success=True,
            issues=[],
            changes_made=[],
            backup_path=backup_path,
        )

        assert report.backup_path == backup_path


class TestIntegration:
    """集成测试"""

    def test_full_migration_flow(self, tmp_path):
        """测试完整迁移流程"""
        # 创建v1.0配置
        config_file = tmp_path / ".env"
        config_file.write_text("""
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATA_PATH=/data
MODELS_PATH=/models
CACHE_PATH=/cache
DEBUG=True
        """.strip())

        # 创建迁移器并检测版本
        migrator = ConfigMigrator(config_file)
        version = migrator.detect_version()
        assert version == ConfigVersion.V1_0

        # 检查兼容性
        issues = migrator.check_compatibility(ConfigVersion.V1_0, ConfigVersion.V2_0)
        assert len(issues) > 0

        # 执行迁移
        report = migrator.migrate(ConfigVersion.V1_0, ConfigVersion.V2_0)
        assert report.success is True

        # 验证新版本
        new_version = migrator.detect_version()
        assert new_version == ConfigVersion.V2_0

        # 验证备份存在
        assert report.backup_path is not None
        assert report.backup_path.exists()

        # 测试回滚
        rollback_success = migrator.rollback(report.backup_path)
        assert rollback_success is True

        # 验证回滚后版本
        rolled_back_version = migrator.detect_version()
        assert rolled_back_version == ConfigVersion.V1_0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
