"""批量 AI 分析 Service

封装"单只股票多专家并行分析 + 可选 CIO 综合决策"的完整业务逻辑，供：
- POST /api/stock-ai-analysis/generate-multi 端点调用（单只同步模式）
- batch_ai_analysis Celery 任务调用（多只异步模式，内部 2 并发）

与端点原地实现相比，本 Service 自己管理 SQLAlchemy Session，不依赖 FastAPI 请求作用域。
"""

import asyncio
import time
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal


# 对外暴露的 analysis_type → 默认 template_key 映射（与端点共享）
DEFAULT_TEMPLATE_KEYS: Dict[str, str] = {
    "hot_money_view": "top_speculative_investor_v1",
    "midline_industry_expert": "midline_industry_expert_v1",
    "longterm_value_watcher": "longterm_value_watcher_v3",
    "cio_directive": "cio_directive_v1",
    "macro_risk_expert": "macro_risk_expert_v1",
}

# 前置专家 analysis_type → CIO 模板占位符
EXPERT_TYPE_TO_CIO_PLACEHOLDER: Dict[str, str] = {
    "hot_money_view": "hot_money_summary",
    "midline_industry_expert": "midline_summary",
    "longterm_value_watcher": "longterm_summary",
}


async def _prepare_cio_prompt(
    ts_code: str,
    stock_name: str,
    stock_code: str,
    user_id: int,
    db: Session,
    ai_service,
    expert_outputs: Optional[Dict[str, str]] = None,
) -> Dict:
    """渲染 CIO 模板 + 组装 provider 配置 + 拼 full_prompt。"""
    from app.api.endpoints.prompt_templates import build_stock_prompt

    cio_prompt_data = await build_stock_prompt(
        template_key=DEFAULT_TEMPLATE_KEYS["cio_directive"],
        stock_name=stock_name,
        stock_code=stock_code,
        ts_code=ts_code,
        created_by=user_id,
        db=db,
        allow_generate_data_collection=False,
        expert_outputs=expert_outputs,
    )

    provider_name = cio_prompt_data["recommended_provider"]
    provider_config = ai_service.get_provider_config(provider_name)
    provider_config["temperature"] = cio_prompt_data["recommended_temperature"]
    provider_config["max_tokens"] = cio_prompt_data["recommended_max_tokens"]

    system_prompt = cio_prompt_data["system_prompt"]
    user_prompt = cio_prompt_data["user_prompt"]
    full_prompt = f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "full_prompt": full_prompt,
        "provider_name": provider_name,
        "provider_config": provider_config,
        "trade_date": cio_prompt_data.get("trade_date"),
    }


