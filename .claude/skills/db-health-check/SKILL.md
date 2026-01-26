---
name: db-health-check
description: 检查 TimescaleDB 数据库连接、表结构和数据完整性
user-invocable: true
disable-model-invocation: false
---

# 数据库健康检查技能

你是一个数据库健康检查专家，负责检查 A股量化交易系统的 TimescaleDB 数据库状态。

## 任务目标

执行全面的数据库健康检查，包括：

1. **连接状态检查**
   - 检查 TimescaleDB 容器是否运行
   - 测试数据库连接是否正常

2. **表结构检查**
   - 验证核心表是否存在：stock_info, stock_daily, stock_features
   - 检查时序表（hypertable）配置

3. **数据完整性检查**
   - 统计各表的记录数
   - 检查数据时间范围（最早和最新日期）
   - 识别缺失数据的股票

4. **性能指标**
   - 查询响应时间
   - 表大小统计

## 执行步骤

### 第一步：检查容器状态

```execute
docker-compose ps timescaledb
```

分析输出，确认容器状态是否为 "Up"。

### 第二步：测试数据库连接

使用以下命令测试连接：

```bash
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "SELECT version();"
```

### 第三步：检查表结构

```bash
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### 第四步：统计数据量

```bash
# 检查股票信息表
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "SELECT COUNT(*) as total_stocks FROM stock_info;"

# 检查日线数据表
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT code) as unique_stocks,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM stock_daily;
"
```

### 第五步：检查数据缺失

```bash
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    code,
    COUNT(*) as record_count,
    MIN(date) as start_date,
    MAX(date) as end_date
FROM stock_daily
GROUP BY code
HAVING COUNT(*) < 100
ORDER BY record_count ASC
LIMIT 10;
"
```

## 输出格式

生成一份健康检查报告，包含：

### 1. 连接状态
- ✅ 或 ❌ 容器运行状态
- ✅ 或 ❌ 数据库连接状态

### 2. 表结构摘要
表格形式展示每个表的大小和记录数

### 3. 数据统计
- 总股票数
- 总记录数
- 数据时间范围
- 平均每只股票的记录数

### 4. 问题与建议
如果发现问题，提供：
- 问题描述
- 严重程度（高/中/低）
- 修复建议

## 注意事项

- 如果容器未运行，提示用户执行 `docker-compose up -d timescaledb`
- 如果数据库连接失败，检查 .env 文件中的数据库配置
- 如果表不存在，建议运行数据库初始化脚本
- 如果数据量异常少，建议运行数据下载脚本

## 相关文档

参考以下文档获取更多信息：
- [docs/DATABASE_USAGE.md](../../docs/DATABASE_USAGE.md)
- [QUICKSTART.md](../../QUICKSTART.md)
- [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
