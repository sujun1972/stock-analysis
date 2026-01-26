"""
第一阶段最终版：使用线性模型建立零泄露基准

核心结论：
1. LightGBM即使强正则化仍会过拟合小数据集（492样本）
2. Ridge回归表现正常：Train IC=0.057, 洗牌后应接近0
3. 使用线性模型建立基准，通过后再测试树模型

策略：
- 使用Ridge/LinearRegression作为基准模型
- 仅使用2个最简特征
- 通过洗牌测试和随机目标测试
"""
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from src.database.db_manager import get_database
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score

print("=" * 80)
print("【第一阶段最终版】线性模型零泄露基准")
print("=" * 80)

# 1. 加载原始数据
print("\n1. 加载原始数据...")
db = get_database()
df = db.load_daily_data('000002', '20210101', '20231231')
print(f"   加载 {len(df)} 条记录")

# 2. 创建最小化特征（手工计算）
print("\n2. 创建最小化特征集...")
X = pd.DataFrame(index=df.index)
X['close_pct_change'] = df['close'].pct_change() * 100
X['volume_pct_change'] = df['volume'].pct_change() * 100
print(f"   特征: {list(X.columns)}")

# 3. 创建目标变量（验证正确性）
print("\n3. 创建目标变量...")
target_period = 10
y = (df['close'].shift(-target_period) / df['close'] - 1) * 100
y.name = f'target_{target_period}d_return'

# 手工验证前3个样本
print("   验证前3个样本:")
for i in range(3):
    if i + target_period < len(df):
        close_t = df['close'].iloc[i]
        close_t_plus_n = df['close'].iloc[i + target_period]
        expected_return = (close_t_plus_n / close_t - 1) * 100
        actual_return = y.iloc[i]
        print(f"     [{i}] close[{i}]={close_t:.2f}, close[{i+target_period}]={close_t_plus_n:.2f}")
        print(f"         预期收益: {expected_return:.4f}%, 实际计算: {actual_return:.4f}%")

# 4. 清洗数据
print("\n4. 清洗数据...")
data = pd.concat([X, y], axis=1).dropna()
X = data[['close_pct_change', 'volume_pct_change']]
y = data[y.name]
print(f"   清洗后: {len(X)} 样本")

# 5. 分割数据
print("\n5. 分割数据...")
n = len(X)
train_end = int(n * 0.7)
valid_end = int(n * 0.85)

X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]
X_valid, y_valid = X.iloc[train_end:valid_end], y.iloc[train_end:valid_end]
X_test, y_test = X.iloc[valid_end:], y.iloc[valid_end:]
print(f"   训练: {len(X_train)}, 验证: {len(X_valid)}, 测试: {len(X_test)}")

# 6. 训练线性回归
print("\n6. 训练线性回归...")
lr = LinearRegression()
lr.fit(X_train, y_train)

y_train_pred_lr = lr.predict(X_train)
y_valid_pred_lr = lr.predict(X_valid)
y_test_pred_lr = lr.predict(X_test)

train_ic_lr = np.corrcoef(y_train, y_train_pred_lr)[0, 1]
valid_ic_lr = np.corrcoef(y_valid, y_valid_pred_lr)[0, 1]
test_ic_lr = np.corrcoef(y_test, y_test_pred_lr)[0, 1]
test_r2_lr = r2_score(y_test, y_test_pred_lr)

print(f"\n【线性回归结果】")
print(f"  Train IC: {train_ic_lr:.6f}")
print(f"  Valid IC: {valid_ic_lr:.6f}")
print(f"  Test IC:  {test_ic_lr:.6f}")
print(f"  Test R²:  {test_r2_lr:.6f}")
print(f"  系数: close_pct={lr.coef_[0]:.4f}, volume_pct={lr.coef_[1]:.4f}")

# 7. 训练Ridge回归
print("\n7. 训练Ridge回归...")
ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)

y_train_pred_ridge = ridge.predict(X_train)
y_test_pred_ridge = ridge.predict(X_test)

train_ic_ridge = np.corrcoef(y_train, y_train_pred_ridge)[0, 1]
test_ic_ridge = np.corrcoef(y_test, y_test_pred_ridge)[0, 1]

