# 特征策略模式使用指南

## 概述

特征策略模式通过策略模式 (Strategy Pattern) 实现可组合的特征计算，使特征工程更加模块化、可维护和可扩展。

## 问题：紧耦合的特征计算

### ❌ 之前的做法

```python
# 硬编码在一个大类中
class FeatureEngineer:
    def create_all_features(self, df):
        # 技术指标
        df['MA_5'] = df['close'].rolling(5).mean()
        df['MA_20'] = df['close'].rolling(20).mean()
        df['RSI_14'] = self._calculate_rsi(df['close'], 14)
        # ... 100+ 行代码

        # Alpha因子
        df['MOMENTUM_5'] = df['close'].pct_change(5)
        df['MOMENTUM_20'] = df['close'].pct_change(20)
        # ... 更多代码

        return df
```

**问题**：
1. **紧耦合**：所有特征计算混在一起
2. **难以测试**：无法单独测试某个特征类别
3. **难以扩展**：添加新特征需要修改核心类
4. **难以组合**：无法灵活选择需要的特征

## 解决方案：策略模式

### ✅ 改进后的做法

```python
from features.feature_strategy import (
    TechnicalIndicatorStrategy,
    AlphaFactorStrategy,
    CompositeFeatureStrategy
)

# 模块化、可组合
feature_pipeline = CompositeFeatureStrategy([
    TechnicalIndicatorStrategy({'ma': [5, 20], 'rsi': [14]}),
    AlphaFactorStrategy({'momentum': [5, 20]}),
])

# 计算特征
df_with_features = feature_pipeline.compute(df)
```

## 核心概念

### 1. 策略抽象基类

```python
class FeatureStrategy(ABC):
    """特征策略抽象基类"""

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算特征"""
        pass

    @property
    @abstractmethod
    def feature_names(self) -> List[str]:
        """返回特征名称列表"""
        pass
```

### 2. 具体策略实现

- `TechnicalIndicatorStrategy`: 技术指标策略
- `AlphaFactorStrategy`: Alpha因子策略
- `PriceTransformStrategy`: 价格转换策略
- `CompositeFeatureStrategy`: 组合策略

## 使用示例

### 示例 1: 使用单个策略

```python
from features.feature_strategy import TechnicalIndicatorStrategy
import pandas as pd

# 准备数据
df = pd.DataFrame({
    'open': [100, 101, 102],
    'high': [105, 106, 107],
    'low': [99, 100, 101],
    'close': [103, 104, 105],
    'volume': [1000, 1100, 1200],
})

# 创建技术指标策略
strategy = TechnicalIndicatorStrategy(config={
    'ma': [5, 20],  # 5日和20日移动平均线
    'rsi': [14],    # 14日RSI
})

# 计算特征
df_with_features = strategy.compute(df)

# 查看生成的特征
print(strategy.feature_names)
# 输出: ['MA_5', 'MA_20', 'RSI_14']
```

### 示例 2: 组合多个策略

```python
from features.feature_strategy import (
    TechnicalIndicatorStrategy,
    AlphaFactorStrategy,
    PriceTransformStrategy,
    CompositeFeatureStrategy
)

# 创建组合策略
pipeline = CompositeFeatureStrategy([
    # 技术指标
    TechnicalIndicatorStrategy({
        'ma': [5, 10, 20],
        'rsi': [6, 14],
        'macd': [(12, 26, 9)],
    }),
    # Alpha因子
    AlphaFactorStrategy({
        'momentum': [5, 10, 20],
        'volatility': [5, 20],
    }),
    # 价格转换
    PriceTransformStrategy({
        'returns': [1, 5, 10],
        'ohlc_features': True,
    }),
])

# 一次性计算所有特征
df_with_features = pipeline.compute(df)

# 查看所有特征
print(f"Total features: {len(pipeline.feature_names)}")
print(pipeline.feature_names)
```

### 示例 3: 使用预定义流水线

```python
from features.feature_strategy import (
    create_default_feature_pipeline,
    create_minimal_feature_pipeline,
    create_custom_feature_pipeline
)

# 方式1: 默认流水线（完整特征）
pipeline = create_default_feature_pipeline()

# 方式2: 最小流水线（快速计算）
pipeline = create_minimal_feature_pipeline()

# 方式3: 自定义流水线
pipeline = create_custom_feature_pipeline(
    technical_config={'ma': [5, 20], 'rsi': [14]},
    alpha_config={'momentum': [5, 20]},
    price_config={'returns': [1, 5]}
)

# 计算特征
df_with_features = pipeline.compute(df)
```

### 示例 4: 动态选择策略

