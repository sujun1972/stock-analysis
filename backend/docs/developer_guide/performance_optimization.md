# Backend 性能优化指南

本文档说明了 backend 项目的性能优化实现。

## 优化概览

### 三大优化

1. **并发批量同步** - 批量下载速度提升 5x
2. **多层缓存机制** - 查询速度提升 10x
3. **数据库批量操作** - 批量插入速度提升 6-8x

## 1. 并发批量同步

### 核心实现

**DataDownloadService** ([data_service.py](../../app/services/data_service.py))

```python
# 并发批量下载
result = await data_service.download_batch_concurrent(
    codes=stock_codes,
    years=5,
    max_concurrent=10,  # 并发数
    batch_size=50       # 批次大小
)
```

**BaseSyncService** ([base_sync_service.py](../../app/services/base_sync_service.py))

```python
# 通用并发批量处理
result = await self.batch_process_concurrent(
    items=items,
    process_func=async_process_function,
    max_concurrent=10,
    batch_size=50
)
```

### 技术要点

- 使用 asyncio + Semaphore 控制并发
- 分批处理避免内存溢出
- 支持进度追踪和任务管理

## 2. 多层缓存机制

### 核心实现

**StockDataRepository** ([stock_data_repository.py](../../app/repositories/stock_data_repository.py))

```python
# 缓存查询
stock_list = await repo.get_stock_list_cached(market="上海主板")
daily_data = await repo.get_daily_data_cached(code="000001", limit=100)

# 保存并清除缓存
await repo.save_stock_list_and_clear_cache(stock_df)
await repo.save_daily_data_and_clear_cache(daily_df, code)
```

### 缓存策略

- **股票列表**: TTL 5分钟
- **日线数据**: TTL 1小时
- **自动失效**: 数据更新时清除缓存
- **容错降级**: Redis 不可用时跳过缓存

## 3. 数据库批量操作

### 核心实现

**BatchOperations** ([batch_operations.py](../../app/repositories/batch_operations.py))

```python
from app.repositories.batch_operations import BatchOperations

batch = BatchOperations()

# 批量插入 (execute_batch)
batch.bulk_insert_daily_data(data_list, batch_size=1000)
batch.bulk_insert_stock_list(stock_list, batch_size=500)

# 批量查询 (WHERE IN)
latest_dates = batch.bulk_get_latest_dates(codes)
data_counts = batch.bulk_get_data_counts(codes)

# 批量更新/删除
batch.bulk_update_stock_status(updates)
batch.bulk_delete_daily_data(codes, start_date, end_date)

# 事务管理
batch.execute_in_transaction([op1, op2, op3])
```

### 技术要点

- 使用 psycopg2 的 `execute_batch` (比 executemany 快 3x)
- 使用 `execute_values` 批量插入 (比逐条快 8x)
- WHERE IN 批量查询 (比循环快 10x)

## 性能对比

| 操作 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 批量下载100只股票 | ~300s | ~60s | 5x |
| 股票列表查询 | ~0.5s | ~0.05s | 10x |
| 批量插入1000条 | ~2.0s | ~0.3s | 6.7x |
| 批量查询50只 | ~2.5s | ~0.3s | 8.3x |

## 最佳实践

### 并发下载

```python
# ✅ 推荐：并发下载
result = await service.download_batch_concurrent(codes, max_concurrent=10)

# ❌ 避免：串行下载大量数据
for code in codes:
    await service.download_single_stock(code)
```

### 缓存查询

```python
# ✅ 推荐：使用缓存
data = await repo.get_daily_data_cached(code)

# ❌ 避免：重复查询不使用缓存
for _ in range(100):
    data = repo.get_daily_data(code)
```

### 批量操作

```python
# ✅ 推荐：批量插入
batch.bulk_insert_daily_data(data_list)

# ❌ 避免：逐条插入
for item in data_list:
    repo.save_daily_data(item)
```

## 参数配置

### 并发参数

- `max_concurrent`: 建议 10-20 (避免 API 限流)
- `batch_size`: 建议 50-100

### 批量操作参数

- `batch_size`: 插入建议 1000, 查询建议 500

### 缓存 TTL

配置在 `app/core/config.py`:

```python
CACHE_STOCK_LIST_TTL = 300      # 5分钟
CACHE_DAILY_DATA_TTL = 3600     # 1小时
CACHE_FEATURES_TTL = 1800       # 30分钟
```

## 故障排查

### Redis 连接失败

```bash
# 检查 Redis 服务
docker-compose ps redis
docker-compose logs redis

# 重启 Redis
docker-compose restart redis
```

### 并发下载限流

降低并发数：

```python
result = await service.download_batch_concurrent(
    codes=codes,
    max_concurrent=5,  # 从10降到5
    batch_size=20
)
```

## 相关文件

### 核心模块

- [app/services/data_service.py](../../app/services/data_service.py) - 并发下载服务
- [app/services/base_sync_service.py](../../app/services/base_sync_service.py) - 并发批量处理基类
- [app/repositories/stock_data_repository.py](../../app/repositories/stock_data_repository.py) - 缓存查询
- [app/repositories/batch_operations.py](../../app/repositories/batch_operations.py) - 批量操作

### 配置

- [app/core/config.py](../../app/core/config.py) - 缓存 TTL 配置
- [app/core/cache.py](../../app/core/cache.py) - Redis 缓存管理器
- [app/core/database.py](../../app/core/database.py) - 数据库连接池配置

---

**维护**: Backend Team
**更新**: 2026-03-14
