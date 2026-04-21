"""舆情情绪打分 Service：对 stock_anns / news_flash 批量打情绪 + 标签。

调用链：
  Service.run_batch_anns / run_batch_news
    → Repository.get_unscored_batch（未打分记录，~30 条/批）
    → PromptTemplateService.render_template（llm_prompt_templates 数据库驱动）
    → AIStrategyService.get_provider_config + create_client
    → LangChainClient.generate_strategy（单次 LLM 调用，返回 JSON 数组）
    → 解析并归一化 → Repository.bulk_update_scores 回写
    → 全程走 LLMCallLogger（admin 的 LLM 调用日志页面可见）

降级：整批 JSON 解析失败时跳过下次重试；单条字段不合法时仅丢弃该条。
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date as date_type, datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.news_flash_repository import NewsFlashRepository
from app.repositories.stock_anns_repository import StockAnnsRepository
from app.schemas.llm_call_log import BusinessType, CallStatus
from app.services.ai_service import AIStrategyService
from app.services.llm_call_logger import llm_call_logger
from app.services.prompt_template_service import get_prompt_template_service


DEFAULT_BATCH_SIZE = 30

# 事件标签枚举（与 Prompt 模板对齐）
VALID_EVENT_TAGS = {
    '减持', '增持', '回购', '业绩预增', '业绩预减',
    '诉讼', '重组', '股权激励', '可转债', '定增',
    '分红派息', '资产出售', '合同订单', '其他',
}
VALID_SENTIMENT_IMPACTS = {'bullish', 'bearish', 'neutral'}


# ============================================================================
# JSON 数组解析辅助
# ============================================================================

_JSON_ARRAY_FENCE = re.compile(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", re.DOTALL)


def _extract_json_array(text: str) -> Optional[list]:
    """从 LLM 响应中提取 JSON 数组。

    策略：① ```json [...] ``` 围栏；② 首个 [ 到最后 ] 的切片；③ 原文。
    任一策略成功即返回。
    """
    if not text or not isinstance(text, str):
        return None

    # 策略 1：围栏
    m = _JSON_ARRAY_FENCE.search(text)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # 策略 2：首 [ 到最后 ]
    lbr = text.find('[')
    rbr = text.rfind(']')
    if 0 <= lbr < rbr:
        candidate = text[lbr:rbr + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # 策略 3：原文
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    return None


# ============================================================================
# 归一化单条评分字段
# ============================================================================

def _clamp_score(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return max(-1.0, min(1.0, f))


def _normalize_impact(v: Any, score: Optional[float]) -> Optional[str]:
    """规范化 sentiment_impact；若 LLM 给的不在枚举内，按 score 兜底。"""
    if isinstance(v, str) and v.lower() in VALID_SENTIMENT_IMPACTS:
        return v.lower()
    if score is None:
        return 'neutral'
    if score >= 0.3:
        return 'bullish'
    if score <= -0.3:
        return 'bearish'
    return 'neutral'


def _normalize_event_tags(v: Any) -> Optional[List[str]]:
    """取前 2 个合法事件标签；都不合法则返回 ['其他']。"""
    if not v:
        return ['其他']
    tags = v if isinstance(v, list) else [v]
    out: List[str] = []
    for t in tags:
        if isinstance(t, str) and t in VALID_EVENT_TAGS:
            if t not in out:
                out.append(t)
        if len(out) >= 2:
            break
    return out if out else ['其他']


def _normalize_theme_tags(v: Any) -> Optional[List[str]]:
    """取前 3 个主题标签；无则返回 None（快讯无硬枚举）。"""
    if not v:
        return None
    tags = v if isinstance(v, list) else [v]
    out = [str(t).strip() for t in tags if t and str(t).strip()]
    return out[:3] if out else None


# ============================================================================
# SentimentScoringService
# ============================================================================

class SentimentScoringService:
    """公告 / 快讯批量舆情打分服务。"""

    ANNS_TEMPLATE_KEY = 'anns_sentiment_v1'
    NEWS_TEMPLATE_KEY = 'news_flash_sentiment_v1'

    def __init__(self) -> None:
        self.ai_strategy = AIStrategyService()
        self.anns_repo = StockAnnsRepository()
        self.news_repo = NewsFlashRepository()

    # ---- 公告 ----

    async def run_batch_anns(
        self,
        limit: int = DEFAULT_BATCH_SIZE,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """扫描未打分的公告，取一个批次送 LLM 打分。

        返回：{'status', 'taken', 'scored', 'skipped', 'error'}
        """
        return await self._run_batch(
            kind='anns',
            template_key=self.ANNS_TEMPLATE_KEY,
            fetch_fn=self.anns_repo.get_unscored_batch,
            build_variables_fn=self._build_anns_variables,
            normalize_item_fn=self._normalize_anns_score_item,
            write_fn=self.anns_repo.bulk_update_scores,
            limit=limit,
            provider=provider,
        )

    # ---- 快讯 ----

    async def run_batch_news(
        self,
        limit: int = DEFAULT_BATCH_SIZE,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._run_batch(
            kind='news',
            template_key=self.NEWS_TEMPLATE_KEY,
            fetch_fn=self.news_repo.get_unscored_batch,
            build_variables_fn=self._build_news_variables,
            normalize_item_fn=self._normalize_news_score_item,
            write_fn=self.news_repo.bulk_update_scores,
            limit=limit,
            provider=provider,
        )

    # ---- 通用批次骨架 ----

    async def _run_batch(
        self,
        kind: str,
        template_key: str,
        fetch_fn,
        build_variables_fn,
        normalize_item_fn,
        write_fn,
        limit: int,
        provider: Optional[str],
    ) -> Dict[str, Any]:
        items = await asyncio.to_thread(fetch_fn, limit)
        if not items:
            logger.info(f"[sentiment_scoring] {kind}: 无未打分记录")
            return {"status": "noop", "taken": 0, "scored": 0, "skipped": 0}

        logger.info(f"[sentiment_scoring] {kind}: 取 {len(items)} 条待打分")

        db: Session = next(get_db())
        call_id: Optional[str] = None
        start_log_time: Optional[datetime] = None

        try:
            # 1) 加载 Prompt 模板 + 提供商配置
            template, provider_config = await asyncio.to_thread(
                self._prepare_prompt_context, db, template_key, provider
            )

            # 2) 渲染 Prompt
            variables = build_variables_fn(items)
            system_prompt, user_prompt = await asyncio.to_thread(
                get_prompt_template_service().render_template,
                db, template.id, variables,
            )

            # 3) 记录 LLM 调用日志（调用前）
            call_parameters = {
                "temperature": provider_config.get("temperature", 0.2),
                "max_tokens": provider_config.get("max_tokens", 4000),
                "timeout": provider_config.get("timeout", 60),
                "batch_size": len(items),
                "template_key": template_key,
                "kind": kind,
            }
            full_prompt_for_log = (
                f"[system]\n{system_prompt}\n\n[user]\n{user_prompt}"
                if system_prompt else user_prompt
            )
            try:
                call_id, start_log_time = llm_call_logger.create_log_entry(
                    db=db,
                    business_type=BusinessType.SENTIMENT_SCORING,
                    provider=provider_config.get("provider"),
                    model_name=provider_config.get("model_name"),
                    call_parameters=call_parameters,
                    prompt_text=full_prompt_for_log,
                    caller_service="SentimentScoringService",
                    caller_function=f"run_batch_{kind}",
                    business_date=date_type.today(),
                    is_scheduled=True,
                )
            except Exception as e:
                logger.warning(f"[sentiment_scoring] 创建 LLM 日志失败（不影响主流程）: {e}")

            # 4) 调用 LLM
            client = self.ai_strategy.create_client(provider_config.get("provider"), provider_config)
            response_text, tokens_used = await client.generate_strategy(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # 5) 解析 JSON 数组
            parsed_array = _extract_json_array(response_text)
            if parsed_array is None:
                # 整批解析失败
                self._mark_log_failure(db, call_id, start_log_time,
                                        CallStatus.FAILED,
                                        error_code="JSON_PARSE_FAILED",
                                        error_message=f"LLM 返回无法解析为 JSON 数组 (length={len(response_text)})")
                logger.warning(f"[sentiment_scoring] {kind} JSON 解析失败，整批跳过")
                return {
                    "status": "parse_failed", "taken": len(items), "scored": 0,
                    "skipped": len(items), "error": "JSON parse failed",
                    "call_id": call_id,
                }

            # 6) 归一化并写回
            id_index: Dict[str, Dict[str, Any]] = {str(it['id']): it for it in items}
            score_model = f"{provider_config.get('provider')}/{provider_config.get('model_name')}"
            scores_to_write: List[Dict[str, Any]] = []
            for raw in parsed_array:
                if not isinstance(raw, dict):
                    continue
                item_id = raw.get('id')
                if item_id is None:
                    continue
                source_item = id_index.get(str(item_id))
                if source_item is None:
                    continue
                normalized = normalize_item_fn(raw, source_item, score_model)
                if normalized is None:
                    continue
                scores_to_write.append(normalized)

            scored = 0
            if scores_to_write:
                scored = await asyncio.to_thread(write_fn, scores_to_write)
            skipped = len(items) - len(scores_to_write)

            # 7) 更新 LLM 日志为成功
            if call_id and start_log_time:
                try:
                    llm_call_logger.update_log_success(
                        db=db,
                        call_id=call_id,
                        start_time=start_log_time,
                        response_text=response_text,
                        parsed_result={
                            "scored_count": scored,
                            "skipped_count": skipped,
                            "items_preview": parsed_array[:3],
                        },
                        tokens_total=tokens_used,
                    )
                except Exception as e:
                    logger.warning(f"[sentiment_scoring] 更新 LLM 日志失败: {e}")

            logger.info(
                f"[sentiment_scoring] {kind}: taken={len(items)} scored={scored} skipped={skipped}"
            )
            return {
                "status": "success",
                "taken": len(items),
                "scored": scored,
                "skipped": skipped,
                "tokens_used": tokens_used,
                "call_id": call_id,
            }

        except Exception as e:
            logger.error(f"[sentiment_scoring] {kind} 运行失败: {e}", exc_info=True)
            self._mark_log_failure(db, call_id, start_log_time,
                                    CallStatus.FAILED,
                                    error_code=type(e).__name__,
                                    error_message=str(e))
            return {
                "status": "error", "taken": len(items), "scored": 0,
                "skipped": len(items), "error": str(e),
                "call_id": call_id,
            }
        finally:
            db.close()

    # ---- Prompt / Provider 准备 ----

    def _prepare_prompt_context(
        self,
        db: Session,
        template_key: str,
        provider: Optional[str],
    ) -> Tuple[Any, Dict[str, Any]]:
        """同步方法：加载模板 + 解析 provider 配置。

        provider 优先级：显式入参 > 模板 recommended_provider > 系统默认（is_default）
        """
        service = get_prompt_template_service()
        template = service.get_template_by_key(db, template_key)
        if template is None:
            raise RuntimeError(f"Prompt 模板未找到: {template_key}")

        # provider：如果没显式传入，用模板推荐；仍为空则系统默认
        effective_provider = provider or template.recommended_provider
        provider_config = self.ai_strategy.get_provider_config(
            provider=effective_provider,
            model=template.recommended_model,
        )
        # 模板声明的 temperature / max_tokens 覆盖 provider 默认
        if template.recommended_temperature is not None:
            provider_config["temperature"] = float(template.recommended_temperature)
        if template.recommended_max_tokens is not None:
            provider_config["max_tokens"] = int(template.recommended_max_tokens)
        return template, provider_config

    # ---- 变量构建 ----

    @staticmethod
    def _build_anns_variables(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = [
            {
                "id": it['id'],
                "title": it.get('title') or '',
                "anno_type": it.get('anno_type') or '',
                "stock_name": it.get('stock_name') or '',
            }
            for it in items
        ]
        return {
            "batch_size": len(items),
            "announcements_json": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    @staticmethod
    def _build_news_variables(items: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = [
            {
                "id": it['id'],
                "title": it.get('title') or '',
                "summary": (it.get('summary') or '')[:280],
                "related_ts_codes": it.get('related_ts_codes') or [],
            }
            for it in items
        ]
        return {
            "batch_size": len(items),
            "news_items_json": json.dumps(payload, ensure_ascii=False, indent=2),
        }

    # ---- 单条结果归一化（公告） ----

    @staticmethod
    def _normalize_anns_score_item(
        raw: Dict[str, Any],
        source: Dict[str, Any],
        score_model: str,
    ) -> Optional[Dict[str, Any]]:
        score = _clamp_score(raw.get('sentiment_score'))
        if score is None:
            return None
        return {
            'id': source['id'],
            'event_tags': _normalize_event_tags(raw.get('event_tags')),
            'sentiment_score': score,
            'sentiment_impact': _normalize_impact(raw.get('sentiment_impact'), score),
            'scoring_reason': (raw.get('scoring_reason') or '')[:400] or None,
            'score_model': score_model[:80],
        }

    # ---- 单条结果归一化（快讯） ----

    @staticmethod
    def _normalize_news_score_item(
        raw: Dict[str, Any],
        source: Dict[str, Any],
        score_model: str,
    ) -> Optional[Dict[str, Any]]:
        score = _clamp_score(raw.get('sentiment_score'))
        if score is None:
            return None
        return {
            'id': source['id'],
            'publish_time': source.get('publish_time'),
            'sentiment_score': score,
            'sentiment_impact': _normalize_impact(raw.get('sentiment_impact'), score),
            'sentiment_tags': _normalize_theme_tags(raw.get('sentiment_tags')),
            'scoring_reason': (raw.get('scoring_reason') or '')[:400] or None,
            'score_model': score_model[:80],
        }

    # ---- 日志兜底 ----

    @staticmethod
    def _mark_log_failure(
        db: Session,
        call_id: Optional[str],
        start_time: Optional[datetime],
        status: CallStatus,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        if not call_id or not start_time:
            return
        try:
            llm_call_logger.update_log_failure(
                db=db,
                call_id=call_id,
                start_time=start_time,
                status=status,
                error_code=error_code,
                error_message=error_message,
            )
        except Exception as e:
            logger.warning(f"[sentiment_scoring] 更新 LLM 日志失败: {e}")


_sentiment_scoring_service = SentimentScoringService()


def get_sentiment_scoring_service() -> SentimentScoringService:
    return _sentiment_scoring_service
