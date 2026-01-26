"""
行业池化训练：解决LightGBM过拟合问题

策略：
1. 选择银行或地产板块的20只股票
2. 将多只股票的数据池化（pooled），拼接成大数据集
3. 使样本量达到5000+，缓解过拟合
4. 使用审计建议的正则化配置
"""
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from src.database.db_manager import get_database
from src.data_pipeline.feature_engineer import FeatureEngineer
from src.models.model_trainer import ModelTrainer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("【行业池化训练】解决过拟合问题")
print("=" * 80)

# 1. 获取股票列表并选择板块
print("\n1. 选择行业板块股票...")
db = get_database()
stock_df = db.get_stock_list()

# 选择银行板块
bank_stocks = stock_df[stock_df['industry'] == '银行']['code'].tolist()
print(f"   银行板块: {len(bank_stocks)} 只")

# 选择地产板块
estate_stocks = stock_df[stock_df['industry'].isin(['房地产', '房地产开发'])]['code'].tolist()
print(f"   地产板块: {len(estate_stocks)} 只")

# 选择样本量更多的板块
if len(bank_stocks) >= 20:
    sector = '银行'
    selected_stocks = bank_stocks[:20]
elif len(estate_stocks) >= 20:
    sector = '地产'
    selected_stocks = estate_stocks[:20]
else:
    # 如果特定板块不够，选择前20只有数据的股票
    print("   板块股票不足20只，改为选择前20只有历史数据的股票")
    sector = '混合'
    selected_stocks = stock_df['code'].tolist()[:20]

print(f"\n   选择板块: {sector}")
print(f"   选择股票数: {len(selected_stocks)}")
print(f"   股票列表: {selected_stocks}")

# 2. 加载并池化数据
print("\n2. 加载股票数据...")
pooled_data = []
target_period = 10
date_range = ('20210101', '20231231')

for i, stock_code in enumerate(selected_stocks):
    try:
        # 加载原始数据
        df_raw = db.load_daily_data(stock_code, date_range[0], date_range[1])

        if len(df_raw) < 100:
            print(f"   [{i+1}/{len(selected_stocks)}] {stock_code}: 数据不足({len(df_raw)}条)，跳过")
            continue

        # 计算特征
        fe = FeatureEngineer(verbose=False)
        df_features = fe.compute_all_features(df_raw, target_period=target_period)

        # 添加股票代码列
        df_features['stock_code'] = stock_code

        pooled_data.append(df_features)
        print(f"   [{i+1}/{len(selected_stocks)}] {stock_code}: {len(df_features)} 条数据")

    except Exception as e:
        print(f"   [{i+1}/{len(selected_stocks)}] {stock_code}: 错误 - {e}")
        continue

if len(pooled_data) == 0:
    print("\n❌ 没有成功加载任何股票数据")
    sys.exit(1)

# 3. 拼接数据
print(f"\n3. 拼接数据...")
df_all = pd.concat(pooled_data, axis=0, ignore_index=True)
print(f"   拼接后总样本: {len(df_all)} 条")
print(f"   特征数: {len([c for c in df_all.columns if not c.startswith('target_') and c != 'stock_code'])} 个")

# 4. 准备训练数据
print("\n4. 准备训练数据...")
target_col = f'target_{target_period}d_return'

# 选择特征（排除target和stock_code）
feature_cols = [c for c in df_all.columns if not c.startswith('target_') and c != 'stock_code']
print(f"   特征列数: {len(feature_cols)}")

# 删除缺失值
df_clean = df_all[feature_cols + [target_col]].dropna()
print(f"   清洗后样本: {len(df_clean)} 条")

if len(df_clean) < 1000:
    print(f"\n⚠️  警告: 样本量({len(df_clean)})仍然不足，建议至少5000+")

X = df_clean[feature_cols]
y = df_clean[target_col]

# 5. 时间序列分割（保持时序，不打乱）
print("\n5. 分割数据（时间序列）...")
n = len(X)
train_end = int(n * 0.7)
valid_end = int(n * 0.85)

X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
X_valid, y_valid = X.iloc[train_end:valid_end], y.iloc[train_end:valid_end]
X_test, y_test = X.iloc[valid_end:], y.iloc[valid_end:]

print(f"   训练集: {len(X_train)} 样本")
print(f"   验证集: {len(X_valid)} 样本")
print(f"   测试集: {len(X_test)} 样本")

# 6. 训练Ridge线性模型（基准）
print("\n6. 训练Ridge线性模型（基准）...")
ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)

y_train_pred_ridge = ridge.predict(X_train)
y_valid_pred_ridge = ridge.predict(X_valid)
y_test_pred_ridge = ridge.predict(X_test)

train_ic_ridge = np.corrcoef(y_train, y_train_pred_ridge)[0, 1]
valid_ic_ridge = np.corrcoef(y_valid, y_valid_pred_ridge)[0, 1]
test_ic_ridge = np.corrcoef(y_test, y_test_pred_ridge)[0, 1]
test_r2_ridge = r2_score(y_test, y_test_pred_ridge)

