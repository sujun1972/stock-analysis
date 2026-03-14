# AI分析功能 - 故障排查指南

## 🐛 常见问题

### 问题1：加载AI配置失败

**错误信息**：`加载AI配置失败：Cannot read properties of undefined (reading 'filter')` 或 `AI配置数据格式错误`

**可能原因**：
1. ✅ **已修复**：前端代码错误地访问了 `response.data.data` 而不是直接访问 `response.data`
2. API返回数据格式不符合预期
3. 未登录或Token过期
4. API端点返回错误

**已修复**（2026-03-10）：
- 修复了 `loadProviders`、`loadAnalysis`、`handleGenerate` 三个函数中的响应数据访问错误
- `apiClient.get()` 和 `apiClient.post()` 已经返回 `response.data`，不需要再次访问 `.data` 属性
- 修复文件：`admin/app/(dashboard)/sentiment/ai-analysis/page.tsx`

**排查步骤**：

#### 步骤1：检查浏览器控制台

打开浏览器开发者工具（F12），查看Console标签页：

```javascript
// 应该看到调试信息
AI Providers Response: { data: [...] }
```

#### 步骤2：检查是否已登录

确保你已登录Admin后台。如果Token过期，请重新登录。

#### 步骤3：手动测试API

在浏览器中打开：
```
http://localhost:8000/api/ai-strategy/providers
```

**正确的返回**应该是一个数组：
```json
[
  {
    "id": 1,
    "provider": "deepseek",
    "display_name": "DeepSeek",
    "is_active": true,
    "is_default": true,
    ...
  }
]
```

**如果返回错误**（如401 Unauthorized），说明需要认证：
- 在Admin界面重新登录
- 检查Token是否有效

#### 步骤4：检查AI配置是否存在

```bash
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "SELECT id, provider, display_name, is_active FROM ai_provider_configs;"
```

**预期输出**：
```
 id | provider | display_name  | is_active
----+----------+---------------+-----------
  1 | deepseek | DeepSeek      | t
  2 | gemini   | Google Gemini | f
```

**如果没有数据**，需要添加AI配置：
1. 访问：http://localhost:3002/settings/ai-config
2. 点击"添加AI提供商"
3. 填写配置并保存

---

### 问题2：生成AI分析失败

**错误信息**：`生成失败：...`

#### 2.1 提示"无情绪数据"但数据实际存在

**错误信息**：
```json
{
  "code": 400,
  "message": "2026-03-10 无情绪数据，请先执行数据同步"
}
```

**但是**：在"市场情绪 → 情绪数据"页面能看到该日期的数据。

**真实原因**：后端代码使用了不存在的数据库字段名（如 `limit_ratio`）

**排查方法**：
```bash
# 查看backend日志
docker-compose logs backend --tail=50 | grep -i error

# 期望看到类似错误：
# ERROR: column "limit_ratio" does not exist
```

**已修复**（2026-03-10）：
- ✅ 修正了 `limit_ratio` → `rise_fall_ratio`
- ✅ 修复文件：`backend/app/services/sentiment_ai_analysis_service.py`
- ✅ 如果仍有此问题，重启backend：`docker-compose restart backend`

#### 2.2 提示"无情绪数据"且数据确实不存在

**原因**：数据库中没有该日期的情绪数据

**解决**：
1. 进入：市场情绪 → 情绪数据
2. 点击"同步数据"
3. 等待同步完成
4. 返回AI分析页面重试

#### 2.2 DeepSeek API返回400错误："Invalid temperature value"

**错误信息**：
```json
{
  "code": 400,
  "message": "[AI_SERVICE] DeepSeek API请求失败: 400"
}
```

**Backend日志**：
```
DeepSeek API请求失败: 400 - {
  "error": {
    "message": "Invalid temperature value, the valid range of temperature is [0, 2]"
  }
}
```

**原因**：数据库中 `temperature` 字段类型错误（INTEGER），导致小数值（0.7）被存储为整数（70或1）

