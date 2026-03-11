# 盘前预期管理系统

**版本**: 1.0.0
**状态**: ✅ 已部署
**最后更新**: 2026-03-11

---

## 系统概述

盘前预期管理系统用于每日早8:00自动执行"计划碰撞测试"，将昨晚的明日战术与今晨的市场环境进行对比，生成实时的早盘行动指令。

### 核心功能

1. **数据同步**
   - 隔夜外盘数据：A50期指、中概股、大宗商品、汇率、美股
   - 盘前核心新闻：22:00-8:00财联社/金十快讯，关键词过滤

2. **战术获取**
   - 优先读取当日战术（如果已生成）
   - 如未生成，自动生成上一个交易日的战术
   - 自动跳过周末和节假日

3. **碰撞分析**
   - 调用LLM进行四维分析：
     - 宏观定调（高开/低开预判）
     - 持仓排雷（风险股票提示）
     - 计划修正（取消买入/提前止损）
     - 竞价盯盘（9:15-9:25核心标的）
   - 生成200字精华行动指令

4. **自动执行**
   - 每日早8:00（北京时间）自动运行
   - 只在交易日执行
   - 完整工作流：同步数据 → 获取战术 → 生成分析

---

## 快速开始

### 1. 数据库初始化

```bash
docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis \
  -f /docker-entrypoint-initdb.d/08_premarket_expectation_schema.sql
```

### 2. 重启服务

```bash
docker-compose restart backend celery_worker celery_beat
```

### 3. 访问前端

```
http://localhost:3001/premarket
```

### 4. 手动测试

#### 同步数据
```bash
curl -X POST "http://localhost:8000/api/premarket/sync?date=2026-03-11" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 生成分析
```bash
curl -X POST "http://localhost:8000/api/premarket/collision-analysis/generate?date=2026-03-11" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 查询结果
```bash
curl -X GET "http://localhost:8000/api/premarket/collision-analysis/2026-03-11" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 架构设计

### 目录结构

```
stock-analysis/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/premarket.py          # REST API（6个端点）
│   │   ├── services/premarket_analysis_service.py  # 核心分析服务
│   │   ├── tasks/premarket_tasks.py            # Celery任务
│   │   └── celery_app.py                       # 定时任务配置
├── core/
│   └── src/premarket/
│       ├── fetcher.py                          # 数据抓取引擎
│       └── models.py                           # 数据模型
├── admin/
│   ├── app/(dashboard)/premarket/page.tsx      # React管理页面
│   └── types/premarket.ts                      # TypeScript类型
└── db_init/
    └── 08_premarket_expectation_schema.sql     # 数据库Schema
```

### 数据表

1. **overnight_market_data** - 隔夜外盘数据
   - A50期指、中概股、大宗商品、汇率、美股
   - 每日早晨抓取一次

2. **premarket_news_flash** - 盘前核心新闻
   - 22:00-8:00时间窗口
   - 关键词过滤（25+关键词）
   - 重要性分级（critical/high/medium）

3. **premarket_collision_analysis** - AI碰撞分析
   - 四维分析结果（JSONB）
   - 极简行动指令（TEXT）
   - AI元数据（provider, model, tokens）

### API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/premarket/sync` | POST | 同步盘前数据 |
| `/api/premarket/collision-analysis/generate` | POST | 生成碰撞分析 |
| `/api/premarket/collision-analysis/{date}` | GET | 查询分析结果 |
| `/api/premarket/overnight-data/{date}` | GET | 查询外盘数据 |
| `/api/premarket/news/{date}` | GET | 查询盘前新闻 |
| `/api/premarket/history` | GET | 查询历史记录 |

---

## 关键特性

### 智能战术获取

系统实现了智能的战术获取逻辑：

```python
async def _get_or_generate_tactics(trade_date):
    # 1. 优先读取当日战术
    tactics = fetch_tactics_by_date(trade_date)
    if tactics:
        return tactics

    # 2. 获取上一个交易日
    prev_date = get_previous_trade_date(trade_date)

    # 3. 尝试读取上一交易日战术
    tactics = fetch_tactics_by_date(prev_date)
    if tactics:
        return tactics

    # 4. 生成上一交易日战术
    trigger_tactics_generation(prev_date)
    return fetch_tactics_by_date(prev_date)
```

**关键点**：
- ✅ 不简单回溯历史数据
- ✅ 主动生成缺失的战术
- ✅ 确保使用上一交易日战术（而非更早的）
- ✅ 通过`market_sentiment_daily`查询交易日（自动跳过周末）

### 定时任务配置

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

---

## 常见问题

### Q: 战术数据缺失怎么办？

**A**: 系统会自动处理：
1. 查询上一个交易日
2. 尝试读取上一交易日战术
3. 如果不存在，调用AI服务生成
4. 如果生成失败，使用默认空值

### Q: 为什么某些外盘数据显示为0？

**A**: 部分AkShare API已过期，系统返回默认值0。需要后续更新数据源。

### Q: 定时任务没有执行怎么办？

**A**: 检查步骤：
1. 确认Celery Beat运行中：`docker-compose ps celery_beat`
2. 查看日志：`docker-compose logs celery_beat | grep premarket`
3. 手动触发测试：`celery -A app.celery_app call premarket.full_workflow_8_00`

### Q: 如何修改定时任务时间？

**A**: 编辑`backend/app/celery_app.py`，修改crontab参数后重启Celery Beat。

---

## 技术栈

- **Backend**: Python 3.11, FastAPI
- **Task Queue**: Celery + Celery Beat + Redis
- **Database**: TimescaleDB (PostgreSQL 16)
- **Data Source**: AkShare（金融数据接口）
- **LLM**: DeepSeek/Gemini/OpenAI
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS

---

## 性能指标

- **数据同步**: 10-15秒（取决于网络）
- **AI分析**: 5-10秒（取决于LLM响应速度）
- **完整工作流**: 15-30秒
- **Token消耗**: 约2000-3000 tokens/次

---

## 后续优化方向

1. **数据源多样化**: 增加备用数据源，提高可靠性
2. **缓存机制**: 对外部API调用结果进行短期缓存
3. **错误重试**: 实现指数退避重试策略
4. **AI Prompt优化**: 根据实际使用效果迭代Prompt
5. **前端增强**: 添加数据可视化图表

---

## 相关文档

- **完整实施指南**: `PREMARKET_IMPLEMENTATION_GUIDE.md`
- **快速上手**: `PREMARKET_QUICK_START.md`
- **项目总结**: `PREMARKET_COMPLETION_SUMMARY.md`
- **Skill文档**: `.claude/skills/premarket-analysis/skill.md`

---

**维护者**: AI Strategy Team
**联系方式**: 通过项目Issue反馈问题
