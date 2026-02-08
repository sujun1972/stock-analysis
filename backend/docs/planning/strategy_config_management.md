# 策略配置管理系统设计方案

**文档版本**: v1.0.0
**创建日期**: 2026-02-08
**作者**: Architecture Team
**状态**: 📋 设计阶段 - 待评审

---

## 📋 目录

- [概述](#概述)
- [需求分析](#需求分析)
- [架构设计](#架构设计)
- [数据库设计](#数据库设计)
- [API设计](#api设计)
- [Core层改造](#core层改造)
- [Backend层改造](#backend层改造)
- [前端集成](#前端集成)
- [实施计划](#实施计划)
- [风险评估](#风险评估)

---

## 概述

### 背景

当前系统存在以下问题：

1. **配置分散**: Core 策略配置通过代码硬编码或临时字典传入
2. **无持久化**: 策略配置无法持久化保存
3. **无版本管理**: 配置变更无法追踪历史
4. **无共享机制**: Core 和 Backend 之间无统一的配置管理方式

### 目标

设计一个统一的策略配置管理系统，实现：

1. ✅ **配置持久化**: 策略配置保存到数据库
2. ✅ **CRUD操作**: 前端可通过 Backend API 创建/修改/删除策略配置
3. ✅ **配置共享**: Core 和 Backend 共享同一配置源
4. ✅ **版本管理**: 追踪配置变更历史
5. ✅ **参数验证**: 自动验证配置参数的有效性
6. ✅ **模板系统**: 预置常用策略模板

### 核心设计原则

- **单一数据源 (Single Source of Truth)**: Backend 数据库为配置的唯一真实来源
- **职责分离**: Core 负责策略逻辑，Backend 负责配置管理
- **向后兼容**: 保持 Core 现有 API 不变，支持代码传参
- **易扩展**: 支持未来新增策略类型

---

## 需求分析

### 功能需求

#### 1. 策略模板管理

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 查看策略类型 | 列出所有可用的策略类型(Momentum, MeanReversion等) | P0 |
| 查看参数定义 | 获取策略的参数定义(类型、范围、默认值) | P0 |
| 预置模板 | 内置常用策略配置模板 | P1 |

#### 2. 策略实例管理

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 创建策略 | 创建新的策略配置实例 | P0 |
| 修改策略 | 更新策略配置参数 | P0 |
| 删除策略 | 删除策略配置 | P0 |
| 查看策略列表 | 列出所有策略实例 | P0 |
| 查看策略详情 | 查看单个策略的完整配置 | P0 |
| 启用/禁用 | 切换策略启用状态 | P1 |
| 克隆策略 | 基于现有策略创建副本 | P2 |

#### 3. 配置版本管理

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 保存版本 | 每次修改自动保存版本快照 | P1 |
| 查看历史 | 查看配置变更历史 | P1 |
| 回滚版本 | 恢复到历史版本 | P2 |
| 版本对比 | 对比两个版本的差异 | P2 |

#### 4. 配置共享

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 导出配置 | 导出策略配置为JSON文件 | P2 |
| 导入配置 | 从JSON文件导入策略配置 | P2 |
| 配置市场 | 分享和下载社区策略配置 | P3 |

### 非功能需求

| 需求 | 指标 | 优先级 |
|------|------|--------|
| 性能 | 配置加载 < 100ms | P0 |
| 可靠性 | 配置持久化成功率 > 99.9% | P0 |
| 一致性 | Core 和 Backend 配置强一致 | P0 |
| 可扩展性 | 支持 10,000+ 策略实例 | P1 |
| 安全性 | 配置访问权限控制 | P2 |

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  - 策略管理UI   - 参数配置表单   - 版本历史视图             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Strategy Config Service Layer              │   │
│  │  - ConfigService   - TemplateService                 │   │
│  │  - VersionService  - ValidationService               │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │         Strategy Config Repository Layer             │   │
│  │  - ConfigRepository   - VersionRepository            │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │              PostgreSQL Database                     │   │
│  │  - strategy_configs   - config_versions              │   │
│  │  - strategy_templates                                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ Config Loader
┌────────────────────────▼────────────────────────────────────┐
│                      Core (Python)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Strategy Layer (Enhanced)                 │   │
│  │  - BaseStrategy                                      │   │
│  │  - StrategyConfigLoader (新增)                       │   │
│  │  - MomentumStrategy, MeanReversionStrategy...        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 配置存储位置决策

#### 方案对比

| 方案 | 配置存储位置 | 优点 | 缺点 | 推荐 |
|------|-------------|------|------|------|
| **方案1** | Backend 数据库 | 集中管理、易于维护、支持Web管理 | Core需要访问Backend数据库 | ✅ **推荐** |
| 方案2 | Core 本地文件 | Core独立、无依赖 | 分散管理、难以共享、无Web管理 | ❌ |
| 方案3 | 独立配置中心 | 高可用、分布式 | 架构复杂、增加��维成本 | ❌ |
| 方案4 | Backend API | 完全解耦 | 性能开销、网络依赖 | ❌ |

#### 最终方案: **Backend 数据库存储** (方案1)

**理由**:

1. **统一管理**: Backend 已有完善的数据库基础设施
2. **Web友好**: 前端可通过 Backend API 轻松管理配置
3. **性能优化**: Core 可通过 DatabaseManager 直接访问数据库，无需HTTP调用
4. **一致性**: 使用数据库事务保证配置一致性
5. **可扩展**: 利用PostgreSQL的JSONB特性灵活存储配置

**实现细节**:

```python
# Core 访问配置的方式
from core.database.database_manager import DatabaseManager

class StrategyConfigLoader:
    def __init__(self):
        self.db = DatabaseManager()

    def load_config(self, config_id: int) -> Dict:
        """从数据库加载配置"""
        query = "SELECT config FROM strategy_configs WHERE id = %s"
        result = self.db.execute_query(query, (config_id,))
        return result[0]['config']
```

### 配置加载流程

#### 流程图

```
用户请求 (前端)
    ↓
Backend API: POST /api/backtest/run
    {
        "strategy_config_id": 123,
        "stock_codes": ["000001"],
        ...
    }
    ↓
BacktestService.run_backtest()
    ↓
ConfigService.get_config(123)
    ↓
PostgreSQL: SELECT * FROM strategy_configs WHERE id = 123
    ↓
返回配置: {
    "strategy_type": "momentum",
    "params": {"lookback_period": 20, ...}
}
    ↓
Core.BacktestEngine (通过 Adapter)
    ↓
Strategy = StrategyFactory.create(
    strategy_type="momentum",
    config=config['params']
)
    ↓
执行回测
```

### 配置缓存策略

为提高性能，采用多级缓存:

```
┌─────────────────┐
│  Request Cache  │  (每次请求生命周期)
└────────┬────────┘
         │
┌────────▼────────┐
│   Redis Cache   │  (5分钟TTL)
└────────┬────────┘
         │
┌────────▼────────┐
│   PostgreSQL    │  (持久化存储)
└─────────────────┘
```

**缓存策略**:

- **写入**: 直写 (Write-Through) - 同时更新数据库和Redis
- **失效**: 主动失效 - 配置修改时清除Redis缓存
- **预热**: 启动时加载常用配置到Redis

---

## 数据库设计

### 表结构设计

#### 1. 策略配置表 (strategy_configs)

```sql
CREATE TABLE strategy_configs (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 基本信息
    name VARCHAR(200) NOT NULL,                    -- 策略名称(如 "MOM20_Conservative")
    display_name VARCHAR(200),                     -- 显示名称(前端展示)
    description TEXT,                              -- 策略描述
    strategy_type VARCHAR(50) NOT NULL,            -- 策略类型(momentum, mean_reversion, multi_factor)

    -- 配置内容
    config JSONB NOT NULL,                         -- 策略参数配置

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,                -- 是否启用
    is_template BOOLEAN DEFAULT FALSE,             -- 是否为模板

    -- 版本信息
    version INT DEFAULT 1,                         -- 当前版本号
    config_hash VARCHAR(64),                       -- 配置内容的MD5哈希(用于检测变更)

    -- 分类和标签
    category VARCHAR(50),                          -- 分类(conservative, aggressive, balanced)
    tags VARCHAR(100)[],                           -- 标签数组

    -- 性能指标(最近一次回测)
    last_backtest_metrics JSONB,                   -- {sharpe, return, drawdown, ...}
    last_backtest_date TIMESTAMP,

    -- 审计字段
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN ('momentum', 'mean_reversion', 'multi_factor', 'ml_entry', 'custom')
    ),
    CONSTRAINT unique_name UNIQUE(name)
);

-- 索引
CREATE INDEX idx_strategy_type ON strategy_configs(strategy_type);
CREATE INDEX idx_is_active ON strategy_configs(is_active);
CREATE INDEX idx_is_template ON strategy_configs(is_template);
CREATE INDEX idx_tags ON strategy_configs USING GIN(tags);
CREATE INDEX idx_config ON strategy_configs USING GIN(config);
CREATE INDEX idx_created_at ON strategy_configs(created_at DESC);
```

#### 2. 配置版本表 (strategy_config_versions)

```sql
CREATE TABLE strategy_config_versions (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 关联策略
    config_id INT NOT NULL REFERENCES strategy_configs(id) ON DELETE CASCADE,

    -- 版本信息
    version INT NOT NULL,                          -- 版本号
    config_snapshot JSONB NOT NULL,                -- 配置快照
    config_hash VARCHAR(64),                       -- 快照哈希

    -- 变更信息
    change_type VARCHAR(20) NOT NULL,              -- create, update, rollback
    change_summary TEXT,                           -- 变更摘要
    change_details JSONB,                          -- 变更详情 {added: {}, removed: {}, modified: {}}

    -- 审计字段
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_change_type CHECK (
        change_type IN ('create', 'update', 'rollback', 'clone')
    ),
    CONSTRAINT unique_version UNIQUE(config_id, version)
);

-- 索引
CREATE INDEX idx_version_config_id ON strategy_config_versions(config_id, version DESC);
CREATE INDEX idx_version_created_at ON strategy_config_versions(created_at DESC);
```

#### 3. 策略模板表 (strategy_templates)

```sql
CREATE TABLE strategy_templates (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 模板信息
    template_name VARCHAR(200) NOT NULL UNIQUE,    -- 模板名称
    display_name VARCHAR(200),
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL,

    -- 模板配置
    default_config JSONB NOT NULL,                 -- 默认配置
    config_schema JSONB,                           -- 配置JSON Schema(用于验证)

    -- 分类
    category VARCHAR(50),
    difficulty VARCHAR(20),                        -- beginner, intermediate, advanced

    -- 使用统计
    usage_count INT DEFAULT 0,

    -- 推荐设置
    is_recommended BOOLEAN DEFAULT FALSE,
    recommended_for JSONB,                         -- {market_conditions: [], risk_levels: []}

    -- 示例和文档
    example_config JSONB,                          -- 示例配置
    documentation TEXT,                            -- 使用说明

    -- 审计字段
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_template_strategy_type CHECK (
        strategy_type IN ('momentum', 'mean_reversion', 'multi_factor', 'ml_entry', 'custom')
    )
);

-- 索引
CREATE INDEX idx_template_strategy_type ON strategy_templates(strategy_type);
CREATE INDEX idx_template_category ON strategy_templates(category);
CREATE INDEX idx_template_recommended ON strategy_templates(is_recommended);
```

#### 4. 策略使用记录表 (strategy_usage_logs)

```sql
CREATE TABLE strategy_usage_logs (
    -- 主键
    id BIGSERIAL PRIMARY KEY,

    -- 关联策略
    config_id INT REFERENCES strategy_configs(id) ON DELETE SET NULL,

    -- 使用场景
    usage_type VARCHAR(50) NOT NULL,               -- backtest, live_trading, simulation

    -- 执行信息
    execution_params JSONB,                        -- {stock_codes, start_date, end_date, ...}
    execution_result JSONB,                        -- {metrics, status, error, ...}

    -- 性能指标
    performance_metrics JSONB,                     -- 本次执行的性能指标
    execution_duration_ms INT,

    -- 审计字段
    executed_by VARCHAR(100),
    executed_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_usage_type CHECK (
        usage_type IN ('backtest', 'live_trading', 'simulation', 'optimization', 'validation')
    )
);

-- 索引
CREATE INDEX idx_usage_config_id ON strategy_usage_logs(config_id, executed_at DESC);
CREATE INDEX idx_usage_type ON strategy_usage_logs(usage_type);
CREATE INDEX idx_usage_executed_at ON strategy_usage_logs(executed_at DESC);

-- 分区表(按月分区，提高查询性能)
-- CREATE TABLE strategy_usage_logs_2026_02 PARTITION OF strategy_usage_logs
-- FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

### 配置示例

#### 动量策略配置

```json
{
  "id": 1,
  "name": "MOM20_Conservative",
  "display_name": "保守型动量策略(20日)",
  "description": "基于20日动量的保守型策略，适合震荡市",
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "top_n": 30,
    "holding_period": 5,
    "use_log_return": false,
    "filter_negative": true,
    "min_price": 5.0,
    "max_price": 500.0,
    "min_volume": 5000000,
    "max_position_pct": 0.15,
    "stop_loss_pct": -0.08,
    "take_profit_pct": 0.20
  },
  "is_active": true,
  "is_template": false,
  "version": 3,
  "category": "conservative",
  "tags": ["momentum", "conservative", "medium_term"],
  "last_backtest_metrics": {
    "annual_return": 0.18,
    "sharpe_ratio": 1.45,
    "max_drawdown": -0.12,
    "win_rate": 0.58
  },
  "last_backtest_date": "2026-02-07T10:30:00Z",
  "created_by": "user_001",
  "created_at": "2026-01-15T09:00:00Z",
  "updated_by": "user_001",
  "updated_at": "2026-02-05T14:20:00Z"
}
```

#### 多因子策略配置

```json
{
  "id": 2,
  "name": "MultiF_Balanced_3Factor",
  "display_name": "均衡型三因子策略",
  "description": "结合动量、反转和波动率的均衡策略",
  "strategy_type": "multi_factor",
  "config": {
    "factors": ["MOM20", "REV5", "VOLATILITY20"],
    "weights": [0.4, 0.3, 0.3],
    "normalize_method": "rank",
    "neutralize": false,
    "min_factor_coverage": 0.8,
    "top_n": 50,
    "holding_period": 5,
    "rebalance_freq": "W",
    "min_price": 3.0,
    "min_volume": 3000000
  },
  "is_active": true,
  "is_template": false,
  "version": 1,
  "category": "balanced",
  "tags": ["multi_factor", "diversified", "weekly"],
  "created_at": "2026-02-01T11:00:00Z"
}
```

---

## API设计

### RESTful API规范

#### 基础URL

```
https://api.your-domain.com/api/v1/strategy-configs
```

### API端点列表

#### 1. 策略模板管理

##### 1.1 获取策略类型列表

```http
GET /api/v1/strategy-configs/types

Response 200:
{
  "success": true,
  "data": [
    {
      "id": "momentum",
      "name": "动量策略",
      "description": "买入近期强势股票",
      "core_class": "MomentumStrategy",
      "parameter_count": 8,
      "supported_features": ["backtest", "live_trading"]
    },
    {
      "id": "mean_reversion",
      "name": "均值回归策略",
      "description": "买入短期超跌股票",
      "core_class": "MeanReversionStrategy",
      "parameter_count": 7,
      "supported_features": ["backtest", "live_trading"]
    }
  ]
}
```

##### 1.2 获取策略参数定义

```http
GET /api/v1/strategy-configs/types/:strategy_type/parameters

Example: GET /api/v1/strategy-configs/types/momentum/parameters

Response 200:
{
  "success": true,
  "data": {
    "strategy_type": "momentum",
    "parameters": [
      {
        "name": "lookback_period",
        "label": "动量计算回看期",
        "type": "integer",
        "default": 20,
        "min_value": 5,
        "max_value": 60,
        "step": 1,
        "description": "计算动量使用的历史数据天数",
        "category": "core",
        "required": true
      },
      {
        "name": "top_n",
        "label": "每期选股数量",
        "type": "integer",
        "default": 50,
        "min_value": 5,
        "max_value": 200,
        "step": 5,
        "description": "每次选择排名前N的股票",
        "category": "selection",
        "required": true
      },
      {
        "name": "filter_negative",
        "label": "过滤负动量",
        "type": "boolean",
        "default": true,
        "description": "是否过滤动量为负的股票",
        "category": "filter",
        "required": false
      }
    ]
  }
}
```

##### 1.3 获取策略模板列表

```http
GET /api/v1/strategy-configs/templates
Query Parameters:
  - strategy_type: string (optional) - 策略类型筛选
  - category: string (optional) - 分类筛选
  - difficulty: string (optional) - 难度筛选

Response 200:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "template_name": "momentum_conservative",
      "display_name": "保守型动量策略",
      "strategy_type": "momentum",
      "category": "conservative",
      "difficulty": "beginner",
      "description": "适合新手的保守型动量策略",
      "default_config": {...},
      "usage_count": 125,
      "is_recommended": true
    }
  ],
  "meta": {
    "total": 15,
    "page": 1,
    "page_size": 20
  }
}
```

##### 1.4 获取模板详情

```http
GET /api/v1/strategy-configs/templates/:template_id

Response 200:
{
  "success": true,
  "data": {
    "id": 1,
    "template_name": "momentum_conservative",
    "display_name": "保守型动量策略",
    "strategy_type": "momentum",
    "default_config": {
      "lookback_period": 20,
      "top_n": 30,
      "holding_period": 5,
      "filter_negative": true
    },
    "config_schema": {...},
    "documentation": "## 使用说明\n...",
    "example_config": {...},
    "recommended_for": {
      "market_conditions": ["sideways", "moderate_uptrend"],
      "risk_levels": ["low", "medium"]
    }
  }
}
```

#### 2. 策略实例管理

##### 2.1 创建策略

```http
POST /api/v1/strategy-configs

Request Body:
{
  "name": "My_MOM20_Strategy",
  "display_name": "我的动量策略",
  "description": "自定义的20日动量策略",
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "top_n": 30,
    "holding_period": 5
  },
  "category": "conservative",
  "tags": ["momentum", "conservative"]
}

Response 201:
{
  "success": true,
  "message": "策略创建成功",
  "data": {
    "id": 123,
    "name": "My_MOM20_Strategy",
    "version": 1,
    "created_at": "2026-02-08T10:00:00Z"
  }
}

Response 400 (参数错误):
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "参数验证失败",
    "details": [
      {
        "field": "config.lookback_period",
        "message": "lookback_period must be between 5 and 60"
      }
    ]
  }
}
```

##### 2.2 获取策略列表

```http
GET /api/v1/strategy-configs
Query Parameters:
  - strategy_type: string (optional)
  - category: string (optional)
  - is_active: boolean (optional)
  - tags: string[] (optional)
  - page: int (default: 1)
  - page_size: int (default: 20)
  - sort_by: string (default: "created_at")
  - sort_order: "asc"|"desc" (default: "desc")
  - search: string (optional) - 搜索名称/描述

Response 200:
{
  "success": true,
  "data": [
    {
      "id": 123,
      "name": "My_MOM20_Strategy",
      "display_name": "我的动量策略",
      "strategy_type": "momentum",
      "category": "conservative",
      "is_active": true,
      "version": 1,
      "last_backtest_metrics": {
        "annual_return": 0.15,
        "sharpe_ratio": 1.32
      },
      "created_at": "2026-02-08T10:00:00Z",
      "updated_at": "2026-02-08T10:00:00Z"
    }
  ],
  "meta": {
    "total": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

##### 2.3 获取策略详情

```http
GET /api/v1/strategy-configs/:config_id

Response 200:
{
  "success": true,
  "data": {
    "id": 123,
    "name": "My_MOM20_Strategy",
    "display_name": "我的动量策略",
    "description": "自定义的20日动量策略",
    "strategy_type": "momentum",
    "config": {
      "lookback_period": 20,
      "top_n": 30,
      "holding_period": 5,
      "filter_negative": true
    },
    "is_active": true,
    "version": 1,
    "config_hash": "abc123...",
    "category": "conservative",
    "tags": ["momentum", "conservative"],
    "last_backtest_metrics": {...},
    "created_by": "user_001",
    "created_at": "2026-02-08T10:00:00Z",
    "updated_at": "2026-02-08T10:00:00Z"
  }
}
```

##### 2.4 更新策略

```http
PUT /api/v1/strategy-configs/:config_id

Request Body:
{
  "display_name": "更新后的名称",
  "description": "更新后的描述",
  "config": {
    "lookback_period": 25,  // 只更新这个参数
    "top_n": 40
  },
  "category": "balanced",
  "tags": ["momentum", "balanced"]
}

Response 200:
{
  "success": true,
  "message": "策略更新成功",
  "data": {
    "id": 123,
    "version": 2,
    "updated_at": "2026-02-08T11:00:00Z",
    "changes": {
      "modified": ["config.lookback_period", "config.top_n", "category"],
      "version_created": true
    }
  }
}
```

##### 2.5 删除策略

```http
DELETE /api/v1/strategy-configs/:config_id

Response 200:
{
  "success": true,
  "message": "策略删除成功"
}

Response 400 (策略正在使用中):
{
  "success": false,
  "error": {
    "code": "STRATEGY_IN_USE",
    "message": "策略正在使用中，无法删除",
    "details": {
      "active_backtests": 2,
      "running_tasks": 1
    }
  }
}
```

##### 2.6 启用/禁用策略

```http
PATCH /api/v1/strategy-configs/:config_id/status

Request Body:
{
  "is_active": false
}

Response 200:
{
  "success": true,
  "message": "策略状态更新成功",
  "data": {
    "id": 123,
    "is_active": false
  }
}
```

##### 2.7 克隆策略

```http
POST /api/v1/strategy-configs/:config_id/clone

Request Body:
{
  "name": "My_MOM20_Strategy_V2",
  "display_name": "我的动量策略 V2"
}

Response 201:
{
  "success": true,
  "message": "策略克隆成功",
  "data": {
    "id": 124,
    "name": "My_MOM20_Strategy_V2",
    "cloned_from": 123
  }
}
```

#### 3. 版本管理

##### 3.1 获取版本历史

```http
GET /api/v1/strategy-configs/:config_id/versions
Query Parameters:
  - page: int (default: 1)
  - page_size: int (default: 10)

Response 200:
{
  "success": true,
  "data": [
    {
      "id": 456,
      "version": 2,
      "change_type": "update",
      "change_summary": "调整lookback_period从20到25",
      "created_by": "user_001",
      "created_at": "2026-02-08T11:00:00Z"
    },
    {
      "id": 455,
      "version": 1,
      "change_type": "create",
      "change_summary": "初始创建",
      "created_by": "user_001",
      "created_at": "2026-02-08T10:00:00Z"
    }
  ],
  "meta": {
    "total": 2,
    "current_version": 2
  }
}
```

##### 3.2 获取版本详情

```http
GET /api/v1/strategy-configs/:config_id/versions/:version

Response 200:
{
  "success": true,
  "data": {
    "id": 456,
    "config_id": 123,
    "version": 2,
    "config_snapshot": {
      "lookback_period": 25,
      "top_n": 40,
      ...
    },
    "change_type": "update",
    "change_details": {
      "modified": {
        "lookback_period": {"old": 20, "new": 25},
        "top_n": {"old": 30, "new": 40}
      },
      "added": {},
      "removed": {}
    },
    "created_by": "user_001",
    "created_at": "2026-02-08T11:00:00Z"
  }
}
```

##### 3.3 回滚到历史版本

```http
POST /api/v1/strategy-configs/:config_id/versions/:version/rollback

Response 200:
{
  "success": true,
  "message": "成功回滚到版本 2",
  "data": {
    "id": 123,
    "current_version": 3,
    "rollback_to_version": 2,
    "restored_config": {...}
  }
}
```

##### 3.4 对比两个版本

```http
GET /api/v1/strategy-configs/:config_id/versions/compare
Query Parameters:
  - from_version: int (required)
  - to_version: int (required)

Response 200:
{
  "success": true,
  "data": {
    "from_version": 1,
    "to_version": 2,
    "differences": {
      "modified": {
        "config.lookback_period": {"old": 20, "new": 25},
        "config.top_n": {"old": 30, "new": 40}
      },
      "added": {
        "config.use_log_return": false
      },
      "removed": {}
    }
  }
}
```

#### 4. 配置验证

##### 4.1 验证策略配置

```http
POST /api/v1/strategy-configs/validate

Request Body:
{
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 150,  // 超出范围
    "top_n": 30
  }
}

Response 200 (验证通过):
{
  "success": true,
  "valid": true,
  "message": "配置验证通过"
}

Response 200 (验证失败):
{
  "success": true,
  "valid": false,
  "errors": [
    {
      "field": "config.lookback_period",
      "message": "lookback_period must be between 5 and 60",
      "value": 150,
      "constraint": {
        "min": 5,
        "max": 60
      }
    }
  ]
}
```

#### 5. 配置导入导出

##### 5.1 导出配置

```http
GET /api/v1/strategy-configs/:config_id/export
Query Parameters:
  - format: "json"|"yaml" (default: "json")
  - include_metadata: boolean (default: false)

Response 200:
Content-Type: application/json
Content-Disposition: attachment; filename="My_MOM20_Strategy.json"

{
  "name": "My_MOM20_Strategy",
  "strategy_type": "momentum",
  "config": {...},
  "metadata": {...}  // if include_metadata=true
}
```

##### 5.2 导入配置

```http
POST /api/v1/strategy-configs/import

Request Body (multipart/form-data):
{
  "file": <JSON file>,
  "overwrite_existing": false
}

Response 201:
{
  "success": true,
  "message": "配置导入成功",
  "data": {
    "imported_count": 1,
    "configs": [
      {
        "id": 125,
        "name": "Imported_MOM20_Strategy"
      }
    ]
  }
}
```

#### 6. 使用统计

##### 6.1 记录策略使用

```http
POST /api/v1/strategy-configs/:config_id/usage

Request Body:
{
  "usage_type": "backtest",
  "execution_params": {
    "stock_codes": ["000001", "600000"],
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  },
  "execution_result": {
    "status": "completed",
    "metrics": {...}
  },
  "performance_metrics": {
    "annual_return": 0.15,
    "sharpe_ratio": 1.32
  },
  "execution_duration_ms": 5240
}

Response 201:
{
  "success": true,
  "message": "使用记录已保存"
}
```

##### 6.2 获取使用统计

```http
GET /api/v1/strategy-configs/:config_id/usage/stats
Query Parameters:
  - start_date: date (optional)
  - end_date: date (optional)

Response 200:
{
  "success": true,
  "data": {
    "total_usage": 45,
    "usage_by_type": {
      "backtest": 30,
      "live_trading": 10,
      "simulation": 5
    },
    "avg_performance": {
      "annual_return": 0.16,
      "sharpe_ratio": 1.38
    },
    "recent_usage": [...]
  }
}
```

---

## Core层改造

### 新增组件

#### 1. StrategyConfigLoader (配置加载器)

```python
# core/src/strategies/config_loader.py

from typing import Dict, Optional, Any
from loguru import logger
from ..database.database_manager import DatabaseManager


class StrategyConfigLoader:
    """
    策略配置加载器

    负责从数据库加载策略配置，支持缓存
    """

    def __init__(self, use_cache: bool = True):
        """
        初始化配置加载器

        Args:
            use_cache: 是否启用缓存
        """
        self.db = DatabaseManager()
        self.use_cache = use_cache
        self._cache = {}  # 简单内存缓存

    def load_config(
        self,
        config_id: Optional[int] = None,
        config_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载策略配置

        Args:
            config_id: 配置ID
            config_name: 配置名称

        Returns:
            配置字典 {strategy_type, config, metadata}

        Raises:
            ValueError: 配置不存在
        """
        if config_id is None and config_name is None:
            raise ValueError("必须提供 config_id 或 config_name")

        # 检查缓存
        cache_key = f"id_{config_id}" if config_id else f"name_{config_name}"
        if self.use_cache and cache_key in self._cache:
            logger.debug(f"从缓存加载配置: {cache_key}")
            return self._cache[cache_key]

        # 从数据库加载
        if config_id:
            query = """
                SELECT id, name, strategy_type, config, version, is_active
                FROM strategy_configs
                WHERE id = %s
            """
            params = (config_id,)
        else:
            query = """
                SELECT id, name, strategy_type, config, version, is_active
                FROM strategy_configs
                WHERE name = %s
            """
            params = (config_name,)

        result = self.db.execute_query(query, params)

        if not result:
            raise ValueError(f"策略配置不存在: {config_id or config_name}")

        row = result[0]

        # 检查是否启用
        if not row['is_active']:
            logger.warning(f"策略配置已禁用: {row['name']}")

        config_data = {
            'id': row['id'],
            'name': row['name'],
            'strategy_type': row['strategy_type'],
            'config': row['config'],  # JSONB 自动解析为dict
            'version': row['version'],
            'is_active': row['is_active']
        }

        # 缓存
        if self.use_cache:
            self._cache[cache_key] = config_data

        logger.info(f"已加载策略配置: {row['name']} (v{row['version']})")

        return config_data

    def clear_cache(self, config_id: Optional[int] = None):
        """清除缓存"""
        if config_id:
            cache_key = f"id_{config_id}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"已清除缓存: {cache_key}")
        else:
            self._cache.clear()
            logger.debug("已清除所有缓存")
```

#### 2. StrategyFactory (策略工厂)

```python
# core/src/strategies/strategy_factory.py

from typing import Dict, Any, Optional
from loguru import logger

from .base_strategy import BaseStrategy
from .momentum_strategy import MomentumStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .multi_factor_strategy import MultiFactorStrategy
from .config_loader import StrategyConfigLoader


class StrategyFactory:
    """
    策略工厂类

    根据配置创建策略实例
    """

    # 策略类型映射
    STRATEGY_CLASSES = {
        'momentum': MomentumStrategy,
        'mean_reversion': MeanReversionStrategy,
        'multi_factor': MultiFactorStrategy,
    }

    def __init__(self):
        self.config_loader = StrategyConfigLoader()

    @classmethod
    def create(
        cls,
        strategy_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None
    ) -> BaseStrategy:
        """
        根据类型和配置创建策略实例

        Args:
            strategy_type: 策略类型
            config: 策略配置
            name: 策略名称

        Returns:
            策略实例

        Raises:
            ValueError: 不支持的策略类型
        """
        if strategy_type not in cls.STRATEGY_CLASSES:
            raise ValueError(
                f"不支持的策略类型: {strategy_type}. "
                f"支持的类型: {list(cls.STRATEGY_CLASSES.keys())}"
            )

        strategy_class = cls.STRATEGY_CLASSES[strategy_type]
        strategy_name = name or f"{strategy_type}_strategy"

        logger.debug(f"创建策略实例: {strategy_name} ({strategy_type})")

        return strategy_class(strategy_name, config)

    def create_from_db(
        self,
        config_id: Optional[int] = None,
        config_name: Optional[str] = None
    ) -> BaseStrategy:
        """
        从数据库加载配置并创建策略实例

        Args:
            config_id: 配置ID
            config_name: 配置名称

        Returns:
            策略实例
        """
        # 加载配置
        config_data = self.config_loader.load_config(config_id, config_name)

        # 创建策略
        return self.create(
            strategy_type=config_data['strategy_type'],
            config=config_data['config'],
            name=config_data['name']
        )

    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: type):
        """
        注册自定义策略类型

        Args:
            strategy_type: 策略类型标识
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"{strategy_class} 必须继承自 BaseStrategy")

        cls.STRATEGY_CLASSES[strategy_type] = strategy_class
        logger.info(f"已注册策略类型: {strategy_type} -> {strategy_class.__name__}")
```

### BaseStrategy 改造

```python
# core/src/strategies/base_strategy.py (部分修改)

class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            name: 策略名称
            config: 策略配置 (可以是字典或配置ID)
        """
        self.name = name

        # 支持两种方式:
        # 1. 直接传入配置字典 (向后兼容)
        # 2. 传入 {"config_id": 123} 从数据库加载
        if isinstance(config, dict) and 'config_id' in config:
            # 从数据库加载配置
            from .config_loader import StrategyConfigLoader
            loader = StrategyConfigLoader()
            config_data = loader.load_config(config_id=config['config_id'])
            self.config = self._parse_config(config_data['config'])
            self.config_id = config_data['id']
            self.config_version = config_data['version']
        else:
            # 直接使用传入的配置
            self.config = self._parse_config(config)
            self.config_id = None
            self.config_version = None

        self._signal_cache = {}

        logger.info(f"初始化策略: {self.name}")
        if self.config_id:
            logger.debug(f"使用数据库配置: ID={self.config_id}, Version={self.config_version}")

    # ... 其他方法保持不变
```

### 使用示例

```python
# 使用方式1: 直接传入配置 (向后兼容)
from core.strategies import MomentumStrategy

config = {
    'lookback_period': 20,
    'top_n': 30,
    'holding_period': 5
}
strategy = MomentumStrategy('MOM20', config)

# 使用方式2: 从数据库加载配置
from core.strategies import StrategyFactory

factory = StrategyFactory()
strategy = factory.create_from_db(config_id=123)

# 使用方式3: 通过 config_id 参数
strategy = MomentumStrategy('MOM20', {'config_id': 123})
```

---

## Backend层改造

### 新增服务层

#### 1. StrategyConfigService

```python
# backend/app/services/strategy_config_service.py

from typing import List, Dict, Any, Optional
from loguru import logger

from app.repositories.strategy_config_repository import StrategyConfigRepository
from app.repositories.strategy_version_repository import StrategyVersionRepository
from app.core.exceptions import ValidationError, NotFoundError
from app.utils.config_validator import ConfigValidator


class StrategyConfigService:
    """策略配置服务"""

    def __init__(self):
        self.config_repo = StrategyConfigRepository()
        self.version_repo = StrategyVersionRepository()
        self.validator = ConfigValidator()

    async def create_config(
        self,
        name: str,
        strategy_type: str,
        config: Dict[str, Any],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建策略配置

        Args:
            name: 策略名称
            strategy_type: 策略类型
            config: 配置参数
            display_name: 显示名称
            description: 描述
            category: 分类
            tags: 标签
            created_by: 创建人

        Returns:
            创建的配置信息

        Raises:
            ValidationError: 参数验证失败
        """
        # 验证配置
        validation_result = await self.validator.validate(strategy_type, config)
        if not validation_result['valid']:
            raise ValidationError(
                "配置验证失败",
                details=validation_result['errors']
            )

        # 计算配置哈希
        config_hash = self._calculate_hash(config)

        # 创建配置
        config_data = {
            'name': name,
            'display_name': display_name or name,
            'description': description,
            'strategy_type': strategy_type,
            'config': config,
            'config_hash': config_hash,
            'version': 1,
            'category': category,
            'tags': tags or [],
            'is_active': True,
            'created_by': created_by
        }

        config_id = await self.config_repo.create(config_data)

        # 创建初始版本
        await self.version_repo.create_version(
            config_id=config_id,
            version=1,
            config_snapshot=config,
            change_type='create',
            change_summary='初始创建',
            created_by=created_by
        )

        logger.info(f"已创建策略配置: {name} (ID={config_id})")

        return await self.get_config(config_id)

    async def update_config(
        self,
        config_id: int,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新策略配置

        Args:
            config_id: 配置ID
            updates: 更新的字段
            updated_by: 更新人

        Returns:
            更新后的配置
        """
        # 获取当前配置
        current = await self.config_repo.get_by_id(config_id)
        if not current:
            raise NotFoundError(f"策略配置不存在: {config_id}")

        # 如果更新了 config 字段，需要验证
        if 'config' in updates:
            new_config = {**current['config'], **updates['config']}
            validation_result = await self.validator.validate(
                current['strategy_type'],
                new_config
            )
            if not validation_result['valid']:
                raise ValidationError(
                    "配置验证失败",
                    details=validation_result['errors']
                )
            updates['config'] = new_config
            updates['config_hash'] = self._calculate_hash(new_config)

        # 更新版本号
        new_version = current['version'] + 1
        updates['version'] = new_version
        updates['updated_by'] = updated_by

        # 执行更新
        await self.config_repo.update(config_id, updates)

        # 创建版本快照
        change_details = self._calculate_changes(
            current['config'],
            updates.get('config', current['config'])
        )

        await self.version_repo.create_version(
            config_id=config_id,
            version=new_version,
            config_snapshot=updates.get('config', current['config']),
            change_type='update',
            change_summary=self._summarize_changes(change_details),
            change_details=change_details,
            created_by=updated_by
        )

        logger.info(f"已更新策略配置: ID={config_id}, Version={new_version}")

        return await self.get_config(config_id)

    async def get_config(self, config_id: int) -> Dict[str, Any]:
        """获取策略配置"""
        config = await self.config_repo.get_by_id(config_id)
        if not config:
            raise NotFoundError(f"策略配置不存在: {config_id}")
        return config

    async def list_configs(
        self,
        strategy_type: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取策略配置列表"""
        filters = {}
        if strategy_type:
            filters['strategy_type'] = strategy_type
        if category:
            filters['category'] = category
        if is_active is not None:
            filters['is_active'] = is_active
        if tags:
            filters['tags'] = tags

        configs = await self.config_repo.list(
            filters=filters,
            page=page,
            page_size=page_size
        )

        return configs

    async def delete_config(self, config_id: int):
        """删除策略配置"""
        # 检查是否在使用
        usage_count = await self._check_usage(config_id)
        if usage_count > 0:
            raise ValidationError(
                f"策略正在使用中，无法删除 (活跃使用: {usage_count})"
            )

        await self.config_repo.delete(config_id)
        logger.info(f"已删除策略配置: ID={config_id}")

    async def clone_config(
        self,
        config_id: int,
        new_name: str,
        new_display_name: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """克隆策略配置"""
        # 获取源配置
        source = await self.get_config(config_id)

        # 创建新配置
        return await self.create_config(
            name=new_name,
            strategy_type=source['strategy_type'],
            config=source['config'],
            display_name=new_display_name or f"{source['display_name']} (副本)",
            description=f"克隆自: {source['name']}",
            category=source['category'],
            tags=source['tags'],
            created_by=created_by
        )

    def _calculate_hash(self, config: Dict) -> str:
        """计算配置哈希"""
        import hashlib
        import json
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def _calculate_changes(
        self,
        old_config: Dict,
        new_config: Dict
    ) -> Dict[str, Any]:
        """计算配置变更"""
        changes = {
            'added': {},
            'removed': {},
            'modified': {}
        }

        # 检测新增和修改
        for key, new_value in new_config.items():
            if key not in old_config:
                changes['added'][key] = new_value
            elif old_config[key] != new_value:
                changes['modified'][key] = {
                    'old': old_config[key],
                    'new': new_value
                }

        # 检测删除
        for key in old_config:
            if key not in new_config:
                changes['removed'][key] = old_config[key]

        return changes

    def _summarize_changes(self, change_details: Dict) -> str:
        """生成变更摘要"""
        parts = []
        if change_details['added']:
            parts.append(f"新增 {len(change_details['added'])} 个参数")
        if change_details['modified']:
            modified_keys = list(change_details['modified'].keys())
            parts.append(f"修改参数: {', '.join(modified_keys)}")
        if change_details['removed']:
            parts.append(f"删除 {len(change_details['removed'])} 个参数")
        return '; '.join(parts) if parts else "无变更"

    async def _check_usage(self, config_id: int) -> int:
        """检查配置使用情况"""
        # 检查是否有活跃的回测任务、实盘交易等
        # 这里简化处理，实际需要查询相关表
        return 0
```

#### 2. StrategyTemplateService

```python
# backend/app/services/strategy_template_service.py

from typing import List, Dict, Any, Optional
from app.repositories.strategy_template_repository import StrategyTemplateRepository


class StrategyTemplateService:
    """策略模板服务"""

    def __init__(self):
        self.template_repo = StrategyTemplateRepository()

    async def list_templates(
        self,
        strategy_type: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取模板列表"""
        filters = {}
        if strategy_type:
            filters['strategy_type'] = strategy_type
        if category:
            filters['category'] = category
        if difficulty:
            filters['difficulty'] = difficulty

        return await self.template_repo.list(filters)

    async def get_template(self, template_id: int) -> Dict[str, Any]:
        """获取模板详情"""
        return await self.template_repo.get_by_id(template_id)

    async def create_from_template(
        self,
        template_id: int,
        name: str,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """从模板创建策略配置"""
        from app.services.strategy_config_service import StrategyConfigService

        # 获取模板
        template = await self.get_template(template_id)

        # 增加使用次数
        await self.template_repo.increment_usage(template_id)

        # 创建配置
        config_service = StrategyConfigService()
        return await config_service.create_config(
            name=name,
            strategy_type=template['strategy_type'],
            config=template['default_config'],
            display_name=template['display_name'],
            description=f"基于模板: {template['template_name']}",
            category=template['category'],
            created_by=created_by
        )
```

### 新增Repository层

```python
# backend/app/repositories/strategy_config_repository.py

from typing import List, Dict, Any, Optional
from app.database.connection import get_db_connection


class StrategyConfigRepository:
    """策略配置数据访问层"""

    async def create(self, data: Dict[str, Any]) -> int:
        """创建配置"""
        query = """
            INSERT INTO strategy_configs (
                name, display_name, description, strategy_type,
                config, config_hash, version, category, tags,
                is_active, created_by
            )
            VALUES (
                %(name)s, %(display_name)s, %(description)s, %(strategy_type)s,
                %(config)s::jsonb, %(config_hash)s, %(version)s,
                %(category)s, %(tags)s, %(is_active)s, %(created_by)s
            )
            RETURNING id
        """

        async with get_db_connection() as conn:
            result = await conn.fetchrow(query, data)
            return result['id']

    async def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取配置"""
        query = """
            SELECT *
            FROM strategy_configs
            WHERE id = $1
        """

        async with get_db_connection() as conn:
            row = await conn.fetchrow(query, config_id)
            return dict(row) if row else None

    async def list(
        self,
        filters: Dict[str, Any],
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取配置列表"""
        # 构建WHERE子句
        where_clauses = []
        params = []
        param_idx = 1

        if 'strategy_type' in filters:
            where_clauses.append(f"strategy_type = ${param_idx}")
            params.append(filters['strategy_type'])
            param_idx += 1

        if 'category' in filters:
            where_clauses.append(f"category = ${param_idx}")
            params.append(filters['category'])
            param_idx += 1

        if 'is_active' in filters:
            where_clauses.append(f"is_active = ${param_idx}")
            params.append(filters['is_active'])
            param_idx += 1

        if 'tags' in filters:
            where_clauses.append(f"tags && ${param_idx}")
            params.append(filters['tags'])
            param_idx += 1

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM strategy_configs WHERE {where_sql}"

        # 查询数据
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT *
            FROM strategy_configs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([page_size, offset])

        async with get_db_connection() as conn:
            total = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(data_query, *params)

        return {
            'data': [dict(row) for row in rows],
            'meta': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        }

    async def update(self, config_id: int, updates: Dict[str, Any]):
        """更新配置"""
        # 构建SET子句
        set_clauses = []
        params = []
        param_idx = 1

        for key, value in updates.items():
            if key == 'config':
                set_clauses.append(f"{key} = ${param_idx}::jsonb")
            else:
                set_clauses.append(f"{key} = ${param_idx}")
            params.append(value)
            param_idx += 1

        # 添加 updated_at
        set_clauses.append("updated_at = NOW()")

        set_sql = ", ".join(set_clauses)
        query = f"""
            UPDATE strategy_configs
            SET {set_sql}
            WHERE id = ${param_idx}
        """
        params.append(config_id)

        async with get_db_connection() as conn:
            await conn.execute(query, *params)

    async def delete(self, config_id: int):
        """删除配置"""
        query = "DELETE FROM strategy_configs WHERE id = $1"

        async with get_db_connection() as conn:
            await conn.execute(query, config_id)
```

### API路由

```python
# backend/app/api/endpoints/strategy_config.py

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional

from app.services.strategy_config_service import StrategyConfigService
from app.models.strategy_config_models import (
    StrategyConfigCreate,
    StrategyConfigUpdate,
    StrategyConfigResponse
)

router = APIRouter(prefix="/api/v1/strategy-configs", tags=["Strategy Configs"])


@router.post("/", response_model=StrategyConfigResponse, status_code=201)
async def create_config(
    data: StrategyConfigCreate,
    service: StrategyConfigService = Depends()
):
    """创建策略配置"""
    try:
        result = await service.create_config(
            name=data.name,
            strategy_type=data.strategy_type,
            config=data.config,
            display_name=data.display_name,
            description=data.description,
            category=data.category,
            tags=data.tags
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_configs(
    strategy_type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: StrategyConfigService = Depends()
):
    """获取策略配置列表"""
    result = await service.list_configs(
        strategy_type=strategy_type,
        category=category,
        is_active=is_active,
        page=page,
        page_size=page_size
    )
    return {"success": True, **result}


@router.get("/{config_id}")
async def get_config(
    config_id: int,
    service: StrategyConfigService = Depends()
):
    """获取策略配置详情"""
    try:
        result = await service.get_config(config_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{config_id}")
async def update_config(
    config_id: int,
    data: StrategyConfigUpdate,
    service: StrategyConfigService = Depends()
):
    """更新策略配置"""
    try:
        result = await service.update_config(
            config_id=config_id,
            updates=data.dict(exclude_unset=True)
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    service: StrategyConfigService = Depends()
):
    """删除策略配置"""
    try:
        await service.delete_config(config_id)
        return {"success": True, "message": "策略删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{config_id}/clone")
async def clone_config(
    config_id: int,
    new_name: str,
    new_display_name: Optional[str] = None,
    service: StrategyConfigService = Depends()
):
    """克隆策略配置"""
    try:
        result = await service.clone_config(
            config_id=config_id,
            new_name=new_name,
            new_display_name=new_display_name
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 前端集成

### UI组件设计

#### 1. 策略配置列表页面

**功能**:
- 显示所有策略配置
- 支持筛选、搜索、排序
- 显示关键指标(最近回测结果)
- 快速操作(启用/禁用、编辑、删除)

**关键组件**:
```tsx
// StrategyConfigList.tsx
import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal } from 'antd';
import { useStrategyConfigs } from '@/hooks/useStrategyConfigs';

export const StrategyConfigList: React.FC = () => {
  const { configs, loading, filters, setFilters, deleteConfig } = useStrategyConfigs();

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'strategy_type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'status',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'gray'}>
          {active ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '最近回测',
      key: 'backtest',
      render: (_, record) => {
        if (!record.last_backtest_metrics) return '-';
        return (
          <Space>
            <span>收益: {(record.last_backtest_metrics.annual_return * 100).toFixed(2)}%</span>
            <span>夏普: {record.last_backtest_metrics.sharpe_ratio.toFixed(2)}</span>
          </Space>
        );
      }
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => handleEdit(record.id)}>编辑</Button>
          <Button size="small" onClick={() => handleClone(record.id)}>克隆</Button>
          <Button size="small" danger onClick={() => handleDelete(record.id)}>删除</Button>
        </Space>
      )
    }
  ];

  // ... 处理函数

  return (
    <div>
      {/* 筛选器 */}
      <FilterPanel filters={filters} onChange={setFilters} />

      {/* 表格 */}
      <Table
        columns={columns}
        dataSource={configs.data}
        loading={loading}
        pagination={{
          current: configs.meta.page,
          pageSize: configs.meta.page_size,
          total: configs.meta.total
        }}
      />
    </div>
  );
};
```

#### 2. 策略配置编辑表单

**功能**:
- 动态生成参数表单(根据策略类型)
- 实时参数验证
- 显示参数说明和范围
- 支持预览效果

**关键组件**:
```tsx
// StrategyConfigForm.tsx
import React, { useEffect } from 'react';
import { Form, Input, InputNumber, Switch, Select, Button } from 'antd';
import { useStrategyParameters } from '@/hooks/useStrategyParameters';

export const StrategyConfigForm: React.FC<{
  strategyType: string;
  initialValues?: any;
  onSubmit: (values: any) => void;
}> = ({ strategyType, initialValues, onSubmit }) => {
  const [form] = Form.useForm();
  const { parameters, loading } = useStrategyParameters(strategyType);

  // 根据参数类型渲染表单项
  const renderFormItem = (param: any) => {
    switch (param.type) {
      case 'integer':
        return (
          <InputNumber
            min={param.min_value}
            max={param.max_value}
            step={param.step || 1}
            style={{ width: '100%' }}
          />
        );
      case 'float':
        return (
          <InputNumber
            min={param.min_value}
            max={param.max_value}
            step={param.step || 0.01}
            style={{ width: '100%' }}
          />
        );
      case 'boolean':
        return <Switch />;
      case 'select':
        return (
          <Select>
            {param.options.map((opt: any) => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
        );
      default:
        return <Input />;
    }
  };

  // 按分类分组参数
  const parametersByCategory = parameters.reduce((acc, param) => {
    if (!acc[param.category]) acc[param.category] = [];
    acc[param.category].push(param);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues}
      onFinish={onSubmit}
    >
      {Object.entries(parametersByCategory).map(([category, params]) => (
        <div key={category}>
          <h3>{category}</h3>
          {params.map((param) => (
            <Form.Item
              key={param.name}
              name={['config', param.name]}
              label={param.label}
              help={param.description}
              rules={[
                { required: param.required, message: `请输入${param.label}` }
              ]}
            >
              {renderFormItem(param)}
            </Form.Item>
          ))}
        </div>
      ))}

      <Form.Item>
        <Button type="primary" htmlType="submit">
          保存
        </Button>
      </Form.Item>
    </Form>
  );
};
```

#### 3. 版本历史视图

**功能**:
- 显示配置变更历史
- 版本对比
- 一键回滚

**关键组件**:
```tsx
// StrategyVersionHistory.tsx
import React from 'react';
import { Timeline, Button, Modal } from 'antd';
import { useVersionHistory } from '@/hooks/useVersionHistory';

export const StrategyVersionHistory: React.FC<{ configId: number }> = ({ configId }) => {
  const { versions, loading, rollback } = useVersionHistory(configId);

  const handleRollback = (version: number) => {
    Modal.confirm({
      title: '确认回滚',
      content: `确定要回滚到版本 ${version} 吗?`,
      onOk: () => rollback(version)
    });
  };

  return (
    <Timeline>
      {versions.map((ver) => (
        <Timeline.Item key={ver.id} color={ver.version === versions[0].version ? 'green' : 'gray'}>
          <div>
            <strong>版本 {ver.version}</strong>
            {ver.version === versions[0].version && <Tag color="green">当前</Tag>}
          </div>
          <div>{ver.change_summary}</div>
          <div>{ver.created_at}</div>
          {ver.version !== versions[0].version && (
            <Button size="small" onClick={() => handleRollback(ver.version)}>
              回滚到此版本
            </Button>
          )}
        </Timeline.Item>
      ))}
    </Timeline>
  );
};
```

---

## 实施计划

### Phase 1: 数据库和Core层改造 (1-2周)

**任务**:
1. 创建数据库表结构
2. 实现 StrategyConfigLoader
3. 实现 StrategyFactory
4. 修改 BaseStrategy 支持配置加载
5. 编写单元测试

**交付物**:
- SQL migration 脚本
- Core 层新增组件
- 单元测试覆盖率 > 80%

### Phase 2: Backend层改造 (2-3周)

**任务**:
1. 实现 Service 层 (ConfigService, TemplateService)
2. 实现 Repository 层
3. 实现 API 路由
4. 添加参数验证逻辑
5. 集成测试

**交付物**:
- Backend API 实现
- API 文档 (Swagger)
- 集成测试

### Phase 3: 前端集成 (2-3周)

**任务**:
1. 实现策略配置列表页面
2. 实现配置编辑表单
3. 实现版本历史视图
4. 实现模板选择器
5. E2E 测试

**交付物**:
- 前端UI组件
- E2E 测试

### Phase 4: 测试和优化 (1周)

**任务**:
1. 性能测试
2. 压力测试
3. 安全测试
4. 优化查询性能
5. 完善文档

**交付物**:
- 测试报告
- 性能优化报告
- 完整文档

---

## 风险评估

### 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 数据库性能问题 | 高 | 中 | 1. 添加索引优化查询<br>2. 使用Redis缓存<br>3. 分页限制 |
| 配置一致性问题 | 高 | 中 | 1. 使用数据库事务<br>2. 配置哈希校验<br>3. 版本锁机制 |
| Core-Backend耦合 | 中 | 低 | 1. 保持API向后兼容<br>2. 支持本地配置回退 |
| 参数验证遗漏 | 中 | 中 | 1. JSON Schema验证<br>2. 前后端双重验证 |

### 业务风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 用户学习成本 | 中 | 高 | 1. 提供详细文档<br>2. 内置模板<br>3. 交互式教程 |
| 历史配置迁移 | 高 | 高 | 1. 提供迁移脚本<br>2. 支持批量导入<br>3. 向后兼容 |
| 权限管理缺失 | 中 | 中 | 1. 添加用户认证<br>2. 配置访问控制 |

### 运维风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 配置数据丢失 | 高 | 低 | 1. 定期备份<br>2. 版本快照<br>3. 导出功能 |
| 数据库迁移失败 | 高 | 低 | 1. 完整测试<br>2. 回滚计划<br>3. 蓝绿部署 |
| 缓存不一致 | 中 | 中 | 1. 主动失效<br>2. TTL设置<br>3. 监控告警 |

---

## 附录

### A. 配置示例库

#### A.1 保守型动量策略
```json
{
  "name": "momentum_conservative",
  "strategy_type": "momentum",
  "config": {
    "lookback_period": 20,
    "top_n": 30,
    "holding_period": 5,
    "filter_negative": true,
    "min_price": 5.0,
    "min_volume": 5000000,
    "max_position_pct": 0.15,
    "stop_loss_pct": -0.08
  },
  "category": "conservative"
}
```

#### A.2 激进型均值回归策略
```json
{
  "name": "mean_reversion_aggressive",
  "strategy_type": "mean_reversion",
  "config": {
    "lookback_period": 10,
    "z_score_threshold": -1.5,
    "top_n": 50,
    "holding_period": 3,
    "use_bollinger": true,
    "stop_loss_pct": -0.12
  },
  "category": "aggressive"
}
```

### B. JSON Schema 示例

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "lookback_period": {
      "type": "integer",
      "minimum": 5,
      "maximum": 60,
      "description": "动量计算回看期"
    },
    "top_n": {
      "type": "integer",
      "minimum": 5,
      "maximum": 200,
      "description": "每期选股数量"
    },
    "filter_negative": {
      "type": "boolean",
      "description": "是否过滤负动量"
    }
  },
  "required": ["lookback_period", "top_n"]
}
```

---

## 总结

本方案设计了一个完整的策略配置管理系统，核心优势包括:

1. **统一管理**: Backend 数据库作为配置的唯一数据源
2. **易于使用**: 前端Web界面管理，支持CRUD操作
3. **版本控制**: 完整的配置变更历史和回滚功能
4. **向后兼容**: 保持Core现有API不变
5. **可扩展**: 支持自定义策略类型和参数

实施后将显著提升策略配置的管理效率和系统的可维护性。

---

**文档状态**: ✅ 已完成初稿，待评审

**下一步**:
1. 团队评审本设计方案
2. 确定实施优先级和时间表
3. 分配开发任务
4. 启动 Phase 1 开发

**联系人**: Architecture Team
**更新日期**: 2026-02-08
