# 数据质量检查模块使用指南

## 概述

数据质量检查模块提供了完整的股票数据验证、清洗和处理功能，包括：

1. **异常值检测器** (OutlierDetector) - 检测和处理价格异常
2. **停牌过滤器** (SuspendFilter) - 识别和过滤停牌股票
3. **数据验证器** (DataValidator) - 全面验证数据质量
4. **缺失值处理器** (MissingHandler) - 智能处理缺失值

---

## 1. 异常值检测器 (OutlierDetector)

### 功能

- IQR方法检测异常值
- Z-score方法检测异常值
- 单日暴涨暴跌检测
- 成交量异常检测
- 异常值处理（移除/截断/插值）

### 快速开始

```python
from data import OutlierDetector, clean_outliers

# 方法1：使用类
detector = OutlierDetector(df)
outliers_df = detector.detect_all_outliers()
df_cleaned = detector.handle_outliers(outliers_df['is_outlier'], method='interpolate')

# 方法2：使用便捷函数
df_cleaned = clean_outliers(df, method='interpolate', threshold=3.0)
```

### 详细用法

#### 1.1 创建检测器

```python
from data import OutlierDetector

detector = OutlierDetector(
    df,                         # DataFrame（包含OHLCV数据）
    price_cols=['close'],       # 要检测的价格列
    volume_col='volume'         # 成交量列（自动检测）
)
```

#### 1.2 检测异常值

**IQR方法（推荐用于价格数据）**

```python
# 检测close列的异常值
outliers = detector.detect_by_iqr(
    'close',
    multiplier=3.0,      # IQR倍数（3.0较宽松，1.5较严格）
    use_returns=True     # 检测收益率异常（推荐）
)

# outliers: 布尔Series，True表示异常
```

**Z-score方法**

```python
# 标准Z-score
outliers = detector.detect_by_zscore(
    'close',
    threshold=3.0,       # Z-score阈值
    use_modified=False   # 使用标准Z-score
)

# 修正Z-score（基于中位数，更鲁棒）
outliers = detector.detect_by_zscore(
    'close',
    threshold=3.0,
    use_modified=True    # 使用修正Z-score (MAD)
)
```

**价格跳空检测**

```python
# 检测单日涨跌幅>20%
jumps = detector.detect_price_jumps(threshold=0.20)
```

**成交量异常检测**

```python
# 检测成交量异常
anomalies = detector.detect_volume_anomalies(
    method='zscore',     # 'zscore' 或 'iqr'
    threshold=3.0
)
```

**综合检测**

```python
# 一键检测所有类型的异常
outliers_df = detector.detect_all_outliers(
    price_method='both',         # 'iqr', 'zscore', 'both'
    price_threshold=3.0,
    jump_threshold=0.20,
    volume_method='zscore',
    volume_threshold=3.0
)

# outliers_df包含：
# - close_outlier_iqr: IQR检测结果
# - close_outlier_zscore: Z-score检测结果
# - price_jump: 价格跳空
# - volume_outlier: 成交量异常
# - is_outlier: 综合异常标记
```

#### 1.3 获取统计摘要

```python
summary = detector.get_outlier_summary(outliers_df)

print(summary)
# {
#     'total_records': 100,
#     'total_outliers': 5,
#     'outlier_percentage': 5.0,
#     'by_type': {
#         'price_jump': {'count': 2, 'percentage': 2.0},
#         'close_outlier_iqr': {'count': 3, 'percentage': 3.0}
#     },
#     'outlier_dates': [...]
# }
```

#### 1.4 处理异常值

**移除异常值（设为NaN）**

```python
df_cleaned = detector.remove_outliers(outliers_df['is_outlier'])
```

**缩尾处理（Winsorization）**

```python
df_cleaned = detector.winsorize_outliers(
    outliers_df['is_outlier'],
    lower_percentile=0.01,    # 下边界1%
    upper_percentile=0.99     # 上边界99%
)
```

**插值处理（推荐）**

```python
df_cleaned = detector.interpolate_outliers(
    outliers_df['is_outlier'],
    method='linear'    # 'linear', 'time', 'spline'
)
```

**统一接口**

```python
df_cleaned = detector.handle_outliers(
    outliers_df['is_outlier'],
    method='interpolate',    # 'remove', 'winsorize', 'interpolate'
    columns=['close']        # 指定要处理的列
)
```

### 使用建议

1. **检测方法选择**：
   - 价格数据：使用IQR方法检测收益率异常（`use_returns=True`）
   - 成交量数据：使用修正Z-score（`use_modified=True`）

