"""
股票AI分析结果 API 端点
支持保存分析结果（游资观点等多种类型）、查询最新版本、浏览历史版本
"""

import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_ai_analysis_service import StockAiAnalysisService
from sqlalchemy.orm import Session


def _extract_json_and_score(ai_text: str) -> tuple[str, Optional[float]]:
    """
    从 AI 返回文本中：
    1. 去掉 ```json ... ``` 代码块标识，只保留纯 JSON 内容
    2. 尝试用 Pydantic 模型提取评分，失败降级为手动路径查找

    返回 (cleaned_text, score_or_None)
    """
    from app.schemas.ai_analysis_result import StockExpertAnalysisResult
    from app.services.ai_output_parser import extract_json_text, parse_ai_json

    # 提取纯 JSON 文本
    json_text = extract_json_text(ai_text)
    cleaned = json_text if json_text else ai_text.strip()

    # 优先：Pydantic 结构化解析 + 评分提取
    parsed = parse_ai_json(ai_text, StockExpertAnalysisResult)
    if parsed is not None:
        score = parsed.extract_score()
        if score is not None:
            return cleaned, score

    # 降级：手动路径查找
    _SCORE_PATHS = [
        ["final_score", "score"],   # 游资观点
        ["comprehensive_score"],    # 中线专家 / 价值守望者 / CIO
        ["score"],                  # CIO 简单结构兜底
    ]

    score: Optional[float] = None
    try:
        data = json.loads(cleaned)
        for path in _SCORE_PATHS:
            node = data
            for key in path:
                if not isinstance(node, dict):
                    node = None
                    break
                node = node.get(key)
            if node is not None:
                try:
                    candidate = float(node)
                    if 0 <= candidate <= 10:
                        score = candidate
                        break
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass

    return cleaned, score


# 需要走 JSON 清洗 + 评分提取的分析类型集合
_JSON_ANALYSIS_TYPES = {
    "hot_money_view",
    "midline_industry_expert",
    "longterm_value_watcher",
    "cio_directive",
    "macro_risk_expert",
}

router = APIRouter(prefix="/stock-ai-analysis", tags=["股票AI分析"])


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
# 端点
# ------------------------------------------------------------------

@router.get("/list")
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
    ai_service = AIStrategyService()
    provider_name = prompt_data["recommended_provider"]
    provider_config = ai_service.get_provider_config(provider_name)
    provider_config["temperature"] = prompt_data["recommended_temperature"]
    provider_config["max_tokens"] = prompt_data["recommended_max_tokens"]

    # 3. 调用 AI 生成
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
        return ApiResponse.error(message=f"AI 调用失败: {e}", code=500).to_dict()

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
async def generate_multi_analysis(
    body: GenerateMultiRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """并行调用多个 AI 专家分析同一只股票，数据收集只做一次。

    使用 LCEL RunnableParallel 并行编排多个专家。
    可选：所有专家完成后追加 CIO 综合决策步骤。
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

        client = ai_service.create_client(provider_name, provider_config)
        start_time = time.time()
        ai_text, tokens_used = await client.generate_strategy(full_prompt)
        generation_time = time.time() - start_time

        logger.info(
            f"[generate_multi] {body.ts_code} {analysis_type} "
            f"生成完成: {len(ai_text)}字 / {tokens_used} tokens / {generation_time:.2f}s"
        )

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

    # 4. 可选：CIO 综合决策（串联步骤，将前面专家的输出作为输入）
    cio_result = None
    if body.include_cio and results:
        try:
            cio_template_key = _DEFAULT_TEMPLATE_KEYS["cio_directive"]
            cio_prompt_data = await build_stock_prompt(
                template_key=cio_template_key,
                stock_name=body.stock_name,
                stock_code=body.stock_code,
                ts_code=body.ts_code,
                created_by=current_user.id,
                db=db,
                allow_generate_data_collection=True,
            )

            # 将前面专家的结论摘要注入 CIO prompt
            expert_summary_lines = []
            for r in results:
                score_str = f"（评分: {r['score']}）" if r.get("score") is not None else ""
                # 截取前 500 字作为摘要
                text_preview = r.get("analysis_text", "")[:500]
                expert_summary_lines.append(
                    f"### {r['analysis_type']}{score_str}\n{text_preview}\n"
                )
            expert_summary = "\n".join(expert_summary_lines)

            system_prompt = cio_prompt_data["system_prompt"]
            user_prompt = cio_prompt_data["user_prompt"]
            full_cio_prompt = (
                f"{system_prompt}\n\n"
                f"【其他专家分析结论（供 CIO 参考）】\n{expert_summary}\n\n"
                f"{user_prompt}"
            ).strip()

            provider_name = cio_prompt_data["recommended_provider"]
            provider_config = ai_service.get_provider_config(provider_name)
            provider_config["temperature"] = cio_prompt_data["recommended_temperature"]
            provider_config["max_tokens"] = cio_prompt_data["recommended_max_tokens"]

            client = ai_service.create_client(provider_name, provider_config)
            start_time = time.time()
            cio_text, cio_tokens = await client.generate_strategy(full_cio_prompt)
            cio_gen_time = time.time() - start_time

            cio_text, cio_score = _extract_json_and_score(cio_text)

            cio_saved = await StockAiAnalysisService().save_analysis(
                ts_code=body.ts_code,
                analysis_type="cio_directive",
                analysis_text=cio_text,
                score=cio_score,
                prompt_text=full_cio_prompt,
                ai_provider=provider_name,
                ai_model=provider_config.get("model_name"),
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
            }
        except Exception as e:
            logger.error(f"[generate_multi] CIO 综合决策失败: {e}", exc_info=True)
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
