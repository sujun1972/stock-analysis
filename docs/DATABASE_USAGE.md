# 📊 数据库存储使用指南

## 概述

本项目支持两种数据存储方式：

1. **CSV文件存储**（原始方式）
   - 简单直接，适合测试和学习
   - 存储路径：`data/raw/daily/{股票代码}.csv`

2. **数据库存储**（推荐用于生产）✅
   - 使用PostgreSQL + TimescaleDB
   - 高效查询、自动去重、时序优化
   - 支持增量更新

---

## 为什么使用数据库？

### CSV文件的局限性

```python
# 每次更新都要读写整个文件
df_old = pd.read_csv('000001.csv')  # 读取5年数据
new_data = download_today()
df = pd.concat([df_old, new_data])
df.to_csv('000001.csv')  # 重写整个文件
```

**问题：**
- ⚠️ 文件越大越慢（5000只股票 × 5年 = 25000个文件）
- ⚠️ 无法防止重复数据
- ⚠️ 跨股票查询困难
- ⚠️ 并发写入会出错

### 数据库的优势

```sql
-- 仅插入新数据，自动去重
INSERT INTO stock_daily (code, date, ...)
VALUES ('000001', '2024-01-19', ...)
ON CONFLICT (code, date) DO UPDATE ...
```

**优势：**
- ✅ 增量更新快（仅写入新数据）
- ✅ 主键约束防止重复
- ✅ 跨股票查询秒级响应
- ✅ TimescaleDB时序优化
- ✅ 支持并发读写

---

## 快速开始

### 1. 启动数据库

确保Docker已安装，然后：

```bash
# 进入项目目录
cd /Volumes/MacDriver/stock-analysis

# 启动数据库容器
docker-compose up -d

# 检查运行状态
docker-compose ps

# 预期输出：
# NAME                COMMAND                  SERVICE             STATUS              PORTS
# timescaledb         "docker-entrypoint.s…"   timescaledb         Up 5 minutes        0.0.0.0:5432->5432/tcp
```

### 2. 初始化数据库表结构

```bash
# 激活虚拟环境
source stock_env/bin/activate

# 初始化数据库（仅需执行一次）
python core/scripts/download_data_to_db.py --init-db --stock-list-only
```

**输出示例：**
```
✓ 股票基本信息表创建/验证完成
✓ 股票日线数据表创建/验证完成
✓ TimescaleDB时序表优化完成
✓ 股票特征表创建/验证完成
✓ 模型预测表创建/验证完成
✓ 回测结果表创建/验证完成
✓ 索引创建完成

✅ 数据库初始化完成！
```

### 3. 下载数据到数据库

#### 场景1：测试下载（前10只股票）

```bash
python core/scripts/download_data_to_db.py --years 5 --max-stocks 10
```

#### 场景2：下载主板和创业板

```bash
python core/scripts/download_data_to_db.py --years 5 --markets 上海主板 创业板
```

#### 场景3：下载所有股票（生产环境）

```bash
# 建议增加延迟避免被限流
python core/scripts/download_data_to_db.py --years 5 --delay 1.0
```

**下载过程示例：**
```
[1/10] 000001 (平安银行)
  ✓ 保存成功: 1234 条记录
[2/10] 000002 (万科A)
  ✓ 保存成功: 1256 条记录
...
进度: 10/10 | 成功: 10 | 失败: 0 | 预计剩余: 0.0分钟

下载完成！
总数: 10 | 成功: 10 | 失败: 0
耗时: 1.2 分钟
```

---

## 数据库表结构

### 1. stock_info（股票基本信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(20) | 股票代码（主键） |
| name | VARCHAR(100) | 股票名称 |
| market | VARCHAR(20) | 市场类型 |
| list_date | DATE | 上市日期 |
| industry | VARCHAR(100) | 所属行业 |
| area | VARCHAR(100) | 所属地域 |
| status | VARCHAR(20) | 状态（正常/退市） |