2. **阈值设置**：
   - 宽松检测：multiplier=3.0, threshold=3.0
   - 严格检测：multiplier=1.5, threshold=2.0

3. **处理方法选择**：
   - 插值法：适合中间缺失，保持数据连续性
   - 缩尾法：适合保留数据分布特征
   - 移除法：适合严重异常，需后续填充

---

## 2. 停牌过滤器 (SuspendFilter)

### 功能

- 检测成交量为0的停牌
- 检测价格连续不变的停牌
- 检测涨跌停板
- 识别停牌期间
- 过滤停牌数据

### 快速开始

```python
from data import SuspendFilter, filter_suspended_data

# 方法1：使用类（单股票）
filter_obj = SuspendFilter(df)
suspended_df = filter_obj.detect_all_suspended()
df_filtered = filter_obj.filter_suspended(suspended_df['is_suspended'])

# 方法2：使用便捷函数
df_filtered = filter_suspended_data(df, volume_threshold=100, consecutive_days=3)

# 方法3：多股票模式
filter_obj = SuspendFilter(prices=prices_df, volumes=volumes_df)
suspended_dict = filter_obj.detect_all_suspended()
```

### 详细用法

#### 2.1 单股票模式

```python
from data import SuspendFilter

# 初始化
filter_obj = SuspendFilter(
    df,                      # DataFrame（包含close和volume）
    price_col='close',       # 价格列名
    volume_col='volume'      # 成交量列名（自动检测）
)
```

#### 2.2 多股票模式

```python
# 面板数据（index=日期, columns=股票代码）
filter_obj = SuspendFilter(
    prices=prices_df,        # 价格DataFrame
    volumes=volumes_df       # 成交量DataFrame
)
```

#### 2.3 检测停牌

**零成交量检测**

```python
zero_vol = filter_obj.detect_zero_volume(threshold=100)
# threshold: 成交量阈值（单位：股）
```

**价格不变检测**

```python
unchanged = filter_obj.detect_price_unchanged(
    consecutive_days=3,      # 连续N天价格不变
    tolerance=1e-6           # 价格变化容忍度
)
```

**涨跌停检测**

```python
limit_dict = filter_obj.detect_limit_move(limit_threshold=0.095)

# limit_dict包含：
# - 'upper_limit': 涨停标记
# - 'lower_limit': 跌停标记
# - 'any_limit': 任意涨跌停
```

**综合检测**

```python
suspended_df = filter_obj.detect_all_suspended(
    volume_threshold=100,      # 成交量阈值
    consecutive_days=3,        # 价格不变天数
    detect_limit=True          # 是否检测涨跌停
)

# suspended_df包含：
# - 'zero_volume': 零成交量标记
# - 'price_unchanged': 价格不变标记
# - 'is_suspended': 综合停牌标记
```

#### 2.4 停牌期间分析

```python
# 获取停牌期间列表
periods = filter_obj.get_suspension_periods(
    suspended_df['is_suspended'],
    min_duration=3           # 最小停牌天数
)

# periods: [(开始日期, 结束日期, 天数), ...]
for start, end, days in periods:
    print(f"{start} 至 {end}, 共 {days} 天")
```

**停牌统计摘要**

```python
summary = filter_obj.get_suspension_summary(suspended_df)

print(summary)
# {
#     'total_days': 100,
#     'suspended_days': 10,
#     'suspension_rate': 10.0,
#     'by_type': {...},
#     'suspension_periods': 2,
#     'longest_suspension': (date1, date2, 5)
# }
```

#### 2.5 过滤停牌数据

**设为NaN**

```python
df_filtered = filter_obj.filter_suspended(
    suspended_df['is_suspended'],
    fill_value=np.nan
)
```

**完全移除停牌行（单股票）**

```python
df_filtered = filter_obj.remove_suspended_rows(suspended_df['is_suspended'])
```

### 使用建议

1. **检测阈值**：
   - 成交量阈值：100股（可根据市场调整）
   - 连续天数：3天（A股常见停牌模式）

2. **多股票场景**：
   - 使用面板数据模式（prices+volumes DataFrame）
   - 一次性处理多只股票，提高效率

3. **回测应用**：
   - 在选股时排除当前停牌股票
   - 避免买入即将停牌的股票

---

## 3. 数据验证器 (DataValidator)

### 功能

- 验证必需字段完整性
- 验证数据类型正确性
- 验证价格逻辑关系（high ≥ close ≥ low）
- 验证时间序列连续性
- 验证数值范围合理性
- 验证缺失值比例

### 快速开始

