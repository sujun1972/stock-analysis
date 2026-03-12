# Data Sanitization - 数据清理与序列化

**作用**: 处理数据库特殊值，确保数据能够正确序列化为 JSON
**适用范围**: 所有涉及数据库查询和 API 响应的代码

---

## 📋 概述

PostgreSQL 的 `numeric` 类型支持存储特殊浮点数值（NaN、Infinity、-Infinity），但这些值**不符合 JSON 标准**，会导致 FastAPI 序列化失败：

```
ValueError: Out of range float values are not JSON compliant
```

本文档介绍如何在 Backend 项目中正确处理这些特殊值。

---

## 🎯 问题场景

### 典型错误

```python
# 数据库中存在 NaN 值
# dragon_tiger_list 表: turnover_rate = NaN

@router.get("/dragon-tiger")
async def get_dragon_tiger_list():
    # 查询数据
    data = await service.get_dragon_tiger_list()

    # ❌ 序列化失败！
    return {
        "code": 200,
        "data": data  # 包含 Decimal('NaN')
    }

# 错误: ValueError: Out of range float values are not JSON compliant
```

### 何时会遇到

1. **龙虎榜数据**: 新股、可转债可能缺少换手率数据（NaN）
2. **财务数据**: 某些指标计算结果可能为无穷大
3. **技术指标**: 除零操作导致 Infinity
4. **统计数据**: 平均值计算时数据不足导致 NaN

---

## ✅ 解决方案

### 1. 数据清理方法

在 `MarketSentimentService` 中已实现数据清理方法：

```python
# backend/app/services/sentiment_service.py

from decimal import Decimal
import math

@staticmethod
def _sanitize_float_value(value):
    """
    清理特殊浮点数值，使其符合 JSON 标准

    PostgreSQL 的 numeric 类型支持存储 NaN 和 Infinity，
    但这些值不符合 JSON 标准，会导致序列化失败。
    此方法将特殊浮点数转换为 None (JSON 中的 null)。
    """
    # 处理 Decimal 类型（PostgreSQL numeric 类型）
    if isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            return None
        return value

    # 处理 float 类型
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    return value

@staticmethod
def _sanitize_dict(data: Dict) -> Dict:
    """
    递归清理字典中的特殊浮点数值
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = MarketSentimentService._sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                MarketSentimentService._sanitize_dict(item) if isinstance(item, dict)
                else MarketSentimentService._sanitize_float_value(item)
                for item in value
            ]
        else:
            sanitized[key] = MarketSentimentService._sanitize_float_value(value)
    return sanitized
```

### 2. 使用示例

在所有返回数据库查询结果的方法中应用清理：

```python
async def get_dragon_tiger_list(self, date: str, ...):
    """查询龙虎榜数据"""
    # 查询数据库
    rows = cursor.fetchall()

    items = []
    for row in rows:
        item = dict(zip(col_names, row))

        # 处理日期格式
        if 'trade_date' in item:
            item['trade_date'] = item['trade_date'].strftime('%Y-%m-%d')

        # ✅ 清理特殊浮点数值（NaN, Infinity）
        item = self._sanitize_dict(item)
        items.append(item)

    return {
        "items": items,
        "total": total
    }
```

### 3. 效果对比

**清理前**:
```json
{
  "stock_code": "113700",
  "stock_name": "N海天转",
  "turnover_rate": NaN  // ❌ 导致序列化失败
}
```

**清理后**:
```json
{
  "stock_code": "113700",
  "stock_name": "N海天转",
  "turnover_rate": null  // ✅ 正确序列化
}
```

---

## 🚀 最佳实践

### ✅ 推荐做法

1. **在 Service 层清理数据**
   ```python
   # ✅ 在返回前清理
   result = self._sanitize_dict(data)
   return result
   ```

2. **对所有数据库查询结果应用清理**
   ```python
   async def get_sentiment_report(self, date: str):
       # 查询数据
       market_data = await self._query_market_data(date)
       limit_up_data = await self._query_limit_up(date)

       result = {
           "market_data": market_data,
           "limit_up_data": limit_up_data
       }

       # ✅ 清理特殊浮点数值
       return self._sanitize_dict(result)
   ```

3. **处理嵌套结构**
   ```python
   # _sanitize_dict 会递归处理嵌套的字典和列表
   data = {
       "items": [
           {"value": Decimal('NaN')},
           {"nested": {"score": float('inf')}}
       ]
   }

   clean_data = self._sanitize_dict(data)
   # ✅ 所有 NaN/Infinity 都被转换为 None
   ```

4. **记录数据质量问题**
   ```python
   # 可选：统计 NaN 值的数量
   nan_count = sum(
       1 for item in items
       if item.get('turnover_rate') is None
   )

   if nan_count > 0:
       logger.warning(f"发现 {nan_count} 条记录的换手率为 NaN")
   ```

### ❌ 避免做法

1. **不要在数据库层面过滤 NaN**
   ```sql
   -- ❌ 会丢失数据
   SELECT * FROM table
   WHERE turnover_rate IS NOT NULL
     AND turnover_rate != 'NaN'
   ```

2. **不要忽略序列化错误**
   ```python
   # ❌ 不要用 try-except 掩盖问题
   try:
       return {"data": data_with_nan}
   except ValueError:
       return {"data": None}  # 丢失了所有数据
   ```

3. **不要手动替换每个字段**
   ```python
   # ❌ 难以维护
   if math.isnan(item['field1']):
       item['field1'] = None
   if math.isnan(item['field2']):
       item['field2'] = None
   # ... 重复代码
   ```