print(f"\n【Ridge回归结果】")
print(f"  Train IC: {train_ic_ridge:.6f}")
print(f"  Test IC:  {test_ic_ridge:.6f}")

# 8. 洗牌测试（线性回归）
print("\n8. 洗牌测试（Linear Regression）...")
X_shuffled = X.copy()
for col in X_shuffled.columns:
    X_shuffled[col] = np.random.permutation(X_shuffled[col].values)

X_train_s = X_shuffled.iloc[:train_end]
y_train_s = y.iloc[:train_end]

lr_shuffled = LinearRegression()
lr_shuffled.fit(X_train_s, y_train_s)
y_train_pred_s = lr_shuffled.predict(X_train_s)
train_ic_shuffled = np.corrcoef(y_train_s, y_train_pred_s)[0, 1]

print(f"\n【洗牌后结果】")
print(f"  Train IC: {train_ic_shuffled:.6f}")

if abs(train_ic_shuffled) > 0.1:
    print(f"  ❌ 警告：打乱后Train IC = {train_ic_shuffled:.4f}")
    print("     存在Target泄露或数据对齐问题！")
else:
    print(f"  ✓ 正常：打乱后Train IC = {train_ic_shuffled:.4f} ≈ 0")

# 9. 随机目标测试
print("\n9. 随机目标测试...")
y_random = pd.Series(np.random.randn(len(y_train)), index=y_train.index)

lr_random = LinearRegression()
lr_random.fit(X_train, y_random)
y_random_pred = lr_random.predict(X_train)
ic_random = np.corrcoef(y_random, y_random_pred)[0, 1]

print(f"\n【随机目标结果】")
print(f"  Train IC: {ic_random:.6f}")
if abs(ic_random) > 0.1:
    print(f"  ❌ 模型能拟合噪声（IC={ic_random:.4f}）")
else:
    print(f"  ✓ 正常：模型无法拟合噪声")

# 10. 最终判定
print("\n" + "=" * 80)
print("【第一阶段最终判定】")
print("=" * 80)

# 判定标准（线性模型更宽松）
lr_ok = abs(train_ic_lr) <= 0.2  # 线性模型IC一般较低
ridge_ok = abs(train_ic_ridge) <= 0.2
shuffle_ok = abs(train_ic_shuffled) <= 0.1
random_ok = abs(ic_random) <= 0.1

print(f"\n检查项:")
print(f"  1. 线性回归IC正常: {lr_ok} (IC={train_ic_lr:.4f})")
print(f"  2. Ridge回归IC正常: {ridge_ok} (IC={train_ic_ridge:.4f})")
print(f"  3. 洗牌测试通过: {shuffle_ok} (IC={train_ic_shuffled:.4f})")
print(f"  4. 随机目标测试通过: {random_ok} (IC={ic_random:.4f})")

if all([lr_ok, ridge_ok, shuffle_ok, random_ok]):
    print(f"\n" + "=" * 80)
    print("✓✓✓ 第一阶段 PASS")
    print("=" * 80)
    print("\n结论:")
    print("  1. 最小化特征集（close_pct_change, volume_pct_change）是干净的")
    print("  2. 目标变量计算正确，无泄露")
    print("  3. 数据对齐正确")
    print("  4. Pipeline基础框架合格")
    print("\n✓ 可以进入第二阶段：逐组添加特征，找出高IC的来源")
    print("\n注意:")
    print("  - 第二阶段应优先使用线性模型测试")
    print("  - LightGBM在小数据集上容易过拟合，需谨慎解读")
    print("  - 添加特征后，如果Train IC突然跳到>0.5，说明该组特征有泄露")
else:
    print(f"\n" + "=" * 80)
    print("❌ 第一阶段 FAIL")
    print("=" * 80)
    if not shuffle_ok:
        print("\n问题：洗牌测试未通过")
        print("  可能原因：")
        print("    1. 目标变量计算有误（shift方向错误）")
        print("    2. concat/dropna导致索引错位")
        print("    3. 数据库原始数据已包含未来信息")
    if not random_ok:
        print("\n问题：随机目标测试未通过")
        print("  可能原因：")
        print("    1. 模型过拟合（但线性模型一般不会）")
        print("    2. 特征和目标在内存中的排列有问题")

print("\n" + "=" * 80)
print("第一阶段完成")
print("=" * 80)
