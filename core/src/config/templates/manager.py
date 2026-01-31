#!/usr/bin/env python3
"""
配置模板管理器

提供模板的加载、应用、导出和对比功能
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import shutil
import copy

from loguru import logger

from .base import ConfigTemplate


class ConfigTemplateManager:
    """配置模板管理器

    负责管理配置模板的生命周期，包括加载、应用、导出、对比等操作
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """初始化模板管理器

        Args:
            templates_dir: 模板目录路径，默认使用内置预设目录
        """
        if templates_dir is None:
            # 使用内置预设模板目录
            templates_dir = Path(__file__).parent / "presets"

        self.templates_dir = Path(templates_dir)
        self._cache: Dict[str, ConfigTemplate] = {}

        # 确保模板目录存在
        if not self.templates_dir.exists():
            logger.warning(f"模板目录不存在: {self.templates_dir}")
            self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> List[ConfigTemplate]:
        """列出所有可用模板

        Returns:
            模板列表，按名称排序
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        for yaml_file in sorted(self.templates_dir.glob("*.yaml")):
            try:
                template = ConfigTemplate.from_yaml(yaml_file)
                templates.append(template)
            except Exception as e:
                logger.error(f"加载模板失败: {yaml_file}\n{e}")

        return templates

    def load_template(self, name: str) -> ConfigTemplate:
        """加载指定模板

        Args:
            name: 模板名称（不含 .yaml 后缀）

        Returns:
            加载的模板实例

        Raises:
            ValueError: 模板不存在或加载失败
        """
        # 1. 检查缓存
        if name in self._cache:
            logger.debug(f"从缓存加载模板: {name}")
            return self._cache[name]

        # 2. 从文件加载
        yaml_file = self.templates_dir / f"{name}.yaml"
        if not yaml_file.exists():
            raise ValueError(f"模板不存在: {name}")

        try:
            template = ConfigTemplate.from_yaml(yaml_file)
            logger.debug(f"从文件加载模板: {name}")

            # 3. 处理继承
            if template.extends:
                logger.debug(f"模板 {name} 继承自 {template.extends}")
                parent = self.load_template(template.extends)
                template = template.merge_with_parent(parent)

            # 4. 缓存
            self._cache[name] = template

            return template

        except Exception as e:
            raise ValueError(f"加载模板失败: {name}\n{e}")

    def apply_template(
        self,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        env_path: Optional[Path] = None,
    ) -> str:
        """应用模板到配置文件

        Args:
            name: 模板名称
            overrides: 配置覆盖（可选）
            dry_run: 是否仅预览，不实际写入
            env_path: .env 文件路径，默认为当前目录

        Returns:
            生成的 .env 文件内容

        Raises:
            ValueError: 模板不存在或应用失败
        """
        # 1. 加载模板
        template = self.load_template(name)

        # 2. 准备配置
        settings = copy.deepcopy(template.settings)

        # 3. 应用覆盖
        if overrides:
            settings = self._deep_merge(settings, overrides)

        # 4. 生成 .env 内容
        env_content = self._generate_env_content(settings, template)

        # 5. 如果是预览模式，直接返回
        if dry_run:
            return env_content

        # 6. 写入文件
        if env_path is None:
            env_path = Path.cwd() / ".env"

        # 备份现有文件
        if env_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = env_path.with_suffix(f".env.backup_{timestamp}")
            shutil.copy(env_path, backup_path)
            logger.info(f"已备份现有配置: {backup_path}")

        # 写入新配置
        env_path.write_text(env_content, encoding="utf-8")
        logger.success(f"已应用模板: {name} -> {env_path}")

        return env_content

    def export_current_as_template(
        self,
        name: str,
        description: str,
        env_path: Optional[Path] = None,
        version: str = "1.0",
        tags: Optional[List[str]] = None,
    ) -> Path:
        """导出当前配置为模板

        Args:
            name: 模板名称
            description: 模板描述
            env_path: .env 文件路径，默认为当前目录
            version: 模板版本
            tags: 模板标签

        Returns:
            导出的模板文件路径

        Raises:
            ValueError: .env 文件不存在或解析失败
        """
        # 1. 确定 .env 文件路径
        if env_path is None:
            env_path = Path.cwd() / ".env"

        if not env_path.exists():
            raise ValueError(f".env 文件不存在: {env_path}")

        # 2. 解析 .env 文件
        settings = self._parse_env_file(env_path)

        # 3. 创建模板
        template = ConfigTemplate(
            name=name,
            description=description,
            version=version,
            settings=settings,
            tags=tags or [],
        )

        # 4. 保存模板
        template_path = self.templates_dir / f"{name}.yaml"
        template.to_yaml(template_path)

        logger.success(f"已导出模板: {template_path}")
        return template_path

    def import_template(self, file_path: Path) -> str:
        """导入外部模板

        Args:
            file_path: 外部模板文件路径

        Returns:
            导入后的模板名称

        Raises:
            ValueError: 文件不存在或导入失败
        """
        if not file_path.exists():
            raise ValueError(f"模板文件不存在: {file_path}")

        # 验证模板格式
        try:
            template = ConfigTemplate.from_yaml(file_path)
        except Exception as e:
            raise ValueError(f"无效的模板文件: {file_path}\n{e}")

        # 复制到模板目录
        template_name = file_path.stem  # 文件名（不含扩展名）
        dest_path = self.templates_dir / file_path.name

        shutil.copy(file_path, dest_path)
        logger.success(f"已导入模板: {dest_path}")

        # 清除缓存（如果存在）
        if template_name in self._cache:
            del self._cache[template_name]

        return template_name

    def diff_templates(self, name1: str, name2: str) -> Dict[str, Any]:
        """对比两个模板

        Args:
            name1: 第一个模板名称
            name2: 第二个模板名称

        Returns:
            差异信息字典
        """
        template1 = self.load_template(name1)
        template2 = self.load_template(name2)

        diff_result = {
            "template1": name1,
            "template2": name2,
            "version_diff": {
                "template1": template1.version,
                "template2": template2.version,
            },
            "settings_diff": self._diff_dicts(template1.settings, template2.settings),
        }

        return diff_result

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
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)

        return result

    def _generate_env_content(
        self, settings: dict, template: ConfigTemplate
    ) -> str:
        """生成 .env 文件内容

        Args:
            settings: 配置字典
            template: 模板实例（用于添加注释）

        Returns:
            .env 文件内容
        """
        lines = [
            "# Stock-Analysis 配置文件",
            f"# 模板: {template.name}",
            f"# 版本: {template.version}",
            f"# 生成时间: {datetime.now().isoformat()}",
            "",
        ]

        # 配置分组
        groups = {
            "app": "应用配置",
            "database": "数据库配置",
            "data_source": "数据源配置",
            "paths": "路径配置",
            "ml": "机器学习配置",
            "performance": "性能配置",
            "features": "特征工程配置",
            "strategies": "策略配置",
            "backtest": "回测配置",
            "training": "训练配置",
            "monitoring": "监控配置",
        }

        for group_key, group_name in groups.items():
            if group_key in settings:
                lines.append("")
                lines.append(f"# ==================== {group_name} ====================")

                group_settings = settings[group_key]
                if isinstance(group_settings, dict):
                    self._add_settings_to_lines(lines, group_key, group_settings)

        # 添加建议
        if template.recommendations:
            lines.append("")
            lines.append("# ==================== 配置建议 ====================")
            for i, rec in enumerate(template.recommendations, 1):
                lines.append(f"# {i}. {rec}")

        return "\n".join(lines) + "\n"

    def _add_settings_to_lines(
        self, lines: List[str], prefix: str, settings: dict, level: int = 0
    ) -> None:
        """递归添加配置到行列表

        Args:
            lines: 行列表
            prefix: 环境变量前缀
            settings: 配置字典
            level: 嵌套层级
        """
        for key, value in settings.items():
            if isinstance(value, dict):
                # 嵌套配置：添加注释分组
                if level == 0:
                    lines.append(f"# {key}")
                self._add_settings_to_lines(lines, f"{prefix}_{key}", value, level + 1)
            else:
                # 叶子节点：生成环境变量
                env_key = f"{prefix.upper()}_{key.upper()}"
                env_value = self._format_env_value(value)
                lines.append(f"{env_key}={env_value}")

    def _format_env_value(self, value: Any) -> str:
        """格式化环境变量值

        Args:
            value: 原始值

        Returns:
            格式化后的字符串
        """
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # 保留变量引用格式（如 ${VAR}）
            return value
        elif isinstance(value, list):
            # 列表转为逗号分隔字符串
            return ",".join(str(item) for item in value)
        else:
            return str(value)

    def _parse_env_file(self, env_path: Path) -> dict:
        """解析 .env 文件

        Args:
            env_path: .env 文件路径

        Returns:
            配置字典
        """
        settings = {}

        try:
            from dotenv import dotenv_values

            env_vars = dotenv_values(env_path)
        except ImportError:
            # 手动解析
            env_vars = {}
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

        # 转换为分组格式
        for key, value in env_vars.items():
            if "_" in key:
                parts = key.split("_")
                group = parts[0].lower()
                setting_parts = parts[1:]

                if group not in settings:
                    settings[group] = {}

                # 处理嵌套配置
                current = settings[group]
                for part in setting_parts[:-1]:
                    part_lower = part.lower()
                    if part_lower not in current:
                        current[part_lower] = {}
                    current = current[part_lower]

                # 设置最终值
                final_key = setting_parts[-1].lower()
                current[final_key] = self._parse_env_value(value)

        return settings

    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值

        Args:
            value: 字符串值

        Returns:
            解析后的值（保持原始类型）
        """
        # 布尔值
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # 数字
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # 列表（逗号分隔）
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # 字符串
        return value

    def _diff_dicts(
        self, dict1: dict, dict2: dict, path: str = ""
    ) -> Dict[str, Any]:
        """对比两个字典的差异

        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            path: 当前路径（用于嵌套）

        Returns:
            差异字典
        """
        diff = {"added": {}, "removed": {}, "changed": {}, "unchanged": {}}

        all_keys = set(dict1.keys()) | set(dict2.keys())

        for key in all_keys:
            current_path = f"{path}.{key}" if path else key

            if key not in dict1:
                diff["added"][current_path] = dict2[key]
            elif key not in dict2:
                diff["removed"][current_path] = dict1[key]
            elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                # 递归比较嵌套字典
                nested_diff = self._diff_dicts(dict1[key], dict2[key], current_path)
                # 合并结果
                for category in diff.keys():
                    diff[category].update(nested_diff[category])
            elif dict1[key] != dict2[key]:
                diff["changed"][current_path] = {
                    "from": dict1[key],
                    "to": dict2[key],
                }
            else:
                diff["unchanged"][current_path] = dict1[key]

        return diff

    def clear_cache(self) -> None:
        """清除模板缓存"""
        self._cache.clear()
        logger.debug("已清除模板缓存")
