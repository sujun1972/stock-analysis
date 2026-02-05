"""
特征工程 API (重构版本)

✅ 任务 0.4: 重写 Features API
- 使用 Core Adapters 代替 FeatureService
- Backend 只负责：参数验证、分页、响应格式化
- 业务逻辑全部由 Core 处理

作者: Backend Team
创建日期: 2026-02-01
版本: 2.0.0 (架构修正版)
"""

from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime
from loguru import logger
import pandas as pd
import numpy as np

from app.core_adapters.feature_adapter import FeatureAdapter
from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse
from app.core.exceptions import DataNotFoundError, CalculationError, ValidationError

router = APIRouter()

# 全局适配器实例
feature_adapter = FeatureAdapter()
data_adapter = DataAdapter()


@router.get("/{code}")
async def get_features(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    feature_type: Optional[str] = None,
    limit: int = 500
):
    """
    获取股票特征数据（支持懒加载）

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、分页、响应格式化
    - Core 负责：特征计算、数据库查询

    参数:
    - code: 股票代码
    - start_date: 开始日期（默认最近 500 天）
    - end_date: 结束日期（默认今天）
    - feature_type: 特征类型
      - technical: 技术指标 (MA, MACD, RSI, KDJ 等 50+ 指标)
      - alpha: Alpha 因子 (动量、反转、波动率等 30+ 因子)
      - all: 所有特征 (125+ 特征)
    - limit: 返回记录数限制

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "feature_type": "all",
            "total": 1000,
            "returned": 500,
            "has_more": true,
            "columns": ["date", "close", "ma_5", "ma_10", ...],
            "data": [...]
        }
    }
    """
    try:
        # 1. 参数转换
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError as e:
        return ApiResponse.bad_request(
            message=f"日期格式错误: {str(e)}"
        ).to_dict()

    # 2. 调用 Core Adapter 获取日线数据
    df = await data_adapter.get_daily_data(
        code=code,
        start_date=start_dt,
        end_date=end_dt
    )

    if df.empty:
        return ApiResponse.not_found(
            message=f"股票 {code} 无日线数据"
        ).to_dict()

    # 3. 调用 Core Adapter 计算特征
    if feature_type == "technical":
        df_with_features = await feature_adapter.add_technical_indicators(df)
    elif feature_type == "alpha":
        df_with_features = await feature_adapter.add_alpha_factors(df)
    else:  # all 或 None
        df_with_features = await feature_adapter.add_all_features(df)

    # 4. Backend 职责：数据处理和格式化
    # 重置索引
    df_reset = df_with_features.reset_index()

    # 替换 Inf 和 NaN 为 None（JSON 序列化）
    df_reset = df_reset.replace([np.inf, -np.inf], np.nan)

    # 按日期降序排列（从新到旧）
    if 'date' in df_reset.columns:
        df_reset = df_reset.sort_values('date', ascending=False)

    # 获取总数
    total_count = len(df_reset)

    # 限制返回数量
    df_limited = df_reset.head(limit)

    # 转换为字典列表，将 NaN 转为 None
    data_list = [
        {k: (None if pd.isna(v) else v) for k, v in record.items()}
        for record in df_limited.to_dict('records')
    ]

    # 5. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "code": code,
            "feature_type": feature_type or "all",
            "total": total_count,
            "returned": len(data_list),
            "has_more": total_count > limit,
            "columns": list(df_with_features.columns),
            "data": data_list
        },
        message="获取特征数据成功"
    ).to_dict()


