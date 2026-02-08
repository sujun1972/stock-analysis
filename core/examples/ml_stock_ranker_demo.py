"""
MLStockRanker 使用示例
演示如何使用ML模型对股票池进行评分和排名

功能演示:
1. 基本评分排名
2. 不同评分方法对比
3. 批量评分 (多日期)
4. 股票筛选和过滤
5. Top N股票获取

使用方法:
    python examples/ml_stock_ranker_demo.py

版本: v1.0.0
创建时间: 2026-02-08
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import joblib

from src.ml.ml_stock_ranker import MLStockRanker, ScoringMethod
from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.feature_engine import FeatureEngine


# ============================================================================
# 简单模型类 (模块级定义,可序列化)
# ============================================================================

class SimpleRankerModel:
    """简单评分模型 (基于随机+趋势)"""

    def predict(self, X):
        """
        预测未来收益率
        Args:
            X: 特征矩阵 (N stocks × M features)
        Returns:
            预测收益率数组
        """
        np.random.seed(42)
        # 基于特征的简单预测 (模拟真实模型)
        predictions = np.random.randn(len(X)) * 0.03 + 0.01
        return predictions


class SimpleFeatureEngine:
    """简单特征引擎"""
    def __init__(self):
        self.feature_groups = ['technical']
        self.lookback_window = 20
        self.cache_enabled = True

    def calculate_features(self, stock_codes, market_data, date):
        """计算简单特征"""
        features = pd.DataFrame(index=stock_codes)

        for stock in stock_codes:
            stock_data = market_data[
                (market_data['stock_code'] == stock) &
                (market_data['date'] <= pd.to_datetime(date))
            ].tail(20)

            if len(stock_data) < 5:
                continue

            # 简单特征: 20日收益率
            features.loc[stock, 'return_20d'] = (
                stock_data['close'].iloc[-1] / stock_data['close'].iloc[0] - 1
            )

            # 简单特征: 波动率
            features.loc[stock, 'volatility'] = stock_data['close'].pct_change().std()

        return features.fillna(0)


# ============================================================================
# 辅助函数: 创建模拟数据
# ============================================================================

def create_sample_data():
    """创建示例市场数据"""
    print("📊 创建示例市场数据...")

    # 生成30天的数据
    dates = pd.date_range('2024-01-01', periods=90, freq='D')

    # 使用常见A股代码
    stocks = [
        '600000.SH',  # 浦发银行
        '600036.SH',  # 招商银行
        '600519.SH',  # 贵州茅台
        '600887.SH',  # 伊利股份
        '601318.SH',  # 中国平安
        '000001.SZ',  # 平安银行
        '000002.SZ',  # 万科A
        '000858.SZ',  # 五粮液
        '002415.SZ',  # 海康威视
        '300750.SZ',  # 宁德时代
    ]

    data = []
    np.random.seed(42)  # 固定随机种子

    for stock in stocks:
        base_price = 10 + np.random.rand() * 90  # 10-100之间的基准价格
        for i, date in enumerate(dates):
            # 模拟价格波动
            trend = 0.001 * i  # 缓慢上升趋势
            volatility = np.random.randn() * 0.02  # 2%波动
            price = base_price * (1 + trend + volatility)

            data.append({
                'stock_code': stock,
                'date': date,
                'open': price * (1 + np.random.randn() * 0.01),
                'high': price * (1 + abs(np.random.randn() * 0.02)),
                'low': price * (1 - abs(np.random.randn() * 0.02)),
                'close': price,
                'volume': int(1000000 * (1 + np.random.rand()))
            })

    df = pd.DataFrame(data)
    print(f"✅ 创建完成: {len(stocks)}只股票 × {len(dates)}天 = {len(df)}条记录\n")

    return df, stocks


def create_simple_model():
    """创建简单的可序列化模型"""
    return SimpleRankerModel()


def create_simple_feature_engine():
    """创建简单特征引擎"""
    return SimpleFeatureEngine()


def create_trained_model():
    """创建训练好的模型"""
    print("🔧 创建训练好的模型...")

    model = create_simple_model()
    feature_engine = create_simple_feature_engine()

    config = TrainingConfig(
        model_type='lightgbm',
        train_start_date='2020-01-01',
        train_end_date='2023-12-31',
        forward_window=5,
        feature_groups=['technical']
    )

    trained_model = TrainedModel(
        model=model,
        feature_engine=feature_engine,
        config=config,
        metrics={'ic': 0.08, 'rank_ic': 0.12}
    )

    # 保存到临时文件
    temp_dir = Path(tempfile.gettempdir()) / 'ml_ranker_demo'
    temp_dir.mkdir(exist_ok=True)
    model_path = temp_dir / 'ranker_model.pkl'

    joblib.dump(trained_model, str(model_path))
    print(f"✅ 模型已保存: {model_path}\n")

    return str(model_path)


# ============================================================================
# 示例 1: 基本评分排名
# ============================================================================

def example1_basic_ranking(model_path, market_data, stock_pool):
    """示例1: 基本评分排名"""
    print("=" * 70)
    print("📌 示例 1: 基本评分排名")
    print("=" * 70)

    # 创建ranker
    ranker = MLStockRanker(
        model_path=model_path,
        scoring_method='simple'
    )

    # 评分
    rankings = ranker.rank(
        stock_pool=stock_pool,
        market_data=market_data,
        date='2024-02-15',
        return_top_n=5
    )

    print("\n📊 Top 5 股票评分:")
    print("-" * 50)
    for i, (stock, score) in enumerate(rankings.items(), 1):
        print(f"{i}. {stock:12s} | 评分: {score:.4f}")

    print("\n")


# ============================================================================
# 示例 2: 不同评分方法对比
# ============================================================================

def example2_scoring_methods(model_path, market_data, stock_pool):
    """示例2: 不同评分方法对比"""
    print("=" * 70)
    print("📌 示例 2: 不同评分方法对比")
    print("=" * 70)

    methods = ['simple', 'sharpe', 'risk_adjusted']

    for method in methods:
        ranker = MLStockRanker(
            model_path=model_path,
            scoring_method=method
        )

        rankings = ranker.rank(
            stock_pool=stock_pool,
            market_data=market_data,
            date='2024-02-15',
            return_top_n=3
        )

        print(f"\n📊 评分方法: {method}")
        print("-" * 50)
        for i, (stock, score) in enumerate(rankings.items(), 1):
            print(f"{i}. {stock:12s} | 评分: {score:.4f}")

    print("\n")


# ============================================================================
# 示例 3: 详细评分信息 (DataFrame)
# ============================================================================

def example3_detailed_ranking(model_path, market_data, stock_pool):
    """示例3: 详细评分信息"""
    print("=" * 70)
    print("📌 示例 3: 详细评分信息 (DataFrame)")
    print("=" * 70)

    ranker = MLStockRanker(
        model_path=model_path,
        scoring_method='sharpe',
        min_confidence=0.0,
        min_expected_return=0.0
    )

    # 使用rank_dataframe返回详细信息
    result_df = ranker.rank_dataframe(
        stock_pool=stock_pool,
        market_data=market_data,
        date='2024-02-15',
        return_top_n=5
    )

    print("\n📊 Top 5 股票详细信息:")
    print("-" * 70)
    print(result_df.to_string())

    print("\n")


# ============================================================================
# 示例 4: 批量评分 (多日期)
# ============================================================================

def example4_batch_ranking(model_path, market_data, stock_pool):
    """示例4: 批量评分"""
    print("=" * 70)
    print("📌 示例 4: 批量评分 (多日期)")
    print("=" * 70)

    ranker = MLStockRanker(
        model_path=model_path,
        scoring_method='simple'
    )

    # 批量评分
    dates = ['2024-02-10', '2024-02-15', '2024-02-20']

    results = ranker.batch_rank(
        stock_pool=stock_pool,
        market_data=market_data,
        dates=dates,
        return_top_n=3
    )

    print("\n📊 批量评分结果:")
    print("-" * 70)

    for date, rankings in results.items():
        print(f"\n日期: {date}")
        for i, (stock, score) in enumerate(rankings.items(), 1):
            print(f"  {i}. {stock:12s} | 评分: {score:.4f}")

    print("\n")


# ============================================================================
# 示例 5: 股票筛选和过滤
# ============================================================================

def example5_filtering(model_path, market_data, stock_pool):
    """示例5: 股票筛选和过滤"""
    print("=" * 70)
    print("📌 示例 5: 股票筛选和过滤")
    print("=" * 70)

    # 无筛选
    ranker_no_filter = MLStockRanker(
        model_path=model_path,
        min_confidence=0.0,
        min_expected_return=0.0
    )

    rankings_no_filter = ranker_no_filter.rank(
        stock_pool=stock_pool,
        market_data=market_data,
        date='2024-02-15'
    )

    # 高置信度筛选
    ranker_high_conf = MLStockRanker(
        model_path=model_path,
        min_confidence=0.7,
        min_expected_return=0.02
    )

    rankings_filtered = ranker_high_conf.rank(
        stock_pool=stock_pool,
        market_data=market_data,
        date='2024-02-15'
    )

    print(f"\n📊 无筛选: {len(rankings_no_filter)}只股票")
    print(f"📊 高置信度筛选 (confidence≥0.7, return≥0.02): {len(rankings_filtered)}只股票")

    if rankings_filtered:
        print("\n通过筛选的股票:")
        print("-" * 50)
        for stock, score in rankings_filtered.items():
            print(f"  {stock:12s} | 评分: {score:.4f}")

    print("\n")


# ============================================================================
# 示例 6: Top N股票获取
# ============================================================================

def example6_top_stocks(model_path, market_data, stock_pool):
    """示例6: Top N股票获取"""
    print("=" * 70)
    print("📌 示例 6: Top N股票获取 (辅助方法)")
    print("=" * 70)

    ranker = MLStockRanker(
        model_path=model_path,
        scoring_method='sharpe'
    )

    # 获取Top 3股票
    top_stocks = ranker.get_top_stocks(
        stock_pool=stock_pool,
        market_data=market_data,
        date='2024-02-15',
        top_n=3
    )

    print("\n📊 Top 3 股票代码:")
    print("-" * 50)
    for i, stock in enumerate(top_stocks, 1):
        print(f"{i}. {stock}")

    print("\n")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("🎯 MLStockRanker 使用示例")
    print("=" * 70 + "\n")

    # 准备数据
    market_data, stock_pool = create_sample_data()
    model_path = create_trained_model()

    # 运行示例
    example1_basic_ranking(model_path, market_data, stock_pool)
    example2_scoring_methods(model_path, market_data, stock_pool)
    example3_detailed_ranking(model_path, market_data, stock_pool)
    example4_batch_ranking(model_path, market_data, stock_pool)
    example5_filtering(model_path, market_data, stock_pool)
    example6_top_stocks(model_path, market_data, stock_pool)

    print("=" * 70)
    print("✅ 所有示例运行完成!")
    print("=" * 70 + "\n")

    # 清理临时文件
    Path(model_path).unlink(missing_ok=True)
    print("🧹 临时文件已清理\n")


if __name__ == '__main__':
    main()
