---
name: calculate-features
description: 为指定股票计算技术指标、Alpha因子和特征转换（125+特征）
user-invocable: true
disable-model-invocation: false
---

# 特征工程技能

你是一个量化特征工程专家，负责计算股票的技术指标和 Alpha 因子。

## 任务目标

为指定股票计算完整的特征集，包括：

1. **技术指标（36个）**
   - 趋势类: MA, EMA, MACD, DMA, TRIX
   - 动量类: RSI, KDJ, CCI, WR
   - 波动类: BOLL, ATR, KELT
   - 成交量: OBV, VR, MFI, AD, ADOSC

2. **Alpha因子（51个）**
   - 动量因子: return_1d ~ return_60d
   - 波动率因子: volatility_5d ~ volatility_60d
   - 成交量因子: volume_ratio, amount_ratio
   - 价格关系: high_low_ratio, close_open_ratio

3. **特征转换（38个）**
   - 多时间尺度收益率
   - OHLC 比率特征
   - 时间特征（月份、星期）

4. **特征去价格化和目标标签**
   - 归一化处理
   - 创建预测目标（未来N日收益率）

## 使用场景

### 场景 1: 单只股票特征计算
用户提供股票代码，计算所有特征

### 场景 2: 批量股票特征计算
为多只股票并行计算特征

### 场景 3: 增量特征更新
只计算新增数据的特征

## 执行步骤

### 第一步：参数确认

根据用户需求确定以下参数：

**必需参数：**
- `stock_code`: 股票代码（如 "000001"）

**可选参数：**
- `feature_types`: 特征类型列表
  - "technical" - 仅技术指标
  - "alpha" - 仅 Alpha 因子
  - "transform" - 仅特征转换
  - "all" - 全部特征（默认）
- `prediction_horizon`: 预测周期（默认 5 天）
- `save_to_db`: 是否保存到数据库（默认 true）
- `cache_features`: 是否使用缓存（默认 true）

**示例参数组合：**

计算所有特征：
```
stock_code: "000001"
feature_types: ["all"]
```

仅计算技术指标和Alpha因子：
```
stock_code: "600519"
feature_types: ["technical", "alpha"]
prediction_horizon: 10
```

### 第二步：数据准备检查

```bash
# 检查股票数据是否存在
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    code,
    COUNT(*) as record_count,
    MIN(date) as start_date,
    MAX(date) as end_date
FROM stock_daily
WHERE code = '000001'
GROUP BY code;
"
```

**预期结果：**
- 记录数 > 100（至少需要足够的历史数据计算指标）
- 时间跨度 > 3 个月

**如果数据不足：**
提示用户先下载数据：
```
❌ 错误: 股票 000001 数据不足

建议操作:
1. 使用 /download-stock-data 技能下载数据
2. 或运行: python3 core/scripts/download_data_to_db.py --codes 000001 --years 3
```

### 第三步：执行特征计算

**方式 A: 通过 API（推荐）**

```bash
# 计算所有特征
curl -X POST http://localhost:8000/api/features/calculate/000001 \
  -H "Content-Type: application/json" \
  -d '{
    "feature_types": ["all"],
    "save_to_db": true
  }'

# 仅计算技术指标
curl -X POST http://localhost:8000/api/features/calculate/000001 \
  -H "Content-Type: application/json" \
  -d '{
    "feature_types": ["technical"],
    "save_to_db": true
  }'
```

**方式 B: 使用 Python 脚本**

创建临时脚本 `calculate_features_temp.py`：

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, 'core/src')

from database.db_manager import DatabaseManager
from data_pipeline.data_loader import DataLoader
from data_pipeline.feature_engineer import FeatureEngineer

# 初始化
db = DatabaseManager()
loader = DataLoader(db)
engineer = FeatureEngineer()

# 加载数据
stock_code = "000001"
df = loader.load_data(stock_code)

print(f"加载数据: {len(df)} 条记录")

# 计算特征
df_features = engineer.calculate_all_features(
    df,
    prediction_horizon=5
)

