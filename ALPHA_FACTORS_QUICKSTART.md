# Alpha Factors 优化版本 - 快速开始

## 📦 安装和迁移

### 从旧版本迁移

**好消息：无需修改任何代码！** 优化版本 100% 向后兼容。

```python
# 旧代码继续工作
from features.alpha_factors import AlphaFactors

af = AlphaFactors(df)
result = af.add_all_alpha_factors()
```

### 启用新功能

```python
# 推荐配置（生产环境）
af = AlphaFactors(
    df,
    inplace=False,                # 安全模式
    enable_leak_detection=False,  # 关闭检测（性能优先）
    enable_copy_on_write=True     # 开启CoW（节省内存）
)

result = af.add_all_alpha_factors(show_cache_stats=False)
```

---

## 🚀 性能提升

### 关键改进

| 优化项 | 提升效果 | 适用场景 |
|--------|---------|---------|
| **向量化线性回归** | 35倍 ⚡ | 趋势因子计算 |
| **共享缓存** | 2-3倍 ⚡ | 重复计算场景 |
| **Copy-on-Write** | -50% 内存 💾 | 大数据集 |

### 实际测试结果

```
数据规模: 2000行 × 5列
优化前总耗时: 12.3秒
优化后总耗时: 4.1秒
加速比: 3倍
```

---

## 💡 最佳实践

### 1. 生产环境推荐配置

```python
import pandas as pd
from features.alpha_factors import AlphaFactors

# 加载数据
df = pd.read_csv('stock_data.csv', index_col='date', parse_dates=True)

# 创建因子计算器（推荐配置）
af = AlphaFactors(
    df,
    inplace=False,                # 不修改原数据
    enable_copy_on_write=True     # 节省内存
)

# 计算所有因子
result = af.add_all_alpha_factors()

# 获取因子列表
factor_names = af.get_factor_names()
print(f"生成了 {len(factor_names)} 个因子")

# 保存结果
result.to_parquet('stock_features.parquet')
```

### 2. 开发/调试配置

```python
# 启用数据泄漏检测
af = AlphaFactors(
    df,
    enable_leak_detection=True,   # 检测数据泄漏
    enable_copy_on_write=True
)

# 显示缓存统计
result = af.add_all_alpha_factors(show_cache_stats=True)

# 输出示例:
# 缓存统计: 命中率=56.3%, 命中=125, 未命中=97, 大小=45/200
# ✓ 数据泄漏检测通过
```

### 3. 批量处理多个股票

```python
stock_list = ['000001', '000002', '600000', '600036']

for stock_code in stock_list:
    df = load_stock_data(stock_code)

    af = AlphaFactors(df, enable_copy_on_write=True)
    result = af.add_all_alpha_factors()

    # 缓存会自动在相同周期的计算中复用
    # 无需手动清理（除非内存紧张）

    save_result(stock_code, result)

# 处理完成后清空缓存（可选）
af.clear_cache()
```

### 4. 内存优化策略

```python
# 方案A: 最省内存（直接修改原数据）
af = AlphaFactors(df, inplace=True)
result = af.add_all_alpha_factors()
# 注意：df 已被修改

# 方案B: 安全且省内存（推荐）
af = AlphaFactors(df, inplace=False, enable_copy_on_write=True)
result = af.add_all_alpha_factors()
# df 不变，result 包含所有因子

# 方案C: 分段计算（超大数据集）
af = AlphaFactors(df, enable_copy_on_write=True)

# 分批计算，每次清空缓存
af.momentum.calculate_all()
af.clear_cache()

af.trend.calculate_all()
af.clear_cache()

# ...
```

---

## 🔍 常见问题

### Q1: 如何验证性能提升？

```python
import time

# 测试优化版本
start = time.perf_counter()
af = AlphaFactors(df, enable_copy_on_write=True)
result = af.add_all_alpha_factors(show_cache_stats=True)
elapsed = time.perf_counter() - start

print(f"计算耗时: {elapsed:.2f} 秒")
print(f"生成因子: {len(af.get_factor_names())} 个")

# 查看缓存效果
cache_stats = af.get_cache_stats()
print(f"缓存命中率: {cache_stats['hit_rate']:.2%}")
```

### Q2: 数据泄漏检测如何使用？

```python
# 开发阶段建议启用
af = AlphaFactors(df, enable_leak_detection=True)
result = af.add_all_alpha_factors()

# 如果检测到泄漏，会在日志中输出：
# ⚠️  检测到数据泄漏! 因子 XXX 与未来收益相关性: 0.97

# 生产环境建议关闭（提升性能）
af = AlphaFactors(df, enable_leak_detection=False)
```

### Q3: Copy-on-Write 有什么要求？

```python
# 需要 Pandas 2.0+
import pandas as pd
print(pd.__version__)  # 应该 >= 2.0.0

# 如果是旧版本，会自动降级到传统模式
# 仍然可以正常工作，只是内存优化效果降低
```