```python
def create_strategy_by_model_type(model_type: str):
    """根据模型类型选择特征策略"""

    if model_type == 'lstm':
        # LSTM需要更多时序特征
        return CompositeFeatureStrategy([
            TechnicalIndicatorStrategy({'ma': [5, 10, 20, 60]}),
            AlphaFactorStrategy({'momentum': [5, 10, 20]}),
            PriceTransformStrategy({'returns': [1, 3, 5, 10, 20]}),
        ])

    elif model_type == 'xgboost':
        # XGBoost更适合大量统计特征
        return CompositeFeatureStrategy([
            TechnicalIndicatorStrategy({
                'ma': [5, 10, 20],
                'rsi': [6, 14],
                'macd': [(12, 26, 9)],
                'kdj': [(9, 3, 3)],
            }),
            AlphaFactorStrategy({
                'momentum': [5, 10],
                'volatility': [5, 20],
                'volume': [5, 20],
            }),
        ])

    else:
        # 默认策略
        return create_default_feature_pipeline()

# 使用
strategy = create_strategy_by_model_type('xgboost')
df_with_features = strategy.compute(df)
```

## 策略详解

### TechnicalIndicatorStrategy - 技术指标策略

支持的指标：

| 指标 | 配置键 | 参数说明 | 示例 |
|------|--------|---------|------|
| 移动平均线 | `ma` | 周期列表 | `[5, 10, 20, 60]` |
| 指数移动平均 | `ema` | 周期列表 | `[12, 26]` |
| 相对强弱指标 | `rsi` | 周期列表 | `[6, 14]` |
| MACD | `macd` | (快, 慢, 信号) | `[(12, 26, 9)]` |
| KDJ | `kdj` | (N, M1, M2) | `[(9, 3, 3)]` |
| 布林带 | `boll` | (周期, 标准差倍数) | `[(20, 2)]` |
| 平均真实波幅 | `atr` | 周期列表 | `[14]` |
| 能量潮 | `obv` | 布尔值 | `True` |
| 商品通道指标 | `cci` | 周期列表 | `[14]` |

**示例**：

```python
strategy = TechnicalIndicatorStrategy({
    'ma': [5, 10, 20, 60],      # 4条移动平均线
    'ema': [12, 26],             # 2条指数移动平均线
    'rsi': [6, 14],              # 两个周期的RSI
    'macd': [(12, 26, 9)],       # MACD指标
    'kdj': [(9, 3, 3)],          # KDJ指标
    'boll': [(20, 2)],           # 布林带
    'atr': [14],                 # ATR
    'obv': True,                 # OBV
    'cci': [14],                 # CCI
})

# 生成的特征名称示例:
# MA_5, MA_10, MA_20, MA_60
# EMA_12, EMA_26
# RSI_6, RSI_14
# MACD_12_26, MACD_SIGNAL_12_26, MACD_HIST_12_26
# KDJ_K_9, KDJ_D_9, KDJ_J_9
# BOLL_UPPER_20, BOLL_MIDDLE_20, BOLL_LOWER_20
# ATR_14
# OBV
# CCI_14
```

### AlphaFactorStrategy - Alpha因子策略

支持的因子：

| 因子 | 配置键 | 参数说明 | 示例 |
|------|--------|---------|------|
| 动量 | `momentum` | 周期列表 | `[5, 10, 20]` |
| 反转 | `reversal` | 周期列表 | `[1, 3]` |
| 波动率 | `volatility` | 周期列表 | `[5, 20]` |
| 成交量 | `volume` | 周期列表 | `[5, 20]` |
| 相关性 | `correlation` | (短周期, 长周期) | `[(5, 20)]` |

**示例**：

```python
strategy = AlphaFactorStrategy({
    'momentum': [5, 10, 20],     # 动量因子
    'reversal': [1, 3],          # 反转因子
    'volatility': [5, 20],       # 波动率因子
    'volume': [5, 20],           # 成交量比率
    'correlation': [(5, 20)],    # 价格-成交量相关性
})

# 生成的特征名称示例:
# MOMENTUM_5, MOMENTUM_10, MOMENTUM_20
# REVERSAL_1, REVERSAL_3
# VOLATILITY_5, VOLATILITY_20
# VOLUME_RATIO_5, VOLUME_RATIO_20
# PRICE_VOL_CORR_5_20
```

### PriceTransformStrategy - 价格转换策略

支持的转换：

| 转换 | 配置键 | 参数说明 | 示例 |
|------|--------|---------|------|
| 收益率 | `returns` | 周期列表 | `[1, 3, 5, 10, 20]` |
| 对数收益率 | `log_returns` | 周期列表 | `[1, 5, 20]` |
| 价格位置 | `price_position` | 周期列表 | `[5, 20, 60]` |
| OHLC特征 | `ohlc_features` | 布尔值 | `True` |

**示例**：

