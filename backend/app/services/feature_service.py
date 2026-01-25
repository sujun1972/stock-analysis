"""
特征工程服务
封装特征计算功能
"""

from typing import Optional, List, Dict
import asyncio
import pandas as pd
from loguru import logger

# 使用docker-compose挂载的/app/src目录
from src.features.technical_indicators import TechnicalIndicators
from src.features.alpha_factors import AlphaFactors
from src.features.feature_transformer import FeatureTransformer
from src.database.db_manager import DatabaseManager


class FeatureService:
    """特征工程服务类"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化特征服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()
        logger.info("✓ FeatureService initialized")

    async def calculate_features(
        self,
        code: str,
        feature_types: List[str] = ["technical", "alpha"]
    ) -> Dict:
        """
        计算股票特征

        Args:
            code: 股票代码
            feature_types: 特征类型列表

        Returns:
            {feature_count: int, message: str}
        """
        try:
            logger.info(f"开始计算 {code} 的特征...")

            # 1. 加载数据
            df = await asyncio.to_thread(
                self.db.load_daily_data,
                code
            )

            if df is None or df.empty:
                raise ValueError(f"股票 {code} 无数据")

            original_count = len(df)
            feature_count = 0

            # 2. 计算技术指标
            if "technical" in feature_types:
                logger.info(f"  计算技术指标...")
                ti = TechnicalIndicators(df)
                df = await asyncio.to_thread(ti.add_all_indicators)
                tech_features = len(ti.get_feature_names())
                feature_count += tech_features
                logger.info(f"  ✓ 技术指标: {tech_features} 个")

            # 3. 计算Alpha因子
            if "alpha" in feature_types:
                logger.info(f"  计算Alpha因子...")
                af = AlphaFactors(df)
                df = await asyncio.to_thread(af.add_all_alpha_factors)
                alpha_features = len(af.get_factor_names())
                feature_count += alpha_features
                logger.info(f"  ✓ Alpha因子: {alpha_features} 个")

            # 4. 特征转换（可选）
            if "transformed" in feature_types:
                logger.info(f"  特征转换...")
                ft = FeatureTransformer(df)
                df = await asyncio.to_thread(ft.create_price_change_matrix, 20)
                logger.info(f"  ✓ 价格变化矩阵: 20 期")

            # 5. 保存到数据库（这里简化，实际可以存储到stock_features表）
            # TODO: 将特征数据保存到stock_features表

            logger.info(f"✓ {code} 特征计算完成: {feature_count} 个特征")

            return {
                "code": code,
                "feature_count": feature_count,
                "feature_types": feature_types,
                "data_rows": len(df),
                "message": f"成功计算 {feature_count} 个特征"
            }

        except Exception as e:
            logger.error(f"计算特征失败 {code}: {e}")
            raise

    async def get_features(
        self,
        code: str,
        feature_type: Optional[str] = None,
        end_date = None
    ) -> pd.DataFrame:
        """
        获取股票特征数据（支持懒加载）

        Args:
            code: 股票代码
            feature_type: 特征类型（不影响返回列，仅作为标记）
            end_date: 结束日期（不包含），返回该日期之前的数据

        Returns:
            特征数据DataFrame（按日期降序排列）
        """
        try:
            logger.info(f"获取 {code} 的特征数据 (end_date={end_date})...")

            # 加载日线数据
            df = await asyncio.to_thread(
                self.db.load_daily_data,
                code
            )

            if df is None or df.empty:
                raise ValueError(f"股票 {code} 无数据")

            # 计算技术指标（先计算，后过滤，确保指标计算的连续性）
            ti = TechnicalIndicators(df)
            df = await asyncio.to_thread(ti.add_all_indicators)

            # 按日期过滤（如果提供了end_date，只返回该日期之前的数据，不包含end_date当天）
            if end_date is not None:
                df_reset = df.reset_index()
                # 确保date列是datetime类型，并与end_date比较（end_date可能是date对象或字符串）
                end_dt = pd.Timestamp(end_date)
                df_reset = df_reset[pd.to_datetime(df_reset['date']) < end_dt]
                df = df_reset.set_index('date')

            logger.info(f"✓ 获取 {code} 特征: {len(df)} 行, {len(df.columns)} 列")

            return df

        except Exception as e:
            logger.error(f"获取特征失败 {code}: {e}")
            raise
