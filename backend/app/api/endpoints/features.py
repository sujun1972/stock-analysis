"""
特征工程API
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import date
from loguru import logger
import pandas as pd
import numpy as np

from app.services import FeatureService
from app.api.error_handler import handle_api_errors

router = APIRouter()


@router.get("/{code}")
@handle_api_errors
async def get_features(
    code: str,
    end_date: Optional[date] = None,
    feature_type: Optional[str] = None,
    limit: int = 500
):
    """
    获取股票特征数据（支持懒加载）

    参数:
    - code: 股票代码
    - end_date: 结束日期（不包含），默认为今天。返回该日期之前的数据
    - feature_type: 特征类型（technical/alpha/transformed）
    - limit: 返回记录数限制，默认500条

    返回:
    - 特征数据（按日期降序，从end_date往前取limit条）

    示例:
    - GET /api/features/000031 → 返回最新500条（从今天往前）
    - GET /api/features/000031?end_date=2023-12-27 → 返回2023-12-27之前的500条
    """
    try:
        feature_service = FeatureService()
        df = await feature_service.get_features(code, feature_type, end_date=end_date)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"股票 {code} 无特征数据")

        # 重置索引
        df_reset = df.reset_index()

        # 替换Inf和NaN为None，以便JSON序列化
        df_reset = df_reset.replace([np.inf, -np.inf], np.nan)

        # 按日期降序排列（从新到旧）
        df_reset = df_reset.sort_values('date', ascending=False)

        # 获取总数（不受limit影响）
        total_count = len(df_reset)

        # 限制返回数量
        df_reset = df_reset.head(limit)

        # 转换为字典列表，将NaN转为None
        data_list = [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in df_reset.to_dict('records')
        ]

        return {
            "code": code,
            "feature_type": feature_type or "all",
            "total": total_count,  # 总数据量（截止到end_date）
            "returned": len(data_list),  # 实际返回数量
            "has_more": total_count > limit,  # 是否还有更多数据
            "columns": list(df.columns),
            "data": data_list
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取特征数据失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/{code}")
@handle_api_errors
async def calculate_features(
    code: str,
    feature_types: List[str] = ["technical", "alpha"]
):
    """
    计算股票特征

    参数:
    - code: 股票代码
    - feature_types: 特征类型列表

    返回:
    - 计算结果
    """
    try:
        feature_service = FeatureService()
        result = await feature_service.calculate_features(code, feature_types)
        return result
    except Exception as e:
        logger.error(f"计算特征失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
