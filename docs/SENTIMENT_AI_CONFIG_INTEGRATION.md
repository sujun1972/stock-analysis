# 情绪AI分析 - 集成现有AI配置系统

## 📋 更新说明

AI分析功能现已集成到现有的AI配置管理系统，不再需要在代码中硬编码API Key。

## ✅ 主要改进

### 1. 从数据库读取AI配置

**修改前**（硬编码）：
```python
configs = {
    "deepseek": {
        "api_key": "your-deepseek-api-key",  # ❌ 硬编码
        ...
    }
}
```

**修改后**（动态读取）：
```python
# 从数据库 ai_provider_configs 表读取配置
cursor.execute("""
    SELECT provider, api_key, api_base_url, model_name, ...
    FROM ai_provider_configs
    WHERE provider = %s AND is_active = true
""", (provider,))
```

### 2. Admin页面集成

- ✅ 自动加载可用的AI提供商列表
- ✅ 显示默认提供商
- ✅ 显示模型名称
- ✅ 如果没有配置，提示用户去设置

### 3. 支持默认配置

如果不指定provider参数，自动使用 `is_default = true` 的配置。

## 🚀 使用方式

### 第一步：配置AI提供商

1. 访问Admin后台：http://localhost:3002
2. 进入：**系统设置 → AI配置**
3. 点击"添加AI提供商"
4. 填写配置信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| **提供商** | AI提供商标识 | deepseek |
| **显示名称** | 界面显示的名称 | DeepSeek |
| **API Key** | API密钥 | sk-xxxxxxxxxxxxxxxx |
| **API Base URL** | API基础地址 | https://api.deepseek.com/v1 |
| **模型名称** | 使用的模型 | deepseek-chat |
| **最大Token数** | 单次请求最大Token | 4000 |
| **温度** | 生成随机性（0-1） | 0.7 |
| **超时时间** | 请求超时（秒） | 60 |
| **启用** | 是否启用 | ✅ |
| **设为默认** | 是否为默认 | ✅ |

5. 点击"保存"

### 第二步：使用AI分析

1. 进入：**市场情绪 → AI分析**
2. 选择日期
3. 选择AI提供商（下拉列表自动加载已配置的提供商）
4. 点击"生成分析"

## 📊 数据库表结构

### ai_provider_configs

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| provider | VARCHAR(50) | 提供商标识（deepseek/gemini/openai） |
| display_name | VARCHAR(100) | 显示名称 |
| api_key | TEXT | API密钥（加密存储） |
| api_base_url | VARCHAR(255) | API基础URL |
| model_name | VARCHAR(100) | 模型名称 |
| max_tokens | INTEGER | 最大Token数 |
| temperature | NUMERIC(3,2) | 温度参数 |
| is_active | BOOLEAN | 是否启用 |
| is_default | BOOLEAN | 是否为默认 |
| priority | INTEGER | 优先级 |
| rate_limit | INTEGER | 速率限制 |
| timeout | INTEGER | 超时时间（秒） |
| description | TEXT | 描述 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 🔧 配置示例

### DeepSeek配置（推荐）

```json
{
  "provider": "deepseek",
  "display_name": "DeepSeek",
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "api_base_url": "https://api.deepseek.com/v1",
  "model_name": "deepseek-chat",
  "max_tokens": 4000,
  "temperature": 0.7,
  "timeout": 60,
  "is_active": true,
  "is_default": true,
  "priority": 100
}
```

**成本**：约 ¥0.5-1元/次

### Gemini配置（免费）

```json
{
  "provider": "gemini",
  "display_name": "Google Gemini",
  "api_key": "AIza...",
  "api_base_url": "https://generativelanguage.googleapis.com/v1beta",
  "model_name": "gemini-1.5-flash",
  "max_tokens": 4000,
  "temperature": 0.7,
  "timeout": 60,
  "is_active": true,
  "is_default": false,
  "priority": 90
}
```

**成本**：免费（有额度限制）

### OpenAI配置