print(f"\n【Ridge回归结果】")
print(f"  Train IC: {train_ic_ridge:.6f}")
print(f"  Valid IC: {valid_ic_ridge:.6f}")
print(f"  Test IC:  {test_ic_ridge:.6f}")
print(f"  Test R²:  {test_r2_ridge:.6f}")

# 7. 训练LightGBM（审计建议的正则化配置）
print("\n7. 训练LightGBM（强正则化配置）...")
trainer = ModelTrainer(model_type='lightgbm', model_params={
    'max_depth': 3,
    'num_leaves': 7,
    'n_estimators': 200,
    'learning_rate': 0.03,
    'min_child_samples': 100,      # 增加到100
    'reg_alpha': 2.0,               # 增强L1正则化
    'reg_lambda': 2.0,              # 增强L2正则化
    'subsample': 0.7,               # 降低到70%
    'colsample_bytree': 0.7,        # 降低到70%
    'verbose': -1
})

trainer.train(X_train, y_train, X_valid, y_valid)

y_train_pred_lgb = trainer.model.predict(X_train)
y_valid_pred_lgb = trainer.model.predict(X_valid)
y_test_pred_lgb = trainer.model.predict(X_test)

train_ic_lgb = np.corrcoef(y_train, y_train_pred_lgb)[0, 1]
valid_ic_lgb = np.corrcoef(y_valid, y_valid_pred_lgb)[0, 1]
test_ic_lgb = np.corrcoef(y_test, y_test_pred_lgb)[0, 1]
test_r2_lgb = r2_score(y_test, y_test_pred_lgb)

print(f"\n【LightGBM结果】")
print(f"  Train IC: {train_ic_lgb:.6f}")
print(f"  Valid IC: {valid_ic_lgb:.6f}")
print(f"  Test IC:  {test_ic_lgb:.6f}")
print(f"  Test R²:  {test_r2_lgb:.6f}")

# 8. 对比分析
print("\n" + "=" * 80)
print("【模型对比】")
print("=" * 80)

print(f"\n模型           Train IC  Valid IC  Test IC   Test R²   过拟合程度")
print(f"-" * 80)
print(f"Ridge         {train_ic_ridge:8.4f}  {valid_ic_ridge:8.4f}  {test_ic_ridge:8.4f}  {test_r2_ridge:8.4f}  {train_ic_ridge - test_ic_ridge:+8.4f}")
print(f"LightGBM      {train_ic_lgb:8.4f}  {valid_ic_lgb:8.4f}  {test_ic_lgb:8.4f}  {test_r2_lgb:8.4f}  {train_ic_lgb - test_ic_lgb:+8.4f}")

# 9. 判定
print("\n" + "=" * 80)
print("【判定】")
print("=" * 80)

overfit_ridge = abs(train_ic_ridge - test_ic_ridge)
overfit_lgb = abs(train_ic_lgb - test_ic_lgb)

print(f"\n过拟合指标 (|Train IC - Test IC|):")
print(f"  Ridge:    {overfit_ridge:.4f}")
print(f"  LightGBM: {overfit_lgb:.4f}")

if overfit_lgb < 0.15:
    print(f"\n✓✓✓ LightGBM过拟合显著改善!")
    print(f"  - 池化训练成功缓解了过拟合问题")
    print(f"  - Train-Test IC差距 = {overfit_lgb:.4f} < 0.15")
elif overfit_lgb < 0.3:
    print(f"\n✓ LightGBM过拟合有所改善")
    print(f"  - 池化训练部分缓解了过拟合")
    print(f"  - Train-Test IC差距 = {overfit_lgb:.4f}")
else:
    print(f"\n⚠️  LightGBM仍存在过拟合")
    print(f"  - Train-Test IC差距 = {overfit_lgb:.4f} > 0.3")
    print(f"  - 建议: 继续增加样本量或使用Ridge模型")

# Test性能判定
if test_ic_lgb > 0.02 and test_r2_lgb > 0:
    print(f"\n✓ Test性能合格:")
    print(f"  - Test IC = {test_ic_lgb:.4f} > 0.02 (有预测能力)")
    print(f"  - Test R² = {test_r2_lgb:.4f} > 0 (泛化有效)")
elif test_ic_ridge > 0.02 and test_r2_ridge > 0:
    print(f"\n✓ Ridge Test性能合格:")
    print(f"  - Test IC = {test_ic_ridge:.4f} > 0.02")
    print(f"  - Test R² = {test_r2_ridge:.4f} > 0")
    print(f"\n建议: 使用Ridge模型替代LightGBM")
else:
    print(f"\n⚠️  Test性能不足:")
    print(f"  - 模型泛化能力有限")
    print(f"  - 建议: 检查特征质量或增加更多股票")

print("\n" + "=" * 80)
print(f"池化训练完成 - 总样本: {len(df_clean)}, 板块: {sector}")
print("=" * 80)
