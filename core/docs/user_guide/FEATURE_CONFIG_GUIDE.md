# 特征工程配置指南

## 概述

特征工程配置系统 (`config.features`) 提供了统一的配置管理，消除了硬编码问题，使得所有特征计算参数都可配置。

## 配置结构

配置系统分为以下几个部分：

### 1. TradingDaysConfig - 交易日配置
```python
from config.features import get_feature_config

config = get_feature_config()
print(config.trading_days.annual_trading_days)  # 252
print(config.trading_days.epsilon)              # 1e-8
```

### 2. TechnicalIndicatorConfig - 技术指标配置
```python
config = get_feature_config()
ti_config = config.technical_indicators

# 移动平均线周期
print(ti_config.ma_periods)        # [5, 10, 20, 60, 120, 250]
print(ti_config.ema_periods)       # [12, 26, 50]
print(ti_config.rsi_periods)       # [6, 12, 24]
print(ti_config.atr_periods)       # [14, 28]
print(ti_config.cci_periods)       # [14, 28]

# MACD参数
print(ti_config.macd_fast_period)  # 12
print(ti_config.macd_slow_period)  # 26
print(ti_config.macd_signal_period) # 9

# 布林带参数
print(ti_config.bollinger_period)         # 20
print(ti_config.bollinger_std_multiplier) # 2.0
```

### 3. AlphaFactorConfig - Alpha因子配置
```python
config = get_feature_config()
alpha_config = config.alpha_factors

# 不同周期类型
print(alpha_config.default_short_periods)   # [5, 10, 20]
print(alpha_config.default_medium_periods)  # [20, 60]
print(alpha_config.default_long_periods)    # [60, 120]

# 各类因子周期
print(alpha_config.momentum_periods)        # [5, 10, 20, 60, 120]
print(alpha_config.reversal_short_periods)  # [1, 3, 5]
print(alpha_config.reversal_long_periods)   # [20, 60]
print(alpha_config.volatility_periods)      # [5, 10, 20, 60]
print(alpha_config.volume_periods)          # [5, 10, 20]
print(alpha_config.trend_periods)           # [20, 60]

# 缓存配置
print(alpha_config.cache_max_size)          # 200
```

### 4. FeatureTransformConfig - 特征转换配置
```python
config = get_feature_config()
transform_config = config.feature_transform

print(transform_config.return_periods)         # [1, 3, 5, 10, 20]
print(transform_config.deprice_ma_periods)     # [5, 10, 20, 60, 120, 250]
print(transform_config.deprice_ema_periods)    # [12, 26, 50]
print(transform_config.deprice_atr_periods)    # [14, 28]
```

## 预定义配置

系统提供了几种预定义配置：

### 1. 默认配置 (DEFAULT_FEATURE_CONFIG)
```python
from config.features import DEFAULT_FEATURE_CONFIG, set_feature_config

# 使用默认配置（系统默认已启用）
set_feature_config(DEFAULT_FEATURE_CONFIG)
```

### 2. 快速配置 (QUICK_FEATURE_CONFIG)
减少特征数量，提高计算速度，适合快速实验：
```python
from config.features import QUICK_FEATURE_CONFIG, set_feature_config

set_feature_config(QUICK_FEATURE_CONFIG)
# MA周期: [5, 10, 20, 60]（减少了120, 250）
# 动量周期: [5, 10, 20]（减少了60, 120）
```

### 3. 完整配置 (FULL_FEATURE_CONFIG)
最大化特征数量，适合生产环境：
```python
from config.features import FULL_FEATURE_CONFIG, set_feature_config

set_feature_config(FULL_FEATURE_CONFIG)
# MA周期: [5, 10, 20, 30, 60, 90, 120, 250]（增加了30, 90）
# 动量周期: [5, 10, 20, 30, 60, 90, 120]（增加了30, 90）
```

### 4. 调试配置 (DEBUG_FEATURE_CONFIG)
启用数据泄漏检测和缓存统计：
```python
from config.features import DEBUG_FEATURE_CONFIG, set_feature_config

set_feature_config(DEBUG_FEATURE_CONFIG)
# enable_leak_detection=True
# show_cache_stats=True
```

## 使用方式

### 方式1：使用全局配置（推荐）
```python
from config.features import get_feature_config, set_feature_config, QUICK_FEATURE_CONFIG
from features.alpha_factors import AlphaFactors
from data_pipeline.feature_engineer import FeatureEngineer

# 设置全局配置
set_feature_config(QUICK_FEATURE_CONFIG)

# 使用全局配置（自动加载）
af = AlphaFactors(df)
fe = FeatureEngineer()
```

### 方式2：显式传递配置
```python
from config.features import FULL_FEATURE_CONFIG
from features.alpha_factors import AlphaFactors
from data_pipeline.feature_engineer import FeatureEngineer

# 显式传递配置
af = AlphaFactors(df, config=FULL_FEATURE_CONFIG)
fe = FeatureEngineer(config=FULL_FEATURE_CONFIG)
```

