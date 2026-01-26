# 交易成本配置使用指南

## 概述

`trading_rules.py` 中的 `TradingCosts` 类提供了完整的 A 股交易成本配置，消除了硬编码的魔法数字，提高了代码可维护性和可读性。

## 问题：硬编码的魔法数字

### ❌ 之前的做法

```python
# 不同文件中重复定义
COMMISSION_RATE = 0.0003  # 这是什么场景的佣金？
STAMP_TAX_RATE = 0.001    # 买卖都收吗？

# 使用时缺乏上下文
cost = amount * 0.0003  # 这个0.0003是什么？
```

**问题**：
1. 缺乏语义：数字本身不说明含义
2. 重复定义：多处硬编码，难以统一修改
3. 缺乏文档：不知道费率的适用场景
4. 维护困难：费率调整时需要修改多处

## 解决方案：配置类

### ✅ 改进后的做法

```python
from config.trading_rules import TradingCosts

# 使用配置类，语义清晰
commission = amount * TradingCosts.CommissionRates.STANDARD_RATE  # 标准万2.5
stamp_tax = amount * TradingCosts.STAMP_TAX_RATE  # 印花税0.1%，仅卖出收取
```

## 配置类结构

### 1. 印花税配置

```python
# 印花税（仅卖出时收取）
TradingCosts.STAMP_TAX_RATE = 0.001  # 0.1%
```

**说明**：
- 国家规定的印花税率，2023年8月28日起调整为0.1%
- 仅卖出时收取，买入不收

### 2. 佣金费率配置

```python
# 不同账户类型的佣金费率
TradingCosts.CommissionRates.LOW_RATE = 0.00018       # 万1.8（低佣金账户）
TradingCosts.CommissionRates.STANDARD_RATE = 0.00025  # 万2.5（标准账户）
TradingCosts.CommissionRates.HIGH_RATE = 0.0003       # 万3（高佣金账户）

# 默认使用标准费率
TradingCosts.CommissionRates.DEFAULT = TradingCosts.CommissionRates.STANDARD_RATE
```

**说明**：
- 买入和卖出都收取
- 不同券商费率可能不同
- 默认使用标准万2.5费率

### 3. 最低佣金限制

```python
TradingCosts.MIN_COMMISSION = 5.0  # 5元
```

**说明**：
- 单笔交易的最低佣金限制
- 不同券商可能不同，部分互联网券商无最低限制

### 4. 过户费配置

```python
TradingCosts.TRANSFER_FEE_RATE = 0.00002  # 万0.2
```

**说明**：
- 仅上海交易所股票收取
- 深圳交易所不收过户费
- 买入和卖出都收取

### 5. 市场特定配置

```python
# 上海交易所
TradingCosts.MarketSpecificCosts.SH_COMMISSION_RATE
TradingCosts.MarketSpecificCosts.SH_HAS_TRANSFER_FEE = True

# 深圳交易所
TradingCosts.MarketSpecificCosts.SZ_COMMISSION_RATE
TradingCosts.MarketSpecificCosts.SZ_HAS_TRANSFER_FEE = False

# 北交所
TradingCosts.MarketSpecificCosts.BSE_STAMP_TAX_RATE = 0.0005  # 0.05%双向
```

## 使用示例

### 示例 1: 计算买入成本

```python
from config.trading_rules import TradingCosts

# 买入10000元的上海股票
buy_cost = TradingCosts.calculate_buy_cost(
    amount=10000,
    stock_code='600000'  # 浦发银行（上海）
)

print(f"佣金: {buy_cost['commission']:.2f}元")
print(f"过户费: {buy_cost['transfer_fee']:.2f}元")
print(f"总成本: {buy_cost['total_cost']:.2f}元")

# 输出:
# 佣金: 5.00元（最低5元）
# 过户费: 0.20元
# 总成本: 5.20元
```

### 示例 2: 计算卖出成本

```python
from config.trading_rules import TradingCosts

# 卖出10000元的深圳股票
sell_cost = TradingCosts.calculate_sell_cost(
    amount=10000,
    stock_code='000001'  # 平安银行（深圳）
)

print(f"佣金: {sell_cost['commission']:.2f}元")
print(f"过户费: {sell_cost['transfer_fee']:.2f}元")
print(f"印花税: {sell_cost['stamp_tax']:.2f}元")
print(f"总成本: {sell_cost['total_cost']:.2f}元")

# 输出:
# 佣金: 5.00元
# 过户费: 0.00元（深圳无过户费）
# 印花税: 10.00元
# 总成本: 15.00元
```

### 示例 3: 自定义佣金费率

