# 技术指标模块 - 模块化设计

## 概述

本模块将技术指标按类型进行了模块化拆分，提高了代码的可维护性和可扩展性。

## 模块结构

```
indicators/
├── __init__.py           # 模块导出接口
├── base.py              # 基类和通用工具（包含 TA-Lib fallback 实现）
├── trend.py             # 趋势指标
├── momentum.py          # 动量指标
├── volatility.py        # 波动率指标
├── volume.py            # 成交量指标
└── price_pattern.py     # 价格形态指标
```

## 各模块详细说明

### 1. base.py - 基类和通用工具
- `BaseIndicator`: 所有指标计算器的基类
- `talib`: TA-Lib 库的封装，包含纯 Python fallback 实现
- `HAS_TALIB`: 标识是否安装了 TA-Lib

### 2. trend.py - 趋势指标
**类**: `TrendIndicators`

**方法**:
- `add_ma()`: 移动平均线 (MA)
- `add_ema()`: 指数移动平均线 (EMA)
- `add_bollinger_bands()`: 布林带 (BBANDS)

### 3. momentum.py - 动量指标
**类**: `MomentumIndicators`

**方法**:
- `add_rsi()`: 相对强弱指数 (RSI)
- `add_macd()`: MACD 指标
- `add_kdj()`: KDJ 随机指标
- `add_cci()`: 商品通道指标 (CCI)

### 4. volatility.py - 波动率指标
**类**: `VolatilityIndicators`

**方法**:
- `add_atr()`: 平均真实波幅 (ATR)
- `add_volatility()`: 历史波动率

### 5. volume.py - 成交量指标
**类**: `VolumeIndicators`

**方法**:
- `add_obv()`: 能量潮 (OBV)
- `add_volume_ma()`: 成交量移动平均线

### 6. price_pattern.py - 价格形态指标
**类**: `PricePatternIndicators`

**方法**:
- `add_price_patterns()`: 添加价格形态特征（涨跌幅、振幅、影线等）

## 使用方式

### 方式 1: 使用聚合类（向后兼容）

```python
from src.features.technical_indicators import TechnicalIndicators

# 创建计算器实例
ti = TechnicalIndicators(df)

# 添加各类指标
ti.add_ma([5, 10, 20])
ti.add_rsi([14])
ti.add_macd()

# 或一键添加所有指标
ti.add_all_indicators()

# 获取结果
result_df = ti.get_dataframe()
```

### 方式 2: 使用专用指标模块（推荐）

```python
from src.features.indicators import TrendIndicators, MomentumIndicators

# 只计算趋势指标
trend = TrendIndicators(df)
trend.add_ma([5, 10, 20])
trend.add_ema([12, 26])
df_with_trend = trend.get_dataframe()

# 只计算动量指标
momentum = MomentumIndicators(df)
momentum.add_rsi([6, 12, 24])
momentum.add_macd()
df_with_momentum = momentum.get_dataframe()
```

### 方式 3: 链式调用

```python
from src.features.indicators import TrendIndicators

result = (TrendIndicators(df)
    .add_ma([5, 10, 20])
    .add_ema([12, 26])
    .add_bollinger_bands()
    .get_dataframe())
```

## 优势

1. **模块化设计**: 每个文件职责单一，易于维护和测试
2. **向后兼容**: 保留原有的 `TechnicalIndicators` 类和导入方式，不影响现有代码
3. **按需导入**: 可以只导入需要的指标类型，减少内存占用
4. **易于扩展**: 新增指标时只需修改对应类别的文件
5. **代码复用**: 各模块共享基类和通用工具

## 迁移指南

### 现有代码无需修改
所有使用 `TechnicalIndicators` 的代码都可以继续正常工作：

```python
# ✓ 这些导入方式都能正常工作
from src.features.technical_indicators import TechnicalIndicators
from src.features import TechnicalIndicators
```

### 新代码推荐使用模块化导入

对于新代码，推荐使用更细粒度的导入：

```python
# 推荐：按需导入
from src.features.indicators import TrendIndicators, MomentumIndicators

# 或者导入全部
from src.features.indicators import (
    TrendIndicators,
    MomentumIndicators,
    VolatilityIndicators,
    VolumeIndicators,
    PricePatternIndicators
)
```

## Backend 项目兼容性

已验证以下 backend 项目中的导入方式均正常工作：

- `backend/app/services/feature_service.py`: ✓
- `backend/app/strategies/complex_indicator_strategy.py`: ✓

## 测试

运行以下命令测试模块：

```bash
# 测试导入
python -c "from src.features.technical_indicators import TechnicalIndicators; print('OK')"

# 测试模块化导入
python -c "from src.features.indicators import TrendIndicators; print('OK')"

# 运行完整测试
python src/features/technical_indicators.py
```
