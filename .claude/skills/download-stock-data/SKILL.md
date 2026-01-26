---
name: download-stock-data
description: 下载A股历史数据到TimescaleDB，支持指定股票代码、数量和时间范围
user-invocable: true
disable-model-invocation: false
---

# 股票数据下载技能

你是一个数据下载专家，负责从 AkShare 下载 A股历史数据并存储到 TimescaleDB。

## 任务目标

安全、高效地下载股票数据，包括：

1. **环境准备**
   - 检查 TimescaleDB 是否运行
   - 验证虚拟环境和依赖
   - 测试 AkShare 连接

2. **数据下载**
   - 支持指定股票代码列表
   - 支持指定下载年份
   - 支持限制最大股票数量
   - 自动去重和增量更新

3. **数据验证**
   - 验证下载的数据质量
   - 统计下载成功和失败的股票
   - 检查数据完整性

4. **结果报告**
   - 下载统计信息
   - 失败股票列表
   - 数据存储位置

## 使用场景

### 场景 1: 下载指定股票数据
用户提供股票代码列表，如 "000001", "600519"

### 场景 2: 批量下载热门股票
下载前 N 只活跃股票（如沪深300成分股）

### 场景 3: 增量更新
更新已有股票的最新数据

## 执行步骤

### 第一步：前置检查

```bash
# 检查 TimescaleDB 容器状态
docker-compose ps timescaledb

# 检查虚拟环境
which python3

# 测试 AkShare 连接
cd /Volumes/MacDriver/stock-analysis && python3 core/scripts/test_akshare.py
```

**预期结果：**
- TimescaleDB 状态: Up
- Python 路径: .../stock_env/bin/python3
- AkShare 测试: 全部通过

**如果检查失败：**
- TimescaleDB 未运行 → `docker-compose up -d timescaledb`
- 虚拟环境未激活 → `source stock_env/bin/activate`
- AkShare 连接失败 → 检查网络连接，可能需要等待或更换数据源

### 第二步：确定下载参数

根据用户需求确定以下参数：

**参数说明：**
- `--years`: 下载多少年的历史数据（默认 5 年）
- `--max-stocks`: 最多下载多少只股票（默认 10，防止下载时间过长）
- `--codes`: 指定股票代码列表（可选，逗号分隔）
- `--delay`: 请求间延迟秒数（默认 0.5，避免被限流）

**示例参数组合：**

下载指定股票：
```
--codes 000001,600519,000002 --years 3
```

批量下载（限制数量）：
```
--years 5 --max-stocks 20 --delay 0.5
```

快速测试（少量数据）：
```
--years 1 --max-stocks 3
```

### 第三步：执行下载

```bash
cd /Volumes/MacDriver/stock-analysis

# 方式 A: 使用 API（推荐，异步下载）
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001", "600519", "000002"],
    "years": 5
  }'

# 方式 B: 使用脚本（直接运行）
source stock_env/bin/activate
python3 core/scripts/download_data_to_db.py --years 5 --max-stocks 10 --delay 0.5
```

**推荐使用方式 A（API）的原因：**
- 异步执行，不阻塞
- 可以通过 task_id 查询进度
- 更稳定，有完善的错误处理

**使用方式 B（脚本）的场景：**
- 本地开发调试
- 需要查看详细日志
- API 服务未启动

### 第四步：监控下载进度

**如果使用 API：**
```bash
# API 返回 task_id，使用它查询状态
curl http://localhost:8000/api/data/download/status/{task_id}
```

**如果使用脚本：**
观察终端输出，显示每只股票的下载进度：
```
[INFO] 正在下载股票 000001 (1/10)
[INFO] 000001 下载成功，记录数: 1234
[INFO] 正在下载股票 600519 (2/10)
...
```

### 第五步：验证下载结果

```bash
# 检查数据库中的记录数
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    COUNT(DISTINCT code) as total_stocks,
    COUNT(*) as total_records,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM stock_daily;
"

# 查看最近下载的股票
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    code,
    COUNT(*) as records,
    MIN(date) as start_date,
    MAX(date) as end_date
FROM stock_daily
GROUP BY code
ORDER BY MAX(date) DESC
LIMIT 10;
"
```

