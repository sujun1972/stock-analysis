"""
统一策略系统 Pydantic Schema 定义

根据 UNIFIED_DYNAMIC_STRATEGY_ARCHITECTURE.md Phase 2 设计
所有策略统一存储在 strategies 表中，不再区分预定义/配置/动态

作者: Backend Team
创建日期: 2026-02-09
版本: 2.0.0
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== 请求模型 ====================


class StrategyCreate(BaseModel):
    """创建策略请求模型"""

    name: str = Field(..., description="策略唯一标识", min_length=1, max_length=100)
    display_name: str = Field(..., description="显示名称", min_length=1, max_length=200)

    # 核心代码
    code: str = Field(..., description="完整的 Python 类代码", min_length=1)
    class_name: str = Field(..., description="类名", min_length=1, max_length=100)

    # 来源分类
    source_type: str = Field(
        ...,
        description="来源类型: builtin (系统内置), ai (AI生成), custom (用户自定义)"
    )
    strategy_type: str = Field(
        "entry",
        description="策略类型: entry (入场策略), exit (离场策略)"
    )

    # 策略元信息
    description: Optional[str] = Field(None, description="策略说明")
    category: Optional[str] = Field(None, description="类别")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签数组")

    # 默认参数
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认参数 JSON")

    # 版本和审计
    parent_strategy_id: Optional[int] = Field(None, description="父策略ID")
    created_by: Optional[str] = Field(None, description="创建人")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v):
        """验证来源类型"""
        allowed = ["builtin", "ai", "custom"]
        if v not in allowed:
            raise ValueError(f"source_type 必须是以下之一: {', '.join(allowed)}")
        return v

    @field_validator("strategy_type")
    @classmethod
    def validate_strategy_type(cls, v):
        """验证策略类型"""
        allowed = ["entry", "exit"]
        if v not in allowed:
            raise ValueError(f"strategy_type 必须是以下之一: {', '.join(allowed)}")
        return v

    @field_validator("class_name")
    @classmethod
    def validate_class_name(cls, v):
        """验证类名格式"""
        if not v[0].isupper():
            raise ValueError("类名必须以大写字母开头")
        if not v.replace('_', '').isalnum():
            raise ValueError("类名只能包含字母、数字和下划线")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        """验证类别"""
        if v is not None:
            allowed = ["momentum", "reversal", "factor", "ml", "arbitrage", "hybrid"]
            if v not in allowed:
                raise ValueError(f"category 必须是以下之一: {', '.join(allowed)}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "momentum_20d",
                "display_name": "动量策略 20日",
                "code": "class MomentumStrategy(BaseStrategy):\n    ...",
                "class_name": "MomentumStrategy",
                "source_type": "builtin",
                "description": "基于20日动量选股",
                "category": "momentum",
                "tags": ["动量", "趋势", "短期"],
                "default_params": {
                    "lookback_period": 20,
                    "top_n": 50,
                    "holding_period": 5
                },
                "created_by": "system"
            }
        }
    }


class StrategyUpdate(BaseModel):
    """更新策略请求模型"""

    display_name: Optional[str] = Field(None, description="显示名称", max_length=200)
    description: Optional[str] = Field(None, description="策略说明")
    code: Optional[str] = Field(None, description="完整的 Python 类代码")
    tags: Optional[List[str]] = Field(None, description="标签数组")
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认参数")
    is_enabled: Optional[bool] = Field(None, description="是否启用")

    model_config = {
        "json_schema_extra": {
            "example": {
                "display_name": "动量策略 20日 v2",
                "description": "优化后的20日动量选股策略",
                "is_enabled": True,
                "tags": ["动量", "趋势", "优化"]
            }
        }
    }


class ValidateCodeRequest(BaseModel):
    """验证代码请求模型"""

    code: str = Field(..., description="Python策略代码", min_length=1)
    strict_mode: bool = Field(True, description="严格模式")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "class MyStrategy(BaseStrategy):\n    def calculate_scores(self, prices, features, date):\n        return scores",
                "strict_mode": True
            }
        }
    }


# ==================== 响应模型 ====================


class ValidationResult(BaseModel):
    """代码验证结果"""

    is_valid: bool = Field(..., description="是否通过验证")
    status: str = Field(..., description="验证状态: passed/failed/warning")
    risk_level: str = Field(..., description="风险等级: safe/low/medium/high")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    security_issues: List[str] = Field(default_factory=list, description="安全问题列表")


class StrategyResponse(BaseModel):
    """策略响应模型"""

    # 主键和标识
    id: int = Field(..., description="策略ID")
    name: str = Field(..., description="策略唯一标识")
    display_name: str = Field(..., description="显示名称")

    # 核心代码
    code: str = Field(..., description="完整的 Python 类代码")
    code_hash: str = Field(..., description="SHA256 校验值")
    class_name: str = Field(..., description="类名")

    # 来源分类
    source_type: str = Field(..., description="来源类型: builtin/ai/custom")
    strategy_type: str = Field("entry", description="策略类型: entry/exit")

    # 策略元信息
    description: Optional[str] = Field(None, description="策略说明")
    category: Optional[str] = Field(None, description="类别")
    tags: List[str] = Field(default_factory=list, description="标签数组")

    # 默认参数
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认参数 JSON")

    # 状态和验证
    validation_status: str = Field(..., description="验证状态")
    validation_errors: Optional[Dict[str, Any]] = Field(None, description="验证错误详情")
    validation_warnings: Optional[Dict[str, Any]] = Field(None, description="验证警告")
    risk_level: str = Field(..., description="风险等级")
    is_enabled: bool = Field(..., description="是否启用")

    # 使用统计
    usage_count: int = Field(0, description="使用次数")
    backtest_count: int = Field(0, description="回测次数")
    avg_sharpe_ratio: Optional[float] = Field(None, description="平均夏普率")
    avg_annual_return: Optional[float] = Field(None, description="平均年化收益")

    # 版本和审计
    version: int = Field(1, description="版本号")
    parent_strategy_id: Optional[int] = Field(None, description="父策略ID")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")

    model_config = {"from_attributes": True}


class StrategyListResponse(BaseModel):
    """策略列表响应模型"""

    # 只包含必要字段，不包含完整代码
    id: int
    name: str
    display_name: str
    class_name: str
    source_type: str
    strategy_type: str
    description: Optional[str]
    category: Optional[str]
    tags: List[str]
    validation_status: str
    risk_level: str
    is_enabled: bool
    usage_count: int
    backtest_count: int
    avg_sharpe_ratio: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyStatistics(BaseModel):
    """策略统计信息"""

    total_count: int = Field(..., description="总策略数")
    enabled_count: int = Field(..., description="启用策略数")
    disabled_count: int = Field(..., description="禁用策略数")
    by_source: Dict[str, int] = Field(..., description="按来源分组统计")
    by_category: Dict[str, int] = Field(..., description="按类别分组统计")
    by_validation: Dict[str, int] = Field(..., description="按验证状态分组统计")
    by_risk: Dict[str, int] = Field(..., description="按风险等级分组统计")


# ==================== 简化回测请求 ====================


class SimplifiedBacktestRequest(BaseModel):
    """简化的回测请求模型 (Phase 2 统一版)"""

    # 策略选择
    strategy_id: int = Field(..., description="策略ID")

    # 回测参数
    stock_pool: List[str] = Field(..., description="股票代码列表", min_length=1)
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, gt=0, description="初始资金")

    # 交易成本参数
    commission_rate: float = Field(0.0003, ge=0, le=0.01, description="佣金费率")
    stamp_tax_rate: float = Field(0.001, ge=0, le=0.01, description="印花税率")
    min_commission: float = Field(5.0, ge=0, description="最小佣金")
    slippage: float = Field(0.0, ge=0, description="滑点")

    # 高级选项
    strict_mode: bool = Field(True, description="严格模式")

    # 离场策略（可选，支持多个）
    exit_strategy_ids: Optional[List[int]] = Field(None, description="离场策略ID列表")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式错误，应为 YYYY-MM-DD: {v}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "strategy_id": 1,
                "stock_pool": ["000001.SZ", "600000.SH"],
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 1000000.0,
                "commission_rate": 0.0003,
                "stamp_tax_rate": 0.001,
                "strict_mode": True
            }
        }
    }
