"""
特征工程API
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import date
from loguru import logger

from app.services import FeatureService

router = APIRouter()


@router.get("/{code}")
async def get_features(
    code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    feature_type: Optional[str] = None
):
    """
    获取股票特征数据

    参数:
    - code: 股票代码
    - start_date: 开始日期
    - end_date: 结束日期
    - feature_type: 特征类型（technical/alpha/transformed）

    返回:
    - 特征数据
    """
    try:
        feature_service = FeatureService()
        df = await feature_service.get_features(code, feature_type)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"股票 {code} 无特征数据")

        # 重置索引
        df_reset = df.reset_index()

        return {
            "code": code,
            "feature_type": feature_type or "all",
            "count": len(df),
            "columns": list(df.columns),
            "data": df_reset.head(100).to_dict('records')  # 只返回前100条
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取特征数据失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/{code}")
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
