"""
AI 分析结果的 Pydantic 结构化输出模型

将 AI 返回的 JSON 解析为强类型对象，替代各 Service 中分散的正则 JSON 提取。
配合 ai_output_parser.parse_ai_json() 使用，解析失败时自动降级为原始 dict。

三类分析场景：
  - SentimentAnalysisResult: 市场情绪 AI 分析（sentiment_ai_analysis_service）
  - CollisionAnalysisResult: 盘前碰撞分析（premarket_analysis_service）
  - StockExpertAnalysisResult: 个股专家分析（stock_ai_analysis 端点，游资/中线/长线/CIO/宏观风险）
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================
# 1. 市场情绪 AI 分析
# ============================================================

class MaxContinuousStock(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    days: Optional[int] = None


class SpaceAnalysis(BaseModel):
    max_continuous_stock: Optional[MaxContinuousStock] = None
    theme: Optional[str] = None
    space_level: Optional[str] = Field(None, description="超高空间|高空间|中等空间|低空间")
    analysis: Optional[str] = None


class SentimentSection(BaseModel):
    money_making_effect: Optional[str] = Field(None, description="超强|中等|较差|极差")
    strategy: Optional[str] = Field(None, description="激进进攻|稳健参与|防守为主|空仓观望")
    reasoning: Optional[str] = None


class HotMoneyDirection(BaseModel):
    themes: Optional[List[str]] = None
    stocks: Optional[List[str]] = None
    concentration: Optional[str] = Field(None, description="高度集中|分散|无明显方向")


class InstitutionDirection(BaseModel):
    sectors: Optional[List[str]] = None
    style: Optional[str] = Field(None, description="防御性|进攻性|均衡配置")


class CapitalFlowAnalysis(BaseModel):
    hot_money_direction: Optional[HotMoneyDirection] = None
    institution_direction: Optional[InstitutionDirection] = None
    capital_consensus: Optional[str] = Field(
        None, description="游资机构共振|游资单边进攻|机构独立建仓|资金分歧"
    )
    analysis: Optional[str] = None


class CallAuctionTactics(BaseModel):
    participate_conditions: Optional[str] = None
    avoid_conditions: Optional[str] = None


class OpeningHalfHourTactics(BaseModel):
    low_buy_opportunities: Optional[str] = None
    chase_opportunities: Optional[str] = None
    wait_signals: Optional[str] = None


class TomorrowTactics(BaseModel):
    call_auction_tactics: Optional[CallAuctionTactics] = None
    opening_half_hour_tactics: Optional[OpeningHalfHourTactics] = None
    buy_conditions: Optional[List[str]] = None
    stop_loss_conditions: Optional[List[str]] = None


class SentimentAnalysisResult(BaseModel):
    """市场情绪 AI 分析的结构化输出"""
    space_analysis: Optional[SpaceAnalysis] = None
    sentiment_analysis: Optional[SentimentSection] = None
    capital_flow_analysis: Optional[CapitalFlowAnalysis] = None
    tomorrow_tactics: Optional[TomorrowTactics] = None


# ============================================================
# 2. 盘前碰撞分析
# ============================================================

class MacroTone(BaseModel):
    direction: Optional[str] = Field(None, description="高开|低开|平开")
    confidence: Optional[str] = None
    a50_impact: Optional[str] = None
    reasoning: Optional[str] = None


class AffectedStock(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    reason: Optional[str] = None


class HoldingsAlert(BaseModel):
    has_risk: Optional[bool] = None
    affected_sectors: Optional[List[str]] = None
    affected_stocks: Optional[List[AffectedStock]] = None
    actions: Optional[str] = None


class PlanAdjustmentItem(BaseModel):
    stock: Optional[str] = None
    reason: Optional[str] = None


class PlanAdjustment(BaseModel):
    cancel_buy: Optional[List[PlanAdjustmentItem]] = None
    early_stop_loss: Optional[List[PlanAdjustmentItem]] = None
    keep_plan: Optional[str] = None
    reasoning: Optional[str] = None


class AuctionStock(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    reason: Optional[str] = None


class AuctionConditions(BaseModel):
    participate_conditions: Optional[str] = None
    avoid_conditions: Optional[str] = None


class AuctionFocus(BaseModel):
    stocks: Optional[List[AuctionStock]] = None
    conditions: Optional[AuctionConditions] = None
    actions: Optional[str] = None


class CollisionAnalysisResult(BaseModel):
    """盘前碰撞分析的结构化输出"""
    macro_tone: Optional[MacroTone] = None
    holdings_alert: Optional[HoldingsAlert] = None
    plan_adjustment: Optional[PlanAdjustment] = None
    auction_focus: Optional[AuctionFocus] = None


# ============================================================
# 3. 个股专家分析（支持多种专家类型的评分提取）
# ============================================================

class FinalScore(BaseModel):
    """游资观点/宏观风险专家的 final_score 子对象"""
    score: Optional[float] = Field(None, ge=0, le=10)
    rating: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None


class StockExpertAnalysisResult(BaseModel):
    """
    个股专家分析的结构化输出（统一模型，兼容多种专家类型）。

    评分提取优先级：
    1. final_score.score  — 游资观点 / 宏观风险专家
    2. comprehensive_score — 中线专家 / 长线价值守望者 / CIO
    3. score              — CIO 简单结构兜底
    """
    final_score: Optional[FinalScore] = None
    comprehensive_score: Optional[float] = Field(None, ge=0, le=10)
    score: Optional[float] = Field(None, ge=0, le=10)

    class Config:
        extra = "allow"  # 允许额外字段（各专家输出格式不完全一致）

    def extract_score(self) -> Optional[float]:
        """按优先级提取评分"""
        if self.final_score and self.final_score.score is not None:
            s = self.final_score.score
            if 0 <= s <= 10:
                return s
        if self.comprehensive_score is not None:
            if 0 <= self.comprehensive_score <= 10:
                return self.comprehensive_score
        if self.score is not None:
            if 0 <= self.score <= 10:
                return self.score
        return None