### 2. stock_daily（日线数据）- TimescaleDB优化

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(20) | 股票代码 |
| date | DATE | 交易日期 |
| open | DECIMAL(10,2) | 开盘价 |
| high | DECIMAL(10,2) | 最高价 |
| low | DECIMAL(10,2) | 最低价 |
| close | DECIMAL(10,2) | 收盘价 |
| volume | BIGINT | 成交量 |
| amount | DECIMAL(20,2) | 成交额 |
| amplitude | DECIMAL(10,2) | 振幅 |
| pct_change | DECIMAL(10,2) | 涨跌幅 |
| change | DECIMAL(10,2) | 涨跌额 |
| turnover | DECIMAL(10,2) | 换手率 |

**主键：** `(code, date)` - 自动去重

### 3. stock_features（特征数据）

存储计算后的技术指标和Alpha因子：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(20) | 股票代码 |
| date | DATE | 日期 |
| feature_type | VARCHAR(50) | 特征类型（technical/alpha/transformed） |
| feature_data | JSONB | 特征数据（JSON格式） |

### 4. stock_predictions（模型预测）

| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(20) | 股票代码 |
| pred_date | DATE | 预测日期 |
| model_name | VARCHAR(100) | 模型名称 |
| model_version | VARCHAR(50) | 模型版本 |
| prediction | DECIMAL(10,4) | 预测值 |
| confidence | DECIMAL(5,4) | 置信度 |
| actual_return | DECIMAL(10,4) | 实际收益率 |

### 5. backtest_results（回测结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_name | VARCHAR(100) | 策略名称 |
| start_date | DATE | 开始日期 |
| end_date | DATE | 结束日期 |
| initial_capital | DECIMAL(20,2) | 初始资金 |
| final_value | DECIMAL(20,2) | 最终价值 |
| total_return | DECIMAL(10,4) | 总收益率 |
| sharpe_ratio | DECIMAL(10,4) | 夏普比率 |
| max_drawdown | DECIMAL(10,4) | 最大回撤 |
| win_rate | DECIMAL(10,4) | 胜率 |
| config | JSONB | 配置参数 |

---

## Python代码示例

### 示例1：基本使用

```python
from core.src.database.db_manager import DatabaseManager
import pandas as pd

# 1. 连接数据库
db = DatabaseManager()

# 2. 获取股票列表
stock_list = db.get_stock_list(market='上海主板')
print(f"上海主板股票数量: {len(stock_list)}")

# 3. 加载单只股票数据
df = db.load_daily_data('000001', start_date='2024-01-01')
print(f"数据行数: {len(df)}")
print(df.head())

# 4. 保存数据
db.save_daily_data(df, '000001')
```

### 示例2：批量查询多只股票

```python
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()

# SQL查询：获取2024年所有涨停股票
query = """
SELECT code, date, close, pct_change
FROM stock_daily
WHERE date >= '2024-01-01'
  AND pct_change >= 9.9
ORDER BY date DESC, pct_change DESC
LIMIT 100;
"""

df = pd.read_sql_query(query, conn)
db.release_connection(conn)

print(f"涨停股票数: {len(df)}")
print(df)
```

### 示例3：计算市场平均指标

```python
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()

# 计算每日市场平均收益率
query = """
SELECT
    date,
    AVG(pct_change) as avg_return,
    AVG(turnover) as avg_turnover,
    COUNT(*) as stock_count
FROM stock_daily
WHERE date >= '2024-01-01'
GROUP BY date
ORDER BY date;
"""

market_stats = pd.read_sql_query(query, conn)
db.release_connection(conn)

print(market_stats.head())
```

### 示例4：增量更新数据

```python
import akshare as ak
from datetime import datetime, timedelta
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()

# 获取最近1个月的新数据
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

# 下载新数据
df = ak.stock_zh_a_hist(
    symbol='000001',
    start_date=start_date,
    end_date=end_date,
    adjust='qfq'
)

# 保存（自动去重，冲突时更新）
db.save_daily_data(df, '000001')
print("✓ 增量更新完成")
```

