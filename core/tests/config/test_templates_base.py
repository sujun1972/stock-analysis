#!/usr/bin/env python3
"""
测试配置模板基础类
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.config.templates.base import ConfigTemplate


class TestConfigTemplate:
    """测试 ConfigTemplate 类"""

    def test_create_template(self):
        """测试创建模板"""
        template = ConfigTemplate(
            name="test_template",
            description="测试模板",
            version="1.0",
            settings={"app": {"debug": True}},
            tags=["test"],
        )

        assert template.name == "test_template"
        assert template.description == "测试模板"
        assert template.version == "1.0"
        assert template.settings == {"app": {"debug": True}}
        assert template.tags == ["test"]

    def test_from_yaml_valid(self, tmp_path):
        """测试从有效的 YAML 文件加载"""
        yaml_content = {
            "name": "test",
            "description": "Test template",
            "version": "1.0",
            "settings": {"app": {"debug": True}},
            "tags": ["test"],
        }

        yaml_file = tmp_path / "test.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        template = ConfigTemplate.from_yaml(yaml_file)

        assert template.name == "test"
        assert template.description == "Test template"
        assert template.version == "1.0"
        assert template.settings == {"app": {"debug": True}}

    def test_from_yaml_missing_required_fields(self, tmp_path):
        """测试从缺少必需字段的 YAML 文件加载"""
        yaml_content = {
            "name": "test",
            # 缺少 description 和 version
        }

        yaml_file = tmp_path / "invalid.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        with pytest.raises(ValueError, match="缺少必需字段"):
            ConfigTemplate.from_yaml(yaml_file)

    def test_from_yaml_file_not_found(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            ConfigTemplate.from_yaml(Path("/nonexistent/file.yaml"))

    def test_to_yaml(self, tmp_path):
        """测试保存为 YAML 文件"""
        template = ConfigTemplate(
            name="test",
            description="Test template",
            version="1.0",
            settings={"app": {"debug": True}},
            tags=["test"],
        )

        yaml_file = tmp_path / "output.yaml"
        template.to_yaml(yaml_file)

        assert yaml_file.exists()

        # 验证内容
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        assert data["name"] == "test"
        assert data["description"] == "Test template"
        assert data["version"] == "1.0"
        assert data["settings"] == {"app": {"debug": True}}

    def test_merge_with_parent_simple(self):
        """测试简单合并"""
        parent = ConfigTemplate(
            name="parent",
            description="Parent template",
            version="1.0",
            settings={"app": {"debug": False, "log_level": "INFO"}},
        )

        child = ConfigTemplate(
            name="child",
            description="Child template",
            version="1.0",
            settings={"app": {"debug": True}},  # 覆盖 debug
            extends="parent",
        )

        merged = child.merge_with_parent(parent)

        assert merged.settings["app"]["debug"] is True  # 子覆盖父
        assert merged.settings["app"]["log_level"] == "INFO"  # 继承父

    def test_merge_with_parent_nested(self):
        """测试嵌套字典合并"""
        parent = ConfigTemplate(
            name="parent",
            description="Parent",
            version="1.0",
            settings={
                "database": {"host": "localhost", "port": 5432},
                "app": {"debug": False},
            },
        )

        child = ConfigTemplate(
            name="child",
            description="Child",
            version="1.0",
            settings={
                "database": {"port": 3306},  # 只覆盖 port
                "app": {"debug": True},
            },
            extends="parent",
        )

        merged = child.merge_with_parent(parent)

        assert merged.settings["database"]["host"] == "localhost"  # 继承
        assert merged.settings["database"]["port"] == 3306  # 覆盖
        assert merged.settings["app"]["debug"] is True

    def test_deep_merge_preserves_types(self):
        """测试深度合并保持类型"""
        template = ConfigTemplate(
            name="test", description="Test", version="1.0", settings={}
        )

        base = {"a": 1, "b": [1, 2], "c": {"d": "test"}}
        override = {"b": [3, 4], "c": {"e": "new"}}

        result = template._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"] == [3, 4]  # 覆盖
        assert result["c"]["d"] == "test"  # 保留
        assert result["c"]["e"] == "new"  # 新增

    def test_validate_success(self):
        """测试验证成功"""
        template = ConfigTemplate(
            name="test",
            description="Test",
            version="1.0",
            settings={"app": {"debug": True}},
        )

        errors = template.validate()
        assert len(errors) == 0

    def test_validate_missing_name(self):
        """测试验证失败 - 缺少名称"""
        template = ConfigTemplate(
            name="", description="Test", version="1.0", settings={"app": {}}
        )

        errors = template.validate()
        assert any("名称" in err for err in errors)

    def test_validate_missing_settings(self):
        """测试验证失败 - 缺少配置"""
        template = ConfigTemplate(
            name="test", description="Test", version="1.0", settings={}
        )

        errors = template.validate()
        assert any("配置" in err for err in errors)

    def test_to_dict(self):
        """测试转换为字典"""
        template = ConfigTemplate(
            name="test",
            description="Test",
            version="1.0",
            settings={"app": {"debug": True}},
            tags=["test"],
        )

        data = template.to_dict()

        assert isinstance(data, dict)
        assert data["name"] == "test"
        assert data["settings"] == {"app": {"debug": True}}

    def test_repr(self):
        """测试字符串表示"""
        template = ConfigTemplate(
            name="test", description="Test", version="1.0", tags=["test"]
        )

        repr_str = repr(template)

        assert "test" in repr_str
        assert "1.0" in repr_str
        assert "ConfigTemplate" in repr_str

    def test_merge_tags(self):
        """测试合并标签"""
        parent = ConfigTemplate(
            name="parent",
            description="Parent",
            version="1.0",
            settings={},
            tags=["base", "production"],
        )

        child = ConfigTemplate(
            name="child",
            description="Child",
            version="1.0",
            settings={},
            tags=["custom", "production"],  # 有重复
            extends="parent",
        )

        merged = child.merge_with_parent(parent)

        # 标签应该去重
        assert set(merged.tags) == {"base", "production", "custom"}

    def test_yaml_round_trip(self, tmp_path):
        """测试 YAML 往返（保存后加载）"""
        original = ConfigTemplate(
            name="test",
            description="Test template",
            version="1.0",
            settings={"app": {"debug": True, "log_level": "INFO"}},
            tags=["test", "dev"],
            recommendations=["建议1", "建议2"],
        )

        yaml_file = tmp_path / "roundtrip.yaml"
        original.to_yaml(yaml_file)
        loaded = ConfigTemplate.from_yaml(yaml_file)

        assert loaded.name == original.name
        assert loaded.description == original.description
        assert loaded.version == original.version
        assert loaded.settings == original.settings
        assert loaded.tags == original.tags
        assert loaded.recommendations == original.recommendations
