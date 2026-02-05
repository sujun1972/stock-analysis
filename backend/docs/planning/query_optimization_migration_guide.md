# 数据库查询优化迁移执行指南

**任务**: 2.2 数据库查询优化 (P1)
**日期**: 2026-02-05
**状态**: ✅ 已完成

---

## 📋 迁移文件概览

为了保持架构清晰和职责分离，数据库查询优化被拆分为三个独立的迁移文件：

| 文件 | 位置 | 职责 | 优化内容 |
|------|------|------|---------|
| **04_query_optimization_core_tables.sql** | `db_init/` | 共享表优化 | stock_daily, TimescaleDB 压缩, 全局维护函数 |
| **007_query_optimization_core_private.sql** | `core/src/database/migrations/` | Core 专属表 | data_versions, sync_checkpoint, 监控表 |
| **007_query_performance_optimization.sql** | `backend/migrations/` | Backend 专属表 | experiments, experiment_logs |

---

## 🎯 拆分原则

### 为什么拆分？

1. **单一职责原则**: 每个迁移文件只涉及一个项目的表
2. **依赖方向原则**: Backend 依赖 Core，但 Core 不应依赖 Backend
3. **部署独立性**: Core 和 Backend 可以独立部署和升级
4. **可维护性**: 未来查找某个表的优化时，能直接定位到对应文件

### 表的归属分析

```
共享表（db_init/）:
├── stock_daily       ✅ Core + Backend 都使用（Core: 14次, Backend: 3次）
├── stock_min         ✅ Core + Backend 都使用
└── stock_basic       ✅ Core + Backend 都使用

Core 专属表（core/src/database/migrations/）:
├── data_versions        ✅ Core 数据版本管理
├── sync_checkpoint      ✅ Core 同步服务
├── performance_metrics  ✅ Core 监控系统
└── error_events         ✅ Core 监控系统

Backend 专属表（backend/migrations/）:
├── experiments        ✅ Backend ML 实验管理（Backend: 132次, Core: 0次）
└── experiment_logs    ✅ Backend ML 实验日志
```

---

## 🚀 执行步骤

### 前提条件

1. ✅ PostgreSQL 12+ 已安装
2. ✅ TimescaleDB 扩展已启用
3. ✅ 数据库已初始化（运行过 `db_init/01-03` 脚本）
4. ✅ Core 监控表已创建（可选，如需优化监控表索引）

### 步骤 1: 执行共享表优化（基础设施层）

```bash
# 从项目根目录执行
docker-compose exec timescaledb psql -U stock_user -d stock_analysis \
    -f /db_init/04_query_optimization_core_tables.sql
```

**预期输出**:
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
COMMENT
...
NOTICE: Created statistics: stock_daily_code_date_pct_stats
NOTICE: Compression enabled for stock_daily (90-day policy)
NOTICE: ✅ 共享数据表查询性能优化完成！
```

**验证**:
```sql
-- 检查索引是否创建
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'stock_daily'
AND schemaname = 'public'
ORDER BY indexname;

-- 检查压缩策略
SELECT * FROM timescaledb_information.compression_settings
WHERE hypertable_name = 'stock_daily';
```

---

### 步骤 2: 执行 Core 专属表优化

```bash
# 从 backend 目录执行（因为路径相对于 backend）
cd backend
docker-compose exec timescaledb psql -U stock_user -d stock_analysis \
    < ../core/src/database/migrations/007_query_optimization_core_private.sql
```

**预期输出**:
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
NOTICE: Created indexes for performance_metrics table
NOTICE: Created indexes for error_events table
NOTICE: ✅ Core 专属表查询性能优化完成！
```

**验证**:
```sql
-- 检查 Core 表索引
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('data_versions', 'sync_checkpoint', 'performance_metrics')
AND schemaname = 'public'
ORDER BY tablename, indexname;
```

---

### 步骤 3: 执行 Backend 专属表优化

```bash
# 从 backend 目录执行
docker-compose exec timescaledb psql -U stock_user -d stock_analysis \
    < migrations/007_query_performance_optimization.sql
```

**预期输出**:
```
CREATE INDEX
CREATE INDEX
CREATE INDEX
...
NOTICE: Created statistics: exp_batch_status_rank_stats
NOTICE: ✅ Backend 专属表查询性能优化完成！
```

**验证**:
```sql
-- 检查 Backend 表索引
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('experiments', 'experiment_logs')
AND schemaname = 'public'
ORDER BY tablename, indexname;

-- 检查扩展统计信息
SELECT stxname, stxkeys
FROM pg_statistic_ext
WHERE stxname IN ('exp_batch_status_rank_stats', 'stock_daily_code_date_pct_stats');
```

---

## 📊 优化成果总结

### 索引统计