---

## SQL查询技巧

### 1. 查询最新价格

```sql
SELECT DISTINCT ON (code)
    code, date, close
FROM stock_daily
ORDER BY code, date DESC;
```

### 2. 计算5日涨跌幅

```sql
SELECT
    code,
    date,
    close,
    LAG(close, 5) OVER (PARTITION BY code ORDER BY date) as close_5d_ago,
    (close - LAG(close, 5) OVER (PARTITION BY code ORDER BY date))
        / LAG(close, 5) OVER (PARTITION BY code ORDER BY date) * 100 as pct_change_5d
FROM stock_daily
WHERE date >= '2024-01-01'
ORDER BY code, date DESC;
```

### 3. 筛选高换手率股票

```sql
SELECT code, date, close, turnover
FROM stock_daily
WHERE date = (SELECT MAX(date) FROM stock_daily)
  AND turnover > 10.0
ORDER BY turnover DESC
LIMIT 50;
```

### 4. TimescaleDB时序聚合

```sql
-- 计算每周平均价格
SELECT
    time_bucket('7 days', date) as week,
    code,
    AVG(close) as avg_close,
    MAX(high) as max_high,
    MIN(low) as min_low
FROM stock_daily
WHERE code = '000001'
GROUP BY week, code
ORDER BY week DESC;
```

---

## 数据迁移

### 从CSV迁移到数据库

```python
from pathlib import Path
import pandas as pd
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()

# 遍历所有CSV文件
data_dir = Path('data/raw/daily')
csv_files = list(data_dir.glob('*.csv'))

print(f"找到 {len(csv_files)} 个CSV文件")

for csv_file in csv_files:
    stock_code = csv_file.stem  # 文件名（不含扩展名）

    # 读取CSV
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)

    # 保存到数据库
    try:
        count = db.save_daily_data(df, stock_code)
        print(f"✓ {stock_code}: {count} 条记录")
    except Exception as e:
        print(f"✗ {stock_code}: {e}")
```

### 从数据库导出到CSV（备份）

```python
from core.src.database.db_manager import DatabaseManager
from pathlib import Path

db = DatabaseManager()

# 获取所有股票代码
stock_list = db.get_stock_list()

# 创建导出目录
export_dir = Path('data/backup')
export_dir.mkdir(exist_ok=True)

for _, row in stock_list.iterrows():
    code = row['code']

    # 从数据库加载
    df = db.load_daily_data(code)

    # 保存为CSV
    df.to_csv(export_dir / f"{code}.csv")
    print(f"✓ 导出 {code}: {len(df)} 条记录")
```

---

## 性能对比

### CSV文件方式

```python
import time

# 查询5只股票的最近1年数据
codes = ['000001', '000002', '600000', '600036', '601318']
start = time.time()

data = []
for code in codes:
    df = pd.read_csv(f'data/raw/daily/{code}.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= '2024-01-01']
    data.append(df)

result = pd.concat(data)
print(f"CSV耗时: {time.time() - start:.2f}秒")
# 输出：CSV耗时: 0.35秒
```

### 数据库方式

```python
import time
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()

codes = ['000001', '000002', '600000', '600036', '601318']
start = time.time()

query = """
SELECT * FROM stock_daily
WHERE code = ANY(%s) AND date >= '2024-01-01'
ORDER BY code, date;
"""

result = pd.read_sql_query(query, conn, params=(codes,))
db.release_connection(conn)

print(f"数据库耗时: {time.time() - start:.2f}秒")
# 输出：数据库耗时: 0.08秒
```

**结论：数据库查询速度提升 4-5倍** 🚀

---

## 常见问题

### Q1: 如何查看数据库内容？

**方法1：使用psql命令行**

```bash
docker exec -it stock_timescaledb psql -U stock_user -d stock_analysis

# 列出所有表
\dt

# 查询股票数量
SELECT COUNT(*) FROM stock_info;

# 查询数据量
SELECT
    code,
    COUNT(*) as record_count,
    MIN(date) as start_date,
    MAX(date) as end_date
FROM stock_daily
GROUP BY code
ORDER BY record_count DESC
LIMIT 10;

# 退出
\q
```