@router.post("/calculate/{code}")
async def calculate_features(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    feature_types: List[str] = ["technical", "alpha"],
    include_transforms: bool = False
):
    """
    计算股票特征（支持批量计算）

    ✅ 架构修正版：调用 Core Adapter 的特征计算方法

    参数:
    - code: 股票代码
    - start_date: 开始日期（默认最近 100 天）
    - end_date: 结束日期（默认今天）
    - feature_types: 特征类型列表
    - include_transforms: 是否包含特征转换（标准化、归一化等）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "record_count": 100,
            "feature_count": 125,
            "feature_types": ["technical", "alpha"],
            "columns": [...],
            "sample_data": [...]  // 前 10 条数据
        }
    }
    """
    try:
        # 1. 参数转换
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError as e:
        return ApiResponse.bad_request(
            message=f"参数错误: {str(e)}"
        ).to_dict()

    # 2. 调用 Core Adapter 获取日线数据
    df = await data_adapter.get_daily_data(
        code=code,
        start_date=start_dt,
        end_date=end_dt
    )

    if df.empty:
        return ApiResponse.not_found(
            message=f"股票 {code} 无日线数据"
        ).to_dict()

    # 3. 调用 Core Adapter 计算特征
    df_with_features = await feature_adapter.add_all_features(
        df,
        include_indicators="technical" in feature_types,
        include_factors="alpha" in feature_types,
        include_transforms=include_transforms
    )

    # 4. 准备响应数据
    df_reset = df_with_features.reset_index()
    df_reset = df_reset.replace([np.inf, -np.inf], np.nan)

    # 取前 10 条作为样本
    sample_data = [
        {k: (None if pd.isna(v) else v) for k, v in record.items()}
        for record in df_reset.head(10).to_dict('records')
    ]

    # 5. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "code": code,
            "record_count": len(df_with_features),
            "feature_count": len(df_with_features.columns),
            "feature_types": feature_types,
            "include_transforms": include_transforms,
            "columns": list(df_with_features.columns),
            "sample_data": sample_data
        },
        message="特征计算成功"
    ).to_dict()


@router.get("/names")
async def get_feature_names():
    """
    获取所有可用的特征名称

    ✅ 架构修正版：调用 Core Adapter 获取特征列表

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "technical_indicators": ["ma", "ema", "macd", "rsi", ...],
            "alpha_factors": ["momentum", "reversal", "volatility", ...],
            "transforms": ["standardize", "normalize", "log", "diff"],
            "total_count": {
                "technical_indicators": 50,
                "alpha_factors": 30,
                "transforms": 4
            }
        }
    }
    """
    # 调用 Core Adapter 获取特征名称
    feature_names = await feature_adapter.get_feature_names()

    # 统计数量
    total_count = {
        "technical_indicators": len(feature_names.get("technical_indicators", [])),
        "alpha_factors": len(feature_names.get("alpha_factors", [])),
        "transforms": len(feature_names.get("transforms", []))
    }

    return ApiResponse.success(
        data={
            **feature_names,
            "total_count": total_count
        },
        message="获取特征名称成功"
    ).to_dict()


@router.post("/{code}/select")
async def select_features(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    target_column: str = "close",
    n_features: int = 50,
    method: str = "correlation"
):
    """
    特征选择（基于重要性）

    ✅ 架构修正版：调用 Core Adapter 的特征选择方法

    参数:
    - code: 股票代码
    - start_date: 开始日期
    - end_date: 结束日期
    - target_column: 目标列（默认 close）
    - n_features: 要选择的特征数量
    - method: 选择方法（correlation=相关系数, mutual_info=互信息）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "method": "correlation",
            "n_features": 50,
            "selected_features": ["ma_5", "rsi_14", ...],
            "importance_scores": {"ma_5": 0.85, "rsi_14": 0.78, ...}
        }
    }
    """
    try:
        # 1. 参数转换
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError as e:
        return ApiResponse.bad_request(
            message=f"参数错误: {str(e)}"
        ).to_dict()

    # 2. 调用 Core Adapter 获取日线数据
    df = await data_adapter.get_daily_data(
        code=code,
        start_date=start_dt,
        end_date=end_dt
    )

    if df.empty:
        return ApiResponse.not_found(
            message=f"股票 {code} 无日线数据"
        ).to_dict()

    # 3. 计算所有特征
    df_with_features = await feature_adapter.add_all_features(df)

    # 4. 准备特征矩阵和目标变量
    if target_column not in df_with_features.columns:
        return ApiResponse.bad_request(
            message=f"目标列 '{target_column}' 不存在"
        ).to_dict()

    # 移除非数值列和目标列
    feature_columns = [
        col for col in df_with_features.columns
        if col != target_column and df_with_features[col].dtype in ['float64', 'int64']
    ]

    X = df_with_features[feature_columns].fillna(0)
    y = df_with_features[target_column]

    # 5. 调用 Core Adapter 进行特征选择
    selected_features = await feature_adapter.select_features(
        X=X,
        y=y,
        n_features=n_features,
        method=method
    )

    # 6. 计算重要性分数
    importance = await feature_adapter.calculate_feature_importance(
        X=X[selected_features],
        y=y,
        method=method
    )

    importance_scores = importance.to_dict()

    # 7. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "code": code,
            "method": method,
            "n_features": len(selected_features),
            "total_features": len(feature_columns),
            "selected_features": selected_features,
            "importance_scores": importance_scores
        },
        message="特征选择成功"
    ).to_dict()
