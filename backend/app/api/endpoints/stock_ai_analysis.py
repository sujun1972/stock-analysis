"""
股票AI分析结果 API 端点
支持保存分析结果（游资观点等多种类型）、查询最新版本、浏览历史版本
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.core.database import get_db
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_ai_analysis_service import (
    StockAiAnalysisService,
    extract_json_and_score as _extract_json_and_score,
    JSON_ANALYSIS_TYPES as _JSON_ANALYSIS_TYPES,
)
from app.services.llm_call_logger import llm_call_logger
from app.schemas.llm_call_log import BusinessType, CallStatus
from sqlalchemy.orm import Session

router = APIRouter(prefix="/stock-ai-analysis", tags=["股票AI分析"])


# ------------------------------------------------------------------
# LLM 调用日志辅助（日志失败不阻塞主流程）
# ------------------------------------------------------------------

def _log_llm_start(
    db: Session,
    provider: str,
    provider_config: dict,
    prompt_text: str,
    caller_function: str,
    ts_code: str,
    user_id: int,
    *,
    analysis_type: str | None = None,
    agent_mode: bool = False,
) -> tuple[str | None, object]:
    """创建 LLM 调用日志，返回 (call_id, start_time)。失败返回 (None, None)。"""
    try:
        params = {
            "temperature": provider_config.get("temperature"),
            "max_tokens": provider_config.get("max_tokens"),
        }
        if analysis_type:
            params["analysis_type"] = analysis_type
        if agent_mode:
            params["mode"] = "agent"

        return llm_call_logger.create_log_entry(
            db=db,
            business_type=BusinessType.STOCK_EXPERT_ANALYSIS,
            provider=provider,
            model_name=provider_config.get("model_name", ""),
            call_parameters=params,
            prompt_text=prompt_text,
            caller_service="CIOAgentService" if agent_mode else "StockAiAnalysis",
            caller_function=caller_function,
            business_id=ts_code,
            user_id=str(user_id),
        )
    except Exception as e:
        logger.warning(f"[{caller_function}] 创建LLM调用日志失败: {e}")
        return None, None


def _log_llm_success(db: Session, call_id: str | None, start_time, response_text: str, tokens_total: int):
    """更新 LLM 调用日志为成功。"""
    if not call_id:
        return
    try:
        llm_call_logger.update_log_success(
            db=db, call_id=call_id, start_time=start_time,
            response_text=response_text[:2000],
            tokens_total=tokens_total,
        )
    except Exception as e:
        logger.warning(f"更新LLM调用日志失败: {e}")


def _log_llm_failure(db: Session, call_id: str | None, start_time, error: Exception):
    """更新 LLM 调用日志为失败。"""
    if not call_id:
        return
    try:
        llm_call_logger.update_log_failure(
            db=db, call_id=call_id, start_time=start_time,
            status=CallStatus.FAILED,
            error_code=type(error).__name__, error_message=str(error)[:500],
        )
    except Exception:
        pass


# ------------------------------------------------------------------
# Request 模型
# ------------------------------------------------------------------

class SaveAnalysisRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    analysis_type: str = Field(..., description="分析类型，如 hot_money_view")
    analysis_text: str = Field(..., min_length=1, description="AI分析结果文本")
    score: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10，支持一位小数（可选）")
    prompt_text: Optional[str] = Field(None, description="生成本次分析所用的完整提示词快照")
    ai_provider: Optional[str] = Field(None, description="AI提供商，如 deepseek")
    ai_model: Optional[str] = Field(None, description="AI模型名称，如 deepseek-chat")
    trade_date: Optional[str] = Field(None, description="交易日，YYYYMMDD 格式")


class UpdateAnalysisRequest(BaseModel):
    analysis_text: str = Field(..., min_length=1, description="修改后的AI分析结果文本")
    score: Optional[float] = Field(None, ge=0, le=10, description="评分 0-10，支持一位小数（可选）")


class GenerateAnalysisRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称")
    stock_code: str = Field(..., description="股票纯代码，如 000001")
    analysis_type: str = Field(..., description="分析类型，hot_money_view 或 stock_data_collection")
    template_key: str = Field(..., description="提示词模板 key，如 top_speculative_investor_v1")


# analysis_type → 默认 template_key 映射
_DEFAULT_TEMPLATE_KEYS = {
    "hot_money_view": "top_speculative_investor_v1",
    "midline_industry_expert": "midline_industry_expert_v1",
    "longterm_value_watcher": "longterm_value_watcher_v1",
    "cio_directive": "cio_directive_v1",
    "macro_risk_expert": "macro_risk_expert_v1",
}

# CIO 综合决策时，前置专家 analysis_type → CIO 模板占位符的映射。
# value 必须落在 prompt_templates.EXPERT_OUTPUT_PLACEHOLDERS 集合中。
_EXPERT_TYPE_TO_CIO_PLACEHOLDER = {
    "hot_money_view": "hot_money_summary",
    "midline_industry_expert": "midline_summary",
    "longterm_value_watcher": "longterm_summary",
}


class GenerateMultiRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称")
    stock_code: str = Field(..., description="股票纯代码，如 000001")
    analysis_types: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="分析类型列表，如 ['hot_money_view', 'midline_industry_expert']",
    )
    include_cio: bool = Field(
        False,
        description="是否在所有专家完成后追加 CIO 综合决策（将前面专家的输出作为 CIO 输入）",
    )


# ------------------------------------------------------------------
# CIO Agent 辅助函数
# ------------------------------------------------------------------

async def _prepare_cio_prompt(
    body, current_user, db, ai_service,
    expert_outputs: Optional[dict] = None,
) -> dict:
    """
    渲染 CIO 模板并准备 Agent 调用参数。

    把 build_stock_prompt 渲染、provider 配置组装、system+user 拼接三步集中。
    expert_outputs 为 None 时，CIO 模板中的专家占位符会被渲染为"未提供"提示
    （由 build_stock_prompt 内部处理）。

    Returns:
        {
            "system_prompt": str, "user_prompt": str, "full_prompt": str,
            "provider_name": str, "provider_config": dict, "trade_date": str | None,
        }
    """
    from app.api.endpoints.prompt_templates import build_stock_prompt

    cio_prompt_data = await build_stock_prompt(
        template_key=_DEFAULT_TEMPLATE_KEYS["cio_directive"],
        stock_name=body.stock_name,
        stock_code=body.stock_code,
        ts_code=body.ts_code,
        created_by=current_user.id,
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


async def _run_cio_agent_single(body, current_user, db, ai_service) -> dict:
    """当 /generate 端点的 analysis_type == "cio_directive" 时走 Agent 路径。

    单 CIO 路径无其他专家输出，CIO 模板中的专家占位符渲染为"未提供"提示，
    Agent 完全依靠工具自查。如需注入专家输出请走 /generate-multi。
    """
    from app.services.cio_agent_service import CIOAgentService

    try:
        prep = await _prepare_cio_prompt(body, current_user, db, ai_service)
    except Exception as e:
        logger.error(f"[generate_analysis/cio_agent] 渲染模板失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"渲染 CIO 模板失败: {e}", code=500).to_dict()

    call_id, start_time_log = _log_llm_start(
        db, prep["provider_name"], prep["provider_config"],
        prompt_text=prep["full_prompt"],
        caller_function="generate_analysis",
        ts_code=body.ts_code, user_id=current_user.id,
        analysis_type="cio_directive", agent_mode=True,
    )

    try:
        agent_result = await CIOAgentService().run_agent(
            ts_code=body.ts_code,
            stock_name=body.stock_name,
            system_prompt=prep["system_prompt"],
            user_prompt=prep["user_prompt"],
            provider=prep["provider_name"],
            provider_config=prep["provider_config"],
        )
    except Exception as e:
        logger.error(f"[generate_analysis/cio_agent] Agent 执行失败: {e}", exc_info=True)
        _log_llm_failure(db, call_id, start_time_log, e)
        return ApiResponse.error(message=f"CIO Agent 执行失败: {e}", code=500).to_dict()

    ai_text = agent_result["content"]
    tokens_used = agent_result["tokens_used"]
    generation_time = agent_result["generation_time"]
    _log_llm_success(db, call_id, start_time_log, ai_text, tokens_used)

    ai_text, extracted_score = _extract_json_and_score(ai_text)

    try:
        result = await StockAiAnalysisService().save_analysis(
            ts_code=body.ts_code,
            analysis_type="cio_directive",
            analysis_text=ai_text,
            score=extracted_score,
            prompt_text=prep["full_prompt"],
            ai_provider=prep["provider_name"],
            ai_model=prep["provider_config"].get("model_name"),
            created_by=current_user.id,
            trade_date=prep["trade_date"],
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()

    return ApiResponse.success(
        data={
            **result,
            "analysis_text": ai_text,
            "score": extracted_score,
            "tokens_used": tokens_used,
            "generation_time": round(generation_time, 2),
            "agent_tool_calls": agent_result.get("tool_calls", []),
            "agent_iterations": agent_result.get("iterations", 0),
        },
        message="CIO Agent 分析生成并保存成功",
    ).to_dict()


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.get("/list")
@handle_api_errors
async def list_analyses(
    ts_code: Optional[str] = Query(None, description="股票代码过滤"),
    analysis_type: Optional[str] = Query(None, description="分析类型过滤"),
    ai_provider: Optional[str] = Query(None, description="AI提供商过滤"),
    trade_date: Optional[str] = Query(None, description="交易日过滤，YYYYMMDD"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    limit: int = Query(20, ge=1, le=100, description="每页记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    _: User = Depends(get_current_active_user),
):
    """查询所有股票AI分析记录（支持过滤、排序、分页）"""
    service = StockAiAnalysisService()
    result = await service.list_all(
        ts_code=ts_code,
        analysis_type=analysis_type,
        ai_provider=ai_provider,
        trade_date=trade_date,
        sort_by=sort_by or "created_at",
        sort_order=sort_order or "desc",
        limit=limit,
        offset=offset,
    )
    return ApiResponse.success(data=result).to_dict()


@router.post("/generate")
@handle_api_errors
async def generate_analysis(
    body: GenerateAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """调用后端 AI 服务生成个股分析并自动保存，返回生成的记录。

    提示词通过 build_stock_prompt() 构建，与前端展示的提示词完全一致。
    """
    from app.api.endpoints.prompt_templates import build_stock_prompt
    from app.services.ai_service import AIStrategyService

    ai_service = AIStrategyService()

    # ----------------------------------------------------------
    # CIO Agent 路径：analysis_type == "cio_directive" 走 Agent
    # ----------------------------------------------------------
    if body.analysis_type == "cio_directive":
        return await _run_cio_agent_single(
            body=body,
            current_user=current_user,
            db=db,
            ai_service=ai_service,
        )

    # ----------------------------------------------------------
    # 普通专家路径（非 CIO）
    # ----------------------------------------------------------

    # 1. 构建提示词（生成分析时允许自动触发数据收集）
    try:
        prompt_data = await build_stock_prompt(
            template_key=body.template_key,
            stock_name=body.stock_name,
            stock_code=body.stock_code,
            ts_code=body.ts_code,
            created_by=current_user.id,
            db=db,
            allow_generate_data_collection=True,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        logger.error(f"[generate_analysis] 构建提示词失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"构建提示词失败: {e}", code=500).to_dict()

    # system_prompt + user_prompt 合并为单条 user 消息（与其他 AI 调用路径一致）
    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data["user_prompt"]
    full_prompt = f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt

    # 2. 获取 AI 提供商配置，用模板推荐参数覆盖 temperature / max_tokens
    provider_name = prompt_data["recommended_provider"]
    provider_config = ai_service.get_provider_config(provider_name)
    provider_config["temperature"] = prompt_data["recommended_temperature"]
    provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

    # 3. 创建 LLM 调用日志 + 调用 AI 生成
    call_id, start_time_log = _log_llm_start(
        db, provider_name, provider_config,
        prompt_text=full_prompt,
        caller_function="generate_analysis",
        ts_code=body.ts_code, user_id=current_user.id,
    )

    try:
        client = ai_service.create_client(provider_name, provider_config)
        start_time = time.time()
        ai_text, tokens_used = await client.generate_strategy(full_prompt)
        generation_time = time.time() - start_time
        logger.info(
            f"[generate_analysis] {body.ts_code} {body.analysis_type} "
            f"生成完成: {len(ai_text)}字 / {tokens_used} tokens / {generation_time:.2f}s"
        )
    except Exception as e:
        logger.error(f"[generate_analysis] AI 调用失败: {e}", exc_info=True)
        _log_llm_failure(db, call_id, start_time_log, e)
        return ApiResponse.error(message=f"AI 调用失败: {e}", code=500).to_dict()

    _log_llm_success(db, call_id, start_time_log, ai_text, tokens_used)

    # 4. 清理 JSON 代码块标识并提取评分（对所有 JSON 格式分析类型）
    if body.analysis_type in _JSON_ANALYSIS_TYPES:
        ai_text, extracted_score = _extract_json_and_score(ai_text)
    else:
        extracted_score = None

    # 5. 保存分析结果（版本自动递增）
    #    trade_date 来自数据采集记录，确保分析结果与采集数据对应同一交易日
    trade_date = prompt_data.get("trade_date")
    try:
        result = await StockAiAnalysisService().save_analysis(
            ts_code=body.ts_code,
            analysis_type=body.analysis_type,
            analysis_text=ai_text,
            score=extracted_score,
            prompt_text=full_prompt,
            ai_provider=provider_name,
            ai_model=provider_config.get("model_name"),
            created_by=current_user.id,
            trade_date=trade_date,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()

    return ApiResponse.success(
        data={
            **result,
            "analysis_text": ai_text,
            "score": extracted_score,
            "tokens_used": tokens_used,
            "generation_time": round(generation_time, 2),
        },
        message="AI 分析生成并保存成功",
    ).to_dict()


@router.post("/generate-multi")
@handle_api_errors
async def generate_multi_analysis(
    body: GenerateMultiRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """并行调用多个 AI 专家分析同一只股票，数据收集只做一次。

    通过 asyncio.gather 并行编排多个专家，每个专家独立保存结果。
    可选：所有专家完成后串联 CIO 综合决策步骤（将前面专家的输出摘要注入 CIO prompt）。
    """
    import asyncio
    from app.api.endpoints.prompt_templates import build_stock_prompt
    from app.services.ai_service import AIStrategyService

    # 校验 analysis_types
    invalid_types = [t for t in body.analysis_types if t not in _JSON_ANALYSIS_TYPES and t != "stock_data_collection"]
    if invalid_types:
        return ApiResponse.bad_request(
            message=f"不支持的分析类型: {invalid_types}，允许值: {list(_JSON_ANALYSIS_TYPES)}"
        ).to_dict()

    # 去重，移除 cio_directive（如果 include_cio=True 则最后单独处理）
    expert_types = list(dict.fromkeys(
        t for t in body.analysis_types if t != "cio_directive"
    ))
    if not expert_types and not body.include_cio:
        return ApiResponse.bad_request(message="至少需要一个非 CIO 分析类型").to_dict()

    ai_service = AIStrategyService()

    # 1. 构建第一个专家的提示词（触发数据收集，后续专家共享）
    #    所有专家模板都引用 {{ stock_data_collection }}，第一次调用会生成并缓存
    first_type = expert_types[0] if expert_types else "cio_directive"
    first_template_key = _DEFAULT_TEMPLATE_KEYS.get(first_type)
    if not first_template_key:
        return ApiResponse.bad_request(message=f"分析类型 {first_type} 无默认模板").to_dict()

    try:
        first_prompt_data = await build_stock_prompt(
            template_key=first_template_key,
            stock_name=body.stock_name,
            stock_code=body.stock_code,
            ts_code=body.ts_code,
            created_by=current_user.id,
            db=db,
            allow_generate_data_collection=True,
        )
    except Exception as e:
        logger.error(f"[generate_multi] 构建提示词失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"构建提示词失败: {e}", code=500).to_dict()

    trade_date = first_prompt_data.get("trade_date")

    # 2. 并行构建所有专家的提示词（数据收集已缓存，此步很快）
    async def build_expert_prompt(analysis_type: str) -> dict:
        template_key = _DEFAULT_TEMPLATE_KEYS.get(analysis_type)
        if not template_key:
            raise ValueError(f"分析类型 {analysis_type} 无默认模板")
        return await build_stock_prompt(
            template_key=template_key,
            stock_name=body.stock_name,
            stock_code=body.stock_code,
            ts_code=body.ts_code,
            created_by=current_user.id,
            db=db,
            allow_generate_data_collection=True,
        )

    # 第一个已构建，其余并行构建
    remaining_types = expert_types[1:]
    try:
        remaining_prompts = await asyncio.gather(*[
            build_expert_prompt(t) for t in remaining_types
        ])
    except Exception as e:
        logger.error(f"[generate_multi] 并行构建提示词失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"构建提示词失败: {e}", code=500).to_dict()

    all_prompt_data = {expert_types[0]: first_prompt_data}
    for t, pd_item in zip(remaining_types, remaining_prompts):
        all_prompt_data[t] = pd_item

    # 3. 并行调用 AI 生成
    async def run_expert(analysis_type: str) -> dict:
        prompt_data = all_prompt_data[analysis_type]
        system_prompt = prompt_data["system_prompt"]
        user_prompt = prompt_data["user_prompt"]
        full_prompt = f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt

        provider_name = prompt_data["recommended_provider"]
        provider_config = ai_service.get_provider_config(provider_name)
        provider_config["temperature"] = prompt_data["recommended_temperature"]
        provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

        call_id, start_time_log = _log_llm_start(
            db, provider_name, provider_config,
            prompt_text=full_prompt,
            caller_function="generate_multi_analysis",
            ts_code=body.ts_code, user_id=current_user.id,
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

        logger.info(
            f"[generate_multi] {body.ts_code} {analysis_type} "
            f"生成完成: {len(ai_text)}字 / {tokens_used} tokens / {generation_time:.2f}s"
        )
        _log_llm_success(db, call_id, start_time_log, ai_text, tokens_used)

        # 清理 JSON + 提取评分
        if analysis_type in _JSON_ANALYSIS_TYPES:
            ai_text, extracted_score = _extract_json_and_score(ai_text)
        else:
            extracted_score = None

        # 保存
        result = await StockAiAnalysisService().save_analysis(
            ts_code=body.ts_code,
            analysis_type=analysis_type,
            analysis_text=ai_text,
            score=extracted_score,
            prompt_text=full_prompt,
            ai_provider=provider_name,
            ai_model=provider_config.get("model_name"),
            created_by=current_user.id,
            trade_date=trade_date,
        )

        return {
            "analysis_type": analysis_type,
            **result,
            "analysis_text": ai_text,
            "score": extracted_score,
            "tokens_used": tokens_used,
            "generation_time": round(generation_time, 2),
        }

    try:
        expert_results = await asyncio.gather(*[
            run_expert(t) for t in expert_types
        ], return_exceptions=True)
    except Exception as e:
        logger.error(f"[generate_multi] 并行生成失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"并行生成失败: {e}", code=500).to_dict()

    # 分离成功和失败的结果
    results = []
    errors = []
    for i, r in enumerate(expert_results):
        if isinstance(r, Exception):
            errors.append({"analysis_type": expert_types[i], "error": str(r)})
            logger.error(f"[generate_multi] {expert_types[i]} 失败: {r}")
        else:
            results.append(r)

    # 4. 可选：CIO Agent 综合决策（Agent 自主查询数据 + 参考前面专家结论）
    cio_result = None
    cio_call_id = None
    cio_start_time_log = None
    if body.include_cio and results:
        try:
            from app.services.cio_agent_service import CIOAgentService

            # 把每个完成的专家完整 analysis_text（不截断）按映射注入 CIO 模板占位符
            expert_outputs = {
                placeholder: (r.get("analysis_text") or "")
                for r in results
                if (placeholder := _EXPERT_TYPE_TO_CIO_PLACEHOLDER.get(r["analysis_type"]))
            }

            prep = await _prepare_cio_prompt(
                body, current_user, db, ai_service, expert_outputs=expert_outputs,
            )

            cio_call_id, cio_start_time_log = _log_llm_start(
                db, prep["provider_name"], prep["provider_config"],
                prompt_text=prep["full_prompt"],
                caller_function="generate_multi_analysis",
                ts_code=body.ts_code, user_id=current_user.id,
                analysis_type="cio_directive", agent_mode=True,
            )

            agent_result = await CIOAgentService().run_agent(
                ts_code=body.ts_code,
                stock_name=body.stock_name,
                system_prompt=prep["system_prompt"],
                user_prompt=prep["user_prompt"],
                provider=prep["provider_name"],
                provider_config=prep["provider_config"],
            )

            cio_text = agent_result["content"]
            cio_tokens = agent_result["tokens_used"]
            cio_gen_time = agent_result["generation_time"]
            _log_llm_success(db, cio_call_id, cio_start_time_log, cio_text, cio_tokens)

            cio_text, cio_score = _extract_json_and_score(cio_text)

            cio_saved = await StockAiAnalysisService().save_analysis(
                ts_code=body.ts_code,
                analysis_type="cio_directive",
                analysis_text=cio_text,
                score=cio_score,
                prompt_text=prep["full_prompt"],
                ai_provider=prep["provider_name"],
                ai_model=prep["provider_config"].get("model_name"),
                created_by=current_user.id,
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
            logger.error(f"[generate_multi] CIO Agent 综合决策失败: {e}", exc_info=True)
            _log_llm_failure(db, cio_call_id, cio_start_time_log, e)
            errors.append({"analysis_type": "cio_directive", "error": str(e)})

    total_tokens = sum(r.get("tokens_used", 0) for r in results)
    total_time = sum(r.get("generation_time", 0) for r in results)
    if cio_result:
        total_tokens += cio_result.get("tokens_used", 0)
        total_time += cio_result.get("generation_time", 0)

    return ApiResponse.success(
        data={
            "expert_results": results,
            "cio_result": cio_result,
            "errors": errors if errors else None,
            "total_tokens": total_tokens,
            "total_generation_time": round(total_time, 2),
            "expert_count": len(results) + (1 if cio_result else 0),
        },
        message=f"多专家分析完成：{len(results)} 个专家成功"
        + (f"，{len(errors)} 个失败" if errors else "")
        + ("，含 CIO 综合决策" if cio_result else ""),
    ).to_dict()


@router.post("/")
@handle_api_errors
async def save_analysis(
    body: SaveAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """保存一条新的AI分析结果（每次保存为新版本）"""
    service = StockAiAnalysisService()
    try:
        result = await service.save_analysis(
            ts_code=body.ts_code,
            analysis_type=body.analysis_type,
            analysis_text=body.analysis_text,
            score=body.score,
            prompt_text=body.prompt_text,
            ai_provider=body.ai_provider,
            ai_model=body.ai_model,
            created_by=current_user.id,
            trade_date=body.trade_date,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    return ApiResponse.success(data=result, message="分析结果已保存").to_dict()


@router.get("/latest")
@handle_api_errors
async def get_latest(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    analysis_type: str = Query(..., description="分析类型，如 hot_money_view"),
    _: User = Depends(get_current_active_user),
):
    """获取指定股票+类型的最新一条分析结果"""
    service = StockAiAnalysisService()
    result = await service.get_latest(ts_code, analysis_type)
    if result is None:
        return ApiResponse.not_found(message="暂无分析记录").to_dict()
    return ApiResponse.success(data=result).to_dict()


@router.get("/history")
@handle_api_errors
async def get_history(
    ts_code: str = Query(..., description="股票代码，如 000001.SZ"),
    analysis_type: str = Query(..., description="分析类型，如 hot_money_view"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_active_user),
):
    """获取指定股票+类型的所有版本历史（分页，最新在前）"""
    service = StockAiAnalysisService()
    result = await service.get_history(ts_code, analysis_type, limit, offset)
    return ApiResponse.success(data=result).to_dict()


@router.put("/{record_id}")
@handle_api_errors
async def update_analysis(
    record_id: int,
    body: UpdateAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """修改已保存的分析记录（仅限记录创建者）"""
    service = StockAiAnalysisService()
    try:
        result = await service.update_analysis(
            record_id=record_id,
            analysis_text=body.analysis_text,
            score=body.score,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except PermissionError as e:
        return ApiResponse.forbidden(message=str(e)).to_dict()
    if result is None:
        return ApiResponse.not_found(message="记录不存在").to_dict()
    return ApiResponse.success(data=result, message="修改成功").to_dict()


@router.delete("/{record_id}")
@handle_api_errors
async def delete_analysis(
    record_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """删除已保存的分析记录（创建者或管理员）"""
    service = StockAiAnalysisService()
    try:
        deleted = await service.delete_analysis(
            record_id=record_id,
            current_user_id=current_user.id,
            user_role=current_user.role,
        )
    except PermissionError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    if not deleted:
        return ApiResponse.not_found(message="记录不存在").to_dict()
    return ApiResponse.success(message="删除成功").to_dict()