```python
from data import DataValidator, validate_stock_data, print_validation_report

# 方法1：使用类
validator = DataValidator(df)
results = validator.validate_all()
print(validator.get_validation_report())

# 方法2：使用便捷函数
results = validate_stock_data(df, strict_mode=False)

# 方法3：直接打印报告
print_validation_report(df)
```

### 详细用法

#### 3.1 初始化

```python
from data import DataValidator

validator = DataValidator(
    df,
    required_fields=['close'],    # 必需字段列表
    date_column=None              # 日期列名（None则使用索引）
)
```

#### 3.2 单项验证

**必需字段验证**

```python
passed = validator.validate_required_fields()
# 检查 required_fields 是否都存在
```

**数据类型验证**

```python
passed = validator.validate_data_types()
# 检查价格列和成交量列是否为数值类型
```

**价格逻辑验证**

```python
passed, error_stats = validator.validate_price_logic()

print(error_stats)
# {
#     'high_less_than_low': 2,
#     'close_out_of_range': 1,
#     'open_out_of_range': 0,
#     'negative_price': 0
# }
```

**日期连续性验证**

```python
passed, gaps = validator.validate_date_continuity(
    allow_gaps=True,         # 是否允许日期间隔
    max_gap_days=10          # 最大允许间隔天数
)

# gaps: [(开始日期, 结束日期, 间隔天数), ...]
```

**数值范围验证**

```python
passed, range_errors = validator.validate_value_ranges(
    price_min=0.01,          # 最小价格
    price_max=10000.0,       # 最大价格
    volume_min=0,            # 最小成交量
    volume_max=1e12          # 最大成交量
)
```

**缺失值验证**

```python
passed, missing_stats = validator.validate_missing_values(
    max_missing_rate=0.5     # 最大允许缺失率（50%）
)

print(missing_stats)
# {
#     'close': {'count': 5, 'rate': 0.05},
#     'volume': {'count': 0, 'rate': 0.0}
# }
```

**重复记录验证**

```python
passed, dup_count = validator.validate_duplicates()
```

#### 3.3 全面验证

```python
results = validator.validate_all(
    strict_mode=False,           # 严格模式（警告也算失败）
    allow_date_gaps=True,        # 是否允许日期间隔
    max_missing_rate=0.5         # 最大允许缺失率
)

print(results)
# {
#     'passed': True/False,
#     'errors': [...],
#     'warnings': [...],
#     'stats': {...},
#     'summary': {
#         'total_records': 100,
#         'total_columns': 5,
#         'error_count': 0,
#         'warning_count': 2
#     }
# }
```

#### 3.4 生成验证报告

```python
report = validator.get_validation_report()
print(report)

# ============================================================
# 数据验证报告
# ============================================================
#
# 总记录数: 100
# 总列数: 5
# 验证结果: ✓ 通过
# 错误数: 0
# 警告数: 2
#
# 警告列表:
#   1. 发现 2 条记录的close不在[low, high]范围内
#   2. close 缺失率 5.00% 超过阈值 0.00%
# ...
```

### 使用建议

1. **入库前验证**：
   - 在数据写入数据库前进行全面验证
   - 使用严格模式（`strict_mode=True`）

2. **定期监控**：
   - 定期对历史数据进行验证
   - 识别数据质量问题

3. **自定义验证**：
   - 根据业务需求调整验证规则
   - 设置合理的阈值

---

## 4. 缺失值处理器 (MissingHandler)

### 功能

- 缺失值检测和统计
- 前向填充/后向填充
- 线性插值/时间加权插值
- 移动平均填充
- 智能填充（根据位置选择策略）

### 快速开始

```python
from data import MissingHandler, fill_missing, analyze_missing

# 方法1：使用类
handler = MissingHandler(df)
df_filled = handler.smart_fill()

# 方法2：使用便捷函数
df_filled = fill_missing(df, method='interpolate')

# 方法3：分析缺失
analysis = analyze_missing(df)
```

### 详细用法

#### 4.1 初始化

```python
from data import MissingHandler

handler = MissingHandler(df)
```

#### 4.2 检测缺失值

```python
stats = handler.detect_missing()

print(stats)
# {
#     'total_missing': 10,
#     'missing_rate': 5.0,
#     'rows_with_missing': 8,
#     'columns_with_missing': 1,
#     'column_stats': {
#         'close': {
#             'count': 10,
#             'rate': 10.0,
#             'first_missing_index': ...,
#             'last_missing_index': ...
#         }
#     }
# }
```

**分析缺失模式**

