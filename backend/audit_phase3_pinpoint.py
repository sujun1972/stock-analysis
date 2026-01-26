"""
第三阶段：单个特征精确定位

Phase 2 发现4个可疑组，现在对每个组内的特征逐个测试
找出具体哪些特征导致泄露
"""
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from src.database.db_manager import get_database
from src.data_pipeline.feature_engineer import FeatureEngineer
from sklearn.linear_model import LinearRegression

print("=" * 80)
print("【第三阶段】单个特征精确定位")
print("=" * 80)

# 1. 加载数据
print("\n1. 加载数据...")
db = get_database()
df_raw = db.load_daily_data('000002', '20210101', '20231231')
fe = FeatureEngineer(verbose=False)
df_all = fe.compute_all_features(df_raw, target_period=10)

# 2. 准备基准特征
baseline_features = ['close_pct_change', 'volume_pct_change']
df_all['close_pct_change'] = df_raw['close'].pct_change() * 100
df_all['volume_pct_change'] = df_raw['volume'].pct_change() * 100
target_col = 'target_10d_return'

# 3. 定义可疑特征组（从Phase 2结果）
suspicious_groups = {
    'GroupA_MA趋势': [
        'CLOSE_TO_MA5_RATIO', 'CLOSE_TO_MA10_RATIO', 'CLOSE_TO_MA20_RATIO',
        'CLOSE_TO_MA60_RATIO', 'CLOSE_TO_MA120_RATIO', 'CLOSE_TO_MA250_RATIO',
        'CLOSE_TO_EMA12_RATIO', 'CLOSE_TO_EMA26_RATIO', 'CLOSE_TO_EMA50_RATIO'
    ],
    'GroupB_RSI_KDJ震荡': [
        'RSI6', 'RSI12', 'RSI24', 'KDJ_K', 'KDJ_D', 'KDJ_J',
        'MACD', 'MACD_SIGNAL', 'MACD_HIST'
    ],
    'GroupC_动量': [
        'MOM5', 'MOM_LOG5', 'MOM10', 'MOM_LOG10', 'MOM20', 'MOM_LOG20',
        'MOM60', 'MOM_LOG60', 'MOM120', 'MOM_LOG120'
    ],
    'GroupD_波动率': [
        'BOLL_WIDTH', 'BOLL_POS', 'ATR14_PCT', 'ATR28_PCT',
        'VOLATILITY5', 'VOLATILITY10', 'VOLATILITY20', 'VOLATILITY60',
        'CLOSE_TO_BOLL_UPPER_RATIO', 'CLOSE_TO_BOLL_MIDDLE_RATIO', 'CLOSE_TO_BOLL_LOWER_RATIO'
    ]
}

# 4. 逐个特征测试
print("\n" + "=" * 80)
print("逐个特征测试")
print("=" * 80)

all_results = []

for group_name, features in suspicious_groups.items():
    print(f"\n\n【{group_name}】")
    print("=" * 60)

    for feature in features:
        if feature not in df_all.columns:
            print(f"  {feature}: ❌ 不存在")
            continue

        # 基准 + 单个特征
        test_features = baseline_features + [feature]

        # 清洗数据
        df_temp = df_all[test_features + [target_col]].dropna()
        if len(df_temp) < 100:
            print(f"  {feature}: ❌ 数据不足 ({len(df_temp)} 样本)")
            continue

        # 分割
        n = len(df_temp)
        train_end = int(n * 0.7)

        X = df_temp[test_features]
        y = df_temp[target_col]

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        # 训练
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred = lr.predict(X_train)
        train_ic = np.corrcoef(y_train, y_pred)[0, 1]

        # 特征系数
        coef = lr.coef_[-1]  # 最后一个是新加的特征

        # 判定
        if train_ic > 0.5:
            status = "❌❌❌"
            level = "严重泄露"
        elif train_ic > 0.3:
            status = "⚠️⚠️"
            level = "可疑"
        elif train_ic > 0.15:
            status = "⚠️"
            level = "略高"
        else:
            status = "✓"
            level = "正常"

        print(f"  {feature:30s} IC={train_ic:.4f} 系数={coef:+.4f} {status} {level}")

        all_results.append({
            'group': group_name,
            'feature': feature,
            'train_ic': train_ic,
            'coef': coef,
            'status': level,
            'samples': len(df_temp)
        })

# 5. 汇总最严重的泄露特征
print("\n\n" + "=" * 80)
print("【汇总】最严重的泄露特征 (IC > 0.3)")
print("=" * 80)

results_df = pd.DataFrame(all_results)
leaky_features = results_df[results_df['train_ic'] > 0.3].sort_values('train_ic', ascending=False)

if len(leaky_features) > 0:
    print(f"\n发现 {len(leaky_features)} 个高IC特征:\n")
    for _, row in leaky_features.iterrows():
        print(f"  [{row['group']}]")
        print(f"    特征: {row['feature']}")
        print(f"    Train IC: {row['train_ic']:.4f}")
        print(f"    系数: {row['coef']:+.4f}")
        print(f"    样本: {row['samples']}")
        print()

    print("=" * 80)
    print("【结论】")
    print("=" * 80)
    print("\n这些特征需要进入第四阶段，检查代码计算逻辑:")

    for _, row in leaky_features.iterrows():
        print(f"  - {row['feature']} (IC={row['train_ic']:.4f})")

    print("\n检查重点:")
    print("  1. 是否使用了shift(-N)获取未来数据")
    print("  2. 是否使用了cumsum/expanding等累积计算导致信息泄露")
    print("  3. 是否使用了forward-fill填充导致未来信息传递")
    print("  4. MA/EMA/BOLL等指标的计算窗口是否包含当前点")

else:
    print("\n✓ 未发现IC>0.3的特征")
    print("  所有特征在单独测试时均正常")
    print("  Phase 2的高IC可能来自特征组合效应")

print("\n" + "=" * 80)
print("第三阶段完成")
print("=" * 80)
