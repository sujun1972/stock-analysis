# 市场情绪AI分析模块 - 使用指南

## 📖 模块概述

市场情绪AI分析模块是基于LLM的盘后情绪深度分析系统，通过"四个灵魂拷问"的方式，帮助用户快速理解市场情绪、资金动向和明日操作策略。

### 核心功能

1. **【看空间】** - 最高连板分析：今日最高连板是谁？代表什么题材？空间是否被打开？
2. **【看情绪】** - 赚钱效应分析：炸板率和跌停数如何？接力资金赚钱效应如何？该进攻还是防守？
3. **【看暗流】** - 资金动向分析：顶级游资主攻哪个方向？机构在建仓什么？
4. **【明日战术】** - 操作策略：集合竞价、开盘半小时的应对策略、买入条件、止损条件

---

## 🚀 快速开始

### 1. 数据库初始化

首先需要执行数据库初始化脚本：

```bash
# 进入项目目录
cd /Volumes/MacDriver/stock-analysis

# 执行SQL脚本（需要docker环境运行）
docker-compose exec db psql -U postgres -d stock_analysis -f /docker-entrypoint-initdb.d/07_sentiment_ai_analysis_schema.sql
```

或者直接在PostgreSQL客户端中执行：
```sql
-- 连接到 stock_analysis 数据库
\c stock_analysis

-- 执行脚本
\i db_init/07_sentiment_ai_analysis_schema.sql
```

### 2. 配置AI提供商API Key

编辑服务配置文件，添加AI提供商的API Key：

```python
# backend/app/services/sentiment_ai_analysis_service.py

def _get_provider_config(self, provider: str, model: str = None) -> Dict[str, Any]:
    """获取AI提供商配置"""
    configs = {
        "deepseek": {
            "provider": "deepseek",
            "api_key": "sk-xxxxxxxxxxxxxxxx",  # 替换为你的DeepSeek API Key
            "model_name": model or "deepseek-chat",
            "max_tokens": 4000,
            "temperature": 0.7
        },
        # ... 其他配置
    }
```

**推荐使用 DeepSeek**，成本低、效果好：
- 官网：https://platform.deepseek.com/
- 每次分析成本约 ¥0.5-1元
- 支持中文，理解A股市场术语

### 3. 启动服务

```bash
# 启动后端服务（如果还没启动）
cd backend
docker-compose up -d

# 启动Celery Worker（处理异步任务）
celery -A app.celery_app worker --loglevel=info

# 启动Celery Beat（定时任务调度器）
celery -A app.celery_app beat --loglevel=info
```

---

## 💻 使用方式

### 方式1：Admin后台手动执行（推荐用于测试）

1. 访问Admin后台：http://localhost:3002

2. 登录后，点击左侧菜单：**市场情绪 -> AI分析**

3. 在控制面板中：
   - 选择分析日期
   - 选择AI提供商（推荐DeepSeek）
   - 点击"生成分析"按钮

4. 等待AI生成（约5-10秒），刷新查看结果

5. 查看四个维度的分析结果：
   - **🚀 看空间** - 最高连板和题材分析
   - **🔥 看情绪** - 赚钱效应和操作策略
   - **💰 看暗流** - 游资和机构动向
   - **📝 明日战术** - 具体操作建议

### 方式2：定时任务自动执行

系统已配置每日18:00（北京时间）自动执行AI分析任务。

查看定时任务配置：
1. Admin后台 -> 系统设置 -> 定时任务
2. 找到"sentiment.ai_analysis_18_00"任务
3. 确认任务已启用

任务执行流程：
```
17:30 - 执行数据抓取（模块1+2）
    ↓
18:00 - 自动触发AI分析
    ↓
生成四个灵魂拷问分析报告
    ↓
存储到数据库
```

### 方式3：API调用

#### 3.1 生成AI分析

```bash
curl -X POST "http://localhost:8000/api/sentiment/ai-analysis/generate?date=2026-03-10&provider=deepseek" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3.2 查询AI分析结果

```bash
curl -X GET "http://localhost:8000/api/sentiment/ai-analysis/2026-03-10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