```python
patterns = handler.get_missing_patterns()

print(patterns)
# {
#     'consecutive_missing': {
#         'close': [(start_date, end_date, length), ...]
#     },
#     'leading_missing': {'close': 3},      # 前导缺失3天
#     'trailing_missing': {'close': 5}      # 尾部缺失5天
# }
```

#### 4.3 填充方法

**前向填充（Forward Fill）**

```python
df_filled = handler.fill_forward(
    columns=['close'],       # 要填充的列
    limit=5                  # 最大连续填充数量
)
```

**后向填充（Backward Fill）**

```python
df_filled = handler.fill_backward(
    columns=['close'],
    limit=5
)
```

**插值填充（Interpolate）**

```python
df_filled = handler.interpolate(
    method='linear',         # 'linear', 'time', 'spline', 'polynomial'
    columns=['close'],
    order=2,                 # 样条/多项式阶数
    limit=10                 # 最大连续插值数量
)
```

**均值填充**

```python
# 全局均值
df_filled = handler.fill_with_mean(columns=['close'])

# 滚动窗口均值
df_filled = handler.fill_with_mean(
    columns=['close'],
    window=10                # 滚动窗口大小
)
```

**指定值填充**

```python
# 标量值
df_filled = handler.fill_with_value(value=100.0)

# 字典（不同列不同值）
df_filled = handler.fill_with_value(
    value={'close': 100.0, 'volume': 5000000.0}
)
```

**删除缺失行**

```python
df_dropped = handler.drop_missing(
    how='any',               # 'any' 或 'all'
    subset=['close'],        # 只考虑这些列
    threshold=None           # 非缺失值数量阈值
)
```

#### 4.4 智能填充（推荐）

```python
df_filled = handler.smart_fill(
    columns=['close'],
    leading_method='bfill',         # 前导缺失：后向填充
    trailing_method='ffill',        # 尾部缺失：前向填充
    middle_method='interpolate',    # 中间缺失：插值
    max_gap=5                       # 最大允许间隔
)
```

**智能填充策略**：
- 前导缺失（数据开头）：用后向填充或删除
- 尾部缺失（数据末尾）：用前向填充或删除
- 中间缺失（数据中间）：用插值或前向填充
- 大间隔（>max_gap）：保留为NaN

#### 4.5 统一接口

```python
df_filled = handler.handle_missing(
    method='smart',          # 'ffill', 'bfill', 'interpolate', 'mean', 'drop', 'smart'
    columns=['close'],
    **kwargs                 # 传递给具体方法的参数
)
```

#### 4.6 填充报告

```python
df_filled = handler.smart_fill()
report = handler.get_fill_report(df_filled)

print(report)
# {
#     'original_shape': (100, 2),
#     'filled_shape': (100, 2),
#     'original_missing': 10,
#     'remaining_missing': 2,
#     'filled_count': 8,
#     'fill_rate': 80.0,
#     'by_column': {...}
# }
```

### 使用建议

1. **方法选择**：
   - **智能填充（smart）**：推荐，自动根据位置选择最佳方法
   - **插值（interpolate）**：适合中间缺失，保持趋势
   - **前向填充（ffill）**：适合时间序列，假设值不变
   - **均值填充（mean）**：适合随机缺失

2. **间隔控制**：
   - 设置 `max_gap` 限制填充的最大间隔
   - 避免对大间隔进行插值（可能不准确）

3. **验证填充结果**：
   - 检查 `fill_report` 确认填充率
   - 对关键数据点进行人工检查

---

## 5. 完整的数据清洗流程

### 推荐流程

```python
from data import (
    DataValidator,
    OutlierDetector,
    SuspendFilter,
    MissingHandler
)

# 步骤1：数据验证
validator = DataValidator(df)
results = validator.validate_all(strict_mode=False)

if not results['passed']:
    print("数据验证失败，开始清洗...")

# 步骤2：异常值处理
detector = OutlierDetector(df)
outliers_df = detector.detect_all_outliers()
df = detector.handle_outliers(outliers_df['is_outlier'], method='interpolate')

# 步骤3：停牌过滤
filter_obj = SuspendFilter(df)
suspended_df = filter_obj.detect_all_suspended()
df = filter_obj.filter_suspended(suspended_df['is_suspended'])

# 步骤4：缺失值填充
handler = MissingHandler(df)
df = handler.smart_fill()

# 步骤5：最终验证
validator_final = DataValidator(df)
final_results = validator_final.validate_all()

if final_results['passed']:
    print("✓ 数据清洗完成，质量验证通过!")
else:
    print("✗ 数据清洗后仍有问题，请检查...")
```