**已修复**（2026-03-10）：
- ✅ 修改字段类型：`INTEGER` → `NUMERIC(3,2)`
- ✅ 更正DeepSeek temperature值：`70` → `0.7`
- ✅ 添加约束：确保temperature范围在[0, 2]之间
- ✅ 迁移脚本：`db_init/99_fix_ai_provider_temperature.sql`

**如果仍有此问题**：
```sql
-- 检查temperature值
SELECT provider, temperature FROM ai_provider_configs;

-- 如果看到异常值（如70、1等），执行：
UPDATE ai_provider_configs SET temperature = 0.7;
```

#### 2.3 提示"API Key无效"或"401错误"

**原因**：AI提供商的API Key错误或未配置

**解决**：
1. 进入：系统设置 → AI配置
2. 编辑DeepSeek配置
3. 填入正确的API Key
4. 保存后重试

#### 2.4 提示"超时"或"网络错误"

**原因**：网络问题或AI服务响应慢

**解决**：
1. 检查网络连接
2. 尝试其他AI提供商
3. 增加超时时间（在AI配置页面修改）

---

### 问题3：AI提供商下拉列表为空

**现象**：下拉列表显示"暂无可用配置"

**原因**：
- 数据库中没有 `is_active = true` 的AI配置
- API请求失败

**解决**：

#### 方案A：通过Admin界面添加

1. 访问：http://localhost:3002/settings/ai-config
2. 点击"添加AI提供商"
3. 填写配置：

| 字段 | 值 |
|------|-----|
| 提供商 | deepseek |
| 显示名称 | DeepSeek |
| API Key | sk-xxxxxxxxxxxxxxxx |
| API Base URL | https://api.deepseek.com/v1 |
| 模型名称 | deepseek-chat |
| 最大Token | 4000 |
| 温度 | 0.7 |
| 超时 | 60 |
| 启用 | ✅ |
| 设为默认 | ✅ |

4. 保存
5. 刷新AI分析页面

#### 方案B：直接插入数据库

```sql
INSERT INTO ai_provider_configs (
  provider, display_name, api_key, api_base_url,
  model_name, max_tokens, temperature, is_active, is_default,
  priority, rate_limit, timeout, description
) VALUES (
  'deepseek',
  'DeepSeek',
  'sk-your-api-key-here',
  'https://api.deepseek.com/v1',
  'deepseek-chat',
  4000,
  0.7,
  true,
  true,
  100,
  10,
  60,
  'DeepSeek AI - 高性价比的中文AI模型'
);
```

---

### 问题4：生成成功但结果显示异常

**现象**：AI分析生成了，但某些字段为空或显示"暂无数据"

**可能原因**：
1. AI返回的JSON格式不符合预期
2. AI没有按要求返回完整的四个维度

**排查**：

#### 查看原始报告

```sql
SELECT full_report FROM market_sentiment_ai_analysis
WHERE trade_date = '2026-03-10';
```

检查AI返回的原始文本，看是否包含完整的JSON。

#### 查看解析状态

```sql
SELECT
  trade_date,
  status,
  space_analysis IS NOT NULL as has_space,
  sentiment_analysis IS NOT NULL as has_sentiment,
  capital_flow_analysis IS NOT NULL as has_capital,
  tomorrow_tactics IS NOT NULL as has_tactics
FROM market_sentiment_ai_analysis
WHERE trade_date = '2026-03-10';
```

如果某个字段为false，说明该部分没有成功解析。

**解决**：
1. 调整Prompt模板，强化JSON格式要求
2. 更换AI提供商（如Claude、GPT-4）
3. 重新生成分析

---

## 🔍 调试技巧

### 1. 查看浏览器控制台

打开F12开发者工具，查看：
- **Console**: JavaScript错误和调试信息
- **Network**: API请求和响应
- **Application**: LocalStorage中的Token

### 2. 查看Backend日志

```bash
# 实时查看backend日志
docker-compose logs -f backend

# 查看最近100行
docker-compose logs backend --tail=100
```

关键日志：
- `已加载AI配置: deepseek / deepseek-chat` - 配置加载成功
- `开始生成 xxx 的AI情绪分析...` - 开始生成
- `xxx AI分析生成成功` - 生成成功