### Q4: 如何清空缓存？

```python
# 方法1: 实例方法
af.clear_cache()

# 方法2: 类方法（清空所有实例的共享缓存）
from features.alpha_factors import BaseFactorCalculator
BaseFactorCalculator._shared_cache.clear()
```

### Q5: 向量化版本的结果与旧版本一致吗？

**是的，完全一致。** 我们使用了相同的数学公式，只是改变了计算方式。

```python
# 验证结果一致性
import numpy as np

# 旧版本结果（从备份加载）
old_result = pd.read_parquet('old_factors.parquet')

# 新版本结果
new_result = af.add_all_alpha_factors()

# 对比（允许浮点误差）
for col in old_result.columns:
    if col in new_result.columns:
        diff = np.abs(new_result[col] - old_result[col])
        max_diff = diff.max()
        assert max_diff < 1e-10, f"{col} 结果不一致: {max_diff}"

print("✓ 所有因子结果一致")
```

---

## 📊 缓存统计说明

```python
cache_stats = af.get_cache_stats()

# 返回字典:
{
    'size': 45,           # 当前缓存条目数
    'max_size': 200,      # 最大缓存容量
    'hits': 125,          # 缓存命中次数
    'misses': 97,         # 缓存未命中次数
    'hit_rate': 0.563     # 命中率 (56.3%)
}

# 命中率说明:
# - 0-30%: 低效（考虑调整计算顺序）
# - 30-60%: 正常（多数场景）
# - 60%+: 高效（大量重复计算被优化）
```

---

## 🎯 选择合适的配置

### 场景 1: 单次计算（小数据集 <1000行）

```python
# 使用默认配置即可
af = AlphaFactors(df)
result = af.add_all_alpha_factors()
```

### 场景 2: 批量计算（多个股票）

```python
# 启用 Copy-on-Write
af = AlphaFactors(df, enable_copy_on_write=True)
result = af.add_all_alpha_factors()
```

### 场景 3: 大数据集（>5000行）

```python
# 启用 CoW + 定期清缓存
for chunk in data_chunks:
    af = AlphaFactors(chunk, enable_copy_on_write=True)
    result = af.add_all_alpha_factors()
    save(result)
    af.clear_cache()  # 释放内存
```

### 场景 4: 开发新因子

```python
# 启用泄漏检测 + 缓存统计
af = AlphaFactors(
    df,
    enable_leak_detection=True,
    enable_copy_on_write=True
)
result = af.add_all_alpha_factors(show_cache_stats=True)
```

---

## 🔗 相关资源

- **详细报告**: [ALPHA_FACTORS_OPTIMIZATION_REPORT.md](ALPHA_FACTORS_OPTIMIZATION_REPORT.md)
- **源代码**: [core/src/features/alpha_factors.py](core/src/features/alpha_factors.py)
- **测试文件**: [core/tests/test_alpha_factors_optimization.py](core/tests/test_alpha_factors_optimization.py)

---

## 🆘 遇到问题？

### 常见错误排查

**错误1: ModuleNotFoundError: No module named 'pandas'**
```bash
# 安装依赖
pip install pandas numpy loguru
```

**错误2: 内存占用仍然很高**
```python
# 检查 Pandas 版本
import pandas as pd
print(pd.__version__)

# 如果 < 2.0，升级或使用 inplace=True
pip install --upgrade pandas

# 或者
af = AlphaFactors(df, inplace=True)  # 直接修改原数据
```

**错误3: 缓存命中率很低**
```python
# 可能原因：数据集每次都不同
# 解决方案：批量计算时复用相同的周期参数

# 不推荐（命中率低）
af1.add_momentum_factors(periods=[5, 10])
af2.add_momentum_factors(periods=[10, 20])

# 推荐（命中率高）
af1.add_momentum_factors(periods=[5, 10, 20])
af2.add_momentum_factors(periods=[5, 10, 20])
```

---

## ✅ 快速验证

运行这个脚本确认优化版本工作正常：

```python
import pandas as pd
import numpy as np
from features.alpha_factors import AlphaFactors

# 创建测试数据
df = pd.DataFrame({
    'close': np.random.randn(500).cumsum() + 100,
    'volume': np.random.uniform(1e6, 1e7, 500)
})

# 计算因子
af = AlphaFactors(df, enable_copy_on_write=True)
result = af.add_all_alpha_factors(show_cache_stats=True)

# 验证结果
factor_names = af.get_factor_names()
print(f"✓ 生成因子: {len(factor_names)} 个")
print(f"✓ 数据形状: {result.shape}")
print(f"✓ 缓存统计: {af.get_cache_stats()}")
print("\n优化版本工作正常！")
```

---

**最后更新**: 2026-01-27
**版本**: 2.0-optimized