async def run_multi_expert_for_stock(
    *,
    ts_code: str,
    stock_name: str,
    stock_code: str,
    analysis_types: List[str],
    include_cio: bool,
    user_id: int,
    db: Optional[Session] = None,
) -> Dict:
    """对单只股票并行生成多个专家分析 + 可选 CIO 综合决策。

    端点路径和 Celery 任务共用此函数。db 为 None 时自行开启 Session。

    返回结构与原 generate-multi 端点一致：
        {
            "expert_results": [...],
            "cio_result": {...} | None,
            "errors": [...] | None,
            "total_tokens": int,
            "total_generation_time": float,
            "expert_count": int,
            "trade_date": str | None,
        }
    """
    # 端点内引用，避免循环 import
    from app.api.endpoints.prompt_templates import build_stock_prompt
    from app.api.endpoints.stock_ai_analysis import (
        _log_llm_start, _log_llm_success, _log_llm_failure,
    )
    from app.services.ai_service import AIStrategyService
    from app.services.stock_ai_analysis_service import (
        StockAiAnalysisService,
        extract_json_and_score,
        JSON_ANALYSIS_TYPES,
    )

    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        ai_service = AIStrategyService()

        # 去重，移除 cio_directive（若 include_cio=True 末尾单独处理）
        expert_types = list(dict.fromkeys(
            t for t in analysis_types if t != "cio_directive"
        ))

        if not expert_types and not include_cio:
            raise ValueError("至少需要一个非 CIO 分析类型")

        # 1. 构建第一个专家的提示词（触发数据收集，后续专家共享缓存）
        first_type = expert_types[0] if expert_types else "cio_directive"
        first_template_key = DEFAULT_TEMPLATE_KEYS.get(first_type)
        if not first_template_key:
            raise ValueError(f"分析类型 {first_type} 无默认模板")

        first_prompt_data = await build_stock_prompt(
            template_key=first_template_key,
            stock_name=stock_name,
            stock_code=stock_code,
            ts_code=ts_code,
            created_by=user_id,
            db=db,
            allow_generate_data_collection=True,
        )
        trade_date = first_prompt_data.get("trade_date")

        # 2. 并行构建其余专家提示词
        async def build_expert_prompt(analysis_type: str) -> Dict:
            template_key = DEFAULT_TEMPLATE_KEYS.get(analysis_type)
            if not template_key:
                raise ValueError(f"分析类型 {analysis_type} 无默认模板")
            return await build_stock_prompt(
                template_key=template_key,
                stock_name=stock_name,
                stock_code=stock_code,
                ts_code=ts_code,
                created_by=user_id,
                db=db,
                allow_generate_data_collection=True,
            )

        remaining_types = expert_types[1:]
        remaining_prompts = await asyncio.gather(*[
            build_expert_prompt(t) for t in remaining_types
        ])

        all_prompt_data = {expert_types[0]: first_prompt_data} if expert_types else {}
        for t, pd_item in zip(remaining_types, remaining_prompts):
            all_prompt_data[t] = pd_item

        # 3. 并行调用 AI 生成
        async def run_expert(analysis_type: str) -> Dict:
            prompt_data = all_prompt_data[analysis_type]
            system_prompt = prompt_data["system_prompt"]
            user_prompt = prompt_data["user_prompt"]
            full_prompt = (
                f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt
            )

            provider_name = prompt_data["recommended_provider"]
            provider_config = ai_service.get_provider_config(provider_name)
            provider_config["temperature"] = prompt_data["recommended_temperature"]
            provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

            call_id, start_time_log = _log_llm_start(
                db, provider_name, provider_config,
                prompt_text=full_prompt,
                caller_function="run_multi_expert_for_stock",
                ts_code=ts_code, user_id=user_id,
                analysis_type=analysis_type,
            )

            try:
                client = ai_service.create_client(provider_name, provider_config)
                start_time = time.time()
                ai_text, tokens_used = await client.generate_strategy(full_prompt)
                generation_time = time.time() - start_time
            except Exception as e:
                _log_llm_failure(db, call_id, start_time_log, e)
                raise

            _log_llm_success(db, call_id, start_time_log, ai_text, tokens_used)

            if analysis_type in JSON_ANALYSIS_TYPES:
                ai_text, extracted_score = extract_json_and_score(ai_text)
            else:
                extracted_score = None

            saved = await StockAiAnalysisService().save_analysis(
                ts_code=ts_code,
                analysis_type=analysis_type,
                analysis_text=ai_text,
                score=extracted_score,
                prompt_text=full_prompt,
                ai_provider=provider_name,
                ai_model=provider_config.get("model_name"),
                created_by=user_id,
                trade_date=trade_date,
            )

            return {
                "analysis_type": analysis_type,
                **saved,
                "analysis_text": ai_text,
                "score": extracted_score,
                "tokens_used": tokens_used,
                "generation_time": round(generation_time, 2),
            }

        expert_raw_results = await asyncio.gather(*[
            run_expert(t) for t in expert_types
        ], return_exceptions=True)

        results: List[Dict] = []
        errors: List[Dict] = []
        for i, r in enumerate(expert_raw_results):
            if isinstance(r, Exception):
                errors.append({"analysis_type": expert_types[i], "error": str(r)})
                logger.error(f"[run_multi_expert] {ts_code} {expert_types[i]} 失败: {r}")
            else:
                results.append(r)

        # 4. 可选：CIO Agent 综合决策
        cio_result: Optional[Dict] = None
        if include_cio and results:
            try:
                from app.services.cio_agent_service import CIOAgentService

                expert_outputs = {
                    placeholder: (r.get("analysis_text") or "")
                    for r in results
                    if (placeholder := EXPERT_TYPE_TO_CIO_PLACEHOLDER.get(r["analysis_type"]))
                }

                prep = await _prepare_cio_prompt(
                    ts_code=ts_code, stock_name=stock_name, stock_code=stock_code,
                    user_id=user_id, db=db, ai_service=ai_service,
                    expert_outputs=expert_outputs,
                )

                cio_call_id, cio_start_time_log = _log_llm_start(
                    db, prep["provider_name"], prep["provider_config"],
                    prompt_text=prep["full_prompt"],
                    caller_function="run_multi_expert_for_stock",
                    ts_code=ts_code, user_id=user_id,
                    analysis_type="cio_directive", agent_mode=True,
                )

                try:
                    agent_result = await CIOAgentService().run_agent(
                        ts_code=ts_code,
                        stock_name=stock_name,
                        system_prompt=prep["system_prompt"],
                        user_prompt=prep["user_prompt"],
                        provider=prep["provider_name"],
                        provider_config=prep["provider_config"],
                    )
                except Exception as e:
                    _log_llm_failure(db, cio_call_id, cio_start_time_log, e)
                    raise

                cio_text = agent_result["content"]
                cio_tokens = agent_result["tokens_used"]
                cio_gen_time = agent_result["generation_time"]
                _log_llm_success(db, cio_call_id, cio_start_time_log, cio_text, cio_tokens)

                cio_text, cio_score = extract_json_and_score(cio_text)

                cio_saved = await StockAiAnalysisService().save_analysis(
                    ts_code=ts_code,
                    analysis_type="cio_directive",
                    analysis_text=cio_text,
                    score=cio_score,
                    prompt_text=prep["full_prompt"],
                    ai_provider=prep["provider_name"],
                    ai_model=prep["provider_config"].get("model_name"),
                    created_by=user_id,
                    trade_date=trade_date,
                )

                cio_result = {
                    "analysis_type": "cio_directive",
                    **cio_saved,
                    "analysis_text": cio_text,
                    "score": cio_score,
                    "tokens_used": cio_tokens,
                    "generation_time": round(cio_gen_time, 2),
                    "agent_tool_calls": agent_result.get("tool_calls", []),
                    "agent_iterations": agent_result.get("iterations", 0),
                }
            except Exception as e:
                logger.error(f"[run_multi_expert] {ts_code} CIO Agent 综合决策失败: {e}", exc_info=True)
                errors.append({"analysis_type": "cio_directive", "error": str(e)})

        total_tokens = sum(r.get("tokens_used", 0) for r in results)
        total_time = sum(r.get("generation_time", 0) for r in results)
        if cio_result:
            total_tokens += cio_result.get("tokens_used", 0)
            total_time += cio_result.get("generation_time", 0)

        return {
            "expert_results": results,
            "cio_result": cio_result,
            "errors": errors if errors else None,
            "total_tokens": total_tokens,
            "total_generation_time": round(total_time, 2),
            "expert_count": len(results) + (1 if cio_result else 0),
            "trade_date": trade_date,
        }
    finally:
        if owns_session and db is not None:
            db.close()