### 3. 测试API端点

```bash
# 测试获取AI提供商列表
curl http://localhost:8000/api/ai-strategy/providers

# 测试生成AI分析（需要认证）
curl -X POST "http://localhost:8000/api/sentiment/ai-analysis/generate?date=2026-03-10&provider=deepseek" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 测试查询AI分析结果
curl "http://localhost:8000/api/sentiment/ai-analysis/2026-03-10"
```

### 4. 检查数据库

```bash
# 进入数据库
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 检查AI配置
SELECT * FROM ai_provider_configs WHERE is_active = true;

# 检查情绪数据
SELECT * FROM market_sentiment_daily WHERE trade_date = '2026-03-10';

# 检查AI分析结果
SELECT * FROM market_sentiment_ai_analysis WHERE trade_date = '2026-03-10';
```

---

## 📋 检查清单

在使用AI分析功能前，请确认：

- [ ] ✅ 已登录Admin后台
- [ ] ✅ 在"系统设置 → AI配置"中已添加至少一个AI提供商
- [ ] ✅ AI提供商的API Key有效
- [ ] ✅ 该日期的情绪数据已同步（market_sentiment_daily, limit_up_pool等）
- [ ] ✅ Backend服务正常运行
- [ ] ✅ 网络连接正常

---

## 🚑 快速修复

### 完全重置AI配置

如果一切都不工作，尝试重置：

```bash
# 1. 删除现有AI配置
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "DELETE FROM ai_provider_configs;"

# 2. 插入默认配置
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "INSERT INTO ai_provider_configs (provider, display_name, api_key, api_base_url, model_name, max_tokens, temperature, is_active, is_default, priority, rate_limit, timeout, description)
   VALUES ('deepseek', 'DeepSeek', 'sk-your-key', 'https://api.deepseek.com/v1', 'deepseek-chat', 4000, 0.7, true, true, 100, 10, 60, 'DeepSeek AI');"

# 3. 重启backend
docker-compose restart backend

# 4. 刷新Admin页面
```

### 清除前端缓存

```bash
# 在浏览器中
- 打开F12开发者工具
- 右键点击刷新按钮
- 选择"清空缓存并硬性重新加载"
```

---

## 📞 寻求帮助

如果以上方法都无法解决问题，请提供以下信息：

1. **错误信息截图**（浏览器控制台）
2. **Backend日志**（最后100行）
3. **数据库检查结果**：
   ```bash
   docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
     "SELECT COUNT(*) FROM ai_provider_configs WHERE is_active = true;"
   ```
4. **浏览器和版本**（如Chrome 120）
5. **操作系统**（如macOS 14.1）

---

### 问题5：保存AI配置时出现500错误

**错误类型**：多种可能的错误情况

#### 5.1 温度值(Temperature)数据库溢出错误

**错误现象**：保存AI配置时后端返回500错误

**Backend日志**：
```
numeric field overflow: A field with precision 3, scale 2 must round to an absolute value less than 10^1
```

**根本原因**：
- 数据库字段定义为 `NUMERIC(3,2)`（支持0.00-9.99）
- 代码错误地将温度值乘以100（0.7 → 70）再存入数据库
- 70超过了字段的最大值9.99，导致溢出

**已修复**（2026-03-12）：
- ✅ 移除了 `ai_config_repository.py` 中的温度值转换（乘100操作）
- ✅ 直接存储0-1范围的温度值，数据库字段足以支持
- ✅ 修复文件：`backend/app/repositories/ai_config_repository.py`（第78-79行、104-106行）

**如果仍有此问题**：
```bash
# 检查数据库中的温度值
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "SELECT provider, temperature FROM ai_provider_configs;"

# 如果看到超出范围的值（如70），手动修正：
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "UPDATE ai_provider_configs SET temperature = 0.7 WHERE temperature > 2;"

# 重启backend
docker-compose restart backend
```

#### 5.2 错误日志记录导致KeyError

**错误现象**：保存AI配置失败，日志显示KeyError

**Backend日志**：
```
KeyError: "'display_name'"
```

