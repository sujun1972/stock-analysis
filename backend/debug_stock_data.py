#!/usr/bin/env python3
"""
调试股票数据质量
检查指定股票的原始数据完整性、缺失值、停牌情况等
"""

import sys
sys.path.insert(0, '/app/src')

import pandas as pd
from database.db_manager import DatabaseManager

def analyze_stock_data(symbol: str, start_date: str, end_date: str):
    """分析股票数据质量"""
    print(f"\n{'='*80}")
    print(f"  股票数据质量分析: {symbol}")
    print(f"  日期范围: {start_date} ~ {end_date}")
    print(f"{'='*80}\n")

    db = DatabaseManager()

    # 1. 查询原始数据
    query = """
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_price
        WHERE ts_code = %s
          AND trade_date >= %s
          AND trade_date <= %s
        ORDER BY trade_date
    """

    # 转换股票代码格式 (000031 -> 000031.SZ)
    if len(symbol) == 6:
        if symbol.startswith('6'):
            ts_code = f"{symbol}.SH"
        else:
            ts_code = f"{symbol}.SZ"
    else:
        ts_code = symbol

    results = db._execute_query(query, (ts_code, start_date, end_date))

    if not results or len(results) == 0:
        print(f"❌ 没有找到股票 {symbol} ({ts_code}) 的数据!")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results, columns=['trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df = df.set_index('trade_date')

    print(f"✅ 数据总行数: {len(df)}")
    print(f"✅ 日期范围: {df.index.min()} ~ {df.index.max()}")
    print(f"✅ 实际交易天数: {len(df)}")

    # 2. 检查缺失值
    print(f"\n{'='*80}")
    print(f"  缺失值检查")
    print(f"{'='*80}\n")

    missing = df.isnull().sum()
    if missing.sum() > 0:
        print("⚠️  发现缺失值:")
        for col in missing[missing > 0].index:
            pct = (missing[col] / len(df)) * 100
            print(f"  - {col}: {missing[col]} 个 ({pct:.2f}%)")
    else:
        print("✅ 没有缺失值")

    # 3. 检查异常值
    print(f"\n{'='*80}")
    print(f"  异常值检查")
    print(f"{'='*80}\n")

    # 检查价格为0的情况
    zero_prices = (df[['open', 'high', 'low', 'close']] == 0).any(axis=1).sum()
    if zero_prices > 0:
        print(f"⚠️  发现 {zero_prices} 天价格为0 (可能停牌)")
        zero_dates = df[(df[['open', 'high', 'low', 'close']] == 0).any(axis=1)].index
        print(f"  停牌日期示例: {zero_dates[:5].tolist()}")
    else:
        print("✅ 没有价格为0的情况")

    # 检查成交量为0的情况
    zero_volume = (df['volume'] == 0).sum()
    if zero_volume > 0:
        pct = (zero_volume / len(df)) * 100
        print(f"⚠️  发现 {zero_volume} 天成交量为0 ({pct:.2f}%)")
    else:
        print("✅ 没有成交量为0的情况")

    # 4. 检查数据连续性
    print(f"\n{'='*80}")
    print(f"  数据连续性检查")
    print(f"{'='*80}\n")

    # 计算每日涨跌幅
    df['pct_change'] = df['close'].pct_change() * 100

    # 检查异常涨跌幅 (>10%或<-10%)
    extreme_changes = df[(df['pct_change'].abs() > 10)].copy()
    if len(extreme_changes) > 0:
        print(f"⚠️  发现 {len(extreme_changes)} 天涨跌幅超过±10%:")
        print(extreme_changes[['close', 'pct_change']].head(10))
    else:
        print("✅ 没有极端涨跌幅")

    # 5. 基本统计信息
    print(f"\n{'='*80}")
    print(f"  基本统计信息")
    print(f"{'='*80}\n")

    print("价格统计:")
    print(df[['open', 'high', 'low', 'close']].describe())

    print("\n成交量统计:")
    print(df[['volume', 'amount']].describe())

    # 6. 数据质量评分
    print(f"\n{'='*80}")
    print(f"  数据质量评分")
    print(f"{'='*80}\n")

    score = 100
    issues = []

    # 扣分项
    missing_pct = (missing.sum() / (len(df) * len(missing))) * 100
    if missing_pct > 0:
        deduction = min(missing_pct * 10, 30)
        score -= deduction
        issues.append(f"缺失值 {missing_pct:.2f}% (扣{deduction:.0f}分)")

    if zero_prices > 0:
        zero_pct = (zero_prices / len(df)) * 100
        deduction = min(zero_pct * 5, 20)
        score -= deduction
        issues.append(f"停牌 {zero_pct:.2f}% (扣{deduction:.0f}分)")

    if zero_volume > 0:
        zero_vol_pct = (zero_volume / len(df)) * 100
        deduction = min(zero_vol_pct * 3, 15)
        score -= deduction
        issues.append(f"无成交量 {zero_vol_pct:.2f}% (扣{deduction:.0f}分)")

    if len(extreme_changes) > 10:
        deduction = 10
        score -= deduction
        issues.append(f"频繁极端波动 (扣{deduction}分)")

    print(f"数据质量评分: {score:.1f}/100")

    if score >= 90:
        print("✅ 数据质量优秀，适合训练模型")
    elif score >= 70:
        print("⚠️  数据质量良好，建议谨慎使用")
    elif score >= 50:
        print("⚠️  数据质量一般，可能影响模型效果")
    else:
        print("❌ 数据质量较差，不建议使用此股票训练")

    if issues:
        print("\n主要问题:")
        for issue in issues:
            print(f"  - {issue}")

    # 7. 推荐建议
    print(f"\n{'='*80}")
    print(f"  训练建议")
    print(f"{'='*80}\n")

    if score < 70:
        print("❌ 建议更换股票:")
        print("  - 推荐使用: 000001 (平安银行), 000002 (万科A), 600000 (浦发银行)")
        print("  - 这些股票流动性好，数据质量高")
    else:
        if zero_prices > 0 or zero_volume > 0:
            print("⚠️  建议:")
            print("  - 数据预处理时启用 NaN 填充")
            print("  - 使用 forward fill 处理停牌期间的数据")

        if len(extreme_changes) > 5:
            print("⚠️  建议:")
            print("  - 启用样本平衡 (balance_samples=True)")
            print("  - 使用 Robust Scaler 处理异常值")

if __name__ == '__main__':
    # 分析000031
    print("\n" + "="*80)
    print("  分析 000031 (大悦城)")
    print("="*80)
    analyze_stock_data('000031', '20210125', '20260125')

    # 对比分析000001
    print("\n\n" + "="*80)
    print("  对比分析 000001 (平安银行)")
    print("="*80)
    analyze_stock_data('000001', '20210125', '20260125')