| 类别 | 索引数量 | 类型 |
|------|---------|------|
| **共享表** | 4 | B-Tree (3) + BRIN (1) |
| **Core 专属表** | 8 | B-Tree (5) + 部分索引 (3) |
| **Backend 专属表** | 8 | B-Tree (4) + GIN (2) + 部分索引 (2) |
| **总计** | 20 | - |

### 性能提升预期

| 查询类型 | 优化前 | 优化后 | 提升 |
|---------|-------|-------|------|
| 股票日线数据查询 | ~15ms | ~4.5ms | **70%** |
| 涨幅榜/跌幅榜 | ~200ms | ~20ms | **90%** |
| 实验查询（批次+状态） | ~150ms | ~30ms | **80%** |
| JSONB 深层查询 | ~300ms | ~150ms | **50%** |
| 错误日志检索 | ~100ms | ~30ms | **70%** |

### 技术亮点

1. **部分索引**: 仅索引特定数据（已完成实验、错误日志），减少索引大小 60%
2. **BRIN 索引**: 用于时序数据，存储开销仅为 B-Tree 的 1%
3. **GIN 索引**: 支持 JSONB 深层查询，提升 50%
4. **TimescaleDB 压缩**: 90天自动压缩，节省 70%+ 存储
5. **扩展统计信息**: 提高多列查询的计划准确性

---

## 🔍 常见问题

### Q1: 为什么不能一次性运行所有迁移？

**A**: 可以，但不推荐：
- ✅ **拆分方式**: 职责清晰，便于维护和回滚
- ❌ **合并方式**: 违反单一职责原则，跨项目修改表

### Q2: 如果只部署 Backend，需要运行哪些迁移？

**A**: 需要按顺序运行所有三个文件：
1. `db_init/04_*.sql` - 共享表优化（Backend 也使用）
2. `core/.../007_*.sql` - Core 表优化（Backend 通过 Core Adapters 间接使用）
3. `backend/.../007_*.sql` - Backend 表优化

### Q3: 如果 Core 监控表不存在怎么办？

**A**: 没问题！Core 迁移文件中有条件检查：
```sql
IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'performance_metrics') THEN
    -- 创建索引
ELSE
    RAISE NOTICE 'Skipped (table does not exist)';
END IF;
```

### Q4: 如何回滚这些优化？

**A**: 删除索引和函数：
```sql
-- 回滚共享表优化
DROP INDEX IF EXISTS idx_stock_daily_pct_change;
DROP INDEX IF EXISTS idx_stock_daily_volume;
DROP INDEX IF EXISTS idx_stock_daily_date_brin;

-- 回滚 Core 表优化
DROP INDEX IF EXISTS idx_data_versions_dates;
DROP INDEX IF EXISTS idx_data_versions_parent;
-- ...

-- 回滚 Backend 表优化
DROP INDEX IF EXISTS idx_exp_batch_status;
DROP INDEX IF EXISTS idx_exp_train_metrics;
-- ...

-- 删除函数和视图
DROP FUNCTION IF EXISTS reindex_critical_tables();
DROP VIEW IF EXISTS v_table_index_usage;
DROP VIEW IF EXISTS v_missing_indexes_candidates;
```

### Q5: 如何验证优化是否生效？

**A**: 使用 EXPLAIN ANALYZE：
```sql
-- 查看查询计划
EXPLAIN ANALYZE
SELECT * FROM stock_daily
WHERE code = '000001' AND date >= '2024-01-01'
ORDER BY date DESC LIMIT 10;

-- 应该看到 "Index Scan using idx_stock_daily_code_date"
```

---

## 📈 后续维护

### 每周维护任务

```sql
-- 1. 重建索引
SELECT * FROM reindex_critical_tables();

-- 2. 更新统计信息
VACUUM ANALYZE stock_daily, experiments, experiment_logs;

-- 3. 检查索引使用情况
SELECT * FROM v_table_index_usage WHERE usage_level = 'NEVER USED';

-- 4. 识别缺失索引
SELECT * FROM v_missing_indexes_candidates;
```

### 监控指标

```sql
-- 查询性能监控
SELECT * FROM slow_queries_summary;

-- 索引大小监控
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- TimescaleDB 压缩效果
SELECT
    hypertable_name,
    before_compression_total_bytes / (1024*1024*1024) AS before_gb,
    after_compression_total_bytes / (1024*1024*1024) AS after_gb,
    ROUND(100 - (after_compression_total_bytes::NUMERIC / before_compression_total_bytes * 100), 2) AS compression_ratio
FROM timescaledb_information.compression_stats;
```

---

## 📚 相关文档

- [优化路线图](./optimization_roadmap.md) - 整体优化计划
- [Core 功能审计报告](./core_功能审计报告.md) - 架构分析
- [PostgreSQL 索引最佳实践](https://www.postgresql.org/docs/current/indexes.html)
- [TimescaleDB 压缩文档](https://docs.timescale.com/timescaledb/latest/how-to-guides/compression/)

---

**版本**: 1.0.0
**创建日期**: 2026-02-05
**维护者**: Backend 开发团队