**根本原因**：
- 数据库错误消息中包含大括号（如SQL HINT中的 `{display_name}`）
- loguru的f-string格式化将大括号误认为是格式化占位符
- 导致在记录日志时抛出KeyError

**已修复**（2026-03-12）：
- ✅ 在记录错误日志前，先转义错误消息中的花括号：`raw_error.replace("{", "{{").replace("}", "}}")`
- ✅ 修复文件：`backend/app/api/error_handler.py`（第142-144行、228-230行）
- ✅ 同时修复了异步和同步版本的错误处理装饰器

**技术细节**：
```python
# 修复前（会导致KeyError）
logger.error(f"服务器错误 [ID:{error_id}]: {raw_error}", exc_info=True)

# 修复后（安全记录含大括号的错误）
safe_raw_error = raw_error.replace("{", "{{").replace("}", "}}")
logger.error(f"服务器错误 [ID:{error_id}]: {safe_raw_error}", exc_info=True)
```

#### 5.3 更新配置时返回旧的温度值

**错误现象**：更新AI配置后，API返回的温度值仍然是旧值

**根本原因**：
- 代码使用了更新前的 `config.temperature` 而不是更新后的 `updated_config.temperature`

**已修复**（2026-03-12）：
- ✅ 修正响应数据使用 `updated_config.temperature`
- ✅ 修复文件：`backend/app/api/endpoints/ai_strategy.py`（第250行）

---

### 问题6：LLM调用日志无法记录（外键约束错误）

**错误现象**：AI分析生成成功，但LLM调用日志表没有记录

**Backend日志**：
```
Foreign key associated with column 'llm_call_logs.prompt_template_id' could not find table 'llm_prompt_templates'
```

**根本原因**：
- `llm_call_log.py` 和 `llm_prompt_template.py` 使用了不同的 `declarative_base()` 实例
- SQLAlchemy要求外键关联的两个模型必须使用同一个Base实例
- 外键约束导致表创建失败

**已修复**（2026-03-12）：
- ✅ 临时移除了 `prompt_template_id` 的外键约束，保留为普通Integer字段
- ✅ 添加了TODO注释：统一所有模型使用同一个Base实例后再添加外键约束
- ✅ 修复文件：`backend/app/models/llm_call_log.py`（第43-46行）

**技术细节**：
```python
# 修复前（会导致表创建失败）
prompt_template_id = Column(Integer, ForeignKey("llm_prompt_templates.id"), index=True)

# 修复后（临时移除外键约束）
# 注意：由于使用了不同的declarative_base()，暂时移除ForeignKey约束
# TODO: 统一所有模型使用同一个Base实例后再添加外键约束
prompt_template_id = Column(Integer, index=True)
```

**长期解决方案**（TODO）：
1. 创建统一的 `Base` 实例在 `app/models/base.py`
2. 所有模型文件导入并使用同一个Base
3. 恢复外键约束以保证数据完整性

**如果仍有此问题**：
```bash
# 检查LLM日志表是否存在
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "\d llm_call_logs"

# 如果表不存在或结构有问题，重建：
docker-compose restart backend

# 验证日志记录功能
# 生成一次AI分析，然后检查：
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "SELECT COUNT(*) FROM llm_call_logs;"
```

---

**更新时间**：2026-03-12
**适用版本**：v2.0+

---

### 问题5：AI分析任务提交后无法在异步任务管理中追踪

**错误现象**（2026-03-14）：
- 点击"生成分析"按钮后，显示toast提示
- 任务不出现在"异步任务管理"列表中
- 前端轮询一直返回 `PENDING` 状态
- 用户感觉"没有之后了"

**根本原因**：
1. **后端任务类型识别错误**：`sentiment.ai_analysis_18_00` 被识别为 `sentiment` 类型而非 `ai_analysis` 类型
2. **任务显示名称缺失**：未在映射表中添加AI分析任务的显示名称
3. **前端参数传递不完整**：`addTaskToQueue` 未传递完整的任务类型参数
4. **Celery任务状态检查错误**：`PENDING` 状态误判导致重复提交被拒绝
5. **任务进度未更新**：任务执行过程中没有更新中间状态

