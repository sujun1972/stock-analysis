"""
股票AI分析结果 API 端点
支持保存分析结果（游资观点等多种类型）、查询最新版本、浏览历史版本
"""

import asyncio
import time
import uuid
from datetime import datetime
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
    extract_cio_followup_triggers,
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


# analysis_type 相关常量（DEFAULT_TEMPLATE_KEYS、EXPERT_TYPE_TO_CIO_PLACEHOLDER）
# 集中在 batch_ai_analysis_service 中定义，供端点和 Celery 任务共享。
from app.services.batch_ai_analysis_service import (  # noqa: E402
    DEFAULT_TEMPLATE_KEYS as _DEFAULT_TEMPLATE_KEYS,
)


class GenerateReviewRequest(BaseModel):
    ts_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称")
    stock_code: str = Field(..., description="股票纯代码，如 000001")
    original_analysis_id: int = Field(..., description="被复盘的原专家分析记录 ID")
    review_type: str = Field(
        "hot_money",
        description="复盘类型：hot_money（短线）/ midline（中线）/ longterm（长线）",
    )
    force: bool = Field(
        False,
        description="跳过时间窗/数据前置条件校验（用于用户知情后强制触发）",
    )


# 复盘类型 → 配置映射。新增复盘类型时在此追加一行即可。
# source_type: 被复盘记录必须是哪种 analysis_type
# save_type:   复盘结果写入表时的 analysis_type
# template_key: 复盘提示词模板 key
# min_days_lag: 建议的最小复盘间隔（自然日）；force=False 时低于此阈值拒绝
REVIEW_CONFIGS: dict = {
    "hot_money": {
        "source_type": "hot_money_view",
        "save_type": "hot_money_review",
        "template_key": "hot_money_review_v1",
        "min_days_lag": 0,  # 短线 T+1 就可复盘
        "min_days_lag_message": "",
    },
    "midline": {
        "source_type": "midline_industry_expert",
        "save_type": "midline_review",
        "template_key": "midline_review_v1",
        "min_days_lag": 20,
        "min_days_lag_message": (
            "中线复盘建议在原报告发布 20 个自然日后进行（至少跨越 1 个月的"
            "板块景气度演变 / 业绩预告窗口）。如需强制复盘请勾选 force。"
        ),
    },
    "longterm": {
        "source_type": "longterm_value_watcher",
        "save_type": "longterm_review",
        "template_key": "longterm_review_v1",
        "min_days_lag": 90,
        "min_days_lag_message": (
            "长线复盘建议在原报告发布 90 个自然日后进行（至少跨越 1 个季度，"
            "覆盖新的财报披露 / ROE 更新）。如需强制复盘请勾选 force。"
        ),
    },
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
    reuse_existing_experts: bool = Field(
        True,
        description="同一交易日已有合法专家报告时是否复用（默认开启，避免重复消耗 LLM 配额）。"
                    "CIO 始终重跑（综合性结论用户每次都希望刷新）。",
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

    ai_text, extracted_score, is_malformed = _extract_json_and_score(ai_text)

    # CIO 是强结构化展示场景，修复链覆盖不到的偶发畸形必须拦在写库前
    if is_malformed:
        logger.warning(
            f"[generate_analysis/cio] {body.ts_code} CIO 输出 JSON 畸形且修复失败"
        )
        return ApiResponse.bad_request(
            message="CIO 输出 JSON 畸形且自动修复失败，请重试"
        ).to_dict()

    followup_triggers = extract_cio_followup_triggers(ai_text)

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
            followup_triggers=followup_triggers,
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
            "followup_triggers": followup_triggers,
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

    # 4. 清理 JSON + 评分提取。普通专家走 MarkdownContent 兜底渲染，畸形仅告警不阻断
    if body.analysis_type in _JSON_ANALYSIS_TYPES:
        ai_text, extracted_score, is_malformed = _extract_json_and_score(ai_text)
        if is_malformed:
            logger.warning(
                f"[generate_analysis] {body.ts_code} {body.analysis_type} JSON 畸形,"
                f"前端将走 MarkdownContent 兜底渲染"
            )
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


@router.post("/generate-review")
@handle_api_errors
async def generate_review(
    body: GenerateReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """专家自评：基于原专家分析报告 + 当前最新数据，生成事后复盘分析。

    支持三种复盘类型（review_type 指定）：
    - hot_money：短线游资观点复盘（对照次日三档概率 / 席位信号 / 执行计划）
    - midline：中线产业趋势复盘（对照板块景气度演变 / 业绩预告兑现）
    - longterm：长线价值守望复盘（对照 ROE 兑现 / 护城河验证 / 估值修复进度）

    时间窗校验：中线 >= 20 自然日、长线 >= 90 自然日，不足时返回 bad_request（force=True 跳过）。
    """
    from app.api.endpoints.prompt_templates import build_stock_prompt
    from app.services.ai_service import AIStrategyService

    # 1. 校验 review_type
    cfg = REVIEW_CONFIGS.get(body.review_type)
    if cfg is None:
        return ApiResponse.bad_request(
            message=f"不支持的 review_type: {body.review_type}，允许值: {list(REVIEW_CONFIGS)}"
        ).to_dict()

    # 2. 读取原分析记录
    analysis_service = StockAiAnalysisService()
    original = await asyncio.to_thread(analysis_service.repo.get_by_id, body.original_analysis_id)
    if original is None:
        return ApiResponse.not_found(message=f"原分析记录不存在 (id={body.original_analysis_id})").to_dict()
    if original.get("analysis_type") != cfg["source_type"]:
        return ApiResponse.bad_request(
            message=f"{body.review_type} 复盘只支持 {cfg['source_type']} 类型，当前记录为 {original.get('analysis_type')}"
        ).to_dict()
    if (original.get("ts_code") or "").upper() != body.ts_code.upper():
        return ApiResponse.bad_request(message="原记录 ts_code 与请求不一致").to_dict()

    # 3. 推导原报告日期 + 时间窗校验
    original_trade_date = original.get("trade_date")
    if original_trade_date and len(original_trade_date) == 8:
        original_date_display = f"{original_trade_date[:4]}-{original_trade_date[4:6]}-{original_trade_date[6:8]}"
        try:
            original_dt = datetime.strptime(original_trade_date, "%Y%m%d")
        except ValueError:
            original_dt = None
    else:
        created_at = original.get("created_at") or ""
        original_date_display = created_at[:10] if isinstance(created_at, str) else str(created_at)[:10]
        try:
            original_dt = datetime.fromisoformat(created_at) if created_at else None
        except (ValueError, TypeError):
            original_dt = None

    days_lag = (datetime.now() - original_dt).days if original_dt else None
    if (
        not body.force
        and cfg["min_days_lag"] > 0
        and days_lag is not None
        and days_lag < cfg["min_days_lag"]
    ):
        return ApiResponse.bad_request(
            message=(
                f"原报告距今仅 {days_lag} 个自然日。{cfg['min_days_lag_message']}"
            )
        ).to_dict()

    # 4. 构建复盘提示词
    try:
        prompt_data = await build_stock_prompt(
            template_key=cfg["template_key"],
            stock_name=body.stock_name,
            stock_code=body.stock_code,
            ts_code=body.ts_code,
            created_by=current_user.id,
            db=db,
            allow_generate_data_collection=True,
            extra_variables={
                "original_analysis_date": original_date_display,
                "original_analysis_json": original.get("analysis_text") or "",
                "days_since_original": str(days_lag) if days_lag is not None else "未知",
            },
        )
    except ValueError as e:
        return ApiResponse.bad_request(message=str(e)).to_dict()
    except Exception as e:
        logger.error(f"[generate_review] 构建提示词失败: {e}", exc_info=True)
        return ApiResponse.error(message=f"构建提示词失败: {e}", code=500).to_dict()

    system_prompt = prompt_data["system_prompt"]
    user_prompt = prompt_data["user_prompt"]
    full_prompt = f"{system_prompt}\n\n{user_prompt}".strip() if system_prompt else user_prompt

    # 5. 组装 provider 配置
    ai_service = AIStrategyService()
    provider_name = prompt_data["recommended_provider"]
    provider_config = ai_service.get_provider_config(provider_name)
    provider_config["temperature"] = prompt_data["recommended_temperature"]
    provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

    # 6. 调 LLM
    call_id, start_time_log = _log_llm_start(
        db, provider_name, provider_config,
        prompt_text=full_prompt,
        caller_function="generate_review",
        ts_code=body.ts_code, user_id=current_user.id,
        analysis_type=cfg["save_type"],
    )

    try:
        client = ai_service.create_client(provider_name, provider_config)
        start_time = time.time()
        ai_text, tokens_used = await client.generate_strategy(full_prompt)
        generation_time = time.time() - start_time
        logger.info(
            f"[generate_review] {body.review_type} / {body.ts_code} 复盘原记录 "
            f"id={body.original_analysis_id} 生成完成: {len(ai_text)}字 / "
            f"{tokens_used} tokens / {generation_time:.2f}s"
        )
    except Exception as e:
        logger.error(f"[generate_review] AI 调用失败: {e}", exc_info=True)
        _log_llm_failure(db, call_id, start_time_log, e)
        return ApiResponse.error(message=f"AI 调用失败: {e}", code=500).to_dict()

    _log_llm_success(db, call_id, start_time_log, ai_text, tokens_used)

    # 7. JSON 清洗 + 评分提取（复盘走 MarkdownContent 兜底渲染，畸形 JSON 仅告警不阻断）
    ai_text, extracted_score, is_malformed = _extract_json_and_score(ai_text)
    if is_malformed:
        logger.warning(
            f"[generate_review] {body.ts_code} {body.review_type} 复盘 JSON 畸形,"
            f"前端将走 MarkdownContent 兜底渲染"
        )

    # 8. 保存复盘结果，携带 original_analysis_id 指向原记录
    try:
        result = await analysis_service.save_analysis(
            ts_code=body.ts_code,
            analysis_type=cfg["save_type"],
            analysis_text=ai_text,
            score=extracted_score,
            prompt_text=full_prompt,
            ai_provider=provider_name,
            ai_model=provider_config.get("model_name"),
            created_by=current_user.id,
            trade_date=prompt_data.get("trade_date"),
            original_analysis_id=body.original_analysis_id,
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
            "original_analysis_id": body.original_analysis_id,
            "original_analysis_date": original_date_display,
            "days_since_original": days_lag,
            "review_type": body.review_type,
        },
        message="复盘分析生成并保存成功",
    ).to_dict()


@router.post("/generate-multi")
@handle_api_errors
async def generate_multi_analysis(
    body: GenerateMultiRequest,
    current_user: User = Depends(get_current_active_user),
):
    """提交单只股票的多专家 AI 分析任务（异步）。

    与批量分析共用 tasks.batch_ai_analysis Celery 任务，ts_codes=[一只] / concurrency=1，
    在 celery_task_history 中以 task_type=single_ai_analysis 区分批量/单只。
    返回 celery_task_id 供前端 3 秒轮询；刷新页面后通过 /batch/active/ts-codes 恢复"分析中"。
    """
    from app.services.task_history_helper import TaskHistoryHelper
    from app.tasks.batch_ai_analysis_tasks import batch_ai_analysis_task, SINGLE_TASK_TYPE

    invalid_types = [t for t in body.analysis_types if t not in _JSON_ANALYSIS_TYPES and t != "stock_data_collection"]
    if invalid_types:
        return ApiResponse.bad_request(
            message=f"不支持的分析类型: {invalid_types}，允许值: {list(_JSON_ANALYSIS_TYPES)}"
        ).to_dict()

    ts_code = body.ts_code.strip().upper()
    if not ts_code:
        return ApiResponse.bad_request(message="ts_code 不能为空").to_dict()

    # 先生成 task_id 写 DB → 再 apply_async，避免 worker 提前跑导致 update_batch_progress
    # 的 WHERE celery_task_id=? 不命中、进度静默丢失（与 /batch 端点同协议）
    celery_task_id = str(uuid.uuid4())

    await TaskHistoryHelper().create_task_record(
        celery_task_id=celery_task_id,
        task_name="tasks.batch_ai_analysis",
        display_name=f"一键分析 {body.stock_name}（{body.stock_code}）",
        task_type=SINGLE_TASK_TYPE,
        user_id=current_user.id,
        task_params={
            "ts_codes": [ts_code],
            "analysis_types": list(body.analysis_types),
            "include_cio": body.include_cio,
            "reuse_existing_experts": body.reuse_existing_experts,
            "concurrency": 1,
        },
        source="analysis_page",
    )

    batch_ai_analysis_task.apply_async(
        task_id=celery_task_id,
        kwargs={
            "ts_codes": [ts_code],
            "stock_names": {ts_code: body.stock_name},
            "analysis_types": list(body.analysis_types),
            "include_cio": body.include_cio,
            "reuse_existing_experts": body.reuse_existing_experts,
            "user_id": current_user.id,
            "concurrency": 1,
        },
    )

    return ApiResponse.success(
        data={"celery_task_id": celery_task_id, "ts_code": ts_code},
        message="一键分析任务已提交，请等待生成完成",
    ).to_dict()


# ------------------------------------------------------------------
# 批量 AI 分析（异步）
# ------------------------------------------------------------------

class BatchAnalysisRequest(BaseModel):
    ts_codes: list[str] = Field(..., min_length=1, description="股票 ts_code 列表，如 ['000001.SZ', '600519.SH']")
    analysis_types: list[str] = Field(
        default_factory=lambda: ["hot_money_view", "midline_industry_expert", "longterm_value_watcher"],
        description="分析类型列表，默认 3 专家",
    )
    include_cio: bool = Field(True, description="是否追加 CIO 综合决策")
    reuse_existing_experts: bool = Field(
        True,
        description="同一交易日已有合法专家报告时是否复用（默认开启，避免重复消耗 LLM 配额）。"
                    "CIO 始终重跑。",
    )
    concurrency: Optional[int] = Field(
        None,
        ge=1, le=8,
        description="股票层面并发数（1~8），不传走默认 4。提高可加速但占更多 LLM 配额",
    )


@router.post("/batch")
@handle_api_errors
async def submit_batch_analysis(
    body: BatchAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
):
    """提交批量 AI 分析任务，后端异步执行，返回 celery_task_id 供前端轮询。"""
    from app.services.stock_quote_cache import stock_quote_cache
    from app.services.task_history_helper import TaskHistoryHelper
    from app.tasks.batch_ai_analysis_tasks import batch_ai_analysis_task, TASK_TYPE, MAX_BATCH_SIZE

    # 去重 + 规范化
    ts_codes = list(dict.fromkeys(c.strip().upper() for c in body.ts_codes if c and c.strip()))
    if not ts_codes:
        return ApiResponse.bad_request(message="ts_codes 不能为空").to_dict()

    # 单批上限保护：超过 MAX_BATCH_SIZE 拒绝（任务级 soft_time_limit 7200s 是按此规模设计的）
    if len(ts_codes) > MAX_BATCH_SIZE:
        return ApiResponse.bad_request(
            message=(
                f"单次批量 AI 分析最多 {MAX_BATCH_SIZE} 只股票，本次提交 {len(ts_codes)} 只。"
                f"请分批提交，或使用更小的选股策略缩减结果集。"
            )
        ).to_dict()

    # 校验 analysis_types
    invalid = [t for t in body.analysis_types if t not in _JSON_ANALYSIS_TYPES and t != "stock_data_collection"]
    if invalid:
        return ApiResponse.bad_request(message=f"不支持的分析类型: {invalid}").to_dict()

    # 批量查股票名（走 StockQuoteCache）；查询失败不致命，回落到纯数字代码
    try:
        quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
    except Exception as e:
        logger.warning(f"[batch] 查询股票名失败，fallback 用代码: {e}")
        quotes = {}
    stock_names = {
        ts: (quotes.get(ts, {}).get("name") or ts.split(".")[0])
        for ts in ts_codes
    }

    # 先生成 Celery task_id 并登记历史记录，再 apply_async 提交任务。
    # 避免 worker 已经开始跑、update_batch_progress() 找不到 WHERE celery_task_id=? 记录。
    celery_task_id = str(uuid.uuid4())

    await TaskHistoryHelper().create_task_record(
        celery_task_id=celery_task_id,
        task_name="tasks.batch_ai_analysis",
        display_name=f"批量 AI 分析（{len(ts_codes)} 只）",
        task_type=TASK_TYPE,
        user_id=current_user.id,
        task_params={
            "ts_codes": ts_codes,
            "analysis_types": list(body.analysis_types),
            "include_cio": body.include_cio,
            "reuse_existing_experts": body.reuse_existing_experts,
            "concurrency": body.concurrency,
        },
        source="stocks_page",
    )

    batch_ai_analysis_task.apply_async(
        task_id=celery_task_id,
        kwargs={
            "ts_codes": ts_codes,
            "stock_names": stock_names,
            "analysis_types": list(body.analysis_types),
            "include_cio": body.include_cio,
            "reuse_existing_experts": body.reuse_existing_experts,
            "user_id": current_user.id,
            "concurrency": body.concurrency,
        },
    )

    return ApiResponse.success(
        data={"celery_task_id": celery_task_id, "total": len(ts_codes)},
        message=f"已提交 {len(ts_codes)} 只股票的批量分析任务",
    ).to_dict()


@router.get("/batch/{celery_task_id}")
@handle_api_errors
async def get_batch_analysis(
    celery_task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """查询批量 AI 分析任务进度（供前端 3 秒轮询）。"""
    from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository

    repo = CeleryTaskHistoryRepository()
    record = await asyncio.to_thread(repo.get_by_task_id, celery_task_id)
    if record is None:
        return ApiResponse.not_found(message="任务不存在").to_dict()
    if record.get("user_id") != current_user.id:
        return ApiResponse.bad_request(message="无权查看该任务").to_dict()

    metadata = record.get("metadata") or {}
    return ApiResponse.success(data={
        "celery_task_id": record["celery_task_id"],
        "status": record["status"],
        "progress": record.get("progress") or 0,
        "total_items": record.get("total_items"),
        "completed_items": record.get("completed_items"),
        "success_items": record.get("success_items"),
        "failed_items": record.get("failed_items"),
        "items": metadata.get("items") or [],
        "created_at": record.get("created_at").isoformat() if record.get("created_at") else None,
        "completed_at": record.get("completed_at").isoformat() if record.get("completed_at") else None,
        "error": record.get("error"),
    }).to_dict()


@router.get("/batch/active/ts-codes")
@handle_api_errors
async def get_active_batch_ts_codes(
    current_user: User = Depends(get_current_active_user),
):
    """返回当前用户所有活跃 AI 分析任务中"尚未完成"的 ts_code 集合。

    覆盖批量分析（task_type=batch_ai_analysis）和单只一键分析（task_type=single_ai_analysis），
    用于股票列表页标记"分析中"的股票，支持刷新后恢复显示。
    """
    from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
    from app.tasks.batch_ai_analysis_tasks import TASK_TYPE, SINGLE_TASK_TYPE

    repo = CeleryTaskHistoryRepository()
    ts_codes = await asyncio.to_thread(
        repo.get_active_batch_ts_codes, current_user.id, [TASK_TYPE, SINGLE_TASK_TYPE],
    )
    return ApiResponse.success(data={"ts_codes": ts_codes}).to_dict()


@router.get("/active/by-ts-code/{ts_code}")
@handle_api_errors
async def get_active_task_by_ts_code(
    ts_code: str,
    current_user: User = Depends(get_current_active_user),
):
    """查询某只股票当前是否有活跃的 AI 分析任务（批量或单只一键），返回其 celery_task_id。

    供 /analysis 页面刷新后恢复"分析中"状态：命中则前端续轮询 /batch/{id}，
    完成后正常刷新各专家最新数据。
    """
    from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
    from app.tasks.batch_ai_analysis_tasks import TASK_TYPE, SINGLE_TASK_TYPE

    normalized = (ts_code or "").strip().upper()
    if not normalized:
        return ApiResponse.bad_request(message="ts_code 不能为空").to_dict()

    repo = CeleryTaskHistoryRepository()
    task_id = await asyncio.to_thread(
        repo.get_active_task_id_by_ts_code,
        current_user.id, normalized, [TASK_TYPE, SINGLE_TASK_TYPE],
    )
    return ApiResponse.success(data={"celery_task_id": task_id}).to_dict()


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