print(f"特征数量: {len(df_features.columns) - len(df.columns)}")
print(f"总列数: {len(df_features.columns)}")

# 保存到数据库（可选）
# db.save_features(stock_code, df_features)

print("✅ 特征计算完成")
```

运行：
```bash
cd /Volumes/MacDriver/stock-analysis
source stock_env/bin/activate
python3 calculate_features_temp.py
```

### 第四步：验证特征质量

```python
# 添加到临时脚本

# 检查特征数量
feature_cols = [col for col in df_features.columns if col not in df.columns]
print(f"\n生成的特征:")
print(f"- 技术指标: {len([c for c in feature_cols if any(ind in c for ind in ['ma_', 'ema_', 'rsi_', 'macd_', 'kdj_', 'boll_'])])}")
print(f"- Alpha因子: {len([c for c in feature_cols if any(a in c for a in ['return_', 'volatility_', 'volume_ratio'])])}")
print(f"- 特征转换: {len([c for c in feature_cols if any(t in c for t in ['log_', 'pct_', 'month', 'dayofweek'])])}")

# 检查缺失值
nan_counts = df_features[feature_cols].isna().sum()
print(f"\n缺失值统计:")
print(f"- 特征总数: {len(feature_cols)}")
print(f"- 有缺失值的特征: {(nan_counts > 0).sum()}")
print(f"- 最大缺失率: {nan_counts.max() / len(df_features) * 100:.2f}%")

# 检查异常值
print(f"\n异常值检查:")
for col in feature_cols[:5]:  # 检查前5个特征
    q1 = df_features[col].quantile(0.25)
    q3 = df_features[col].quantile(0.75)
    iqr = q3 - q1
    outliers = ((df_features[col] < q1 - 3*iqr) | (df_features[col] > q3 + 3*iqr)).sum()
    print(f"- {col}: {outliers} 个异常值 ({outliers/len(df_features)*100:.2f}%)")
```

### 第五步：保存结果

**保存到数据库：**

```python
# 保存特征数据
db.save_features(stock_code, df_features)

# 验证保存
result = db.query(f"""
    SELECT COUNT(*) as record_count
    FROM stock_features
    WHERE code = '{stock_code}'
""")
print(f"数据库中的特征记录数: {result[0]['record_count']}")
```

**保存到文件（可选）：**

```python
# 保存为 CSV
output_path = f"data/features/{stock_code}_features.csv"
df_features.to_csv(output_path)
print(f"特征已保存到: {output_path}")

# 保存特征列表
feature_list_path = f"data/features/{stock_code}_feature_list.txt"
with open(feature_list_path, 'w') as f:
    for col in feature_cols:
        f.write(f"{col}\n")
print(f"特征列表已保存到: {feature_list_path}")
```

## 输出格式

生成一份特征计算报告，包含：

### 1. 执行摘要
```
================================================================================
                          特征工程报告
================================================================================
股票代码: 000001 (平安银行)
计算时间: 2026-01-26 11:00:00
数据范围: 2021-01-26 ~ 2026-01-26 (1234 条记录)
```

### 2. 特征统计
```
特征计算结果:
✅ 技术指标: 36 个
✅ Alpha因子: 51 个
✅ 特征转换: 38 个
📊 总特征数: 125 个
🎯 目标标签: target_5d (未来5日收益率)
```

### 3. 数据质量
```
数据质量检查:
✅ 原始数据: 1234 条
✅ 特征数据: 1234 条 (无丢失)
⚠️  缺失值: 前60行（用于计算长期指标）
✅ 有效数据: 1174 条 (95.1%)
✅ 异常值: < 1%
```

### 4. 特征详情

```
主要特征类别:

【趋势指标】
- ma_5, ma_10, ma_20, ma_60  (移动平均)
- ema_12, ema_26              (指数移动平均)
- macd, macd_signal, macd_hist (MACD)

【动量指标】
- rsi_6, rsi_12, rsi_24       (相对强弱)
- kdj_k, kdj_d, kdj_j         (KDJ)
- cci_14                       (顺势指标)