响应示例：
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "trade_date": "2026-03-10",
    "space_analysis": {
      "max_continuous_stock": {
        "code": "000001",
        "name": "平安银行",
        "days": 7
      },
      "theme": "AI芯片+算力",
      "space_level": "超高空间",
      "analysis": "今日市场情绪极度亢奋..."
    },
    "sentiment_analysis": {
      "money_making_effect": "超强",
      "strategy": "激进进攻",
      "reasoning": "炸板率仅25%..."
    },
    "capital_flow_analysis": { ... },
    "tomorrow_tactics": { ... },
    "ai_provider": "deepseek",
    "tokens_used": 1523,
    "generation_time": 5.2
  }
}
```

---

## 📊 数据库表结构

### market_sentiment_ai_analysis

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| trade_date | DATE | 交易日期（唯一） |
| space_analysis | JSONB | 【看空间】分析结果 |
| sentiment_analysis | JSONB | 【看情绪】分析结果 |
| capital_flow_analysis | JSONB | 【看暗流】分析结果 |
| tomorrow_tactics | JSONB | 【明日战术】 |
| full_report | TEXT | AI返回的完整原始报告 |
| ai_provider | VARCHAR(50) | AI提供商 |
| ai_model | VARCHAR(100) | 模型名称 |
| tokens_used | INTEGER | Token消耗 |
| generation_time | NUMERIC(10,2) | 生成耗时(秒) |
| status | VARCHAR(20) | 状态（success/failed/partial） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

---

## 🔧 配置说明

### AI提供商配置

支持的AI提供商：

| 提供商 | 推荐度 | 成本 | 速度 | 中文支持 |
|--------|--------|------|------|----------|
| **DeepSeek** | ⭐⭐⭐⭐⭐ | 极低（¥0.5-1/次） | 快 | 优秀 |
| Gemini Flash | ⭐⭐⭐⭐ | 免费/低成本 | 快 | 良好 |
| GPT-4o-mini | ⭐⭐⭐ | 中等（¥2-3/次） | 中 | 良好 |

### Celery定时任务配置

在 `backend/app/celery_app.py` 中：

```python
celery_app.conf.beat_schedule = {
    'daily-sentiment-ai-analysis-18-00': {
        'task': 'sentiment.ai_analysis_18_00',
        'schedule': crontab(
            hour=10,      # UTC 10点 = 北京时间18点
            minute=0,
            day_of_week='1-5'  # 周一到周五
        ),
        'options': {
            'expires': 3600,  # 1小时后过期
        }
    },
}
```

---

## 📈 使用场景

### 场景1：每日盘后复盘

**时间**：18:00后

**操作流程**：
1. 打开Admin -> 市场情绪 -> AI分析
2. 查看当天的AI分析报告
3. 重点关注：
   - 最高连板股票和题材
   - 赚钱效应和操作策略建议
   - 游资和机构的资金方向
4. 根据"明日战术"制定第二天的操作计划

### 场景2：历史数据回溯

**操作流程**：
1. 在Admin页面选择历史日期
2. 点击"生成分析"按钮
3. 查看历史市场情绪和AI建议
4. 对比实际走势，验证AI分析的准确性

### 场景3：策略研究

**操作流程**：
1. 批量生成近30天的AI分析
2. 导出数据（通过API）
3. 统计分析：
   - AI建议"激进进攻"时的第二天表现
   - 不同空间级别下的成功率
   - 资金共振时的题材持续性

---

## ⚠️ 注意事项

### 1. API Key安全

- **不要**将API Key提交到Git仓库
- 建议使用环境变量或配置管理系统
- 定期更换API Key

### 2. 成本控制

- DeepSeek每次分析约消耗1500-2000 tokens
- 每次成本约 ¥0.5-1元
- 每月成本约 ¥10-20元（每日一次）
- 建议设置每日生成次数限制

### 3. 数据依赖

AI分析依赖以下数据：
- ✅ 大盘数据（market_sentiment_daily）
- ✅ 涨停板池（limit_up_pool）
- ✅ 情绪周期（market_sentiment_cycle）
- ✅ 龙虎榜（dragon_tiger_list）

**如果缺少数据，AI分析将失败！**

确保17:30的数据抓取任务正常执行。

### 4. AI分析质量

- AI分析结果仅供参考，不构成投资建议
- AI可能出现"幻觉"，编造不存在的股票代码
- 建议结合自己的判断和市场实际情况
- 定期检查AI分析的准确性

### 5. Prompt优化

如果AI分析质量不佳，可以调整Prompt模板：
- 编辑 `backend/app/services/sentiment_ai_analysis_service.py`
- 修改 `SOUL_QUESTIONING_PROMPT` 变量
- 添加更多示例或约束条件

---

## 🐛 故障排查

### 问题1：生成失败，提示"无情绪数据"

**原因**：17:30的数据抓取任务未执行或失败

**解决方案**：
1. 检查Celery Worker是否运行
2. 手动执行数据抓取：Admin -> 市场情绪 -> 情绪数据 -> 同步数据
3. 查看任务执行历史：Admin -> 系统设置 -> 定时任务

### 问题2：AI返回格式错误

**原因**：AI未按照要求返回JSON格式

**解决方案**：
1. 查看 `full_report` 字段，检查AI原始返回
2. 调整Prompt，强调JSON格式要求
3. 尝试更换AI提供商

### 问题3：生成超时

**原因**：AI服务响应慢或网络问题

**解决方案**：
1. 检查网络连接
2. 增加超时时间（在 `ai_service.py` 中）
3. 更换AI提供商

### 问题4：Token消耗过高

**原因**：Prompt过长或AI返回过多

**解决方案**：
1. 精简Prompt模板
2. 减少输入数据量（如只传前5个涨停股）
3. 设置 `max_tokens` 限制

---

## 📚 技术架构

### 数据流

```
模块1（数据抓取）
    ↓
模块2（情绪周期计算）
    ↓
数据存储（PostgreSQL）
    ↓
模块3（AI分析）
    ├─ 读取完整情绪数据
    ├─ 构建结构化Prompt
    ├─ 调用AI服务（DeepSeek/Gemini/OpenAI）
    ├─ 解析JSON结果
    └─ 存储分析报告
    ↓
前端展示（Admin页面）
```

### 核心文件

| 文件 | 说明 |
|------|------|
| `db_init/07_sentiment_ai_analysis_schema.sql` | 数据库表结构 |
| `backend/app/services/sentiment_ai_analysis_service.py` | AI分析服务层 |
| `backend/app/tasks/sentiment_ai_analysis_task.py` | Celery定时任务 |
| `backend/app/api/endpoints/sentiment.py` | API端点 |
| `admin/app/(dashboard)/sentiment/ai-analysis/page.tsx` | Admin前端页面 |

---

## 📞 技术支持

如有问题，请查阅：
- 项目文档：`docs/`
- API文档：http://localhost:8000/docs
- 日志文件：`backend/logs/`

或联系技术团队。

---

**祝使用愉快！📈**
