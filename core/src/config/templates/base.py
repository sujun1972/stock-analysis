#!/usr/bin/env python3
"""
配置模板基础类

提供配置模板的数据结构和基本操作
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
import yaml
import copy


@dataclass
class ConfigTemplate:
    """配置模板

    Attributes:
        name: 模板名称
        description: 模板描述
        version: 模板版本
        extends: 继承的父模板名称（可选）
        settings: 配置内容（字典格式）
        recommendations: 使用建议列表
        tags: 模板标签列表
        author: 作者信息
    """

    name: str
    description: str
    version: str
    settings: Dict[str, Any] = field(default_factory=dict)
    extends: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: str = "Stock-Analysis Team"

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ConfigTemplate":
        """从 YAML 文件加载模板

        Args:
            yaml_path: YAML 文件路径

        Returns:
            ConfigTemplate 实例

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: YAML 格式错误
        """
        if not yaml_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {yaml_path}")

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError(f"无效的模板文件格式: {yaml_path}")

            # 提取必需字段
            name = data.get("name")
            description = data.get("description")
            version = data.get("version")

            if not all([name, description, version]):
                raise ValueError(
                    f"模板缺少必需字段 (name, description, version): {yaml_path}"
                )

            # 创建模板实例
            return cls(
                name=name,
                description=description,
                version=version,
                settings=data.get("settings", {}),
                extends=data.get("extends"),
                recommendations=data.get("recommendations", []),
                tags=data.get("tags", []),
                author=data.get("author", "Stock-Analysis Team"),
            )

        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析错误: {yaml_path}\n{e}")

    def to_yaml(self, yaml_path: Path) -> None:
        """保存为 YAML 文件

        Args:
            yaml_path: 目标文件路径
        """
        data = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "settings": self.settings,
        }

        # 添加可选字段
        if self.extends:
            data["extends"] = self.extends
        if self.recommendations:
            data["recommendations"] = self.recommendations
        if self.tags:
            data["tags"] = self.tags
        if self.author != "Stock-Analysis Team":
            data["author"] = self.author

        # 确保目录存在
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

    def merge_with_parent(self, parent: "ConfigTemplate") -> "ConfigTemplate":
        """与父模板合并

        Args:
            parent: 父模板

        Returns:
            合并后的新模板实例
        """
        # 深度合并配置
        merged_settings = self._deep_merge(parent.settings, self.settings)

        # 创建新实例（保留子模板的元信息）
        return ConfigTemplate(
            name=self.name,
            description=self.description,
            version=self.version,
            settings=merged_settings,
            extends=self.extends,  # 保留继承信息
            recommendations=self.recommendations or parent.recommendations,
            tags=list(set((parent.tags or []) + (self.tags or []))),  # 合并标签
            author=self.author,
        )

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """深度合并两个字典

        Args:
            base: 基础字典
            override: 覆盖字典

        Returns:
            合并后的字典
        """
        result = copy.deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # 递归合并字典
                result[key] = self._deep_merge(result[key], value)
            else:
                # 直接覆盖
                result[key] = copy.deepcopy(value)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            字典表示
        """
        return asdict(self)

    def validate(self) -> List[str]:
        """验证模板的完整性

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 检查必需字段
        if not self.name:
            errors.append("模板名称不能为空")
        if not self.description:
            errors.append("模板描述不能为空")
        if not self.version:
            errors.append("模板版本不能为空")

        # 检查设置不为空
        if not self.settings:
            errors.append("模板配置不能为空")

        # 检查设置结构
        if self.settings and not isinstance(self.settings, dict):
            errors.append("模板配置必须是字典格式")

        return errors

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"ConfigTemplate(name={self.name!r}, "
            f"version={self.version!r}, "
            f"tags={self.tags})"
        )
