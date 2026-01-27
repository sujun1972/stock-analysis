#!/usr/bin/env python3
"""
Phase 2 特征工程测试脚本
测试技术指标、Alpha因子、特征转换和特征存储功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent

from src.features.technical_indicators import TechnicalIndicators, calculate_all_indicators
from src.features.alpha_factors import AlphaFactors, calculate_all_alpha_factors
from src.features.feature_transformer import FeatureTransformer, prepare_ml_features
from src.features.feature_storage import FeatureStorage

import pandas as pd
import numpy as np


def create_test_data(num_days: int = 300) -> pd.DataFrame:
    """创建测试数据"""
    dates = pd.date_range('2023-01-01', periods=num_days, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, num_days)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, num_days)),
        'high': prices * (1 + np.random.uniform(0, 0.03, num_days)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, num_days)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, num_days)
    }, index=dates)

    return df


def test_technical_indicators():
    """测试技术指标模块"""
    print("\n" + "="*60)
    print("测试1: 技术指标计算")
    print("="*60)

    # 创建测试数据
    test_df = create_test_data(300)
    print(f"\n1.1 原始数据: {len(test_df)} 行 × {len(test_df.columns)} 列")

    # 初始化技术指标计算器
    ti = TechnicalIndicators(test_df)

    # 测试各类指标
    print("\n1.2 添加趋势指标")
    ti.add_ma([5, 10, 20, 60])
    ti.add_ema([12, 26])
    ti.add_bollinger_bands()

    print("\n1.3 添加动量指标")
    ti.add_rsi([6, 12, 24])
    ti.add_macd()
    ti.add_kdj()
    ti.add_cci()

    print("\n1.4 添加波动率指标")
    ti.add_atr()
    ti.add_volatility([5, 10, 20])

    print("\n1.5 添加成交量指标")
    ti.add_obv()
    ti.add_volume_ma([5, 10, 20])

    print("\n1.6 添加价格形态")
    ti.add_price_patterns()

    result_df = ti.get_dataframe()
    feature_names = ti.get_feature_names()

    print(f"\n结果统计:")
    print(f"  总列数: {len(result_df.columns)}")
    print(f"  技术指标数: {len(feature_names)}")
    print(f"  数据缺失率: {result_df.isnull().sum().sum() / (len(result_df) * len(result_df.columns)) * 100:.2f}%")

    # 检查关键指标
    print("\n关键指标检查:")
    key_indicators = ['MA5', 'MA20', 'RSI6', 'MACD', 'KDJ_K', 'BOLL_UPPER', 'ATR']
    for indicator in key_indicators:
        if indicator in result_df.columns:
            valid_pct = result_df[indicator].notna().sum() / len(result_df) * 100
            print(f"  {indicator:12s}: {valid_pct:.1f}% 有效数据")

    print("\n✅ 测试1通过")
    return result_df


def test_alpha_factors():
    """测试Alpha因子模块"""
    print("\n" + "="*60)
    print("测试2: Alpha因子计算")
    print("="*60)

    # 创建测试数据
    test_df = create_test_data(300)
    print(f"\n2.1 原始数据: {len(test_df)} 行 × {len(test_df.columns)} 列")

    # 初始化Alpha因子计算器
    af = AlphaFactors(test_df)

    # 测试各类因子
    print("\n2.2 添加动量因子")
    af.add_momentum_factors(periods=[5, 10, 20, 60])
    af.add_relative_strength(periods=[20, 60])
    af.add_acceleration(periods=[5, 10, 20])

    print("\n2.3 添加反转因子")
    af.add_reversal_factors(short_periods=[1, 3, 5], long_periods=[20, 60])
    af.add_overnight_reversal()

    print("\n2.4 添加波动率因子")
    af.add_volatility_factors(periods=[5, 10, 20])
    af.add_high_low_volatility(periods=[10, 20])

    print("\n2.5 添加成交量因子")
    af.add_volume_factors(periods=[5, 10, 20])
    af.add_price_volume_correlation(periods=[20, 60])

    print("\n2.6 添加趋势强度因子")
    af.add_trend_strength(periods=[20, 60])
    af.add_breakout_factors(periods=[20, 60])

    print("\n2.7 添加流动性因子")
    af.add_liquidity_factors(periods=[20])

    result_df = af.get_dataframe()
    factor_names = af.get_factor_names()

    print(f"\n结果统计:")
    print(f"  总列数: {len(result_df.columns)}")
    print(f"  Alpha因子数: {len(factor_names)}")
    print(f"  数据缺失率: {result_df.isnull().sum().sum() / (len(result_df) * len(result_df.columns)) * 100:.2f}%")

    # 检查关键因子
    print("\n关键因子检查:")
    key_factors = ['MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20', 'PRICE_POSITION20']
    for factor in key_factors:
        if factor in result_df.columns:
            valid_pct = result_df[factor].notna().sum() / len(result_df) * 100
            mean_val = result_df[factor].mean()
            std_val = result_df[factor].std()
            print(f"  {factor:20s}: {valid_pct:.1f}% 有效, 均值={mean_val:.2f}, 标准差={std_val:.2f}")

    print("\n✅ 测试2通过")
    return result_df


def test_feature_transformer():
    """测试特征转换器"""
    print("\n" + "="*60)
    print("测试3: 特征转换器")
    print("="*60)

    # 创建测试数据
    test_df = create_test_data(300)
    print(f"\n3.1 原始数据: {len(test_df)} 行 × {len(test_df.columns)} 列")

    # 初始化特征转换器
    ft = FeatureTransformer(test_df)

    # 测试价格变动率矩阵
    print("\n3.2 创建价格变动率矩阵（20天回看）")
    ft.create_price_change_matrix(lookback_days=20)
    price_chg_cols = [col for col in ft.df.columns if 'PRICE_CHG_T-' in col]
    print(f"  创建了 {len(price_chg_cols)} 个价格变动率特征")

    # 测试多时间尺度收益率
    print("\n3.3 创建多时间尺度收益率")
    ft.create_multi_timeframe_returns([1, 3, 5, 10, 20])
    ret_cols = [col for col in ft.df.columns if 'RET_' in col or 'LOG_RET_' in col]
    print(f"  创建了 {len(ret_cols)} 个收益率特征")

    # 测试OHLC特征
    print("\n3.4 创建OHLC特征")
    ft.create_ohlc_features()

    # 测试时间特征
    print("\n3.5 添加时间特征")
    ft.add_time_features()
    time_cols = ['DAY_OF_WEEK', 'MONTH', 'QUARTER']
    print(f"  时间特征: {[col for col in time_cols if col in ft.df.columns]}")

    # 测试滞后特征
    print("\n3.6 创建滞后特征")
    ft.create_lag_features(['close'], lags=[1, 2, 3, 5])
    lag_cols = [col for col in ft.df.columns if 'LAG' in col]
    print(f"  创建了 {len(lag_cols)} 个滞后特征")

    # 测试滚动特征
    print("\n3.7 创建滚动统计特征")
    ft.create_rolling_features(['close'], windows=[5, 10], funcs=['mean', 'std'])
    roll_cols = [col for col in ft.df.columns if 'ROLL' in col]
    print(f"  创建了 {len(roll_cols)} 个滚动统计特征")

    # 处理缺失值
    print("\n3.8 处理缺失值和无穷值")
    ft.handle_infinite_values()
    ft.handle_missing_values(method='forward')

    result_df = ft.get_dataframe()

    print(f"\n结果统计:")
    print(f"  总列数: {len(result_df.columns)}")
    print(f"  数据缺失率: {result_df.isnull().sum().sum() / (len(result_df) * len(result_df.columns)) * 100:.2f}%")
    print(f"  无穷值数: {np.isinf(result_df.select_dtypes(include=[np.number])).sum().sum()}")

    print("\n✅ 测试3通过")
    return result_df


def test_feature_storage():
    """测试特征存储管理器"""
    print("\n" + "="*60)
    print("测试4: 特征存储管理器")
    print("="*60)

    # 创建测试数据
    test_df = create_test_data(100)

    # 初始化存储管理器
    storage_dir = project_root / 'data' / 'features_test'
    storage = FeatureStorage(storage_dir=str(storage_dir), format='parquet')

    print("\n4.1 保存特征数据")
    stocks = ['000001', '000002', '600000']
    for stock_code in stocks:
        success = storage.save_features(
            test_df,
            stock_code=stock_code,
            feature_type='technical',
            version='v1',
            metadata={'test': True}
        )
        assert success, f"保存 {stock_code} 失败"

    print("\n4.2 加载特征数据")
    loaded_df = storage.load_features('000001', feature_type='technical')
    assert loaded_df is not None, "加载失败"
    assert len(loaded_df) == len(test_df), "数据长度不匹配"
    assert list(loaded_df.columns) == list(test_df.columns), "列名不匹配"
    print(f"  加载成功: {len(loaded_df)} 行 × {len(loaded_df.columns)} 列")

    print("\n4.3 批量加载")
    features_dict = storage.load_multiple_stocks(stocks, feature_type='technical')
    assert len(features_dict) == len(stocks), "批量加载数量不匹配"

    print("\n4.4 列出股票")
    stock_list = storage.list_stocks(feature_type='technical')
    print(f"  股票列表: {stock_list}")
    assert set(stock_list) == set(stocks), "股票列表不匹配"

    print("\n4.5 获取特征列名")
    columns = storage.get_feature_columns('000001', feature_type='technical')
    print(f"  特征列数: {len(columns)}")
    assert columns == test_df.columns.tolist(), "特征列名不匹配"

    print("\n4.6 更新特征")
    new_df = create_test_data(50)
    success = storage.update_features('000001', new_df, feature_type='technical', mode='append')
    assert success, "更新失败"

    print("\n4.7 统计信息")
    storage.print_statistics()

    print("\n4.8 删除特征")
    success = storage.delete_features('000001', feature_type='technical')
    assert success, "删除失败"

    print("\n✅ 测试4通过")


def test_integrated_pipeline():
    """测试完整特征工程流程"""
    print("\n" + "="*60)
    print("测试5: 完整特征工程流程")
    print("="*60)

    # 创建原始数据
    raw_df = create_test_data(300)
    print(f"\n5.1 原始数据: {len(raw_df)} 行 × {len(raw_df.columns)} 列")

    # Step 1: 计算技术指标
    print("\n5.2 计算技术指标")
    ti = TechnicalIndicators(raw_df)
    ti_df = ti.add_all_indicators()
    print(f"  技术指标后: {len(ti_df.columns)} 列")

    # Step 2: 计算Alpha因子
    print("\n5.3 计算Alpha因子")
    af = AlphaFactors(ti_df)
    af_df = af.add_all_alpha_factors()
    print(f"  Alpha因子后: {len(af_df.columns)} 列")

    # Step 3: 特征转换
    print("\n5.4 特征转换")
    ft = FeatureTransformer(af_df)
    ft.create_price_change_matrix(lookback_days=10)
    ft.create_multi_timeframe_returns([1, 5, 10])
    ft.add_time_features()
    ft.handle_infinite_values()
    ft.handle_missing_values(method='forward')
    final_df = ft.get_dataframe()
    print(f"  特征转换后: {len(final_df.columns)} 列")

    # Step 4: 保存特征
    print("\n5.5 保存特征")
    storage_dir = project_root / 'data' / 'features_test'
    storage = FeatureStorage(storage_dir=str(storage_dir), format='parquet')

    storage.save_features(raw_df, '000001', 'raw', 'v1')
    storage.save_features(ti_df, '000001', 'technical', 'v1')
    storage.save_features(af_df, '000001', 'alpha', 'v1')
    storage.save_features(final_df, '000001', 'transformed', 'v1')

    print("\n5.6 验证保存")
    loaded_df = storage.load_features('000001', 'transformed', 'v1')
    assert loaded_df is not None, "加载失败"
    assert len(loaded_df.columns) == len(final_df.columns), "列数不匹配"

    print(f"\n最终特征集:")
    print(f"  总特征数: {len(final_df.columns)}")
    print(f"  数据行数: {len(final_df)}")
    print(f"  缺失率: {final_df.isnull().sum().sum() / (len(final_df) * len(final_df.columns)) * 100:.2f}%")

    # 显示部分特征
    print(f"\n部分特征列表（前20个）:")
    for i, col in enumerate(final_df.columns[:20], 1):
        print(f"  {i:2d}. {col}")

    print("\n✅ 测试5通过")


def main():
    """运行所有测试"""
    print("\n" + "🧪"*30)
    print("Phase 2: 特征工程测试")
    print("🧪"*30)

    try:
        # 运行各项测试
        test_technical_indicators()
        test_alpha_factors()
        test_feature_transformer()
        test_feature_storage()
        test_integrated_pipeline()

        print("\n" + "="*60)
        print("✅ 所有测试通过！Phase 2 特征工程运行正常")
        print("="*60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
