#!/usr/bin/env python3
"""
测试配置模板管理器
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.config.templates.manager import ConfigTemplateManager
from src.config.templates.base import ConfigTemplate


class TestConfigTemplateManager:
    """测试 ConfigTemplateManager 类"""

    @pytest.fixture
    def temp_templates_dir(self, tmp_path):
        """创建临时模板目录"""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # 创建测试模板
        template1 = {
            "name": "template1",
            "description": "Test template 1",
            "version": "1.0",
            "settings": {"app": {"debug": True}},
            "tags": ["test"],
        }

        template2 = {
            "name": "template2",
            "description": "Test template 2",
            "version": "1.0",
            "settings": {"app": {"debug": False}},
            "tags": ["prod"],
        }

        with open(templates_dir / "template1.yaml", "w") as f:
            yaml.dump(template1, f)

        with open(templates_dir / "template2.yaml", "w") as f:
            yaml.dump(template2, f)

        return templates_dir

    def test_init_creates_directory(self, tmp_path):
        """测试初始化时创建目录"""
        templates_dir = tmp_path / "nonexistent"
        manager = ConfigTemplateManager(templates_dir)

        assert templates_dir.exists()

    def test_list_templates(self, temp_templates_dir):
        """测试列出所有模板"""
        manager = ConfigTemplateManager(temp_templates_dir)
        templates = manager.list_templates()

        assert len(templates) == 2
        template_names = [t.name for t in templates]
        assert "template1" in template_names
        assert "template2" in template_names

    def test_list_templates_empty_dir(self, tmp_path):
        """测试列出空目录的模板"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        manager = ConfigTemplateManager(empty_dir)
        templates = manager.list_templates()

        assert len(templates) == 0

    def test_load_template(self, temp_templates_dir):
        """测试加载模板"""
        manager = ConfigTemplateManager(temp_templates_dir)
        template = manager.load_template("template1")

        assert template.name == "template1"
        assert template.settings["app"]["debug"] is True

    def test_load_template_not_found(self, temp_templates_dir):
        """测试加载不存在的模板"""
        manager = ConfigTemplateManager(temp_templates_dir)

        with pytest.raises(ValueError, match="模板不存在"):
            manager.load_template("nonexistent")

    def test_load_template_with_inheritance(self, temp_templates_dir):
        """测试加载继承模板"""
        # 创建父模板
        parent = {
            "name": "parent",
            "description": "Parent",
            "version": "1.0",
            "settings": {"app": {"debug": False, "log_level": "INFO"}},
        }

        # 创建子模板
        child = {
            "name": "child",
            "description": "Child",
            "version": "1.0",
            "extends": "parent",
            "settings": {"app": {"debug": True}},
        }

        with open(temp_templates_dir / "parent.yaml", "w") as f:
            yaml.dump(parent, f)

        with open(temp_templates_dir / "child.yaml", "w") as f:
            yaml.dump(child, f)

        manager = ConfigTemplateManager(temp_templates_dir)
        template = manager.load_template("child")

        # 应该合并父子配置
        assert template.settings["app"]["debug"] is True  # 子覆盖
        assert template.settings["app"]["log_level"] == "INFO"  # 父继承

    def test_load_template_caching(self, temp_templates_dir):
        """测试模板缓存"""
        manager = ConfigTemplateManager(temp_templates_dir)

        # 第一次加载
        template1 = manager.load_template("template1")

        # 第二次加载（应该从缓存）
        template2 = manager.load_template("template1")

        assert template1 is template2  # 同一个对象

    def test_apply_template_dry_run(self, temp_templates_dir):
        """测试预览模式应用模板"""
        manager = ConfigTemplateManager(temp_templates_dir)
        env_content = manager.apply_template("template1", dry_run=True)

        assert isinstance(env_content, str)
        assert "Stock-Analysis 配置文件" in env_content
        assert "APP_DEBUG=true" in env_content

    def test_apply_template_write_file(self, temp_templates_dir, tmp_path):
        """测试实际写入模板"""
        manager = ConfigTemplateManager(temp_templates_dir)
        env_path = tmp_path / ".env"

        env_content = manager.apply_template(
            "template1", dry_run=False, env_path=env_path
        )

        assert env_path.exists()
        content = env_path.read_text()
        assert "APP_DEBUG=true" in content

    def test_apply_template_backup_existing(self, temp_templates_dir, tmp_path):
        """测试备份现有配置"""
        env_path = tmp_path / ".env"
        env_path.write_text("OLD_CONFIG=value\n")

        manager = ConfigTemplateManager(temp_templates_dir)
        manager.apply_template("template1", dry_run=False, env_path=env_path)

        # 检查备份文件 - 备份文件格式为.env.backup_YYYYMMDD_HHMMSS
        # 注意: 文件名是 ".env.backup_时间戳"，不是 ".env.backup_*"
        backup_files = list(tmp_path.glob("*.backup_*"))
        assert len(backup_files) >= 1
        # 读取第一个备份文件
        if backup_files:
            assert "OLD_CONFIG=value" in backup_files[0].read_text()

    def test_export_current_as_template(self, temp_templates_dir, tmp_path):
        """测试导出当前配置为模板"""
        # 创建 .env 文件
        env_path = tmp_path / ".env"
        env_content = """
APP_DEBUG=true
DATABASE_HOST=localhost
DATABASE_PORT=5432
        """
        env_path.write_text(env_content.strip())

        manager = ConfigTemplateManager(temp_templates_dir)
        template_path = manager.export_current_as_template(
            name="exported",
            description="Exported config",
            env_path=env_path,
            version="2.0",
            tags=["custom"],
        )

        assert template_path.exists()

        # 验证导出的模板
        template = ConfigTemplate.from_yaml(template_path)
        assert template.name == "exported"
        assert template.version == "2.0"
        assert "app" in template.settings

    def test_export_without_env_file(self, temp_templates_dir):
        """测试导出时缺少 .env 文件"""
        manager = ConfigTemplateManager(temp_templates_dir)

        with pytest.raises(ValueError, match=".env 文件不存在"):
            manager.export_current_as_template(
                name="test",
                description="Test",
                env_path=Path("/nonexistent/.env"),
            )

    def test_import_template(self, temp_templates_dir, tmp_path):
        """测试导入外部模板"""
        # 创建外部模板
        external_template = {
            "name": "external",
            "description": "External template",
            "version": "1.0",
            "settings": {"app": {"debug": True}},
        }

        external_path = tmp_path / "external.yaml"
        with open(external_path, "w") as f:
            yaml.dump(external_template, f)

        manager = ConfigTemplateManager(temp_templates_dir)
        template_name = manager.import_template(external_path)

        assert template_name == "external"
        assert (temp_templates_dir / "external.yaml").exists()

    def test_import_invalid_template(self, temp_templates_dir, tmp_path):
        """测试导入无效模板"""
        # 创建无效 YAML
        invalid_path = tmp_path / "invalid.yaml"
        invalid_path.write_text("not: valid\nmissing: required fields")

        manager = ConfigTemplateManager(temp_templates_dir)

        with pytest.raises(ValueError, match="无效的模板文件"):
            manager.import_template(invalid_path)

    def test_diff_templates(self, temp_templates_dir):
        """测试对比模板"""
        manager = ConfigTemplateManager(temp_templates_dir)
        diff_result = manager.diff_templates("template1", "template2")

        assert "template1" in diff_result
        assert "template2" in diff_result
        assert "settings_diff" in diff_result

        settings_diff = diff_result["settings_diff"]
        assert "changed" in settings_diff

    def test_deep_merge(self, temp_templates_dir):
        """测试深度合并"""
        manager = ConfigTemplateManager(temp_templates_dir)

        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"d": 4, "e": 5}, "f": 6}

        result = manager._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 4  # 覆盖
        assert result["b"]["e"] == 5  # 新增
        assert result["f"] == 6

    def test_generate_env_content_formatting(self, temp_templates_dir):
        """测试生成 .env 内容的格式"""
        manager = ConfigTemplateManager(temp_templates_dir)
        template = manager.load_template("template1")

        settings = {"app": {"debug": True, "log_level": "INFO"}}
        env_content = manager._generate_env_content(settings, template)

        # 检查格式
        assert "Stock-Analysis 配置文件" in env_content
        assert "APP_DEBUG=true" in env_content
        assert "APP_LOG_LEVEL=INFO" in env_content
        assert "应用配置" in env_content

    def test_format_env_value_types(self, temp_templates_dir):
        """测试格式化各种类型的环境变量值"""
        manager = ConfigTemplateManager(temp_templates_dir)

        assert manager._format_env_value(True) == "true"
        assert manager._format_env_value(False) == "false"
        assert manager._format_env_value(123) == "123"
        assert manager._format_env_value(3.14) == "3.14"
        assert manager._format_env_value("test") == "test"
        assert manager._format_env_value([1, 2, 3]) == "1,2,3"

    def test_parse_env_file(self, temp_templates_dir, tmp_path):
        """测试解析 .env 文件"""
        env_content = """
# 注释
APP_DEBUG=true
APP_LOG_LEVEL=INFO
DATABASE_HOST=localhost
DATABASE_PORT=5432
        """
        env_path = tmp_path / ".env"
        env_path.write_text(env_content.strip())

        manager = ConfigTemplateManager(temp_templates_dir)
        settings = manager._parse_env_file(env_path)

        # _parse_env_file会将APP_DEBUG解析为settings["app"]["debug"]
        # APP_LOG_LEVEL会被解析为settings["app"]["log"]["level"]
        assert "app" in settings
        assert settings["app"]["debug"] is True
        # 注意：APP_LOG_LEVEL会被解析为嵌套的log.level
        assert "log" in settings["app"]
        assert settings["app"]["log"]["level"] == "INFO"
        assert settings["database"]["host"] == "localhost"
        assert settings["database"]["port"] == 5432

    def test_parse_env_value_types(self, temp_templates_dir):
        """测试解析各种类型的环境变量值"""
        manager = ConfigTemplateManager(temp_templates_dir)

        assert manager._parse_env_value("true") is True
        assert manager._parse_env_value("false") is False
        assert manager._parse_env_value("123") == 123
        assert manager._parse_env_value("3.14") == 3.14
        assert manager._parse_env_value("test") == "test"
        assert manager._parse_env_value("a,b,c") == ["a", "b", "c"]

    def test_clear_cache(self, temp_templates_dir):
        """测试清除缓存"""
        manager = ConfigTemplateManager(temp_templates_dir)

        # 加载模板（会缓存）
        manager.load_template("template1")
        assert len(manager._cache) > 0

        # 清除缓存
        manager.clear_cache()
        assert len(manager._cache) == 0

    def test_diff_dicts_comprehensive(self, temp_templates_dir):
        """测试全面的字典对比"""
        manager = ConfigTemplateManager(temp_templates_dir)

        dict1 = {"a": 1, "b": 2, "c": {"d": 3, "e": 4}}
        dict2 = {"a": 1, "b": 3, "c": {"d": 3, "f": 5}, "g": 6}

        diff = manager._diff_dicts(dict1, dict2)

        assert diff["unchanged"]["a"] == 1
        assert "b" in diff["changed"]
        assert diff["changed"]["b"]["from"] == 2
        assert diff["changed"]["b"]["to"] == 3
        assert "c.e" in diff["removed"]
        assert "c.f" in diff["added"]
        assert "g" in diff["added"]
