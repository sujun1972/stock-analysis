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

# markdown ```json ... ``` 代码块提取（贪婪匹配，确保捕获到最外层 }）
_JSON_BLOCK_PATTERN = re.compile(r'```json\s*(\{[\s\S]*\})\s*```')

# 去掉 markdown 标识（非捕获组版本）
_LEADING_MD = re.compile(r'^```(?:json)?\s*\n?', re.MULTILINE)
_TRAILING_MD = re.compile(r'\n?```\s*$', re.MULTILINE)

# AI 专家分析 JSON 中预期出现在顶层（depth=1）的关键字段，
# 用于 _repair_misplaced_keys 检测嵌套错位
_EXPECTED_TOP_KEYS = {
    "expert_identity", "stock_target", "analysis_date",
    "probability_metrics", "dimensions", "trading_strategy",
    "final_score", "comprehensive_score", "score",
    "macro_environment", "risk_factors", "investment_suggestion",
}


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
        candidate = matches[0]
        try:
            json.loads(candidate)
            return candidate
        except (json.JSONDecodeError, ValueError):
            # 代码块内 JSON 不合法，尝试修复
            repaired = _try_repair_json(candidate)
            if repaired is not None:
                return repaired
            return candidate  # 返回原文，让调用方决定降级

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

    # 策略4: 修复 AI 常见的不完整 JSON
    repaired = _try_repair_json(cleaned)
    if repaired is not None:
        return repaired

    return None


def _try_repair_json(text: str) -> Optional[str]:
    """尝试修复 AI 输出中结构损坏的 JSON。

    处理两类常见错误：
    1. 中间遗漏：嵌套对象缺少闭合 }，导致后续同级字段被错误嵌入上级对象
    2. 末尾截断：AI 输出被截断，缺少最后的 } 或 ]
    """
    if not text or not text.strip().startswith('{'):
        return None

    # 优先尝试中间修复（检测顶层 key 出现在错误深度）
    mid_repaired = _repair_misplaced_keys(text)
    if mid_repaired is not None:
        return mid_repaired

    # 再尝试纯末尾补全
    return _repair_trailing(text)


def _repair_trailing(text: str) -> Optional[str]:
    """在末尾补全缺失的闭合符号（最多 3 个）。"""
    open_stack = []
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
        return None

    if len(open_stack) > 3:
        logger.warning(f"JSON 缺失 {len(open_stack)} 个闭合符号，超过修复阈值，跳过")
        return None

    suffix = '\n' + '\n'.join(reversed(open_stack))
    repaired = text + suffix

    try:
        json.loads(repaired)
        logger.info(f"JSON 末尾修复成功：补全了 {''.join(reversed(open_stack))}")
        return repaired
    except (json.JSONDecodeError, ValueError):
        logger.debug("JSON 末尾修复后仍无法解析，放弃")
        return None


def _repair_misplaced_keys(text: str) -> Optional[str]:
    """通过深度追踪检测并修复中间缺失的闭合 }。

    典型场景：AI 生成嵌套 JSON 时漏掉父对象的 }，例如：
        "dimensions": {
            "sentiment_index": { ... }    ← 正确关闭了子对象
        ←── 这里漏掉了 dimensions 的 }
        "trading_strategy": { ... }       ← 被错误地归入 dimensions

    算法：逐字符扫描并维护括号深度，当发现 _EXPECTED_TOP_KEYS 中的 key
    出现在 depth > 1 时，定位其前方的逗号并插入缺失的 }。
    """
    depth = 0
    in_string = False
    escape_next = False
    insertions: list[tuple[int, int]] = []  # (comma_pos, missing_brace_count)
    i = 0

    while i < len(text):
        ch = text[i]

        if escape_next:
            escape_next = False
            i += 1
            continue
        if ch == '\\' and in_string:
            escape_next = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                in_string = True
                # 尝试提取 key 名（快速查找闭合引号，key 名不含转义引号）
                end_quote = text.find('"', i + 1)
                if end_quote > 0:
                    key = text[i + 1:end_quote]
                    rest = text[end_quote + 1:].lstrip()
                    if rest.startswith(':') and key in _EXPECTED_TOP_KEYS and depth > 1:
                        missing = depth - 1
                        # 向前跳过空白找到分隔逗号
                        scan = i - 1
                        while scan >= 0 and text[scan] in ' \t\n\r':
                            scan -= 1
                        if scan >= 0 and text[scan] == ',':
                            insertions.append((scan, missing))
                            depth -= missing
            else:
                in_string = False
            i += 1
            continue

        if not in_string:
            if ch in ('{', '['):
                depth += 1
            elif ch in ('}', ']'):
                depth -= 1

        i += 1

    if not insertions:
        return None

    # 从后向前插入以保持前面的位置索引不偏移
    fixed = text
    for comma_pos, _ in reversed(insertions):
        line_start = fixed.rfind('\n', 0, comma_pos) + 1
        indent = ''
        for ch in fixed[line_start:comma_pos]:
            if ch in ' \t':
                indent += ch
            else:
                break
        # 在逗号前插入 }，逗号保留给下一个 key
        fixed = fixed[:comma_pos] + '}\n' + indent + fixed[comma_pos:]

    try:
        json.loads(fixed)
        logger.info(f"JSON 中间修复成功：在 {len(insertions)} 处插入了缺失的 }}")
        return fixed
    except (json.JSONDecodeError, ValueError):
        pass

    # 中间修复后仍需末尾补全的情况
    result = _repair_trailing(fixed)
    if result is not None:
        logger.info("JSON 中间+末尾联合修复成功")
        return result

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
        logger.debug("[ai_output_parser] 无法从 AI 响应中提取 JSON 文本")
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
