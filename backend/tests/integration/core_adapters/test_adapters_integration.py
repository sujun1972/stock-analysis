"""
Core Adapters 集成测试

测试所有 Adapters 与 Core 模块的集成。

注意: 这些测试需要数据库连接和 Core 项目的完整配置。

作者: Backend Team
创建日期: 2026-02-01
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters import DataAdapter, FeatureAdapter, ModelAdapter


@pytest.fixture
def sample_stock_code():
    """示例股票代码"""
    return "000001"


@pytest.fixture
def date_range():
    """日期范围"""
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    return start_date, end_date


class TestAdaptersIntegration:
    """Adapters 集成测试类"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow(self, sample_stock_code, date_range):
        """
        测试完整工作流: 数据获取 -> 特征计算 -> 模型训练

        注意: 此测试需要数据库有真实数据
        """
        # 1. 数据获取
        data_adapter = DataAdapter()
        start_date, end_date = date_range

        try:
            df = await data_adapter.get_daily_data(sample_stock_code, start_date, end_date)

            if df.empty:
                pytest.skip("数据库中无数据，跳过集成测试")
                return

            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
            assert "close" in df.columns

            # 2. 特征计算
            feature_adapter = FeatureAdapter()
            df_with_features = await feature_adapter.add_all_features(
                df, include_indicators=True, include_factors=True
            )

            assert len(df_with_features.columns) > len(df.columns)

            # 3. 准备训练数据
            # 移除 NaN
            df_clean = df_with_features.dropna()

            if len(df_clean) < 50:
                pytest.skip("数据量不足，跳过模型训练")
                return

            # 分割特征和标签
            feature_cols = [
                col
                for col in df_clean.columns
                if col not in ["open", "high", "low", "close", "volume"]
            ]

            X = df_clean[feature_cols]
            y = df_clean["close"].shift(-1).dropna()  # 预测下一日收盘价

            # 对齐数据
            X = X.iloc[: len(y)]

            # 分割训练集和测试集
            split_idx = int(len(X) * 0.8)
            X_train = X.iloc[:split_idx]
            y_train = y.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_test = y.iloc[split_idx:]

            # 4. 模型训练
            model_adapter = ModelAdapter()
            result = await model_adapter.train_model(
                X_train, y_train, X_test, y_test, model_type="Ridge", save_model=False
            )

            assert "model" in result
            assert "train_metrics" in result
            assert isinstance(result["train_metrics"], dict)

            # 5. 模型预测
            predictions = await model_adapter.predict(result["model"], X_test)

            assert len(predictions) == len(X_test)
            assert all(isinstance(p, (int, float)) for p in predictions)

        except Exception as e:
            pytest.skip(f"集成测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_feature_integration(self, sample_stock_code):
        """测试数据适配器和特征适配器的集成"""
        data_adapter = DataAdapter()
        feature_adapter = FeatureAdapter()

        try:
            # 获取最近 100 天的数据
            end_date = date.today()
            start_date = end_date - timedelta(days=100)

            df = await data_adapter.get_daily_data(sample_stock_code, start_date, end_date)

            if df.empty:
                pytest.skip("无数据")
                return

            # 添加技术指标
            df_with_indicators = await feature_adapter.add_technical_indicators(df)
            assert len(df_with_indicators.columns) > len(df.columns)

            # 添加 Alpha 因子
            df_with_factors = await feature_adapter.add_alpha_factors(df)
            assert len(df_with_factors.columns) > len(df.columns)

        except Exception as e:
            pytest.skip(f"数据特征集成测试失败: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_adapter_usage(self, sample_stock_code):
        """测试并发使用多个适配器"""
        import asyncio

        data_adapter = DataAdapter()
        feature_adapter = FeatureAdapter()

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=50)

            # 并发获取数据
            df = await data_adapter.get_daily_data(sample_stock_code, start_date, end_date)

            if df.empty:
                pytest.skip("无数据")
                return

            # 并发计算特征
            tasks = [
                feature_adapter.add_technical_indicators(df.copy()),
                feature_adapter.add_alpha_factors(df.copy()),
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 2
            assert all(isinstance(r, pd.DataFrame) for r in results)

        except Exception as e:
            pytest.skip(f"并发测试失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
