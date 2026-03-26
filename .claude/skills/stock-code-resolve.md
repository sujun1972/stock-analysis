# 股票代码自动补全规范 (Stock Code Auto-Resolve)

## 概述

用户在前端输入股票代码时，只需填写纯数字代码（如 `000001`），后端自动补全为完整 ts_code（如 `000001.SZ`）。这是一个通用能力，集中在 `StockQuoteCache` 中实现。

---

## 后端实现

### 核心方法

**位置**：`backend/app/services/stock_quote_cache.py` → `StockQuoteCache.resolve_ts_code()`

```python
from app.services.stock_quote_cache import stock_quote_cache

# 用户输入 '000001' → 返回 '000001.SZ'
# 用户输入 '600519' → 返回 '600519.SH'
# 用户输入 '000001.SZ'（已含后缀）→ 直接返回 '000001.SZ'
# 查不到 → 返回 None
ts_code = await stock_quote_cache.resolve_ts_code(user_input)
```

### 规则

| 输入形式 | 处理方式 | 示例 |
|---|---|---|
| 包含 `.` | 视为完整 ts_code，直接返回（转大写） | `000001.sz` → `000001.SZ` |
| 纯数字代码 | 查 `stock_basic.code` 补全后缀 | `600519` → `600519.SH` |
| 查不到 | 返回 `None` | `999999` → `None` |

### 缓存策略

- Redis key：`stock:code_map:{pure_code}`
- TTL：**86400 秒（24 小时）**，交易所后缀极少变化，不需要短 TTL
- 降级：Redis 不可用时直接查数据库，不影响主流程

### 底层数据源

`_QuoteRepository.resolve_ts_codes()` 批量查询 `stock_basic` 表：

```sql
SELECT code, ts_code FROM stock_basic WHERE code IN (...)
```

---

## 在 API 端点中使用

在接收 `ts_code` 参数的端点，查询前加一行补全：

```python
from app.services.stock_quote_cache import stock_quote_cache

# GET 端点示例
@router.get("")
async def get_data(ts_code: Optional[str] = Query(None)):
    # 自动补全股票代码后缀
    resolved_ts_code = await stock_quote_cache.resolve_ts_code(ts_code) if ts_code else None

    result = await service.get_data(ts_code=resolved_ts_code, ...)
    return ApiResponse.success(data=result)
```

**已接入的端点**：
- `GET /api/top-inst` — 龙虎榜机构明细

---

## 前端规范

前端输入框 **无需任何改动**：
- placeholder 改为 `如 000001 或 000001.SZ`，提示用户两种格式均可接受
- 不需要在前端做任何格式化或校验，完全由后端处理

```tsx
<Input
  placeholder="如 000001 或 000001.SZ"
  value={tsCode}
  onChange={(e) => setTsCode(e.target.value)}
/>
```

---

## 扩展到其他页面

当其他页面（如资金流向、龙虎榜每日明细等）有股票代码筛选时，在对应 API 端点加同样两行代码即可：

```python
resolved_ts_code = await stock_quote_cache.resolve_ts_code(ts_code) if ts_code else None
```

无需修改 Repository、Service 层，也无需修改前端。
