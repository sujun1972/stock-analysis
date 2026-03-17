# 数据质量检查

检查和修复Tushare扩展数据的质量问题。

## 使用方法

运行以下命令检查数据质量：

```bash
# 检查所有数据类型
python -m backend.app.services.data_quality_service check-all

# 检查特定数据类型
python -m backend.app.services.data_quality_service check --type daily_basic --date 2024-03-15

# 生成质量报告
python -m backend.app.services.data_quality_service report --start 2024-03-01 --end 2024-03-15
```

## 支持的数据类型

- `daily_basic`: 每日指标（换手率、PE等）
- `moneyflow`: 资金流向
- `hk_hold`: 北向资金
- `margin_detail`: 融资融券
- `stk_limit`: 涨跌停价格
- `adj_factor`: 复权因子
- `block_trade`: 大宗交易

## 验证规则

### 每日指标 (daily_basic)
- 换手率范围：0-100%
- 市盈率范围：-1000到1000
- 市值逻辑：流通市值 ≤ 总市值
- 股本逻辑：自由流通 ≤ 流通 ≤ 总股本

### 资金流向 (moneyflow)
- 买卖平衡检查（允许5%误差）
- 净流入 = 买入总额 - 卖出总额
- 金额不能为负值

### 北向资金 (hk_hold)
- 持股数量 ≥ 0
- 持股占比：0-100%
- 交易所代码：SH或SZ

### 融资融券 (margin_detail)
- 余额不能为负
- 两融余额 = 融资余额 + 融券余额
- 融资融券比例合理性

### 涨跌停价格 (stk_limit)
- 涨停价 > 昨收价
- 跌停价 < 昨收价
- 涨跌幅度：10%或20%

## 自动修复功能

系统会自动修复以下问题：
1. 换手率超过100%（可能是单位错误）
2. 市值关系错误（交换值）
3. 净流入计算错误（重新计算）
4. 负值修正为0
5. 涨跌停价格按规则重算

## 性能优化

- 批量验证：支持一次验证多个数据集
- 并行处理：多线程加速验证
- 缓存机制：避免重复验证
- 增量验证：只验证新增数据

## 输出报告

验证完成后会生成详细报告，包括：
- 错误数量和类型
- 警告信息
- 修复记录
- 数据质量评分
- 改进建议