**方法2：使用Python**

```python
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()

# 查看表统计
stats = pd.read_sql_query("""
    SELECT
        'stock_info' as table_name,
        COUNT(*) as row_count
    FROM stock_info
    UNION ALL
    SELECT
        'stock_daily' as table_name,
        COUNT(*) as row_count
    FROM stock_daily;
""", conn)

print(stats)
db.release_connection(conn)
```

### Q2: 数据库占用多少空间？

```bash
docker exec -it stock_timescaledb psql -U stock_user -d stock_analysis -c "\
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

### Q3: 如何备份数据库？

```bash
# 备份整个数据库
docker exec -t stock_timescaledb pg_dump -U stock_user stock_analysis > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i stock_timescaledb psql -U stock_user stock_analysis < backup_20240119.sql
```

### Q4: 如何重置数据库？

```bash
# 方法1：删除所有数据（保留表结构）
docker exec -it stock_timescaledb psql -U stock_user -d stock_analysis -c "\
TRUNCATE stock_daily, stock_info, stock_features, stock_predictions, backtest_results CASCADE;"

# 方法2：删除并重建数据库
docker-compose down -v  # 删除容器和数据卷
docker-compose up -d    # 重新创建
python core/scripts/download_data_to_db.py --init-db --stock-list-only
```

### Q5: 数据库连接失败怎么办？

**检查清单：**

```bash
# 1. 检查Docker是否运行
docker ps | grep timescaledb

# 2. 检查端口是否监听
lsof -i :5432

# 3. 检查数据库配置
cat core/src/config/config.py | grep DATABASE_CONFIG

# 4. 测试连接
python -c "from core.src.database.db_manager import DatabaseManager; db = DatabaseManager(); print('✓ 连接成功')"
```

---

## 最佳实践

### 1. 定期增量更新

创建定时任务每日更新：

```bash
# 创建脚本：core/scripts/daily_update.sh
#!/bin/bash
source stock_env/bin/activate
python core/scripts/download_data_to_db.py --years 0.1 --delay 1.0

# 添加到crontab（每天18:00执行）
0 18 * * * /path/to/stock-analysis/core/scripts/daily_update.sh >> /tmp/stock_update.log 2>&1
```

### 2. 监控数据质量

```python
from core.src.database.db_manager import DatabaseManager

db = DatabaseManager()
conn = db.get_connection()

# 检查数据缺失
query = """
SELECT code, MAX(date) as last_date
FROM stock_daily
GROUP BY code
HAVING MAX(date) < CURRENT_DATE - INTERVAL '7 days'
ORDER BY last_date;
"""

outdated = pd.read_sql_query(query, conn)
print(f"⚠️  超过7天未更新的股票: {len(outdated)}")
```

### 3. 使用连接池

```python
# 高并发场景
from core.src.database.db_manager import DatabaseManager
from concurrent.futures import ThreadPoolExecutor

db = DatabaseManager()

def process_stock(code):
    df = db.load_daily_data(code)
    # ... 处理数据 ...
    return result

with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(process_stock, stock_codes)
```

---

## 总结

✅ **推荐使用数据库存储的场景：**
- 股票数量 > 100
- 需要频繁查询和更新
- 需要跨股票分析
- 生产环境部署

❌ **可以继续使用CSV的场景：**
- 仅分析少数几只股票
- 一次性下载不再更新
- 学习测试阶段

**混合方案：**
- 数据库用于日常查询和更新
- CSV用于定期备份和归档

---

**相关文档：**
- [快速开始指南](../QUICKSTART.md)
- [故障排除指南](../TROUBLESHOOTING.md)
- [系统架构文档](ARCHITECTURE.md)
- [Backend README](../backend/README.md)
- [Core README](../core/README.md)

**最后更新：2026-01-20**