---

## 🔧 数据源修复

### 预防 NaN 值写入数据库

如果可能，在数据采集时就处理 NaN：

```python
# 数据采集时
def fetch_dragon_tiger_data(stock_code: str):
    """获取龙虎榜数据"""
    data = external_api.get_data(stock_code)

    # ✅ 在写入数据库前清理
    if pd.isna(data['turnover_rate']):
        data['turnover_rate'] = None  # 存储为 NULL 而不是 NaN

    return data
```

### 清理现有数据

```sql
-- 将 NaN 更新为 NULL
UPDATE dragon_tiger_list
SET turnover_rate = NULL
WHERE turnover_rate = 'NaN';

UPDATE dragon_tiger_list
SET price_change = NULL
WHERE price_change = 'Infinity' OR price_change = '-Infinity';
```

---

## 📊 应用场景

### 场景 1: 龙虎榜查询

```python
# backend/app/services/sentiment_service.py

async def get_dragon_tiger_list(self, date, page, limit):
    """查询龙虎榜数据（支持 NaN 值）"""
    rows = cursor.fetchall()

    items = []
    for row in rows:
        item = dict(zip(col_names, row))

        # 清理特殊浮点数值
        item = self._sanitize_dict(item)
        items.append(item)

    return {
        "items": items,
        "total": total
    }
```

### 场景 2: 涨停板详情

```python
async def get_limit_up_detail(self, date: str):
    """获取涨停板详细数据"""
    data = self._row_to_dict(row, cursor.description)

    # 解析 JSONB 字段
    if 'continuous_ladder' in data:
        data['continuous_ladder'] = json.loads(data['continuous_ladder'])

    # 清理特殊浮点数值
    return self._sanitize_dict(data)
```

### 场景 3: 统计分析

```python
async def get_sentiment_statistics(self, start_date, end_date):
    """统计分析（处理平均值可能为 NaN）"""
    stats = {
        "avg_blast_rate": float(row[0]) if row[0] else 0,
        "avg_limit_up": float(row[1]) if row[1] else 0
    }

    # 清理特殊浮点数值（平均值可能为 NaN）
    return self._sanitize_dict(stats)
```

---

## 🎯 检查清单

在编写涉及数据库查询的代码时，确保：

- [ ] 导入了 `Decimal` 和 `math` 模块
- [ ] 实现了 `_sanitize_float_value` 方法
- [ ] 实现了 `_sanitize_dict` 方法
- [ ] 在返回数据前应用 `_sanitize_dict`
- [ ] 处理了嵌套结构（字典、列表）
- [ ] 记录了数据质量问题（可选）
- [ ] 测试了包含 NaN 值的数据

---

## 🧪 测试示例

```python
# tests/unit/services/test_data_sanitization.py

import math
from decimal import Decimal
from app.services.sentiment_service import MarketSentimentService

def test_sanitize_decimal_nan():
    """测试 Decimal NaN 清理"""
    value = Decimal('NaN')
    result = MarketSentimentService._sanitize_float_value(value)
    assert result is None

def test_sanitize_decimal_infinity():
    """测试 Decimal Infinity 清理"""
    value = Decimal('Infinity')
    result = MarketSentimentService._sanitize_float_value(value)
    assert result is None

def test_sanitize_float_nan():
    """测试 float NaN 清理"""
    value = float('nan')
    result = MarketSentimentService._sanitize_float_value(value)
    assert result is None

def test_sanitize_dict_nested():
    """测试嵌套字典清理"""
    data = {
        "stock_code": "113700",
        "turnover_rate": Decimal('NaN'),
        "nested": {
            "score": float('inf')
        },
        "items": [
            {"value": Decimal('NaN')},
            {"value": 1.23}
        ]
    }

    result = MarketSentimentService._sanitize_dict(data)

    assert result["stock_code"] == "113700"
    assert result["turnover_rate"] is None
    assert result["nested"]["score"] is None
    assert result["items"][0]["value"] is None
    assert result["items"][1]["value"] == 1.23
```

---

## 📚 相关资源

### Python 文档
- [decimal — Decimal fixed point and floating point arithmetic](https://docs.python.org/3/library/decimal.html)
- [math — Mathematical functions](https://docs.python.org/3/library/math.html)
- [JSON encoder and decoder](https://docs.python.org/3/library/json.html)

### PostgreSQL 文档
- [Numeric Types - NaN](https://www.postgresql.org/docs/current/datatype-numeric.html#DATATYPE-NUMERIC-DECIMAL)

### 项目文件
- 实现: [backend/app/services/sentiment_service.py](backend/app/services/sentiment_service.py)
- 测试: [backend/tests/unit/services/test_sentiment_service.py](backend/tests/unit/services/test_sentiment_service.py)

### 相关 Skills
- [api-response.md](api-response.md) - API 响应格式
- [exception-handling.md](exception-handling.md) - 异常处理规范
- [code-quality.md](code-quality.md) - 代码质量工具

---

## 🎓 总结

1. **PostgreSQL numeric 类型支持 NaN/Infinity**，但 JSON 不支持
2. **在 Service 层清理数据**，使用 `_sanitize_dict` 方法
3. **将特殊值转换为 None**，在 JSON 中表示为 `null`
4. **递归处理嵌套结构**，确保所有层级的数据都被清理
5. **预防优于修复**，在数据采集时就避免 NaN 值
6. **记录数据质量问题**，便于监控和优化

---

**版本**: 1.0.0
**创建日期**: 2026-03-12
**维护者**: Stock Analysis Team