**已修复**（2026-03-14）：

#### 修复1：后端任务类型识别
**文件**：`backend/app/api/endpoints/sentiment.py` (Line 1001-1005)
```python
# 修复前
elif task_name.startswith('sentiment.'):
    return 'sentiment'  # ❌ 所有sentiment任务都是'sentiment'类型

# 修复后
elif task_name.startswith('sentiment.'):
    # 细分 sentiment 任务类型
    if 'ai_analysis' in task_name:
        return 'ai_analysis'  # ✅ 正确识别AI分析任务
    return 'sentiment'
```

#### 修复2：添加任务显示名称映射
**文件**：`backend/app/api/endpoints/sentiment.py` (Line 1033)
```python
task_name_mapping = {
    # ... 其他映射
    "sentiment.ai_analysis_18_00": "情绪AI分析（定时任务）",  # ✅ 新增
}
```

#### 修复3：前端完整传递任务参数
**文件**：`admin/app/(dashboard)/sentiment/ai-analysis/page.tsx` (Line 140-145)
```typescript
// 修复前
addTaskToQueue(newTaskId, `AI分析生成（${dateStr}）`)

// 修复后
addTaskToQueue(
  newTaskId,
  `sentiment.ai_analysis_18_00`,           // ✅ 任务名称
  `AI分析生成（${dateStr} - ${providerDisplay}）`,  // ✅ 显示名称
  'ai_analysis'                            // ✅ 任务类型
)
```

#### 修复4：优化Celery任务状态检查
**文件**：`backend/app/api/endpoints/sentiment.py` (Line 876-892)
```python
# 修复前：PENDING是默认状态，会误判
if existing_task.state in ['PENDING', 'STARTED']:

# 修复后：只检查真正运行中的状态
if existing_task.state in ['STARTED', 'PROGRESS', 'RETRY']:
    return 409  # 任务确实在执行中

# 如果任务已完成，清除旧结果
if existing_task.state in ['SUCCESS', 'FAILURE']:
    existing_task.forget()  # 允许使用相同ID重新提交
```

#### 修复5：添加任务进度更新
**文件**：`backend/app/tasks/sentiment_ai_analysis_task.py` (Line 57-72)
```python
# 更新任务状态为STARTED
self.update_state(
    state='STARTED',
    meta={'message': f'开始生成{date}的AI分析', 'progress': 10}
)

# 更新进度：正在调用AI服务
self.update_state(
    state='PROGRESS',
    meta={'message': f'正在调用{provider} AI服务生成分析', 'progress': 50}
)
```

#### 修复6：Celery结果持久化配置
**文件**：`backend/app/celery_app.py` (Line 37-39)
```python
# 结果持久化配置
result_backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
result_persistent=True,  # 持久化任务结果
```

**修复效果**：
- ✅ 任务正确出现在"异步任务管理"列表中
- ✅ 任务类型显示为"AI分析"（蓝色标签）
- ✅ 显示名称友好：`AI分析生成（2026-03-13 - DeepSeek）`
- ✅ 实时进度追踪：STARTED → PROGRESS → SUCCESS
- ✅ 任务完成后全局toast通知
- ✅ 完整的异步任务体验

**验证步骤**：
```bash
# 1. 提交AI分析任务
# 访问：http://localhost:3000/sentiment/ai-analysis
# 选择日期和AI提供商，点击"生成分析"

# 2. 检查异步任务管理
# 访问：http://localhost:3000/tasks
# 应该看到任务，类型为"ai_analysis"，蓝色标签

# 3. 验证任务结果
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c \
  "SELECT trade_date, ai_provider, tokens_used, status FROM market_sentiment_ai_analysis ORDER BY created_at DESC LIMIT 3;"
```

**涉及文件**：
- `backend/app/api/endpoints/sentiment.py`
- `backend/app/tasks/sentiment_ai_analysis_task.py`
- `backend/app/celery_app.py`
- `admin/app/(dashboard)/sentiment/ai-analysis/page.tsx`

---

**更新时间**：2026-03-14
**适用版本**：v2.1+
