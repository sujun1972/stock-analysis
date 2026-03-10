---
name: sentiment-cycle-analysis
description: 分析市场情绪周期，计算赚钱效应指数，跟踪游资动向
user-invocable: true
disable-model-invocation: false
---

# 情绪周期分析技能

你是市场情绪分析专家，负责计算和分析A股市场的情绪周期。

## 核心功能

### 1. 情绪周期识别
基于涨停/跌停数据、连板高度、炸板率等指标，将市场划分为四个阶段：

| 阶段 | 特征 | 判断标准 |
|------|------|---------|
| **冰点** | 市场极度低迷 | 跌停≥50家，涨跌比<0.5，炸板率>60% |
| **启动** | 情绪回暖 | 涨停≥20家，涨跌比>1.5，炸板率<40% |
| **发酵** | 情绪高涨 | 涨停≥40家，涨跌比>3，连板≥5天 |
| **退潮** | 情绪降温 | 炸板率>50%，连板高度下降 |

### 2. 赚钱效应指数（0-100分）
```
指数 = 涨停数(30%) + 涨跌比(25%) + 连板高度(25%) + 炸板率(20%)
```

### 3. 游资分析
- 机构净买入TOP3
- 一线顶级游资打板排行
- 游资活跃度榜单（近30天）

## 使用场景

### 场景1: 查看当前市场情绪
```bash
# 获取当前情绪周期
curl http://localhost:8000/api/sentiment/cycle/current

# 通过Admin页面查看
打开: http://localhost:3002/sentiment-cycle
```

### 场景2: 计算情绪周期
```bash
# 计算指定日期的情绪周期
curl -X POST "http://localhost:8000/api/sentiment/cycle/calculate?date=2026-03-10"

# 通过Admin页面计算
点击"计算周期"按钮
```

### 场景3: 查询游资动向
```bash
# 机构净买入排行
curl "http://localhost:8000/api/sentiment/hot-money/institution-top?limit=3"

# 游资打板排行
curl "http://localhost:8000/api/sentiment/hot-money/top-tier-limit-up?limit=10"

# 游资活跃度榜单
curl "http://localhost:8000/api/sentiment/hot-money/activity-ranking?days=30&limit=20"
```

## 执行步骤

### 第一步：检查数据准备

验证是否有市场情绪基础数据：

```bash
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    trade_date,
    limit_up_count,
    limit_down_count,
    blast_rate
FROM market_sentiment
ORDER BY trade_date DESC
LIMIT 5;
"
```

**如果没有数据**，先同步市场情绪数据：
```bash
curl -X POST http://localhost:8000/api/sentiment/sync
```

### 第二步：计算情绪周期

```bash
# 方式A: 使用API
TODAY=$(date +%Y-%m-%d)
curl -s -X POST "http://localhost:8000/api/sentiment/cycle/calculate?date=$TODAY" | python3 -m json.tool

# 方式B: 使用Python脚本
docker-compose exec backend python3 -c "
import sys
sys.path.insert(0, '/app/core')
from src.database.connection_pool_manager import ConnectionPoolManager
from src.sentiment.cycle_calculator import SentimentCycleCalculator

# 数据库配置
db_config = {
    'host': 'timescaledb',
    'port': 5432,
    'database': 'stock_analysis',
    'user': 'stock_user',
    'password': 'stock_password_123'
}

pool_manager = ConnectionPoolManager(db_config)
calculator = SentimentCycleCalculator(pool_manager)

# 计算情绪周期
result = calculator.calculate_cycle('$TODAY')
print(f'阶段: {result.get(\"cycle_stage_cn\")}')
print(f'赚钱效应: {result.get(\"money_making_index\"):.2f}')
print(f'涨停数: {result.get(\"limit_up_count\")}')
"
```

### 第三步：验证计算结果

```bash
# 查询数据库
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    trade_date,
    cycle_stage_cn as 阶段,
    money_making_index as 赚钱效应,
    sentiment_score as 情绪得分,
    limit_up_count as 涨停,
    limit_down_count as 跌停,
    max_continuous_days as 最高连板
FROM market_sentiment_cycle
ORDER BY trade_date DESC
LIMIT 5;
"
```

### 第四步：分析游资动向

```bash
# 查看游资席位数据
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    seat_label as 席位标签,
    seat_type as 类型,
    city as 城市,
    appearance_count as 上榜次数,
    win_rate as 胜率
FROM hot_money_seats
WHERE seat_type = 'top_tier'
ORDER BY appearance_count DESC
LIMIT 10;
"
```

## 输出格式

