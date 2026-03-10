# 情绪AI分析模块 - 修复说明

## 🐛 问题描述

之前的实现中，使用了错误的数据库连接方式：

```python
from app.core.database import get_db_connection  # ❌ 不存在的函数
```

项目实际使用的是 `ConnectionPoolManager` 进行数据库连接管理。

---

## ✅ 已修复的问题

### 1. 数据库连接方式

**修复前**：
```python
conn = get_db_connection()  # ❌ 错误
```

**修复后**：
```python
from src.database.connection_pool_manager import ConnectionPoolManager

# 获取连接池管理器
pool_manager = self._get_pool_manager()
conn = pool_manager.get_connection()

# 使用完毕后释放连接
pool_manager.release_connection(conn)
```

### 2. 数据库字段名错误

**修复的字段**：
- `limit_ratio` → `rise_fall_ratio` (limit_up_pool表)
- `change_pct` → `price_change` (dragon_tiger_list表)
- `*_change_pct` → `*_change` (market_sentiment_daily表)

### 3. AI提供商配置错误

**问题**：temperature字段类型错误（INTEGER存储70，应该是NUMERIC(3,2)存储0.7）

**修复**：
- 修改字段类型：`ALTER TABLE ai_provider_configs ALTER COLUMN temperature TYPE NUMERIC(3,2)`
- 更正所有temperature/100.0除法为float(temperature)直接转换
- 添加约束：CHECK (temperature >= 0 AND temperature <= 2)

### 4. 前端响应数据访问错误

**问题**：apiClient.get()已经返回response.data，但代码错误地再次访问.data属性

**修复**：
- `loadProviders`: 直接使用 `const data = await apiClient.get(...)`
- `loadAnalysis`: 访问 `response.code` 和 `response.data`，不是 `response.data.code`
- `handleGenerate`: 同上

### 5. AI服务方法调用错误（关键修复）

**问题**：情绪分析服务错误地调用了`AIStrategyService.generate_strategy()`，该方法用于生成策略代码，会额外解析Python代码块

**修复**：直接调用AI客户端的底层方法，跳过代码解析逻辑
```python
# 修复前（错误）
ai_result = await self.ai_service.generate_strategy(...)
# 返回: {"strategy_code": "...", "strategy_metadata": {...}}
# 这是策略代码，不是情绪分析文本！

# 修复后（正确）
client = self.ai_strategy_service.create_client(provider, provider_config)
ai_response_text, tokens_used = await client.generate_strategy(prompt)
# 返回: (纯文本, tokens数) - 直接获取AI响应文本
```

### 6. 修复的文件

| 文件 | 修复内容 |
|------|---------|
| `backend/app/services/sentiment_ai_analysis_service.py` | 数据库连接、字段名、AI调用方式 |
| `backend/app/api/endpoints/ai_strategy.py` | temperature除法错误 |
| `admin/app/(dashboard)/sentiment/ai-analysis/page.tsx` | 响应数据访问 |
| `db_init/99_fix_ai_provider_temperature.sql` | temperature字段类型修复 |

---

## 🔧 配置AI API Key

在使用前，需要配置AI提供商的API Key：

### 方法1：修改代码（临时测试）

编辑 `backend/app/services/sentiment_ai_analysis_service.py`，找到 `_get_provider_config` 方法（约第442行）：

```python
def _get_provider_config(self, provider: str, model: str = None) -> Dict[str, Any]:
    """获取AI提供商配置"""
    configs = {
        "deepseek": {
            "provider": "deepseek",
            "api_key": "sk-xxxxxxxxxxxxxxxx",  # 👈 在这里填入你的DeepSeek API Key
            "model_name": model or "deepseek-chat",
            "max_tokens": 4000,
            "temperature": 0.7
        },
        # ... 其他配置
    }
```

### 方法2：环境变量（推荐）

1. 创建 `.env` 文件：
```bash
# AI提供商配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
```

2. 修改 `_get_provider_config` 方法读取环境变量：
```python
import os

configs = {
    "deepseek": {
        "provider": "deepseek",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        # ...
    }
}
```

### 获取DeepSeek API Key

1. 访问：https://platform.deepseek.com/
2. 注册/登录账号
3. 进入"API Keys"页面
4. 创建新的API Key
5. 复制API Key（格式：`sk-xxxxxxxxxxxxxxxx`）

**成本参考**：
- 输入：¥1 / 1M tokens
- 输出：¥2 / 1M tokens
- 每次分析约消耗2000 tokens
- 每次成本约 ¥0.5-1元

---

## 🚀 快速测试

### 1. 使用测试脚本

