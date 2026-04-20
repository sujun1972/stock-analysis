"""股票AI分析结果 Service"""
import json
import asyncio
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.stock_ai_analysis_repository import StockAiAnalysisRepository
from app.services.ai_output_parser import extract_json_text, parse_ai_json

ALLOWED_ANALYSIS_TYPES = {
    "hot_money_view",
    "hot_money_review",
    "stock_data_collection",
    "midline_industry_expert",
    "midline_review",
    "longterm_value_watcher",
    "longterm_review",
    "cio_directive",
    "macro_risk_expert",
}

# 需要走 JSON 清洗 + 评分提取的分析类型集合
JSON_ANALYSIS_TYPES = {
    "hot_money_view",
    "hot_money_review",
    "midline_industry_expert",
    "midline_review",
    "longterm_value_watcher",
    "longterm_review",
    "cio_directive",
    "macro_risk_expert",
}

# 评分查找路径（优先级从高到低）
_SCORE_PATHS = [
    ["final_score", "score"],   # 游资观点
    ["comprehensive_score"],    # 中线专家 / 价值守望者 / CIO
    ["score"],                  # CIO 简单结构兜底
]


def extract_json_and_score(ai_text: str) -> tuple[str, Optional[float]]:
    """
    从 AI 返回文本中：
    1. 去掉 ```json ... ``` 代码块标识，只保留纯 JSON 内容
    2. 尝试用 Pydantic 模型提取评分，失败降级为手动路径查找

    返回 (cleaned_text, score_or_None)
    """
    from app.schemas.ai_analysis_result import StockExpertAnalysisResult

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


class StockAiAnalysisService:
    def __init__(self):
        self.repo = StockAiAnalysisRepository()

    async def save_analysis(
        self,
        ts_code: str,
        analysis_type: str,
        analysis_text: str,
        score: Optional[float],
        prompt_text: Optional[str],
        ai_provider: Optional[str],
        ai_model: Optional[str],
        created_by: Optional[int],
        trade_date: Optional[str] = None,
        original_analysis_id: Optional[int] = None,
    ) -> Dict:
        """校验并保存一条新的分析记录（每次保存都是新版本）"""
        if not ts_code or not ts_code.strip():
            raise ValueError("ts_code 不能为空")
        if analysis_type not in ALLOWED_ANALYSIS_TYPES:
            raise ValueError(f"不支持的分析类型: {analysis_type}，允许值: {ALLOWED_ANALYSIS_TYPES}")
        if not analysis_text or not analysis_text.strip():
            raise ValueError("analysis_text 不能为空")
        if score is not None and not (0 <= score <= 10):
            raise ValueError("score 必须在 0-10 之间")

        return await asyncio.to_thread(
            self.repo.save,
            ts_code.strip(), analysis_type, analysis_text.strip(),
            score, prompt_text, ai_provider, ai_model, created_by,
            trade_date, original_analysis_id,
        )

    async def update_analysis(
        self,
        record_id: int,
        analysis_text: str,
        score: Optional[float],
        current_user_id: int,
    ) -> Optional[Dict]:
        """校验权限后更新分析文本和评分"""
        if not analysis_text or not analysis_text.strip():
            raise ValueError("analysis_text 不能为空")
        if score is not None and not (0 <= score <= 10):
            raise ValueError("score 必须在 0-10 之间")
        rec = await asyncio.to_thread(self.repo.get_by_id, record_id)
        if rec is None:
            return None
        if rec.get("created_by") != current_user_id:
            raise PermissionError("无权修改他人的分析记录")
        return await asyncio.to_thread(self.repo.update, record_id, analysis_text.strip(), score)

    async def delete_analysis(
        self, record_id: int, current_user_id: int, user_role: str = ""
    ) -> bool:
        """校验权限后删除记录（管理员可删除任意记录）"""
        rec = await asyncio.to_thread(self.repo.get_by_id, record_id)
        if rec is None:
            return False
        is_admin = user_role in ("admin", "super_admin")
        if not is_admin and rec.get("created_by") != current_user_id:
            raise PermissionError("无权删除他人的分析记录")
        return await asyncio.to_thread(self.repo.delete, record_id)

    async def get_latest(self, ts_code: str, analysis_type: str) -> Optional[Dict]:
        """获取指定股票+类型的最新分析结果"""
        return await asyncio.to_thread(self.repo.get_latest, ts_code, analysis_type)

    async def get_history(
        self,
        ts_code: str,
        analysis_type: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """获取所有版本历史（分页），返回 {'items': [...], 'total': N}"""
        items, total = await asyncio.gather(
            asyncio.to_thread(self.repo.get_history, ts_code, analysis_type, limit, offset),
            asyncio.to_thread(self.repo.get_history_count, ts_code, analysis_type),
        )
        return {"items": items, "total": total}

    async def list_all(
        self,
        ts_code: Optional[str] = None,
        analysis_type: Optional[str] = None,
        ai_provider: Optional[str] = None,
        trade_date: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """查询所有分析记录（分页），返回 {'items': [...], 'total': N}"""
        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.repo.list_all,
                ts_code, analysis_type, ai_provider, trade_date,
                sort_by, sort_order, limit, offset,
            ),
            asyncio.to_thread(
                self.repo.count_all,
                ts_code, analysis_type, ai_provider, trade_date,
            ),
        )
        return {"items": items, "total": total}

    async def enrich_stock_list(self, items: List[Dict], analysis_type: str) -> List[Dict]:
        """
        批量注入最新分析摘要到股票列表数据。
        每个 item 添加 latest_analysis 字段（无记录时为 None）。
        """
        ts_codes = [item["ts_code"] for item in items if item.get("ts_code")]
        if not ts_codes:
            return items
        try:
            latest_map = await asyncio.to_thread(
                self.repo.get_latest_batch, ts_codes, analysis_type
            )
        except Exception as e:
            logger.warning(f"批量查询AI分析摘要失败，跳过注入: {e}")
            for item in items:
                item["latest_analysis"] = None
            return items

        for item in items:
            rec = latest_map.get(item.get("ts_code"))
            if rec:
                item["latest_analysis"] = {
                    "id": rec["id"],
                    "score": rec["score"],
                    "version": rec["version"],
                    "created_at": rec["created_at"],
                }
            else:
                item["latest_analysis"] = None
        return items

    async def enrich_stock_list_multi(self, items: List[Dict]) -> List[Dict]:
        """
        并发批量注入游资观点、中线专家、价值守望者三种类型的最新评分摘要。
        各自注入字段：latest_analysis_hot_money / latest_analysis_midline / latest_analysis_longterm
        """
        ts_codes = [item["ts_code"] for item in items if item.get("ts_code")]
        if not ts_codes:
            return items

        analysis_types = [
            ("hot_money_view",        "latest_analysis_hot_money"),
            ("midline_industry_expert","latest_analysis_midline"),
            ("longterm_value_watcher", "latest_analysis_longterm"),
        ]

        try:
            maps = await asyncio.gather(*[
                asyncio.to_thread(self.repo.get_latest_batch, ts_codes, atype)
                for atype, _ in analysis_types
            ])
        except Exception as e:
            logger.warning(f"批量查询多类型AI分析摘要失败，跳过注入: {e}")
            for item in items:
                for _, field in analysis_types:
                    item[field] = None
            return items

        for item in items:
            ts = item.get("ts_code")
            for (_, field), latest_map in zip(analysis_types, maps):
                rec = latest_map.get(ts)
                item[field] = {
                    "id": rec["id"],
                    "score": rec["score"],
                    "version": rec["version"],
                    "created_at": rec["created_at"],
                } if rec else None
        return items
