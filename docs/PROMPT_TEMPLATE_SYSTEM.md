# LLM提示词模板管理系统

## 概述

完整的LLM提示词模板管理系统，实现了提示词的数据库化管理、在线编辑、版本控制和性能追踪。

**核心价值**：
- ✅ 无需重启服务即可修改提示词
- ✅ 完整的版本控制和历史追踪
- ✅ 实时性能统计（成功率、Token消耗）
- ✅ 基于Jinja2的灵活模板渲染
- ✅ 多业务场景统一管理

---

## 快速开始

### 1. 访问管理界面

```bash
# Admin服务 (默认端口3001)
http://localhost:3001/settings/prompt-templates
```

导航路径：**系统设置 > 提示词管理**

### 2. 使用API

```bash
# 获取模板列表
curl http://localhost:8000/api/prompt-templates/

# 获取模板详情
curl http://localhost:8000/api/prompt-templates/1

# 预览渲染
curl -X POST http://localhost:8000/api/prompt-templates/1/preview \
  -H "Content-Type: application/json" \
  -d '{"variables": {"trade_date": "2026-03-11"}}'
```

### 3. 在代码中使用

```python
from app.services.prompt_template_service import get_prompt_template_service

service = get_prompt_template_service()

# 获取启用的模板
template = service.get_active_template(
    db,
    business_type="sentiment_analysis"
)

# 渲染提示词
system_prompt, user_prompt = service.render_template(
    db,
    template.id,
    variables={
        "trade_date": "2026-03-11",
        "sh_close": 3200,
        # ... 其他变量
    }
)

# 使用渲染后的提示词调用LLM
```

---

## 架构设计

### 数据库层

#### 核心表
- `llm_prompt_templates` - 提示词模板主表
- `llm_prompt_template_history` - 修改历史表
- `llm_call_logs` - LLM调用日志（已扩展关联模板）

#### 触发器
- 自动记录历史 - 每次INSERT/UPDATE/DELETE自动创建历史记录
- 唯一默认模板 - 确保同一业务类型只有一个默认模板
- 自动更新时间戳 - 更新时自动设置updated_at

#### 视图
- `llm_prompt_template_stats` - 实时统计视图，聚合性能指标

### 后端层

#### 服务层
- `PromptRenderer` - Jinja2模板渲染引擎
  - 变量验证
  - 语法检查
  - 安全渲染

- `PromptTemplateService` - 模板管理服务
  - CRUD操作
  - 版本控制
  - 性能统计

#### API层
- 12个REST端点
- 完整的CRUD支持
- 预览、统计、历史查询

### 前端层

#### 页面
- 列表页 - 查看、筛选、操作模板
- 编辑页 - 完整的模板编辑器

#### 核心功能
- 变量管理器
- 实时预览
- 语法高亮
- 表单验证

---

## API参考

### 核心端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/prompt-templates/` | 获取模板列表 |
| GET | `/api/prompt-templates/{id}` | 获取模板详情 |
| POST | `/api/prompt-templates/` | 创建新模板 |
| PUT | `/api/prompt-templates/{id}` | 更新模板 |
| DELETE | `/api/prompt-templates/{id}` | 删除模板 |
| POST | `/api/prompt-templates/{id}/preview` | 预览渲染 |
| GET | `/api/prompt-templates/{id}/statistics` | 获取统计 |
| GET | `/api/prompt-templates/{id}/history` | 获取历史 |
| POST | `/api/prompt-templates/{id}/activate` | 激活模板 |
| POST | `/api/prompt-templates/{id}/deactivate` | 停用模板 |

---

## 已迁移的模板

### 1. 市场情绪四维度灵魂拷问
- **业务类型**: `sentiment_analysis`
- **模板Key**: `soul_questioning_v1`
- **必填变量**: 25个
- **推荐AI**: DeepSeek Chat
- **来源**: `backend/app/services/sentiment_ai_analysis_service.py`

### 2. AI策略代码生成助手
- **业务类型**: `strategy_generation`
- **模板Key**: `ai_strategy_code_generation_v1`
- **必填变量**: 1个 (strategy_requirement)
- **推荐AI**: Claude 3.5 Sonnet
- **来源**: `frontend/src/components/strategies/AIStrategyPromptHelper.tsx`

### 3. 盘前计划碰撞测试
- **业务类型**: `premarket_analysis`
- **模板Key**: `premarket_collision_test_v1`
- **必填变量**: 11个
- **推荐AI**: DeepSeek Chat
- **来源**: `backend/app/services/premarket_analysis_service.py`

---

## 最佳实践

### 模板命名规范
- 使用描述性名称: "市场情绪四维度灵魂拷问"
- template_key使用下划线: "soul_questioning_v1"
- 版本号使用语义化: "1.0.0", "1.1.0", "2.0.0"

### 变量命名规范
- 使用小写下划线: `trade_date`, `sh_close`
- 保持一致性
- 在`required_variables`中提供清晰说明

### 版本管理建议
- 小改动升级小版本: 1.0.0 → 1.0.1
- 功能优化升级中版本: 1.0.0 → 1.1.0
- 重大改动升级大版本: 1.0.0 → 2.0.0
- 在`changelog`中详细记录变更

### 性能优化
- 定期查看统计数据
- 关注成功率，及时修复失败模板
- 优化高Token消耗的模板

---

## 文件结构

```
backend/
├── app/
│   ├── api/endpoints/
│   │   └── prompt_templates.py          # REST API接口
│   ├── models/
│   │   ├── llm_prompt_template.py       # ORM模型
│   │   └── llm_call_log.py              # 日志模型（已扩展）
│   ├── schemas/
│   │   └── llm_prompt_template.py       # Pydantic Schema
│   └── services/
│       ├── prompt_renderer.py           # Jinja2渲染引擎
│       └── prompt_template_service.py   # 模板管理服务
└── scripts/
    └── migrate_prompt_templates.py      # 数据迁移脚本

admin/
├── app/(dashboard)/settings/prompt-templates/
│   ├── page.tsx                         # 列表页
│   └── [id]/page.tsx                    # 编辑页
├── lib/
│   └── prompt-template-api.ts           # API客户端
└── types/
    └── prompt-template.ts               # TypeScript类型

db_init/
├── 10_prompt_template_schema.sql        # 模板表和触发器
└── 11_alter_llm_call_logs_add_template_fields.sql  # 日志表扩展
```

---

## 常见问题

**Q: 如何创建新模板？**
A: 通过Admin界面或POST `/api/prompt-templates/`

**Q: 模板语法是什么？**
A: Jinja2语法，支持`{{ variable }}`、`{% if %}`等

**Q: 如何查看性能统计？**
A: GET `/api/prompt-templates/{id}/statistics`

**Q: 可以删除正在使用的模板吗？**
A: 不可以，必须先停用并设置其他默认模板

---

## 技术栈

- **数据库**: PostgreSQL + TimescaleDB
- **后端**: FastAPI + SQLAlchemy + Jinja2
- **前端**: Next.js + TypeScript + shadcn/ui
- **状态管理**: React Hooks
- **API客户端**: Axios

---

**实施日期**: 2026-03-11
**维护者**: Stock Analysis Team