### 方式3：自定义配置
```python
from config.features import FeatureEngineerConfig, TechnicalIndicatorConfig, AlphaFactorConfig

# 创建自定义配置
custom_config = FeatureEngineerConfig(
    technical_indicators=TechnicalIndicatorConfig(
        ma_periods=[5, 20, 60],  # 只用3个周期
        ema_periods=[12, 26],
    ),
    alpha_factors=AlphaFactorConfig(
        momentum_periods=[10, 20, 60],  # 自定义动量周期
        cache_max_size=500,             # 增大缓存
    ),
    enable_leak_detection=True,  # 启用泄漏检测
)

# 使用自定义配置
from features.alpha_factors import AlphaFactors
af = AlphaFactors(df, config=custom_config)
```

## 迁移指南

### 旧代码（硬编码）
```python
# 旧的硬编码方式
from features.alpha_factors import AlphaFactors

af = AlphaFactors(df)
af.add_momentum_factors([5, 10, 20, 60, 120])  # 硬编码周期
```

### 新代码（可配置）
```python
# 新的可配置方式
from config.features import get_feature_config
from features.alpha_factors import AlphaFactors

# 方式1：使用配置中的默认值
af = AlphaFactors(df)
config = get_feature_config()
af.add_momentum_factors(config.alpha_factors.momentum_periods)

# 方式2：使用预定义配置
from config.features import set_feature_config, QUICK_FEATURE_CONFIG
set_feature_config(QUICK_FEATURE_CONFIG)
af = AlphaFactors(df)  # 自动使用快速配置
```

## 配置文件支持

未来可以添加从YAML/JSON文件加载配置：

```yaml
# feature_config.yaml
trading_days:
  annual_trading_days: 252
  epsilon: 0.00000001

technical_indicators:
  ma_periods: [5, 10, 20, 60, 120, 250]
  ema_periods: [12, 26, 50]
  rsi_periods: [6, 12, 24]

alpha_factors:
  momentum_periods: [5, 10, 20, 60, 120]
  volatility_periods: [5, 10, 20, 60]
```

```python
# 从文件加载配置（未来实现）
from config.features import load_config_from_file

config = load_config_from_file("feature_config.yaml")
af = AlphaFactors(df, config=config)
```

## 最佳实践

### 1. 开发阶段
使用快速配置，减少计算时间：
```python
from config.features import set_feature_config, QUICK_FEATURE_CONFIG
set_feature_config(QUICK_FEATURE_CONFIG)
```

### 2. 调试阶段
启用数据泄漏检测：
```python
from config.features import DEBUG_FEATURE_CONFIG, set_feature_config
set_feature_config(DEBUG_FEATURE_CONFIG)
```

### 3. 生产环境
使用完整配置，最大化特征：
```python
from config.features import FULL_FEATURE_CONFIG, set_feature_config
set_feature_config(FULL_FEATURE_CONFIG)
```

### 4. 超参数调优
创建多个配置进行网格搜索：
```python
from config.features import FeatureEngineerConfig, AlphaFactorConfig

configs = [
    FeatureEngineerConfig(
        alpha_factors=AlphaFactorConfig(momentum_periods=[5, 10, 20])
    ),
    FeatureEngineerConfig(
        alpha_factors=AlphaFactorConfig(momentum_periods=[10, 20, 60])
    ),
    FeatureEngineerConfig(
        alpha_factors=AlphaFactorConfig(momentum_periods=[5, 20, 120])
    ),
]

for config in configs:
    af = AlphaFactors(df, config=config)
    # 训练和评估...
```

## 配置优先级

配置加载优先级（从高到低）：

1. 显式传递的 `config` 参数
2. 全局设置的配置 (`set_feature_config`)
3. 默认配置 (`DEFAULT_FEATURE_CONFIG`)
4. 硬编码值（向后兼容，但不推荐）

## 查看当前配置

```python
from config import get_config_summary

print(get_config_summary())
```

输出示例：
```
======================================================================
配置系统摘要 (统一配置管理)
======================================================================

【应用配置】
  环境: development
  调试模式: True
  日志级别: INFO

【特征工程配置】
  年交易日数: 252
  MA周期: [5, 10, 20, 60, 120, 250]
  动量因子周期: [5, 10, 20, 60, 120]
  数据泄漏检测: 禁用
  缓存统计: 禁用

======================================================================
```

## 常见问题

### Q: 修改配置后需要重启程序吗？
A: 不需要。使用 `set_feature_config()` 可以动态修改配置。

### Q: 如何重置为默认配置？
A: 使用 `reset_feature_config()` 函数：
```python
from config.features import reset_feature_config
reset_feature_config()
```

### Q: 配置是线程安全的吗？
A: 全局配置不是线程安全的。如果需要多线程，请为每个线程显式传递独立的配置对象。

### Q: 旧代码不传 config 参数还能用吗？
A: 可以。系统会自动使用全局配置，保证向后兼容。

## 参考

- 配置文件位置: `core/src/config/features.py`
- 使用示例: `core/src/config/features.py` (底部的 `if __name__ == "__main__"` 部分)
- 相关文件:
  - `core/src/features/alpha_factors.py`
  - `core/src/data_pipeline/feature_engineer.py`
  - `core/src/config/__init__.py`