### 便捷函数版本

```python
from data import clean_outliers, filter_suspended_data, fill_missing, validate_stock_data

# 一行代码完成每个步骤
df = clean_outliers(df, method='interpolate', threshold=3.0)
df = filter_suspended_data(df, volume_threshold=100, consecutive_days=3)
df = fill_missing(df, method='smart')

# 验证
results = validate_stock_data(df, strict_mode=False)
```

---

## 6. 最佳实践

### 6.1 数据入库前检查

```python
# 入库前必须验证
validator = DataValidator(df, required_fields=['close', 'volume'])
results = validator.validate_all(strict_mode=True)

if not results['passed']:
    raise ValueError(f"数据验证失败: {results['errors']}")

# 入库
save_to_database(df)
```

### 6.2 回测数据准备

```python
# 1. 过滤停牌股票（避免买入无法成交）
df = filter_suspended_data(df)

# 2. 处理异常值（避免虚假信号）
df = clean_outliers(df, method='interpolate')

# 3. 填充缺失值（确保特征计算不中断）
df = fill_missing(df, method='smart')
```

### 6.3 生产环境监控

```python
import schedule

def daily_quality_check():
    """每日数据质量检查"""
    df = load_latest_data()

    # 验证数据质量
    validator = DataValidator(df)
    results = validator.validate_all()

    if not results['passed']:
        # 发送告警
        send_alert(f"数据质量问题: {results['errors']}")

    # 生成报告
    report = validator.get_validation_report()
    save_report(report)

# 每天执行
schedule.every().day.at("09:00").do(daily_quality_check)
```

### 6.4 参数调优建议

**异常值检测**：
- 高频数据（日内）：threshold=2.0（更严格）
- 日线数据：threshold=3.0（标准）
- 周线/月线数据：threshold=5.0（更宽松）

**停牌检测**：
- A股：consecutive_days=3, volume_threshold=100
- 港股：consecutive_days=5, volume_threshold=1000
- 美股：consecutive_days=1, volume_threshold=100

**缺失值填充**：
- 价格数据：优先使用插值（interpolate）
- 成交量数据：优先使用前向填充（ffill）
- 技术指标：可使用均值填充（mean）

---

## 7. 常见问题 (FAQ)

**Q1: 异常值处理会不会影响收益率计算？**

A: 使用插值法可以最小化影响。如果担心，可以：
- 先计算收益率再检测异常
- 使用更宽松的阈值（如threshold=5.0）
- 仅标记异常但不删除，供后续分析

**Q2: 停牌股票应该删除还是填充为NaN？**

A: 取决于应用场景：
- 回测：填充为NaN，避免买入停牌股
- 数据分析：删除，避免影响统计
- 特征工程：填充为NaN，后续用智能填充处理

**Q3: 如何处理新股上市前的缺失数据？**

A: 使用智能填充：
```python
handler = MissingHandler(df)
df = handler.smart_fill(leading_method='drop')  # 删除前导缺失
```

**Q4: 大量缺失值（>50%）应该如何处理？**

A: 建议：
1. 检查数据源是否有问题
2. 如果是合理缺失（如新股），考虑删除该列或该股票
3. 如果必须保留，使用均值填充或模型预测

**Q5: 如何批量处理多只股票？**

A: 使用多股票模式：
```python
# 假设有多个股票的面板数据
prices_df = pd.DataFrame(...)  # columns = ['000001', '000002', ...]
volumes_df = pd.DataFrame(...)

# 停牌过滤（面板模式）
filter_obj = SuspendFilter(prices=prices_df, volumes=volumes_df)
suspended_dict = filter_obj.detect_all_suspended()

# 其他处理可以循环处理每只股票
for stock_code in prices_df.columns:
    df_stock = pd.DataFrame({
        'close': prices_df[stock_code],
        'volume': volumes_df[stock_code]
    })
    df_stock = clean_outliers(df_stock)
    df_stock = fill_missing(df_stock)
    # ...
```

---

## 8. 性能优化建议

1. **批量处理**：对多只股票使用向量化操作
2. **缓存结果**：重复检测时使用缓存
3. **并行计算**：使用multiprocessing处理独立股票
4. **采样检测**：对大数据集先采样检测再全量处理

---

## 9. 参考资料

- 示例代码：`examples/data_quality_demo.py`
- 单元测试：`tests/unit/data/test_*.py`
- 路线图：`DEVELOPMENT_ROADMAP.md`

---

**最后更新**: 2026-01-30
**文档版本**: v1.0
**作者**: AI Assistant
