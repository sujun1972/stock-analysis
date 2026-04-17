"""
AI 输出解析工具

提供统一的 JSON 提取 + Pydantic 验证流程，替代各 Service 中分散的正则 JSON 提取。
失败时降级为原有正则方式，确保向后兼容。

用法示例:
    from app.services.ai_output_parser import parse_ai_json
    from app.schemas.ai_analysis_result import SentimentAnalysisResult

    result = parse_ai_json(ai_response_text, SentimentAnalysisResult)
    if result is not None:
        # 强类型对象
        print(result.space_analysis)
    else:
        # 降级处理
        ...
"""

import json
import re
from typing import Optional, Type, TypeVar

from loguru import logger
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# markdown ```json ... ``` 代码块提取
_JSON_BLOCK_PATTERN = re.compile(r'```json\s*(\{[\s\S]*?\})\s*```')

# 去掉 markdown 标识（非捕获组版本）
_LEADING_MD = re.compile(r'^```(?:json)?\s*\n?', re.MULTILINE)
_TRAILING_MD = re.compile(r'\n?```\s*$', re.MULTILINE)


def extract_json_text(ai_response: str) -> Optional[str]:
    """
    从 AI 响应中提取纯 JSON 文本。

    优先匹配 ```json ... ``` 代码块，
    其次尝试去掉首尾 markdown 标识后直接解析。

    Returns:
        JSON 文本字符串，或 None（提取失败）
    """
    if not ai_response or not isinstance(ai_response, str):
        return None

    # 策略1: ```json { ... } ``` 代码块
    matches = _JSON_BLOCK_PATTERN.findall(ai_response)
    if matches:
        return matches[0]

    # 策略2: 去掉首尾 ``` 标识
    cleaned = _LEADING_MD.sub('', ai_response.strip())
    cleaned = _TRAILING_MD.sub('', cleaned.strip()).strip()

    # 验证是否可解析为 JSON
    try:
        json.loads(cleaned)
        return cleaned
    except (json.JSONDecodeError, ValueError):
        pass

    # 策略3: 尝试直接解析原文
    try:
        json.loads(ai_response.strip())
        return ai_response.strip()
    except (json.JSONDecodeError, ValueError):
        pass

    # 策略4: 修复 AI 常见的不完整 JSON（缺少闭合花括号/方括号）
    repaired = _try_repair_json(cleaned)
    if repaired is not None:
        return repaired

    return None


def _try_repair_json(text: str) -> Optional[str]:
    """尝试修复 AI 输出中缺少闭合花括号/方括号的不完整 JSON。

    AI 模型（尤其长输出时）经常截断最后的 } 或 ]，
    导致花括号/方括号不配对。此函数通过补全缺失的闭合符号来修复。
    """
    if not text or not text.strip().startswith('{'):
        return None

    # 计算结构性花括号/方括号的嵌套深度（跳过字符串内部的）
    open_stack = []  # 记录未闭合的开括号类型
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                open_stack.append('}')
            elif ch == '[':
                open_stack.append(']')
            elif ch in ('}', ']'):
                if open_stack and open_stack[-1] == ch:
                    open_stack.pop()

    if not open_stack:
        return None  # 已经配对完整，无需修复

    # 最多补 3 个闭合符号（避免对完全损坏的文本做大手术）
    if len(open_stack) > 3:
        logger.warning(f"JSON 缺失 {len(open_stack)} 个闭合符号，超过修复阈值，跳过")
        return None

    # 补全缺失的闭合符号（逆序：最内层先关闭）
    suffix = '\n' + '\n'.join(reversed(open_stack))
    repaired = text + suffix

    try:
        json.loads(repaired)
        logger.info(f"JSON 自动修复成功：补全了 {len(open_stack)} 个闭合符号 {''.join(reversed(open_stack))}")
        return repaired
    except (json.JSONDecodeError, ValueError):
        logger.debug(f"JSON 修复后仍无法解析，放弃")
        return None


def parse_ai_json(
    ai_response: str,
    model_class: Type[T],
) -> Optional[T]:
    """
    从 AI 响应中提取 JSON 并解析为 Pydantic 模型。

    Args:
        ai_response: AI 返回的原始文本
        model_class: 目标 Pydantic 模型类

    Returns:
        解析成功返回 Pydantic 模型实例，失败返回 None
    """
    json_text = extract_json_text(ai_response)
    if json_text is None:
        logger.debug(f"[ai_output_parser] 无法从 AI 响应中提取 JSON 文本")
        return None

    try:
        data = json.loads(json_text)
        result = model_class.model_validate(data)
        logger.info(f"[ai_output_parser] 成功解析为 {model_class.__name__}")
        return result
    except Exception as e:
        logger.warning(
            f"[ai_output_parser] Pydantic 解析失败 ({model_class.__name__}): {e}，"
            f"将降级为原始 JSON"
        )
        return None


def parse_ai_json_or_dict(ai_response: str) -> Optional[dict]:
    """
    从 AI 响应中提取 JSON 为 dict，不做 Pydantic 校验。
    用于不需要强类型但需要统一 JSON 提取的场景。

    Returns:
        解析成功返回 dict，失败返回 None
    """
    json_text = extract_json_text(ai_response)
    if json_text is None:
        return None
    try:
        return json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return None


def get_format_instructions(model_class: Type[BaseModel]) -> str:
    """
    生成 LangChain 风格的格式指令，附加到 prompt 末尾。

    Args:
        model_class: Pydantic 模型类

    Returns:
        格式指令文本
    """
    schema = model_class.model_json_schema()
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

    return (
        "\n\n---\n"
        "【输出格式要求】\n"
        "请严格按照以下 JSON Schema 格式输出，不要包含任何额外文字，"
        "只输出纯 JSON（可用 ```json ``` 包裹）：\n"
        f"```json\n{schema_str}\n```"
    )