```json
{
  "provider": "openai",
  "display_name": "OpenAI GPT-4o-mini",
  "api_key": "sk-proj-...",
  "api_base_url": "https://api.openai.com/v1",
  "model_name": "gpt-4o-mini",
  "max_tokens": 4000,
  "temperature": 0.7,
  "timeout": 60,
  "is_active": true,
  "is_default": false,
  "priority": 80
}
```

**成本**：约 ¥2-3元/次

## 💡 优势

### 1. 集中管理

- ✅ 所有AI配置统一在数据库管理
- ✅ 无需修改代码即可更换AI提供商
- ✅ 支持多个提供商配置，可以切换

### 2. 安全性

- ✅ API Key存储在数据库，不暴露在代码中
- ✅ 支持权限控制（只有管理员可配置）
- ✅ 便于API Key轮换

### 3. 灵活性

- ✅ 支持设置默认提供商
- ✅ 支持多个配置并存
- ✅ 可以根据需要启用/禁用某个配置

### 4. 用户友好

- ✅ Admin界面可视化配置
- ✅ 自动验证配置有效性
- ✅ 显示配置状态（启用/禁用/默认）

## 🔄 迁移指南

如果你之前硬编码了API Key，现在需要迁移到数据库：

### 步骤1：导出现有配置

记录你现有的API Key和配置参数。

### 步骤2：在Admin中添加配置

访问 **系统设置 → AI配置**，添加你的AI提供商配置。

### 步骤3：验证配置

在 **市场情绪 → AI分析** 页面，测试是否能正常加载配置并生成分析。

### 步骤4：删除硬编码（可选）

修改后的代码已经不再使用硬编码，但保留了环境变量作为降级方案：

```python
# 如果数据库查询失败，会使用环境变量
"api_key": os.getenv("DEEPSEEK_API_KEY", "")
```

## 🔍 故障排查

### 问题1：下拉列表为空

**原因**：数据库中没有active的AI配置

**解决**：
1. 检查 `ai_provider_configs` 表是否有数据
2. 确保至少有一条 `is_active = true` 的记录
3. 在Admin界面添加AI配置

### 问题2：生成失败，提示API Key无效

**原因**：配置的API Key错误或已过期

**解决**：
1. 在Admin界面编辑AI配置
2. 更新正确的API Key
3. 保存后重试

### 问题3：无法加载AI配置列表

**原因**：API端点 `/api/ai-strategy/providers` 不可用

**解决**：
1. 检查backend服务是否正常运行
2. 查看backend日志：`docker-compose logs backend`
3. 验证数据库连接

## 📝 API端点

### 获取AI提供商列表

```bash
GET /api/ai-strategy/providers

Response:
[
  {
    "id": 1,
    "provider": "deepseek",
    "display_name": "DeepSeek",
    "is_active": true,
    "is_default": true,
    "model_name": "deepseek-chat",
    ...
  }
]
```

### 生成AI分析（使用数据库配置）

```bash
POST /api/sentiment/ai-analysis/generate?date=2026-03-10&provider=deepseek

# provider参数可选，不传则使用默认配置
POST /api/sentiment/ai-analysis/generate?date=2026-03-10
```

## 🎯 最佳实践

### 1. 设置默认提供商

建议设置一个稳定、成本低的提供商作为默认（如DeepSeek）。

### 2. 配置多个提供商

配置多个AI提供商作为备选，如果主要提供商失败，可以切换。

### 3. 定期检查API额度

监控API使用情况，避免超出配额。

### 4. 成本控制

- 使用DeepSeek等低成本提供商
- 设置合理的 `max_tokens` 限制
- 避免频繁重复生成

### 5. 安全性

- 定期更换API Key
- 限制Admin访问权限
- 不要在日志中打印API Key

## 📚 相关文档

- [完整使用指南](SENTIMENT_AI_ANALYSIS_GUIDE.md)
- [字段修复说明](SENTIMENT_AI_ANALYSIS_FIX.md)
- [快速修复总结](../QUICKFIX_SUMMARY.md)

---

**更新时间**：2026-03-10
**版本**：v2.0 - 集成AI配置管理系统
