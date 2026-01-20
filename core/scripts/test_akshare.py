#!/usr/bin/env python3
"""
AkShare数据获取功能测试脚本
测试获取股票列表和历史数据功能
"""

import sys
import os

# 添加core/src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_fetcher import DataFetcher
from a_stock_list_fetcher import fetch_akshare_stock_list
from datetime import datetime, timedelta

def test_stock_list():
    """测试获取股票列表"""
    print("=" * 60)
    print("测试1: 使用AkShare获取A股股票列表")
    print("=" * 60)

    try:
        success = fetch_akshare_stock_list(
            save_path="./data/test_stock_list.csv",
            save_to_db=False
        )

        if success:
            print("\n✅ 股票列表获取测试通过！")
            return True
        else:
            print("\n❌ 股票列表获取测试失败！")
            return False
    except Exception as e:
        print(f"\n❌ 股票列表获取测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stock_data():
    """测试获取股票历史数据"""
    print("\n" + "=" * 60)
    print("测试2: 使用AkShare获取股票历史数据")
    print("=" * 60)

    try:
        # 初始化数据获取器，使用AkShare作为主要数据源
        fetcher = DataFetcher(data_source='akshare')

        # 测试获取平安银行(000001)的数据
        symbol = "000001"
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')

        print(f"\n正在获取 {symbol} 最近30天的数据...")
        data = fetcher.fetch_akshare_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if data is not None and not data.empty:
            print("\n✅ 数据获取成功！")
            print(f"\n数据行数: {len(data)}")
            print(f"\n数据列: {list(data.columns)}")
            print(f"\n数据预览:")
            print(data.head())
            print(f"\n数据统计:")
            print(data[['open', 'close', 'high', 'low', 'vol']].describe())
            return True
        else:
            print("\n❌ 数据获取失败或数据为空！")
            return False

    except Exception as e:
        print(f"\n❌ 股票数据获取测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fetch_data_method():
    """测试智能fetch_data方法"""
    print("\n" + "=" * 60)
    print("测试3: 测试智能fetch_data方法（自动选择AkShare）")
    print("=" * 60)

    try:
        # 使用默认配置（akshare）
        fetcher = DataFetcher()

        # 测试获取贵州茅台(600519)的数据
        symbol = "600519"

        print(f"\n正在使用fetch_data方法获取 {symbol} 最近90天的数据...")
        data = fetcher.fetch_data(
            symbol=symbol,
            start_date=(datetime.now() - timedelta(days=90)).strftime('%Y%m%d'),
            end_date=datetime.now().strftime('%Y%m%d')
        )

        if data is not None and not data.empty:
            print("\n✅ fetch_data方法测试通过！")
            print(f"\n数据行数: {len(data)}")
            print(f"\n最近5天数据:")
            print(data.tail())
            return True
        else:
            print("\n❌ fetch_data方法测试失败！")
            return False

    except Exception as e:
        print(f"\n❌ fetch_data方法测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("AkShare数据获取功能测试")
    print("🚀" * 30 + "\n")

    # 确保data目录存在
    os.makedirs("data", exist_ok=True)

    results = []

    # 运行测试
    results.append(("股票列表获取", test_stock_list()))
    results.append(("股票数据获取", test_stock_data()))
    results.append(("智能fetch_data方法", test_fetch_data_method()))

    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, result in results if result)

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！AkShare集成成功！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查配置和网络连接")
        return 1

if __name__ == "__main__":
    sys.exit(main())