【波动指标】
- boll_upper, boll_mid, boll_lower (布林带)
- atr_14                       (真实波幅)

【Alpha因子】
- return_1d ~ return_60d      (多���期收益)
- volatility_5d ~ volatility_60d (波动率)
- volume_ratio, amount_ratio   (成交量比率)

【特征转换】
- log_close, log_volume        (对数转换)
- pct_change_5d, pct_change_20d (百分比变化)
- month, dayofweek             (时间特征)
```

### 5. 存储位置
```
数据存储:
✅ 数据库: stock_features 表
✅ 文件: data/features/000001_features.csv (可选)
✅ 缓存: data/cache/features_000001_v1.pkl
```

### 6. 下一步建议
```
建议操作:
1. 数据清洗: 使用 DataCleaner 处理缺失值和异常值
2. 数据分割: 使用 DataSplitter 划分训练/测试集
3. 模型训练: 使用 /quick-backtest 或训练 LightGBM 模型
4. 特征重要性分析: 识别最有价值的特征
```

## 特征计算性能

### 时间消耗
- 1000 条数据: 2-5 秒
- 5000 条数据: 5-10 秒
- 10000 条数据: 10-20 秒

### 内存使用
- 原始数据 (6列): ~500 KB / 1000行
- 特征数据 (131列): ~10 MB / 1000行

### 优化建议
如果计算时间过长：
1. 启用特征缓存（默认已启用）
2. 减少特征类型（仅计算需要的）
3. 使用向量化操作（已优化）

## 常见问题处理

### 问题 1: 数据不足
**症状**: 报错 "数据记录数不足"

**解决方案**:
```bash
# 下载更多历史数据
python3 core/scripts/download_data_to_db.py --codes 000001 --years 5
```

### 问题 2: 特征全是 NaN
**症状**: 计算后的特征列全是缺失值

**原因**:
- 数据中价格列有问题（负值、零值）
- 数据未按时间排序

**解决方案**:
```python
# 检查数据质量
print(df[['open', 'high', 'low', 'close', 'volume']].describe())
print((df <= 0).sum())

# 重新排序
df = df.sort_index()
```

### 问题 3: 内存溢出
**症状**: MemoryError

**解决方案**:
1. 分批计算特征
2. 减少数据量（如只计算最近3年）
3. 增加系统内存

### 问题 4: TA-Lib 导入失败
**症状**: ModuleNotFoundError: No module named 'talib'

**解决方案**:
```bash
# macOS
brew install ta-lib
pip install TA-Lib

# Ubuntu
sudo apt-get install ta-lib
pip install TA-Lib

# 或使用纯 Python 实现（无需 TA-Lib）
# 项目已包含 pandas-ta 作为替代
```

## 特征工程最佳实践

### 1. 特征选择
- 避免高度相关的特征（相关系数 > 0.95）
- 使用特征重要性筛选
- 考虑业务含义，不要盲目追求数量

### 2. 特征缩放
计算特征后，使用 DataSplitter 进行标准化：
```python
from data_pipeline.data_splitter import DataSplitter

splitter = DataSplitter()
X_train_scaled, X_test_scaled = splitter.scale_features(
    X_train, X_test,
    method='robust'  # robust/standard/minmax
)
```

### 3. 特征版本管理
使用缓存系统管理特征版本：
- 特征计算方法改变时，版本号自动更新
- 缓存自动失效，重新计算

### 4. 特征监控
定期检查特征质量：
- 缺失率 < 10%
- 异常值比例 < 5%
- 特征分布稳定

## 相关文档

- [QUICKSTART.md](../../QUICKSTART.md#场景2：计算技术指标和Alpha因子) - 特征计算指南
- [core/src/data_pipeline/feature_engineer.py](../../core/src/data_pipeline/feature_engineer.py) - 源代码
- [core/tests/test_feature_engineer.py](../../core/tests/test_feature_engineer.py) - 测试用例
