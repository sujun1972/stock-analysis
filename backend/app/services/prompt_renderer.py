"""
提示词渲染引擎

支持Jinja2模板语法，用于渲染提示词模板中的占位符

作者: Backend Team
创建时间: 2026-03-11
"""

import re
from typing import Dict, Any, List, Set
from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError
from loguru import logger

from app.schemas.llm_prompt_template import PromptRenderError


class PromptRenderer:
    """提示词渲染引擎"""

    def __init__(self):
        """初始化Jinja2环境"""
        self.jinja_env = Environment(
            undefined=StrictUndefined,  # 变量缺失时报错
            autoescape=False,  # 不自动转义（我们不是渲染HTML）
            trim_blocks=True,  # 移除块后的第一个换行
            lstrip_blocks=True  # 移除块前的空白
        )

    def render(
        self,
        template_str: str,
        variables: Dict[str, Any],
        required_vars: List[str] = None
    ) -> str:
        """
        渲染模板

        Args:
            template_str: 模板字符串（支持Jinja2语法）
            variables: 变量字典
            required_vars: 必填变量列表（可选）

        Returns:
            渲染后的字符串

        Raises:
            PromptRenderError: 渲染失败或缺少必填变量
        """
        try:
            # 1. 验证必填变量
            if required_vars:
                missing = set(required_vars) - set(variables.keys())
                if missing:
                    raise PromptRenderError(f"缺少必填变量: {', '.join(missing)}")

            # 2. 渲染模板
            template = self.jinja_env.from_string(template_str)
            rendered = template.render(**variables)

            return rendered

        except UndefinedError as e:
            logger.error(f"模板渲染失败 - 变量未定义: {e}")
            raise PromptRenderError(f"模板中使用了未定义的变量: {e}")

        except TemplateSyntaxError as e:
            logger.error(f"模板渲染失败 - 语法错误: {e}")
            raise PromptRenderError(f"模板语法错误 (行{e.lineno}): {e.message}")

        except Exception as e:
            logger.error(f"模板渲染失败 - 未知错误: {e}")
            raise PromptRenderError(f"模板渲染失败: {str(e)}")

    def extract_variables(self, template_str: str) -> Set[str]:
        """
        从模板字符串中提取所有变量名

        Args:
            template_str: 模板字符串

        Returns:
            变量名集合
        """
        try:
            # 使用Jinja2解析模板
            parsed = self.jinja_env.parse(template_str)

            # 提取所有未声明的变量（即需要外部传入的变量）
            variables = set()
            for node in parsed.find_all():
                if hasattr(node, 'name') and isinstance(node.name, str):
                    variables.add(node.name)

            return variables

        except TemplateSyntaxError as e:
            logger.warning(f"提取变量失败 - 模板语法错误: {e}")
            # 回退到正则表达式方式
            return self._extract_variables_regex(template_str)

        except Exception as e:
            logger.warning(f"提取变量失败 - 未知错误: {e}")
            return self._extract_variables_regex(template_str)

    def _extract_variables_regex(self, template_str: str) -> Set[str]:
        """
        使用正则表达式提取变量（回退方案）

        Args:
            template_str: 模板字符串

        Returns:
            变量名集合
        """
        # 匹配 {{ variable_name }} 或 {% variable_name %}
        pattern = r'\{\{[\s]*([a-zA-Z_][a-zA-Z0-9_]*)[\s]*\}\}|\{%[\s]*([a-zA-Z_][a-zA-Z0-9_]*)[\s]*%\}'
        matches = re.findall(pattern, template_str)

        variables = set()
        for match in matches:
            # match是元组，取非空的组
            var_name = match[0] or match[1]
            if var_name:
                variables.add(var_name)

        return variables

    def validate_template(self, template_str: str) -> tuple[bool, str]:
        """
        验证模板语法是否正确

        Args:
            template_str: 模板字符串

        Returns:
            (是否有效, 错误消息)
        """
        try:
            # 尝试解析模板
            self.jinja_env.from_string(template_str)
            return True, ""

        except TemplateSyntaxError as e:
            return False, f"语法错误 (行{e.lineno}): {e.message}"

        except Exception as e:
            return False, f"验证失败: {str(e)}"

    def preview_render(
        self,
        template_str: str,
        variables: Dict[str, Any],
        required_vars: List[str] = None
    ) -> Dict[str, Any]:
        """
        预览渲染结果（包含诊断信息）

        Args:
            template_str: 模板字符串
            variables: 变量字典
            required_vars: 必填变量列表

        Returns:
            {
                "success": bool,
                "rendered": str,  # 渲染结果（如果成功）
                "error": str,  # 错误信息（如果失败）
                "missing_variables": List[str],  # 缺失的必填变量
                "extra_variables": List[str],  # 多余的变量
                "template_variables": List[str]  # 模板中的所有变量
            }
        """
        result = {
            "success": False,
            "rendered": "",
            "error": "",
            "missing_variables": [],
            "extra_variables": [],
            "template_variables": []
        }

        try:
            # 1. 提取模板中的变量
            template_vars = self.extract_variables(template_str)
            result["template_variables"] = sorted(list(template_vars))

            # 2. 检查缺失的变量
            if required_vars:
                required_set = set(required_vars)
                provided_set = set(variables.keys())
                missing = required_set - provided_set
                if missing:
                    result["missing_variables"] = sorted(list(missing))

            # 3. 检查多余的变量
            provided_set = set(variables.keys())
            extra = provided_set - template_vars
            if extra:
                result["extra_variables"] = sorted(list(extra))

            # 4. 渲染
            rendered = self.render(template_str, variables, required_vars)
            result["success"] = True
            result["rendered"] = rendered

        except PromptRenderError as e:
            result["error"] = str(e)

        except Exception as e:
            result["error"] = f"预览失败: {str(e)}"

        return result


# 全局单例
_prompt_renderer_instance = None


def get_prompt_renderer() -> PromptRenderer:
    """获取提示词渲染器单例"""
    global _prompt_renderer_instance
    if _prompt_renderer_instance is None:
        _prompt_renderer_instance = PromptRenderer()
    return _prompt_renderer_instance