### 情绪周期报告
```
================================================================================
                      市场情绪周期分析报告
================================================================================
交易日期: 2026-03-10
情绪阶段: 启动 (置信度: 75%)
持续天数: 1天

【核心指标】
💰 赚钱效应指数: 60.47/100
📊 情绪得分: 80.23/100
📈 涨停家数: 56
📉 跌停家数: 4
💥 炸板率: 6.67%
🔥 最高连板: 0天

【阶段分析】
涨停家数56家,涨跌比14.00,连板高度开始回升,市场情绪逐步回暖

【风险提示】
市场情绪回暖,可适度参与,注意板块轮动

【市场特征】
- 涨停潮
- 极强赚钱效应
================================================================================
```

### 游资动向报告
```
【机构净买入TOP3】
1. 股票A (000001)
   机构数: 3家
   净买入: 2.35亿

2. 股票B (600519)
   机构数: 5家
   净买入: 1.87亿

【一线游资打板TOP5】
1. 股票C (300750) - 涨停
   游资数: 2个
   合计买入: 5600万
   席位: [溧阳路] [顺德大良]

2. 股票D (002415)
   游资数: 1个
   买入: 3200万
   席位: [成都北一环]

【游资活跃度榜（近30天）】
1. 中信上海溧阳路
   上榜次数: 15次
   活跃度: 95.2分

2. 国泰顺德大良
   上榜次数: 12次
   活跃度: 88.7分
```

## API接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sentiment/cycle/current` | GET | 获取当前情绪周期 |
| `/api/sentiment/cycle/trend?days=30` | GET | 获取趋势数据 |
| `/api/sentiment/cycle/calculate?date=YYYY-MM-DD` | POST | 计算情绪周期 |
| `/api/sentiment/hot-money/institution-top` | GET | 机构排行 |
| `/api/sentiment/hot-money/top-tier-limit-up` | GET | 游资打板排行 |
| `/api/sentiment/hot-money/activity-ranking` | GET | 游资活跃度排行 |

## 前端页面

访问Admin管理后台：
- 路径: `http://localhost:3002/sentiment-cycle`
- 菜单: 市场情绪 → 情绪周期

功能：
- ✅ 实时查看情绪周期阶段
- ✅ 一键计算和刷新数据
- ✅ 查看机构动向
- ✅ 查看游资打板排行
- ✅ 查看游资活跃度榜单

## 数据库表结构

### 主要表
1. **market_sentiment_cycle** - 情绪周期记录
2. **hot_money_seats** - 游资席位字典
3. **hot_money_operations** - 游资操作记录

### 视图
- **daily_sentiment_cycle_summary** - 每日摘要
- **hot_money_activity_ranking** - 活跃度排行

## 常见问题

### Q1: 显示"暂无情绪周期数据"
**原因**: 数据库没有情绪周期计算结果

**解决**:
1. 确保有市场情绪基础数据
2. 点击"计算周期"按钮或调用API

### Q2: 计算失败
**原因**: 缺少涨停板池或龙虎榜数据

**解决**:
```bash
# 同步情绪数据
curl -X POST http://localhost:8000/api/sentiment/sync

# 等待同步完成后，再计算周期
curl -X POST "http://localhost:8000/api/sentiment/cycle/calculate?date=$(date +%Y-%m-%d)"
```

### Q3: 游资数据为空
**原因**: 龙虎榜数据未分类

**解决**: 系统会自动根据游资字典进行分类，确保龙虎榜数据已同步

## 相关文档

- [SENTIMENT_CYCLE_MODULE.md](../../../docs/SENTIMENT_CYCLE_MODULE.md) - 技术文档
- [06_sentiment_cycle_schema.sql](../../../db_init/06_sentiment_cycle_schema.sql) - 数据库表结构
- [sentiment_cycle_service.py](../../../backend/app/services/sentiment_cycle_service.py) - 服务层代码

## 技术架构

```
Frontend (Next.js)
    ↓
API Layer (FastAPI)
    ↓
Service Layer (sentiment_cycle_service.py)
    ↓
Core Engine
    ├─ SentimentCycleCalculator (周期计算)
    ├─ HotMoneyClassifier (游资分类)
    └─ SentimentAnalyzer (综合分析)
    ↓
Database (TimescaleDB)
```

## 性能指标

- 单次计算耗时: < 2秒
- 数据查询: < 500ms
- 支持并发: 10+ 请求/秒

## 最佳实践

1. **每日自动计算**: 配置定时任务在17:30后自动计算
2. **数据验证**: 计算前确保基础数据完整
3. **趋势分析**: 结合近30天趋势判断市场方向
4. **游资跟踪**: 关注一线游资的操作方向
