# 盘前预期管理系统 Skill

运行盘前预期管理系统的完整工作流，包括数据同步、战术获取和碰撞分析生成。

## 功能说明

盘前预期管理系统用于每日早8:00自动执行以下工作流：

1. **数据同步**：抓取隔夜外盘数据（A50、中概股、大宗商品、汇率、美股）和盘前核心新闻
2. **战术获取**：获取或生成最新的明日战术（优先当日，缺失则生成上一交易日）
3. **碰撞分析**：将昨晚计划与今晨现实进行LLM碰撞测试
4. **生成报告**：输出四维分析（宏观定调、持仓排雷、计划修正、竞价盯盘）和行动指令

## 使用场景

- 每日早8:00自动定时执行
- 手动触发测试系统功能
- 验证数据同步和分析流程

## 执行步骤

### 1. 检查服务状态

确保所有服务正常运行：
- Backend（FastAPI）
- Celery Worker
- Celery Beat
- TimescaleDB

### 2. 验证数据库表

检查必要的数据库表是否存在：
- `overnight_market_data` - 隔夜外盘数据
- `premarket_news_flash` - 盘前核心新闻
- `premarket_collision_analysis` - AI碰撞分析结果
- `market_sentiment_ai_analysis` - 明日战术（依赖）
- `market_sentiment_daily` - 市场情绪数据（依赖）

### 3. 执行数据同步

同步当日盘前数据：

```bash
docker-compose exec -T backend python -c "
from src.premarket.fetcher import PremarketDataFetcher
from src.database.connection_pool_manager import ConnectionPoolManager
import os

db_config = {
    'host': os.getenv('DATABASE_HOST', 'timescaledb'),
    'port': int(os.getenv('DATABASE_PORT', '5432')),
    'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
    'user': os.getenv('DATABASE_USER', 'stock_user'),
    'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
}

pool_manager = ConnectionPoolManager(db_config)
fetcher = PremarketDataFetcher(pool_manager)

from datetime import datetime
trade_date = datetime.now().strftime('%Y-%m-%d')

result = fetcher.sync_premarket_data(trade_date)
print(f'同步结果: {result.success}')
print(f'交易日: {result.is_trading_day}')
print(f'同步表: {result.synced_tables}')
"
```

### 4. 生成碰撞分析

执行AI碰撞分析：

```bash
docker-compose exec -T backend python -c "
import asyncio
from datetime import datetime
from app.services.premarket_analysis_service import premarket_analysis_service

async def run_analysis():
    trade_date = datetime.now().strftime('%Y-%m-%d')
    result = await premarket_analysis_service.generate_collision_analysis(
        trade_date=trade_date,
        provider='deepseek'
    )
    print(f'分析结果: {result.get(\"success\")}')
    if result.get('success'):
        print(f'行动指令: {result.get(\"action_command\", \"\")[:100]}...')

asyncio.run(run_analysis())
"
```

### 5. 查看结果

检查生成的碰撞分析：

```bash
docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis -c "
SELECT
    trade_date,
    LEFT(action_command, 100) as action_preview,
    ai_provider,
    tokens_used,
    generation_time,
    status
FROM premarket_collision_analysis
ORDER BY trade_date DESC
LIMIT 1;
"
```

## 关键文件

### Backend（Python）
- `backend/app/api/endpoints/premarket.py` - REST API端点（6个）
- `backend/app/services/premarket_analysis_service.py` - 核心分析服务
- `backend/app/tasks/premarket_tasks.py` - Celery定时任务
- `backend/app/celery_app.py` - Celery配置（含定时任务）

### Core（Python）
- `core/src/premarket/fetcher.py` - 数据抓取引擎
- `core/src/premarket/models.py` - 数据模型定义

### Database
- `db_init/08_premarket_expectation_schema.sql` - 数据库Schema

### Frontend（TypeScript/React）
- `admin/app/(dashboard)/premarket/page.tsx` - 管理页面
- `admin/types/premarket.ts` - 类型定义

## 故障排查

### 战术数据缺失

如果当日战术未生成，系统会自动：
1. 查询上一个交易日（从 `market_sentiment_daily` 表）
2. 检查上一交易日是否有战术
3. 如果没有，调用AI服务生成上一交易日的战术
4. 如果生成失败，使用默认空值

相关日志：
```
[WARNING] 2026-03-11 的战术未生成，尝试生成上一个交易日的战术
[INFO] 开始生成 2026-03-10 的明日战术...
[SUCCESS] 成功生成 2026-03-10 的明日战术
```

### 外盘数据抓取失败

部分AkShare API可能已过期，检查日志：
```bash
docker-compose logs -f backend | grep -i "premarket\|overnight"
```

常见问题：
- A50期指API变更
- 大宗商品API变更
- 新闻快讯API变更

### Celery任务未执行

检查Celery Beat配置：
```bash
docker-compose exec -T celery_beat celery -A app.celery_app inspect registered | grep premarket
```

确认定时任务：
```bash
docker-compose logs celery_beat | grep "premarket-full-workflow"
```

## API端点

盘前预期管理提供6个REST API端点：

1. `POST /api/premarket/sync` - 同步盘前数据
2. `POST /api/premarket/collision-analysis/generate` - 生成碰撞分析
3. `GET /api/premarket/collision-analysis/{date}` - 查询分析结果
4. `GET /api/premarket/overnight-data/{date}` - 查询外盘数据
5. `GET /api/premarket/news/{date}` - 查询盘前新闻
6. `GET /api/premarket/history` - 查询历史记录

前端访问地址：http://localhost:3001/premarket

## 定时任务

系统配置了每日8:00（北京时间）自动执行的定时任务：

```python
# backend/app/celery_app.py
'premarket-full-workflow-8-00': {
    'task': 'premarket.full_workflow_8_00',
    'schedule': crontab(
        hour=0,       # UTC 0点 = 北京时间 8点
        minute=0,
        day_of_week='1-5'  # 周一到周五
    ),
    'options': {'expires': 7200}
}
```

手动触发定时任务：
```bash
docker-compose exec -T celery_worker celery -A app.celery_app call premarket.full_workflow_8_00
```

## 注意事项

1. **数据依赖**：需要先有市场情绪数据（`market_sentiment_daily`）才能生成战术
2. **AI配额**：碰撞分析需要调用AI服务，确保API Key配置正确
3. **交易日判断**：系统通过情绪数据表判断交易日，自动跳过周末和节假日
4. **生成时间**：AI分析可能需要5-10秒，定时任务超时设置为2小时

## 相关文档

- `PREMARKET_IMPLEMENTATION_GUIDE.md` - 完整实施指南
- `PREMARKET_QUICK_START.md` - 快速上手指南
- `PREMARKET_COMPLETION_SUMMARY.md` - 项目总结