```python
strategy = PriceTransformStrategy({
    'returns': [1, 3, 5, 10, 20],   # 多周期收益率
    'log_returns': [1, 5, 20],       # 对数收益率
    'price_position': [5, 20, 60],   # 价格在区间中的位置
    'ohlc_features': True,           # OHLC关系特征
})

# 生成的特征名称示例:
# RETURN_1D, RETURN_3D, RETURN_5D, RETURN_10D, RETURN_20D
# LOG_RETURN_1D, LOG_RETURN_5D, LOG_RETURN_20D
# PRICE_POSITION_5, PRICE_POSITION_20, PRICE_POSITION_60
# BODY_SIZE, UPPER_SHADOW, LOWER_SHADOW, INTRADAY_RANGE
```

## 扩展：创建自定义策略

### 步骤 1: 继承 FeatureStrategy

```python
from features.feature_strategy import FeatureStrategy
import pandas as pd
from typing import List

class MyCustomStrategy(FeatureStrategy):
    """自定义特征策略"""

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """实现特征计算逻辑"""
        result_df = df.copy()

        # 添加自定义特征
        result_df['MY_FEATURE_1'] = df['close'].rolling(10).mean()
        result_df['MY_FEATURE_2'] = df['volume'].rolling(5).sum()

        return result_df

    @property
    def feature_names(self) -> List[str]:
        """返回特征名称"""
        return ['MY_FEATURE_1', 'MY_FEATURE_2']
```

### 步骤 2: 使用自定义策略

```python
# 单独使用
my_strategy = MyCustomStrategy()
df_with_features = my_strategy.compute(df)

# 与其他策略组合
pipeline = CompositeFeatureStrategy([
    TechnicalIndicatorStrategy({'ma': [5, 20]}),
    MyCustomStrategy(),
])

df_with_features = pipeline.compute(df)
```

## 性能优化建议

### 1. 按需选择特征

```python
# ❌ 不好：计算所有特征（可能有100+个）
pipeline = create_default_feature_pipeline()

# ✅ 好：只计算需要的特征
pipeline = CompositeFeatureStrategy([
    TechnicalIndicatorStrategy({'ma': [5, 20]}),  # 只要2个MA
    AlphaFactorStrategy({'momentum': [20]}),      # 只要1个动量
])
```

### 2. 缓存中间结果

```python
# 缓存常用的基础特征
base_features = TechnicalIndicatorStrategy({'ma': [5, 20, 60]}).compute(df)

# 后续只添加增量特征
additional_features = AlphaFactorStrategy({'momentum': [5]}).compute(base_features)
```

### 3. 并行计算（未来扩展）

```python
# 未来可以支持并行计算多个独立策略
# pipeline.compute(df, parallel=True)
```

## 最佳实践

### 1. 配置驱动

```python
# ✅ 好：配置集中管理
FEATURE_CONFIG = {
    'technical': {
        'ma': [5, 10, 20],
        'rsi': [14],
    },
    'alpha': {
        'momentum': [5, 20],
        'volatility': [20],
    },
}

pipeline = create_custom_feature_pipeline(
    technical_config=FEATURE_CONFIG['technical'],
    alpha_config=FEATURE_CONFIG['alpha'],
)
```

### 2. 特征名称追踪

```python
# 获取生成的所有特征名称
feature_names = pipeline.feature_names
print(f"Generated {len(feature_names)} features")

# 保存特征名称列表（用于模型训练）
import json
with open('feature_names.json', 'w') as f:
    json.dump(feature_names, f)
```

### 3. 单元测试

```python
import unittest

class TestMyCustomStrategy(unittest.TestCase):
    def test_compute(self):
        strategy = MyCustomStrategy()
        df = create_test_dataframe()
        result = strategy.compute(df)

        # 验证特征生成
        self.assertIn('MY_FEATURE_1', result.columns)
        self.assertEqual(len(strategy.feature_names), 2)
```

## 对比：改进前 vs 改进后

| 维度 | 改进前 | 改进后 |
|------|--------|--------|
| **代码组织** | 单一大类，1000+ 行 | 多个小类，各200行左右 |
| **可测试性** | 难以单独测试 | 每个策略独立测试 |
| **可扩展性** | 修改核心类 | 添加新策略类 |
| **灵活性** | 全有或全无 | 按需组合 |
| **复用性** | 低 | 高 |
| **维护成本** | 高 | 低 |

## 总结

使用特征策略模式的优势：

1. **模块化** ✅: 每个策略专注于一类特征
2. **可组合** ✅: 灵活选择和组合策略
3. **可扩展** ✅: 轻松添加新策略
4. **可测试** ✅: 独立测试每个策略
5. **可维护** ✅: 代码结构清晰

从紧耦合的特征计算到灵活的策略组合，让特征工程更加优雅！
