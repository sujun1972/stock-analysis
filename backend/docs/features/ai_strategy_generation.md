# AI策略生成 API 文档

## 概述

AI策略生成功能允许用户通过后端API直接调用AI（如DeepSeek、Gemini、OpenAI等）生成量化交易策略代码。

## 功能特性

- ✅ 支持多个AI提供商（DeepSeek、Gemini、OpenAI）
- ✅ 可配置默认AI提供商
- ✅ API密钥安全存储和脱敏显示
- ✅ 支持自定义提示词模板
- ✅ 自动解析策略代码和元信息
- ✅ 完整的错误处理和日志记录

## API端点

### 1. AI策略生成

**POST** `/api/ai-strategy/generate`

使用AI生成策略代码。

#### 请求体

```json
{
  "strategy_requirement": "策略需求描述（必填）",
  "provider": "deepseek",  // 可选，不指定则使用默认
  "use_custom_prompt": false,  // 可选，是否使用自定义提示词
  "custom_prompt_template": "自定义提示词模板"  // 可选
}
```

#### 响应示例

```json
{
  "success": true,
  "strategy_code": "from typing import Optional...",
  "strategy_metadata": {
    "strategy_id": "simple_ma_crossover",
    "display_name": "简单均线交叉策略",
    "class_name": "SimpleMACrossoverStrategy",
    "category": "trend_following",
    "description": "基于MA5和MA20均线交叉的趋势跟踪策略",
    "tags": ["趋势跟踪", "均线", "技术指标"]
  },
  "provider_used": "deepseek",
  "tokens_used": 3600,
  "generation_time": 80.58
}
```

### 2. 获取AI提供商列表

**GET** `/api/ai-strategy/providers`

获取所有配置的AI提供商。

#### 响应示例

```json
[
  {
    "id": 1,
    "provider": "deepseek",
    "display_name": "DeepSeek",
    "api_key": "sk-4***************************79fd",  // 已脱敏
    "api_base_url": "https://api.deepseek.com/v1",
    "model_name": "deepseek-chat",
    "max_tokens": 8000,
    "temperature": 0.7,
    "is_active": true,
    "is_default": true,
    "priority": 100,
    "rate_limit": 10,
    "timeout": 60,
    "description": "DeepSeek AI - 高性价比的中文AI模型",
    "created_at": "2026-03-01T10:55:19.777034",
    "updated_at": "2026-03-01T10:55:19.777035"
  }
]
```

### 3. 获取指定AI提供商

**GET** `/api/ai-strategy/providers/{provider}`

获取指定AI提供商的配置。

### 4. 创建AI提供商配置

**POST** `/api/ai-strategy/providers`

创建新的AI提供商配置。

#### 请求体

```json
{
  "provider": "openai",
  "display_name": "OpenAI GPT-4",
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "api_base_url": "https://api.openai.com/v1",
  "model_name": "gpt-4o",
  "max_tokens": 8000,
  "temperature": 0.7,
  "is_active": true,
  "is_default": false,
  "priority": 80,
  "rate_limit": 10,
  "timeout": 60,
  "description": "OpenAI GPT-4"
}
```

### 5. 更新AI提供商配置

**PUT** `/api/ai-strategy/providers/{provider}`

更新指定AI提供商的配置。

#### 请求体（所有字段可选）

```json
{
  "api_key": "新的API密钥",
  "is_active": true,
  "is_default": false
}
```

### 6. 删除AI提供商配置

**DELETE** `/api/ai-strategy/providers/{provider}`

删除指定AI提供商的配置。

### 7. 获取默认AI提供商

**GET** `/api/ai-strategy/providers/default/info`

获取当前默认的AI提供商配置。

## 初始化配置

### 方式 1：通过初始化脚本（推荐）

运行初始化脚本，从环境变量读取 API Key 并创建配置：

```bash
# 确保 .env 文件中已配置 DEEPSEEK_API_KEY
python backend/scripts/init_ai_config.py
```

### 方式 2：通过管理后台

1. 访问管理后台 http://localhost:3002
2. 进入「AI 配置」页面
3. 添加 DeepSeek 或其他 AI 提供商，填入你的 API Key

### 方式 3：通过 API

使用创建 API 端点手动添加配置：

```bash
curl -X POST http://localhost:8000/api/ai-strategy/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "deepseek",
    "display_name": "DeepSeek",
    "api_key": "你的API Key",
    "api_base_url": "https://api.deepseek.com/v1",
    "model_name": "deepseek-chat",
    "max_tokens": 8000,
    "temperature": 0.7,
    "is_active": true,
    "is_default": true,
    "priority": 100,
    "rate_limit": 10,
    "timeout": 60,
    "description": "DeepSeek AI - 高性价比的中文AI模型"
  }'
```

**注意**：请使用你自己的 API Key，不要使用共享密钥。

## 使用示例

### Python示例