```bash
# 进入backend容器
docker-compose exec backend bash

# 测试AI分析（使用今天日期）
python test_ai_analysis.py

# 测试指定日期
python test_ai_analysis.py 2026-03-10

# 测试指定AI提供商
python test_ai_analysis.py 2026-03-10 gemini
```

### 2. 使用Admin界面

1. 访问：http://localhost:3002
2. 登录后进入：**市场情绪 -> AI分析**
3. 选择日期和AI提供商
4. 点击"生成分析"按钮
5. 等待5-10秒，查看结果

### 3. 使用API

```bash
# 生成AI分析
curl -X POST "http://localhost:8000/api/sentiment/ai-analysis/generate?date=2026-03-10&provider=deepseek" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查询AI分析结果
curl -X GET "http://localhost:8000/api/sentiment/ai-analysis/2026-03-10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📋 前置条件检查

在生成AI分析前，确保以下数据已存在：

### 1. 检查情绪数据

```sql
-- 检查大盘数据
SELECT * FROM market_sentiment_daily WHERE trade_date = '2026-03-10';

-- 检查涨停板池
SELECT * FROM limit_up_pool WHERE trade_date = '2026-03-10';

-- 检查情绪周期
SELECT * FROM market_sentiment_cycle WHERE trade_date = '2026-03-10';

-- 检查龙虎榜
SELECT COUNT(*) FROM dragon_tiger_list WHERE trade_date = '2026-03-10';
```

### 2. 如果数据缺失

**方法A：手动同步（Admin界面）**
1. 进入：**市场情绪 -> 情绪数据**
2. 点击"同步数据"按钮

**方法B：手动同步（API）**
```bash
curl -X POST "http://localhost:8000/api/sentiment/sync?date=2026-03-10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**方法C：执行定时任务**
确保Celery Worker和Beat正在运行：
```bash
# 启动Worker
celery -A app.celery_app worker --loglevel=info

# 启动Beat（定时调度）
celery -A app.celery_app beat --loglevel=info
```

---

## 🔍 故障排查

### 问题1：ImportError: cannot import name 'get_db_connection'

**原因**：使用了错误的数据库连接方式

**解决**：已在本次修复中解决，确保使用最新代码

### 问题2：AI分析生成失败，提示"无情绪数据"

**原因**：数据库中缺少该日期的情绪数据

**解决**：先执行数据同步（参考上面"前置条件检查"）

### 问题3：AIServiceError: DeepSeek API请求失败: 401

**原因**：API Key未配置或无效

**解决**：检查API Key配置（参考"配置AI API Key"）

### 问题4：生成超时或网络错误

**原因**：网络问题或AI服务响应慢

**解决**：
1. 检查网络连接
2. 尝试其他AI提供商（gemini、openai）
3. 增加超时时间（在 `ai_service.py` 中修改 `timeout` 参数）

### 问题5：JSON解析失败

**原因**：AI返回格式不符合预期

**解决**：
1. 查看数据库 `full_report` 字段，检查AI原始返回
2. 调整Prompt模板，强化JSON格式要求
3. 更换AI提供商

---

## 📊 数据库表检查

验证AI分析表是否创建成功：

```sql
-- 检查表是否存在
SELECT * FROM information_schema.tables
WHERE table_name = 'market_sentiment_ai_analysis';

-- 检查表结构
\d market_sentiment_ai_analysis

-- 查看最新的AI分析
SELECT
    trade_date,
    ai_provider,
    status,
    tokens_used,
    generation_time,
    created_at
FROM market_sentiment_ai_analysis
ORDER BY trade_date DESC
LIMIT 5;

-- 查看具体分析结果
SELECT
    trade_date,
    space_analysis->>'space_level' as space_level,
    sentiment_analysis->>'strategy' as strategy,
    capital_flow_analysis->>'capital_consensus' as capital_consensus
FROM market_sentiment_ai_analysis
WHERE trade_date = '2026-03-10';
```

---

## 🎯 下一步行动

1. **配置API Key**：填入你的DeepSeek API Key
2. **执行数据库初始化**：运行 `07_sentiment_ai_analysis_schema.sql`
3. **同步情绪数据**：确保有数据可供分析
4. **测试AI分析**：使用测试脚本或Admin界面验证功能
5. **查看分析结果**：在Admin界面查看四个灵魂拷问的结果

---

## 📚 相关文档

- 完整使用指南：[SENTIMENT_AI_ANALYSIS_GUIDE.md](SENTIMENT_AI_ANALYSIS_GUIDE.md)
- 情绪周期模块：[SENTIMENT_CYCLE_MODULE.md](SENTIMENT_CYCLE_MODULE.md)
- AI策略生成：[../AI_STRATEGY_QUICKSTART.md](../AI_STRATEGY_QUICKSTART.md)

---

**修复完成！现在可以正常使用AI分析功能了。** 🎉