```python
from config.trading_rules import TradingCosts

# 使用低佣金账户（万1.8）
buy_cost = TradingCosts.calculate_buy_cost(
    amount=100000,
    stock_code='600000',
    commission_rate=TradingCosts.CommissionRates.LOW_RATE,
    min_commission=0  # 互联网券商无最低佣金
)

print(f"佣金: {buy_cost['commission']:.2f}元")
# 输出: 佣金: 18.00元（100000 * 0.00018）
```

### 示例 4: 获取总成本费率

```python
from config.trading_rules import TradingCosts

# 上海股票卖出总成本费率
sell_rate = TradingCosts.get_total_cost_rate(
    is_buy=False,
    stock_code='600000'
)

print(f"卖出总成本费率: {sell_rate * 100:.4f}%")
# 输出: 卖出总成本费率: 0.1271%
# 组成: 佣金0.025% + 过户费0.002% + 印花税0.1%
```

## 策略参数配置示例

在 ML 策略中使用配置类：

```python
from config.trading_rules import TradingCosts

class MLModelStrategy(BaseStrategy):
    @classmethod
    def get_parameters(cls) -> List[StrategyParameter]:
        return [
            StrategyParameter(
                name="commission",
                label="交易佣金率",
                type=ParameterType.FLOAT,
                default=TradingCosts.CommissionRates.STANDARD_RATE,  # 万2.5
                min_value=TradingCosts.CommissionRates.LOW_RATE,     # 万1.8
                max_value=TradingCosts.CommissionRates.HIGH_RATE,    # 万3
                step=0.00001,
                description="交易佣金费率（标准万2.5，低佣万1.8，高佣万3）",
                category="cost"
            ),
        ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        # 使用配置类的默认值
        self.commission = self.params.get(
            'commission',
            TradingCosts.CommissionRates.DEFAULT
        )
```

## 成本对比

### 不同费率下的交易成本对比

| 场景 | 交易金额 | 账户类型 | 买入成本 | 卖出成本 | 双边成本 | 成本率 |
|------|---------|---------|---------|---------|---------|--------|
| 小额交易 | 1,000元 | 标准万2.5 | 5.20元 | 15.20元 | 20.40元 | 2.04% |
| 中等交易 | 10,000元 | 标准万2.5 | 5.20元 | 15.20元 | 20.40元 | 0.204% |
| 大额交易 | 100,000元 | 标准万2.5 | 27.01元 | 127.01元 | 154.02元 | 0.154% |
| 大额交易 | 100,000元 | 低佣万1.8 | 20.01元 | 120.01元 | 140.02元 | 0.140% |

**结论**：
- 小额交易受最低佣金限制影响大，成本率高
- 大额交易成本率稳定在0.12%-0.15%之间
- 低佣金账户对大额交易优势明显

## 费率更新历史

| 日期 | 项目 | 调整前 | 调整后 | 说明 |
|------|------|--------|--------|------|
| 2023-08-28 | 印花税 | 0.2% | 0.1% | 国家降低印花税率，仅卖出收取 |
| 2022-04-29 | 过户费 | 万0.2 | 万0.2 | 无变化 |
| 近年趋势 | 佣金 | 万3-万5 | 万1.8-万2.5 | 券商竞争，费率持续下降 |

## 最佳实践

1. **使用配置类而非硬编码**
   ```python
   # ✅ 好的做法
   from config.trading_rules import TradingCosts
   commission = amount * TradingCosts.CommissionRates.DEFAULT

   # ❌ 避免硬编码
   commission = amount * 0.00025
   ```

2. **提供配置说明**
   ```python
   # ✅ 带说明的配置
   default=TradingCosts.CommissionRates.STANDARD_RATE,  # 标准万2.5
   description="交易佣金费率（标准万2.5，低佣万1.8，高佣万3）"
   ```

3. **使用辅助方法**
   ```python
   # ✅ 使用封装好的方法
   cost = TradingCosts.calculate_buy_cost(amount, stock_code)

   # ❌ 避免手动计算
   commission = max(amount * 0.00025, 5.0)
   transfer_fee = amount * 0.00002 if is_sh else 0
   ```

4. **文档化特殊情况**
   ```python
   # 北交所印花税特殊处理
   if market == 'BSE':
       stamp_tax_rate = TradingCosts.MarketSpecificCosts.BSE_STAMP_TAX_RATE
   ```

## 总结

使用 `TradingCosts` 配置类的优势：

1. **语义清晰**：每个配置都有明确的名称和注释
2. **集中管理**：所有费率配置在一个地方，便于维护
3. **类型安全**：使用类属性，IDE 提供自动补全
4. **灵活扩展**：支持自定义费率和市场特定配置
5. **文档完善**：配置即文档，降低理解成本

消除硬编码的魔法数字，让代码更易读、更易维护！
