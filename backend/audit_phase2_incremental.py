"""
第二阶段：逐组特征白名单测试

策略：
在第一阶段零泄露基准(IC=0.057)上，逐组添加特征，观察IC变化
- 如果某组加入后IC突然>0.5，说明该组有泄露
- 使用线性回归避免过拟合干扰
"""
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from src.database.db_manager import get_database
from src.data_pipeline.feature_engineer import FeatureEngineer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score

print("=" * 80)
print("【第二阶段】逐组特征白名单测试")
print("=" * 80)

# 1. 加载数据并计算所有特征
print("\n1. 加载数据并计算所有特征...")
db = get_database()
df_raw = db.load_daily_data('000002', '20210101', '20231231')
print(f"   加载 {len(df_raw)} 条原始数据")

fe = FeatureEngineer(verbose=False)
df_all = fe.compute_all_features(df_raw, target_period=10)
print(f"   计算完成: {len(df_all.columns)} 列")

# 2. 定义特征组
print("\n2. 定义特征组...")
feature_groups = {
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

# 过滤存在的特征
for group_name, features in feature_groups.items():
    existing = [f for f in features if f in df_all.columns]
    feature_groups[group_name] = existing
    print(f"   {group_name}: {len(existing)} 个特征")

# 3. 准备基准特征（Phase 1的最小化特征）
print("\n3. 准备数据...")
baseline_features = ['close_pct_change', 'volume_pct_change']
df_all['close_pct_change'] = df_raw['close'].pct_change() * 100
df_all['volume_pct_change'] = df_raw['volume'].pct_change() * 100

target_col = 'target_10d_return'
df_clean = df_all.dropna(subset=baseline_features + [target_col])
print(f"   清洗后: {len(df_clean)} 样本")

# 分割数据
n = len(df_clean)
train_end = int(n * 0.7)
valid_end = int(n * 0.85)

# 4. 测试基准（Phase 1结果）
print("\n4. 测试基准（Phase 1最小化特征）...")
X_baseline = df_clean[baseline_features]
y = df_clean[target_col]

X_train_base = X_baseline.iloc[:train_end]
y_train = y.iloc[:train_end]
X_test_base = X_baseline.iloc[valid_end:]
y_test = y.iloc[valid_end:]

lr_base = LinearRegression()
lr_base.fit(X_train_base, y_train)
y_train_pred_base = lr_base.predict(X_train_base)
y_test_pred_base = lr_base.predict(X_test_base)

train_ic_base = np.corrcoef(y_train, y_train_pred_base)[0, 1]
test_ic_base = np.corrcoef(y_test, y_test_pred_base)[0, 1]

print(f"   基准 Train IC: {train_ic_base:.6f}")
print(f"   基准 Test IC:  {test_ic_base:.6f}")

# 5. 逐组添加特征测试
print("\n" + "=" * 80)
print("5. 逐组添加特征测试")
print("=" * 80)

results = []

for group_name, group_features in feature_groups.items():
    print(f"\n【{group_name}】")
    print(f"  添加 {len(group_features)} 个特征")

    # 合并基准特征 + 当前组特征
    combined_features = baseline_features + group_features

    # 检查哪些特征在df_clean中有效
    valid_features = [f for f in combined_features if f in df_clean.columns]
    missing_features = [f for f in combined_features if f not in df_clean.columns]

    if missing_features:
        print(f"  ⚠️  缺失特征: {missing_features}")

    # 删除NA
    df_temp = df_clean[valid_features + [target_col]].dropna()
    if len(df_temp) < 100:
        print(f"  ❌ 数据不足: {len(df_temp)} 样本")
        continue

    # 重新分割（因为dropna可能改变样本数）
    n_temp = len(df_temp)
    train_end_temp = int(n_temp * 0.7)
    valid_end_temp = int(n_temp * 0.85)

    X_combined = df_temp[valid_features]
    y_temp = df_temp[target_col]

    X_train = X_combined.iloc[:train_end_temp]
    y_train_temp = y_temp.iloc[:train_end_temp]
    X_test = X_combined.iloc[valid_end_temp:]
    y_test_temp = y_temp.iloc[valid_end_temp:]

    # 训练线性回归
    lr = LinearRegression()
    lr.fit(X_train, y_train_temp)

    y_train_pred = lr.predict(X_train)
    y_test_pred = lr.predict(X_test)

    train_ic = np.corrcoef(y_train_temp, y_train_pred)[0, 1]
    test_ic = np.corrcoef(y_test_temp, y_test_pred)[0, 1]
    test_r2 = r2_score(y_test_temp, y_test_pred)

    # 特征重要性（系数）
    coefs = pd.Series(lr.coef_, index=valid_features).abs().sort_values(ascending=False)
    top_features = coefs.head(5)

    print(f"\n  【结果】")
    print(f"    Train IC: {train_ic:.6f} (基准: {train_ic_base:.6f}, 变化: {train_ic - train_ic_base:+.6f})")
    print(f"    Test IC:  {test_ic:.6f}")
    print(f"    Test R²:  {test_r2:.6f}")
    print(f"    有效样本: {len(df_temp)} ({len(X_train)} train, {len(X_test)} test)")
    print(f"\n  Top 5 重要特征 (|系数|):")
    for feat, coef in top_features.items():
        print(f"    {feat}: {coef:.6f}")

    # 判定
    ic_increase = train_ic - train_ic_base
    if train_ic > 0.5:
        status = "❌❌❌ 严重泄露"
        explanation = f"Train IC={train_ic:.4f} > 0.5，该组特征存在严重泄露！"
    elif ic_increase > 0.3:
        status = "⚠️⚠️ 可疑"
        explanation = f"IC提升{ic_increase:.4f}，远超正常范围，需要检查该组特征"
    elif ic_increase > 0.1:
        status = "⚠️ 略高"
        explanation = f"IC提升{ic_increase:.4f}，略高但可能正常"
    else:
        status = "✓ 正常"
        explanation = f"IC提升{ic_increase:.4f}，在合理范围内"

    print(f"\n  【判定】{status}")
    print(f"    {explanation}")

    results.append({
        'group': group_name,
        'num_features': len(valid_features),
        'train_ic': train_ic,
        'test_ic': test_ic,
        'test_r2': test_r2,
        'ic_increase': ic_increase,
        'status': status,
        'samples': len(df_temp),
        'top_feature': top_features.index[0] if len(top_features) > 0 else None
    })

# 6. 汇总结果
print("\n" + "=" * 80)
print("【第二阶段汇总】")
print("=" * 80)

results_df = pd.DataFrame(results)
print("\n特征组测试结果:")
print(results_df[['group', 'train_ic', 'ic_increase', 'status']].to_string(index=False))

# 找出可疑组
suspicious_groups = results_df[results_df['train_ic'] > 0.3]
if len(suspicious_groups) > 0:
    print(f"\n❌ 发现 {len(suspicious_groups)} 个可疑特征组:")
    for _, row in suspicious_groups.iterrows():
        print(f"  - {row['group']}: Train IC={row['train_ic']:.4f}, Top特征={row['top_feature']}")
    print("\n建议:")
    print("  1. 进入第三阶段，对可疑组内的每个特征单独测试")
    print("  2. 检查可疑特征的计算逻辑，是否使用了shift(-N)或未来数据")
else:
    print("\n✓✓✓ 所有特征组通过测试")
    print("  - 未发现明显的特征泄露")
    print("  - 原始高IC可能来自：")
    print("    1. LightGBM过拟合（已在Phase 1确认）")
    print("    2. 数据库预计算字段错误（pct_change字段不一致）")
    print("    3. 特征组合效应（多个特征交互）")

print("\n" + "=" * 80)
print("第二阶段完成")
print("=" * 80)