```python
import httpx
import asyncio

async def generate_strategy():
    url = "http://localhost:8000/api/ai-strategy/generate"

    request_data = {
        "strategy_requirement": """
**策略类型**: 简单均线策略

**核心逻辑**:
- 使用MA(5, 20)判断趋势
- 买入条件：MA5上穿MA20（金叉）
- 卖出条件：MA5下穿MA20（死叉）

**技术指标**: MA（移动平均线）

**参数配置**:
- ma_fast: 5 (快速均线周期)
- ma_slow: 20 (慢速均线周期)

**风险控制**:
- 每期选择前10只股票
        """,
        "use_custom_prompt": False
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=request_data)
        result = response.json()

        print(f"生成成功: {result['success']}")
        print(f"使用AI: {result['provider_used']}")
        print(f"策略代码长度: {len(result['strategy_code'])}")
        print(f"策略元信息: {result['strategy_metadata']}")

asyncio.run(generate_strategy())
```

### cURL示例

```bash
curl -X POST http://localhost:8000/api/ai-strategy/generate \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_requirement": "简单均线策略，使用MA5和MA20，金叉买入，死叉卖出"
  }'
```

## 支持的AI提供商

### 1. DeepSeek

- **provider**: `deepseek`
- **API Base URL**: `https://api.deepseek.com/v1`
- **推荐模型**: `deepseek-chat`
- **特点**: 高性价比，中文支持好

### 2. Google Gemini

- **provider**: `gemini`
- **API Base URL**: `https://generativelanguage.googleapis.com/v1beta`
- **推荐模型**: `gemini-1.5-flash`, `gemini-1.5-pro`
- **特点**: 免费额度高

### 3. OpenAI

- **provider**: `openai`
- **API Base URL**: `https://api.openai.com/v1`
- **推荐模型**: `gpt-4o`, `gpt-4-turbo`
- **特点**: 性能优秀，英文最佳

## 数据库表结构

AI配置存储在 `ai_provider_configs` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| provider | String(50) | 提供商名称（唯一） |
| display_name | String(100) | 显示名称 |
| api_key | String(500) | API密钥（加密存储） |
| api_base_url | String(200) | API基础URL |
| model_name | String(100) | 模型名称 |
| max_tokens | Integer | 最大token数 |
| temperature | Integer | 温度参数（0-100） |
| is_active | Boolean | 是否启用 |
| is_default | Boolean | 是否为默认 |
| priority | Integer | 优先级 |
| rate_limit | Integer | 每分钟请求限制 |
| timeout | Integer | 请求超时时间(秒) |
| description | Text | 描述信息 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 安全说明

1. **API密钥安全**：
   - API密钥在数据库中加密存储
   - 通过API返回时自动脱敏（仅显示前4位和后4位）
   - 建议使用环境变量存储敏感信息

2. **访问控制**：
   - 建议在生产环境中添加认证中间件
   - 限制AI配置管理端点的访问权限

3. **请求限制**：
   - 配置了rate_limit参数，建议在中间件中实现限流
   - timeout参数防止长时间等待

## 错误处理

API会返回详细的错误信息：

```json
{
  "success": false,
  "provider_used": "deepseek",
  "error_message": "DeepSeek API请求失败: 401",
  "tokens_used": null,
  "generation_time": null
}
```

常见错误：
- `404`: 未找到AI提供商配置
- `400`: AI提供商未启用
- `500`: AI服务调用失败（API密钥错误、网络问题等）

## 文件清单

### 新增文件

1. **数据模型**
   - [backend/app/models/ai_config.py](backend/app/models/ai_config.py) - AI配置数据模型

2. **数据访问层**
   - [backend/app/repositories/ai_config_repository.py](backend/app/repositories/ai_config_repository.py) - AI配置CRUD操作

3. **服务层**
   - [backend/app/services/ai_service.py](backend/app/services/ai_service.py) - AI策略生成服务

4. **API层**
   - [backend/app/api/endpoints/ai_strategy.py](backend/app/api/endpoints/ai_strategy.py) - AI策略API端点
   - [backend/app/schemas/ai_config.py](backend/app/schemas/ai_config.py) - Pydantic模型

5. **脚本**
   - [backend/scripts/init_ai_config.py](backend/scripts/init_ai_config.py) - 初始化AI配置
   - [backend/test_ai_generate.py](backend/test_ai_generate.py) - 测试脚本

### 修改文件

1. [backend/app/core/exceptions.py](backend/app/core/exceptions.py) - 添加AIServiceError异常
2. [backend/app/api/__init__.py](backend/app/api/__init__.py) - 注册AI策略路由

## 下一步

1. **前端集成**：
   - 在frontend的 `/strategies/create` 页面添加"使用AI生成"按钮
   - 调用 `/api/ai-strategy/generate` 端点
   - 显示生成的策略代码和元信息

2. **Admin配置页面**：
   - 创建AI提供商管理界面
   - 支持添加、编辑、删除AI配置
   - 设置默认提供商

3. **功能增强**：
   - 添加策略生成历史记录
   - 支持策略模板库
   - 实现AI对话式优化策略

## 测试

运行测试脚本：

```bash
# 在Docker容器中运行
docker-compose exec backend python test_ai_generate.py

# 或在本地运行（需要安装依赖）
python backend/test_ai_generate.py
```

## 文档

- API文档：http://localhost:8000/api/docs
- 本文档：[AI_STRATEGY_API.md](AI_STRATEGY_API.md)
