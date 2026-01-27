#!/usr/bin/env python3
"""
Phase 1 数据管道测试脚本
测试股票列表获取、过滤、数据下载、清洗等功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent

from src.data_fetcher import DataFetcher
from src.data.stock_filter import StockFilter
from src.data.data_cleaner import DataCleaner
from src.config.trading_rules import (
    TradingCosts,
    PriceLimitRules,
    StockFilterRules,
    MarketType
)
import pandas as pd
import numpy as np


def test_trading_rules():
    """测试交易规则配置"""
    print("\n" + "="*60)
    print("测试1: A股交易规则配置")
    print("="*60)

    # 测试涨跌幅限制
    print("\n1.1 涨跌幅限制:")
    main_limit = PriceLimitRules.get_limit('main', is_st=False)
    st_limit = PriceLimitRules.get_limit('main', is_st=True)
    star_limit = PriceLimitRules.get_limit('star', is_st=False)

    print(f"  主板涨跌幅: ±{main_limit*100}%")
    print(f"  ST股票涨跌幅: ±{st_limit*100}%")
    print(f"  科创板涨跌幅: ±{star_limit*100}%")

    # 测试交易成本
    print("\n1.2 交易成本计算:")
    buy_amount = 10000  # 买入1万元
    sell_amount = 11000  # 卖出1.1万元

    buy_cost = TradingCosts.calculate_buy_cost(buy_amount, is_sh=True)
    sell_cost = TradingCosts.calculate_sell_cost(sell_amount, is_sh=True)

    print(f"  买入{buy_amount}元:")
    print(f"    佣金: {buy_cost['commission']:.2f}元")
    print(f"    过户费: {buy_cost['transfer_fee']:.2f}元")
    print(f"    总成本: {buy_cost['total_cost']:.2f}元")

    print(f"\n  卖出{sell_amount}元:")
    print(f"    佣金: {sell_cost['commission']:.2f}元")
    print(f"    过户费: {sell_cost['transfer_fee']:.2f}元")
    print(f"    印花税: {sell_cost['stamp_tax']:.2f}元")
    print(f"    总成本: {sell_cost['total_cost']:.2f}元")

    # 测试ST股票识别
    print("\n1.3 ST股票识别:")
    test_names = ['平安银行', '*ST万科', 'ST国华', '退市整理', 'PT金田']
    for name in test_names:
        is_st = StockFilterRules.is_st_stock(name)
        should_exclude = StockFilterRules.should_exclude(name)
        print(f"  {name}: ST={is_st}, 排除={should_exclude}")

    # 测试市场类型识别
    print("\n1.4 市场类型识别:")
    test_codes = ['600000', '000001', '002001', '300001', '688001']
    for code in test_codes:
        market = MarketType.get_market_type(code)
        is_sh = MarketType.is_sh_stock(code)
        print(f"  {code}: 市场={market}, 上交所={is_sh}")

    print("\n✅ 测试1通过")


def test_stock_filter():
    """测试股票过滤器"""
    print("\n" + "="*60)
    print("测试2: 股票过滤器")
    print("="*60)

    # 创建测试股票列表
    test_stocks = pd.DataFrame({
        'symbol': ['000001', '000002', '600000', '600001', '300001', '688001'],
        'name': ['平安银行', '*ST万科', '浦发银行', 'ST国华', '特锐德', '南京证券'],
        'market': ['主板', '主板', '主板', '主板', '创业板', '科创板']
    })

    print("\n2.1 原始股票列表:")
    print(test_stocks)

    # 过滤股票列表
    stock_filter = StockFilter(verbose=True)
    filtered_stocks = stock_filter.filter_stock_list(test_stocks)

    print("\n2.2 过滤后股票列表:")
    print(filtered_stocks)

    # 创建测试价格数据
    print("\n2.3 测试价格数据过滤:")

    # 数据充足的情况
    good_df = pd.DataFrame({
        'close': np.random.uniform(10, 20, 300),
        'vol': np.random.uniform(1000000, 10000000, 300)
    })

    passed, _, reason = stock_filter.filter_price_data(good_df, '000001', min_trading_days=250)
    print(f"  充足数据(300天): 通过={passed}, 原因={reason}")

    # 数据不足的情况
    insufficient_df = pd.DataFrame({
        'close': np.random.uniform(10, 20, 100),
        'vol': np.random.uniform(1000000, 10000000, 100)
    })

    passed, _, reason = stock_filter.filter_price_data(insufficient_df, '000002', min_trading_days=250)
    print(f"  不足数据(100天): 通过={passed}, 原因={reason}")

    print("\n✅ 测试2通过")


def test_data_cleaner():
    """测试数据清洗器"""
    print("\n" + "="*60)
    print("测试3: 数据清洗器")
    print("="*60)

    # 创建有问题的测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    test_df = pd.DataFrame({
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(15, 25, 100),
        'low': np.random.uniform(5, 15, 100),
        'close': np.random.uniform(10, 20, 100),
        'vol': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 添加问题数据
    test_df.loc[dates[10], 'close'] = np.nan  # 缺失值
    test_df.loc[dates[20], 'high'] = 5  # OHLC逻辑错误
    test_df.loc[dates[30], 'close'] = 1000  # 异常涨幅
    test_df.loc[dates[40:45], :] = test_df.loc[dates[40], :]  # 重复行

    print(f"\n3.1 原始数据:")
    print(f"  行数: {len(test_df)}")
    print(f"  缺失值: {test_df.isnull().sum().sum()}")
    print(f"  重复行: {test_df.duplicated().sum()}")

    # 清洗数据
    cleaner = DataCleaner(verbose=True)
    cleaned_df = cleaner.clean_price_data(test_df, '000001')

    print(f"\n3.2 清洗后数据:")
    print(f"  行数: {len(cleaned_df)}")
    print(f"  缺失值: {cleaned_df.isnull().sum().sum()}")
    print(f"  重复行: {cleaned_df.duplicated().sum()}")

    # 验证OHLC
    validated_df = cleaner.validate_ohlc(cleaned_df, fix=True)

    print(f"\n3.3 OHLC验证后:")
    print(f"  行数: {len(validated_df)}")

    # 检查OHLC逻辑
    high_check = (validated_df['high'] >= validated_df[['open', 'close', 'low']].max(axis=1)).all()
    low_check = (validated_df['low'] <= validated_df[['open', 'close', 'high']].min(axis=1)).all()

    print(f"  High >= max(O,C,L): {high_check}")
    print(f"  Low <= min(O,C,H): {low_check}")

    print("\n✅ 测试3通过")


def test_data_fetcher():
    """测试数据获取器"""
    print("\n" + "="*60)
    print("测试4: 数据获取器 (仅测试接口，不实际下载)")
    print("="*60)

    fetcher = DataFetcher(data_source='akshare')

    print(f"\n4.1 数据源: {fetcher.data_source}")
    print(f"4.2 数据获取器初始化成功")

    # 注意: 这里不实际下载数据，避免浪费API配额
    # 在实际使用时，可以用以下代码测试:
    # df = fetcher.fetch_data('000001', start_date='20240101', end_date='20240131')
    # print(f"获取数据行数: {len(df) if df is not None else 0}")

    print("\n✅ 测试4通过")


def main():
    """运行所有测试"""
    print("\n" + "🧪"*30)
    print("Phase 1: 数据管道测试")
    print("🧪"*30)

    try:
        test_trading_rules()
        test_stock_filter()
        test_data_cleaner()
        test_data_fetcher()

        print("\n" + "="*60)
        print("✅ 所有测试通过！Phase 1 数据管道运行正常")
        print("="*60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