### 第六步：数据质量检查

```bash
# 检查是否有缺失数据的股票（记录数异常少）
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    code,
    COUNT(*) as record_count
FROM stock_daily
GROUP BY code
HAVING COUNT(*) < 100
ORDER BY record_count ASC;
"

# 检查是否有异常的价格数据
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT code, date, open, high, low, close
FROM stock_daily
WHERE close <= 0 OR high < low OR open < low OR close < low
LIMIT 10;
"
```

## 输出格式

生成一份下载报告，包含：

### 1. 执行摘要
```
================================================================================
                          股票数据下载报告
================================================================================
下载时间: 2026-01-26 10:30:00
数据源: AkShare
目标数据库: TimescaleDB (stock_analysis)
```

### 2. 下载参数
```
参数配置:
- 下载年份: 5 年
- 最大股票数: 10
- 指定代码: 000001, 600519, 000002
- 请求延迟: 0.5 秒
```

### 3. 下载统计
```
下载统计:
✅ 成功: 8 只股票
❌ 失败: 2 只股票
📊 总记录数: 12,345 条
⏱️  总耗时: 45 秒
```

### 4. 失败股票（如果有）
```
失败股票列表:
- 000003: 数据不存在
- 600000: 网络超时
```

### 5. 数据验证结果
```
数据质量检查:
✅ 价格数据正常（无负值）
✅ 日期范围正常
⚠️  发现 2 只股票数据不足 100 条（可能是新上市）
```

### 6. 下一步建议
```
建议操作:
1. 重试失败的股票: 000003, 600000
2. 计算技术指标: 使用 /calculate-features 技能
3. 运行数据清洗: python3 core/src/data_pipeline/data_cleaner.py
```

## 常见问题处理

### 问题 1: AkShare 限流
**症状**: 返回 429 错误或频繁失败

**解决方案**:
1. 增加延迟参数 `--delay 1.0`
2. 减少批量下载数量 `--max-stocks 5`
3. 分批次下载，每次间隔几分钟

### 问题 2: 数据库连接失败
**症状**: psycopg2.OperationalError

**解决方案**:
1. 检查容器: `docker-compose ps timescaledb`
2. 重启数据库: `docker-compose restart timescaledb`
3. 检查 .env 配置文件

### 问题 3: 部分股票下载失败
**症状**: 某些股票代码无数据

**解决方案**:
1. 验证股票代码是否正确（6位数字）
2. 检查股票是否已退市
3. 尝试更换数据源（如 Tushare）

### 问题 4: 下载速度慢
**症状**: 每只股票下载超过 5 秒

**解决方案**:
1. 检查网络连接
2. 使用 API 异步下载
3. 考虑部署到服务器（更好的网络环境）

## 数据存储说明

### 数据库表结构

**stock_daily 表:**
```sql
CREATE TABLE stock_daily (
    code VARCHAR(20),      -- 股票代码
    date DATE,            -- 交易日期
    open DECIMAL(10,2),   -- 开盘价
    high DECIMAL(10,2),   -- 最高价
    low DECIMAL(10,2),    -- 最低价
    close DECIMAL(10,2),  -- 收盘价
    volume BIGINT,        -- 成交量
    PRIMARY KEY (code, date)
);
```

### TimescaleDB 优化

数据已启用时序优化（Hypertable），查询性能提升 5-120 倍。

参考: [docs/DATABASE_USAGE.md](../../docs/DATABASE_USAGE.md)

## 性能建议

### 下载速度优化
- 单只股票下载时间: 1-3 秒
- 10 只股票总时间: 15-30 秒
- 100 只股票总时间: 2-5 分钟

### 资源占用
- 内存使用: < 500 MB
- 磁盘占用: 每只股票约 500 KB（5年数据）
- 网络流量: 每只股票约 100 KB

## 相关文档

- [QUICKSTART.md](../../QUICKSTART.md#场景1：下载A股历史数据) - 下载指南
- [docs/DATABASE_USAGE.md](../../docs/DATABASE_USAGE.md) - 数据库使用
- [core/scripts/README.md](../../core/scripts/README.md) - 脚本说明
- [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) - 故障排除
