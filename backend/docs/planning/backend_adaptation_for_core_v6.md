# Backend适配Core v6.0架构变更方案

**文档版本**: v1.0.0
**创建日期**: 2026-02-09
**状态**: 📋 待实施
**优先级**: 🔴 P0 - 必须完成

---

## 📋 目录

- [变更概述](#变更概述)
- [Core v6.0重大变化](#core-v60重大变化)
- [Backend受影响模块](#backend受影响模块)
- [迁移方案](#迁移方案)
- [API变更](#api变更)
- [实施计划](#实施计划)
- [风险与缓解](#风险与缓解)

---

## 变更概述

### 背景

Core项目已完成v6.0版本重构（2026-02-08），策略系统架构发生重大变化。Backend项目需要适配这些变化以保持兼容性。

### 核心问题

1. ❌ **Three Layer架构已被移除**
   - Backend仍在使用 `/api/three-layer/*` 端点
   - `ThreeLayerAdapter` 已失效
   - Core不再提供三层架构支持

2. ⚠️ **策略创建方式变更**
   - 旧方式: 基于三层架构组合
   - 新方式: 三种策略类型（预定义/配置驱动/动态代码）

3. ⚠️ **回测接口变更**
   - 旧: `BacktestEngine.backtest_three_layer()`
   - 新: `BacktestEngine.run(strategy, ...)`

---

## Core v6.0重大变化

### 1. Three Layer架构移除

#### 旧架构 (Backend仍在使用)
```
StockSelector → EntryStrategy → ExitStrategy
     ↓              ↓              ↓
   StrategyComposer.compose()
     ↓
BacktestEngine.backtest_three_layer()
```

#### 新架构 (Core v6.0)
```
StrategyFactory
├── create('momentum', config)           # 预定义策略
├── create_from_config(config_id=123)    # 配置驱动策略
└── create_from_code(strategy_id=456)    # 动态代码策略
     ↓
BacktestEngine.run(strategy, ...)
```

**影响范围**:
- ❌ `core.strategies.three_layer.*` 已不存在
- ❌ `StrategyComposer` 已移除
- ❌ `BacktestEngine.backtest_three_layer()` 已移除

### 2. 新增三种策略类型

#### (1) 预定义策略 (Predefined Strategies)

**特点**: 硬编码的策略类，性能最优

**Core使用方式**:
```python
from core.strategies import StrategyFactory

factory = StrategyFactory()
strategy = factory.create('momentum', {
    'lookback_period': 20,
    'threshold': 0.10,
    'top_n': 20
})
```

**可用策略**:
- `momentum` - 动量策略
- `mean_reversion` - 均值回归
- `multi_factor` - 多因子策略

#### (2) 配置驱动策略 (Configured Strategies)

**特点**: 从数据库加载参数配置

**数据流程**:
```
Backend API → strategy_configs表 → Core ConfigLoader → 实例化预定义策略类
```

**数据库表结构** (需要新增):
```sql
CREATE TABLE strategy_configs (
    id SERIAL PRIMARY KEY,
    strategy_type VARCHAR(50) NOT NULL,     -- 'momentum', 'mean_reversion', etc.
    config JSONB NOT NULL,                  -- 策略参数
    name VARCHAR(200),
    description TEXT,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Core使用方式**:
```python
factory = StrategyFactory()
strategy = factory.create_from_config(config_id=123)
```

#### (3) 动态代码策略 (Dynamic Strategies)

**特点**: 动态加载Python代码（支持AI生成）

**数据流程**:
```
Backend API → dynamic_strategies表 → Core DynamicCodeLoader → 安全验证 → 动态编译执行
```

**数据库表结构** (需要新增):
```sql
CREATE TABLE dynamic_strategies (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(200) NOT NULL UNIQUE,
    class_name VARCHAR(100) NOT NULL,
    generated_code TEXT NOT NULL,           -- Python策略类代码
    code_hash VARCHAR(64),
    validation_status VARCHAR(20),
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Core使用方式**:
```python
factory = StrategyFactory()
strategy = factory.create_from_code(strategy_id=456)
```

### 3. 回测接口变更

#### 旧接口 (已移除)
```python
from core.backtest import BacktestEngine

engine = BacktestEngine()
result = engine.backtest_three_layer(
    selector=momentum_selector,
    entry=immediate_entry,
    exit=stop_loss_exit,
    stock_pool=stocks,
    ...
)
```

#### 新接口
```python
from core.strategies import StrategyFactory
from core.backtest import BacktestEngine

factory = StrategyFactory()
strategy = factory.create('momentum', config)

engine = BacktestEngine()
result = engine.run(
    strategy=strategy,
    stock_pool=stocks,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 4. 新增安全防护体系

Core v6.0为动态代码策略新增了多层安全机制：

| 组件 | 功能 |
|------|------|
| **CodeSanitizer** | AST代码分析、危险操作检测 |
| **PermissionChecker** | 权限检查、白名单验证 |
| **ResourceLimiter** | CPU/内存/时间资源限制 |
| **AuditLogger** | 完整审计日志 |

**Backend无需关心这些细节**，Core会自动处理安全验证。

### 5. 性能优化特性

Core v6.0新增性能优化层：

| 特性 | 性能提升 |
|------|---------|
| Redis缓存 | 500x (缓存命中) |
| 批量加载 | 25x |
| 懒加载 | 20x 启动时间 |

**Backend需要配置Redis连接**以使用缓存功能。

---

## Backend受影响模块

### 🔴 需要移除的模块

| 模块 | 文件路径 | 原因 |
|------|---------|------|
| **ThreeLayerAdapter** | `backend/app/core_adapters/three_layer_adapter.py` | Core已移除三层架构 |
| **Three Layer API** | `backend/app/api/v1/three_layer.py` | 依赖已移除的Adapter |
| **Three Layer测试** | `backend/tests/unit/core_adapters/test_three_layer_adapter.py` | 依赖已移除的功能 |
| **Three Layer集成测试** | `backend/tests/integration/test_three_layer_backtest.py` | 依赖已移除的功能 |

**影响统计**:
- 移除文件: 4+
- 移除测试用例: 129个
- 移除API端点: 5个
- 移除文档章节: Backend README中的"三层架构回测"部分

### 🟡 需要重构的模块

| 模块 | 原因 | 新方案 |
|------|------|--------|
| **StrategyAdapter** | 策略创建方式变更 | 适配StrategyFactory三种方法 |
| **BacktestAdapter** | 回测接口变更 | 使用新的 `engine.run()` |
| **策略管理API** | 需要支持新的三种策略类型 | 新增配置驱动和动态代码策略API |

### 🟢 需要新增的模块

| 模块 | 说明 | 优先级 |
|------|------|--------|
| **ConfigStrategyAdapter** | 配置驱动策略适配器 | P0 |
| **DynamicStrategyAdapter** | 动态代码策略适配器 | P1 |
| **策略配置API** | CRUD操作 strategy_configs表 | P0 |
| **动态策略API** | CRUD操作 dynamic_strategies表 | P1 |
| **AI策略生成API** | 调用DeepSeek生成代码（如规划文档所述） | P2 |

---

## 迁移方案

### Phase 1: 移除Three Layer相关代码 (1-2天)

#### Step 1: 标记废弃API

在移除前，先标记API为deprecated：

```python
# backend/app/api/v1/three_layer.py

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/selectors", deprecated=True)
async def get_selectors():
    """
    ⚠️ DEPRECATED: This endpoint is deprecated as of v4.0.
    The Three Layer architecture has been removed from Core v6.0.
    Please use the new Strategy API instead.
    """
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error": "API Deprecated",
            "message": "Three Layer architecture has been removed. Use /api/strategies instead.",
            "migration_guide": "https://docs.example.com/migration-v4"
        }
    )
```

#### Step 2: 通知前端团队

发送迁移通知：
- Three Layer API将在v4.0移除
- 提供迁移文档链接
- 给予2周缓冲期

#### Step 3: 移除代码

```bash
# 移除Three Layer相关文件
rm backend/app/core_adapters/three_layer_adapter.py
rm backend/app/api/v1/three_layer.py
rm backend/tests/unit/core_adapters/test_three_layer_adapter.py
rm backend/tests/integration/test_three_layer_backtest.py

# 更新文档
# - 从 backend/docs/README.md 移除三层架构章节
# - 从 backend/docs/api_reference/README.md 移除相关端点
```

#### Step 4: 更新文档

修改 `backend/docs/README.md`:

```markdown
## 🏛️ 当前架构

Backend (3,000 行)
├── Core Adapters（薄层封装）
│   ├── DataAdapter
│   ├── FeatureAdapter
│   ├── BacktestAdapter
│   ├── MarketAdapter
│   ├── ModelAdapter
│   ├── ConfigStrategyAdapter ⭐ 新增
│   └── DynamicStrategyAdapter ⭐ 新增
├── REST API 层
├── 缓存层（Redis）
└── 监控层（Prometheus）
```

### Phase 2: 新增数据库表 (0.5天)

#### 创建Migration脚本

```sql
-- backend/migrations/V004__add_strategy_configs_and_dynamic_strategies.sql

-- 1. 策略配置表 (Configured Strategies)
CREATE TABLE IF NOT EXISTS strategy_configs (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    strategy_type VARCHAR(50) NOT NULL,              -- 预定义策略类型: 'momentum', 'mean_reversion', 'multi_factor'
    config JSONB NOT NULL,                           -- 策略参数配置

    -- 元数据
    name VARCHAR(200),
    description TEXT,
    category VARCHAR(50),
    tags VARCHAR(100)[],

    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active',             -- active, archived, deprecated

    -- 版本
    version INT DEFAULT 1,
    parent_id INT REFERENCES strategy_configs(id),

    -- 绩效指标 (最近一次回测)
    last_backtest_metrics JSONB,
    last_backtest_date TIMESTAMP,

    -- 审计字段
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN ('momentum', 'mean_reversion', 'multi_factor')
    )
);

-- 索引
CREATE INDEX idx_strategy_configs_type ON strategy_configs(strategy_type);
CREATE INDEX idx_strategy_configs_enabled ON strategy_configs(is_enabled);
CREATE INDEX idx_strategy_configs_status ON strategy_configs(status);
CREATE INDEX idx_strategy_configs_created ON strategy_configs(created_at DESC);

-- 2. 动态代码策略表 (Dynamic Strategies)
CREATE TABLE IF NOT EXISTS dynamic_strategies (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    strategy_name VARCHAR(200) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    class_name VARCHAR(100) NOT NULL,

    -- 代码
    generated_code TEXT NOT NULL,                    -- Python策略类代码
    code_hash VARCHAR(64),

    -- AI生成信息 (如果适用)
    user_prompt TEXT,                                -- 用户的自然语言描述
    ai_model VARCHAR(50),                            -- 'deepseek-coder', 'gpt-4', etc.
    ai_prompt TEXT,                                  -- 完整的AI Prompt
    generation_tokens INT,
    generation_cost DECIMAL(10, 4),

    -- 验证状态
    validation_status VARCHAR(20) DEFAULT 'pending', -- pending, passed, failed, warning
    validation_errors JSONB,
    validation_warnings JSONB,

    -- 测试结果
    test_status VARCHAR(20),                         -- untested, passed, failed
    test_results JSONB,

    -- 绩效指标
    last_backtest_metrics JSONB,
    last_backtest_date TIMESTAMP,

    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'draft',              -- draft, active, archived, deprecated

    -- 版本
    version INT DEFAULT 1,
    parent_id INT REFERENCES dynamic_strategies(id),

    -- 审计字段
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 元数据
    tags VARCHAR(100)[],
    category VARCHAR(50),

    -- 约束
    CONSTRAINT valid_validation_status CHECK (
        validation_status IN ('pending', 'passed', 'failed', 'warning')
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('draft', 'active', 'archived', 'deprecated')
    )
);

-- 索引
CREATE INDEX idx_dynamic_strat_name ON dynamic_strategies(strategy_name);
CREATE INDEX idx_dynamic_strat_class ON dynamic_strategies(class_name);
CREATE INDEX idx_dynamic_strat_enabled ON dynamic_strategies(is_enabled);
CREATE INDEX idx_dynamic_strat_validation ON dynamic_strategies(validation_status);
CREATE INDEX idx_dynamic_strat_created ON dynamic_strategies(created_at DESC);
CREATE INDEX idx_dynamic_strat_tags ON dynamic_strategies USING GIN(tags);

-- 3. 策略执行记录表 (统一记录所有类型策略的执行)
CREATE TABLE IF NOT EXISTS strategy_executions (
    id BIGSERIAL PRIMARY KEY,

    -- 策略引用 (三选一)
    predefined_strategy_type VARCHAR(50),            -- 预定义策略: 'momentum', etc.
    config_strategy_id INT REFERENCES strategy_configs(id) ON DELETE SET NULL,
    dynamic_strategy_id INT REFERENCES dynamic_strategies(id) ON DELETE SET NULL,

    -- 执行类型
    execution_type VARCHAR(20) NOT NULL,             -- backtest, paper_trading, live_trading

    -- 执行参数
    execution_params JSONB NOT NULL,

    -- 执行结果
    status VARCHAR(20) DEFAULT 'pending',            -- pending, running, completed, failed
    result JSONB,
    metrics JSONB,
    error_message TEXT,

    -- 性能
    execution_duration_ms INT,

    -- 审计
    executed_by VARCHAR(100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_exec_type CHECK (
        execution_type IN ('backtest', 'paper_trading', 'live_trading', 'validation')
    ),
    CONSTRAINT valid_exec_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    ),
    -- 确保至少有一个策略类型被设置
    CONSTRAINT at_least_one_strategy CHECK (
        (predefined_strategy_type IS NOT NULL)::int +
        (config_strategy_id IS NOT NULL)::int +
        (dynamic_strategy_id IS NOT NULL)::int = 1
    )
);

-- 索引
CREATE INDEX idx_exec_config_strat ON strategy_executions(config_strategy_id, created_at DESC);
CREATE INDEX idx_exec_dynamic_strat ON strategy_executions(dynamic_strategy_id, created_at DESC);
CREATE INDEX idx_exec_type ON strategy_executions(execution_type);
CREATE INDEX idx_exec_status ON strategy_executions(status);
CREATE INDEX idx_exec_created ON strategy_executions(created_at DESC);
```

### Phase 3: 新增Core Adapters (2-3天)

#### (1) ConfigStrategyAdapter

```python
# backend/app/core_adapters/config_strategy_adapter.py

from typing import Dict, Any, Optional
from loguru import logger

from core.strategies import StrategyFactory
from core.strategies.base_strategy import BaseStrategy
from app.repositories.strategy_config_repository import StrategyConfigRepository
from app.core.exceptions import AdapterError


class ConfigStrategyAdapter:
    """配置驱动策略适配器"""

    def __init__(self):
        self.factory = StrategyFactory()
        self.repo = StrategyConfigRepository()

    async def create_strategy_from_config(self, config_id: int) -> BaseStrategy:
        """
        从配置创建策略

        Args:
            config_id: 配置ID

        Returns:
            策略实例
        """
        try:
            # 从数据库加载配置
            config_data = await self.repo.get_by_id(config_id)

            if not config_data:
                raise AdapterError(f"配置不存在: {config_id}")

            if not config_data['is_enabled']:
                raise AdapterError(f"配置已禁用: {config_id}")

            # 调用Core的StrategyFactory
            strategy = self.factory.create_from_config(config_id=config_id)

            logger.info(f"成功创建配置驱动策略: config_id={config_id}")

            return strategy

        except Exception as e:
            logger.error(f"创建配置驱动策略失败: {e}")
            raise AdapterError(f"创建策略失败: {str(e)}")

    async def get_available_strategy_types(self) -> list:
        """
        获取可用的预定义策略类型

        Returns:
            策略类型列表
        """
        return [
            {
                'type': 'momentum',
                'name': '动量策略',
                'description': '选择近期涨幅最大的股票',
                'default_params': {
                    'lookback_period': 20,
                    'threshold': 0.10,
                    'top_n': 20
                }
            },
            {
                'type': 'mean_reversion',
                'name': '均值回归策略',
                'description': '选择偏离均值的股票',
                'default_params': {
                    'lookback_period': 20,
                    'std_threshold': 2.0,
                    'top_n': 20
                }
            },
            {
                'type': 'multi_factor',
                'name': '多因子策略',
                'description': '综合多个因子进行选股',
                'default_params': {
                    'factors': ['momentum', 'value', 'quality'],
                    'weights': [0.4, 0.3, 0.3],
                    'top_n': 30
                }
            }
        ]
```

#### (2) DynamicStrategyAdapter

```python
# backend/app/core_adapters/dynamic_strategy_adapter.py

from typing import Dict, Any
from loguru import logger

from core.strategies import StrategyFactory
from core.strategies.base_strategy import BaseStrategy
from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository
from app.core.exceptions import AdapterError, SecurityError


class DynamicStrategyAdapter:
    """动态代码策略适配器"""

    def __init__(self):
        self.factory = StrategyFactory()
        self.repo = DynamicStrategyRepository()

    async def create_strategy_from_code(
        self,
        strategy_id: int,
        strict_mode: bool = True
    ) -> BaseStrategy:
        """
        从动态代码创建策略

        Args:
            strategy_id: 策略ID
            strict_mode: 严格模式（任何安全问题都拒绝）

        Returns:
            策略实例

        Raises:
            AdapterError: 策略不存在或已禁用
            SecurityError: 安全验证失败
        """
        try:
            # 从数据库加载策略
            strategy_data = await self.repo.get_by_id(strategy_id)

            if not strategy_data:
                raise AdapterError(f"策略不存在: {strategy_id}")

            if not strategy_data['is_enabled']:
                raise AdapterError(f"策略已禁用: {strategy_id}")

            # 检查验证状态
            if strategy_data['validation_status'] == 'failed':
                raise SecurityError(f"策略验证失败: {strategy_id}")

            # 调用Core的StrategyFactory
            # Core会自动进行安全验证
            strategy = self.factory.create_from_code(
                strategy_id=strategy_id,
                strict_mode=strict_mode
            )

            logger.info(f"成功创建动态代码策略: strategy_id={strategy_id}")

            return strategy

        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"创建动态代码策略失败: {e}")
            raise AdapterError(f"创建策略失败: {str(e)}")

    async def get_strategy_metadata(self, strategy_id: int) -> Dict[str, Any]:
        """
        获取策略元信息（包括安全审计信息）

        Args:
            strategy_id: 策略ID

        Returns:
            元信息字典
        """
        strategy_data = await self.repo.get_by_id(strategy_id)

        if not strategy_data:
            raise AdapterError(f"策略不存在: {strategy_id}")

        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy_data['strategy_name'],
            'class_name': strategy_data['class_name'],
            'validation_status': strategy_data['validation_status'],
            'test_status': strategy_data['test_status'],
            'code_hash': strategy_data['code_hash'],
            'created_at': strategy_data['created_at'],
            'last_backtest_metrics': strategy_data.get('last_backtest_metrics')
        }
```

#### (3) 重构BacktestAdapter

```python
# backend/app/core_adapters/backtest_adapter.py

from typing import Dict, Any, Optional
from loguru import logger

from core.backtest import BacktestEngine
from core.strategies.base_strategy import BaseStrategy
from app.core_adapters.config_strategy_adapter import ConfigStrategyAdapter
from app.core_adapters.dynamic_strategy_adapter import DynamicStrategyAdapter


class BacktestAdapter:
    """回测适配器"""

    def __init__(self):
        self.engine = BacktestEngine()
        self.config_adapter = ConfigStrategyAdapter()
        self.dynamic_adapter = DynamicStrategyAdapter()

    async def run_backtest(
        self,
        strategy_type: str,                       # 'predefined', 'config', 'dynamic'
        strategy_id: Optional[int] = None,        # config_id 或 dynamic_strategy_id
        strategy_name: Optional[str] = None,      # 预定义策略名称
        strategy_config: Optional[Dict] = None,   # 预定义策略配置
        stock_pool: list,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        运行回测（统一接口支持三种策略类型）

        Args:
            strategy_type: 策略类型 ('predefined', 'config', 'dynamic')
            strategy_id: 配置ID或动态策略ID
            strategy_name: 预定义策略名称
            strategy_config: 预定义策略配置
            stock_pool: 股票池
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金

        Returns:
            回测结果
        """
        try:
            # 1. 创建策略实例
            strategy = await self._create_strategy(
                strategy_type=strategy_type,
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                strategy_config=strategy_config
            )

            # 2. 加载市场数据
            from app.core_adapters.data_adapter import DataAdapter
            data_adapter = DataAdapter()

            market_data = await data_adapter.load_market_data(
                stock_codes=stock_pool,
                start_date=start_date,
                end_date=end_date
            )

            # 3. 运行回测
            logger.info(f"开始回测: strategy_type={strategy_type}, stocks={len(stock_pool)}, period={start_date} to {end_date}")

            result = self.engine.run(
                strategy=strategy,
                stock_pool=stock_pool,
                market_data=market_data,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                **kwargs
            )

            logger.success(f"回测完成: total_return={result.total_return:.2%}, sharpe={result.sharpe_ratio:.2f}")

            # 4. 格式化结果
            return {
                'metrics': {
                    'total_return': result.total_return,
                    'annual_return': result.annual_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                },
                'equity_curve': result.equity_curve.to_dict(),
                'trades': result.trades.to_dict('records') if hasattr(result, 'trades') else [],
                'daily_portfolio': result.daily_portfolio.to_dict() if hasattr(result, 'daily_portfolio') else {}
            }

        except Exception as e:
            logger.error(f"回测失败: {e}")
            raise

    async def _create_strategy(
        self,
        strategy_type: str,
        strategy_id: Optional[int],
        strategy_name: Optional[str],
        strategy_config: Optional[Dict]
    ) -> BaseStrategy:
        """根据策略类型创建策略实例"""

        if strategy_type == 'predefined':
            # 预定义策略
            if not strategy_name:
                raise ValueError("预定义策略需要提供 strategy_name")

            from core.strategies import StrategyFactory
            factory = StrategyFactory()
            return factory.create(strategy_name, strategy_config or {})

        elif strategy_type == 'config':
            # 配置驱动策略
            if not strategy_id:
                raise ValueError("配置驱动策略需要提供 strategy_id (config_id)")

            return await self.config_adapter.create_strategy_from_config(strategy_id)

        elif strategy_type == 'dynamic':
            # 动态代码策略
            if not strategy_id:
                raise ValueError("动态代码策略需要提供 strategy_id")

            return await self.dynamic_adapter.create_strategy_from_code(strategy_id)

        else:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
```

### Phase 4: 新增API端点 (2-3天)

#### (1) 策略配置API

```python
# backend/app/api/v1/strategy_configs.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field

from app.core_adapters.config_strategy_adapter import ConfigStrategyAdapter
from app.repositories.strategy_config_repository import StrategyConfigRepository

router = APIRouter(prefix="/strategy-configs", tags=["Strategy Configs"])


class StrategyConfigCreate(BaseModel):
    strategy_type: str = Field(..., description="策略类型: momentum, mean_reversion, multi_factor")
    config: dict = Field(..., description="策略参数")
    name: Optional[str] = None
    description: Optional[str] = None


class StrategyConfigUpdate(BaseModel):
    config: Optional[dict] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


@router.get("/types")
async def get_strategy_types():
    """获取可用的策略类型"""
    adapter = ConfigStrategyAdapter()
    types = await adapter.get_available_strategy_types()
    return {"success": True, "data": types}


@router.post("", status_code=201)
async def create_config(data: StrategyConfigCreate):
    """创建策略配置"""
    repo = StrategyConfigRepository()

    config_id = await repo.create({
        'strategy_type': data.strategy_type,
        'config': data.config,
        'name': data.name,
        'description': data.description
    })

    return {
        "success": True,
        "data": {"config_id": config_id}
    }


@router.get("")
async def list_configs(
    strategy_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取配置列表"""
    repo = StrategyConfigRepository()

    configs = await repo.list(
        strategy_type=strategy_type,
        is_enabled=is_enabled,
        page=page,
        page_size=page_size
    )

    return {"success": True, "data": configs['items'], "meta": configs['meta']}


@router.get("/{config_id}")
async def get_config(config_id: int):
    """获取配置详情"""
    repo = StrategyConfigRepository()
    config = await repo.get_by_id(config_id)

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    return {"success": True, "data": config}


@router.put("/{config_id}")
async def update_config(config_id: int, data: StrategyConfigUpdate):
    """更新配置"""
    repo = StrategyConfigRepository()

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供更新数据")

    await repo.update(config_id, update_data)

    return {"success": True, "message": "配置更新成功"}


@router.delete("/{config_id}")
async def delete_config(config_id: int):
    """删除配置"""
    repo = StrategyConfigRepository()
    await repo.delete(config_id)

    return {"success": True, "message": "配置删除成功"}
```

#### (2) 动态策略API

```python
# backend/app/api/v1/dynamic_strategies.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository
from app.services.code_validator import CodeValidator

router = APIRouter(prefix="/dynamic-strategies", tags=["Dynamic Strategies"])


class DynamicStrategyCreate(BaseModel):
    strategy_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    class_name: str
    generated_code: str


@router.post("", status_code=201)
async def create_dynamic_strategy(data: DynamicStrategyCreate):
    """创建动态代码策略"""

    # 1. 验证代码
    validator = CodeValidator()
    validation_result = await validator.validate(data.generated_code)

    if validation_result['status'] == 'failed':
        return {
            "success": False,
            "message": "代码验证失败",
            "validation": validation_result
        }

    # 2. 保存到数据库
    repo = DynamicStrategyRepository()

    strategy_id = await repo.create({
        'strategy_name': data.strategy_name,
        'display_name': data.display_name,
        'description': data.description,
        'class_name': data.class_name,
        'generated_code': data.generated_code,
        'validation_status': validation_result['status'],
        'validation_errors': validation_result.get('errors'),
        'validation_warnings': validation_result.get('warnings')
    })

    return {
        "success": True,
        "data": {
            "strategy_id": strategy_id,
            "validation": validation_result
        }
    }


@router.get("")
async def list_dynamic_strategies():
    """获取动态策略列表"""
    repo = DynamicStrategyRepository()
    strategies = await repo.list()

    return {"success": True, "data": strategies}


@router.get("/{strategy_id}")
async def get_dynamic_strategy(strategy_id: int):
    """获取动态策略详情"""
    repo = DynamicStrategyRepository()
    strategy = await repo.get_by_id(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    return {"success": True, "data": strategy}
```

#### (3) 统一回测API

```python
# backend/app/api/v1/backtest.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from app.core_adapters.backtest_adapter import BacktestAdapter

router = APIRouter(prefix="/backtest", tags=["Backtest"])


class BacktestRequest(BaseModel):
    # 策略选择 (三选一)
    strategy_type: str = Field(..., description="策略类型: predefined, config, dynamic")
    strategy_id: Optional[int] = Field(None, description="配置ID��动态策略ID")
    strategy_name: Optional[str] = Field(None, description="预定义策略名称")
    strategy_config: Optional[dict] = Field(None, description="预定义策略配置")

    # 回测参数
    stock_pool: List[str] = Field(..., description="股票代码列表")
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0


@router.post("")
async def run_backtest(request: BacktestRequest):
    """运行回测（统一接口）"""

    adapter = BacktestAdapter()

    try:
        result = await adapter.run_backtest(
            strategy_type=request.strategy_type,
            strategy_id=request.strategy_id,
            strategy_name=request.strategy_name,
            strategy_config=request.strategy_config,
            stock_pool=request.stock_pool,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital
        )

        return {"success": True, "data": result}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测失败: {str(e)}")
```

### Phase 5: 更新文档 (1天)

#### 更新Backend README

```markdown
# Stock-Analysis Backend 文档中心

**版本**: v4.0.0
**最后更新**: 2026-02-09

## 🎉 项目状态

Backend 项目已完成Core v6.0适配，支持三种策略类型！

## 🏛️ 当前架构

Backend 通过薄层Adapters集成Core v6.0的新策略系统。

### 三种策略类型

| 策略类型 | 说明 | 适用场景 |
|---------|------|---------|
| **预定义策略** | 硬编码策略，性能最优 | 标准策略、生产环境 |
| **配置驱动策略** | 从数据库加载参数配置 | 参数调优、A/B测试 |
| **动态代码策略** | 动态加载Python代码 | 创新策略、AI生成 |

### API端点

| 模块 | 端点前缀 | 功能 |
|------|---------|------|
| 策略配置 | `/api/strategy-configs` | 配置驱动策略CRUD |
| 动态策略 | `/api/dynamic-strategies` | 动态代码策略CRUD |
| 回测引擎 | `/api/backtest` | 统一回测接口 |

## 🔄 迁移指南

### 从Three Layer迁移

⚠️ **重要**: Three Layer架构已在v4.0移除。

#### 旧方式 (已废弃)
\`\`\`http
POST /api/three-layer/backtest
{
  "selector": {"id": "momentum", "params": {...}},
  "entry": {"id": "immediate", "params": {}},
  "exit": {"id": "fixed_stop_loss", "params": {...}}
}
\`\`\`

#### 新方式 (推荐)
\`\`\`http
POST /api/backtest
{
  "strategy_type": "predefined",
  "strategy_name": "momentum",
  "strategy_config": {"lookback_period": 20, "top_n": 50},
  "stock_pool": ["000001.SZ", "600000.SH"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31"
}
\`\`\`

详见: [完整迁移指南](./docs/migration/v3_to_v4.md)
```

---

## API变更

### 移除的API端点

| 端点 | 状态 | 替代方案 |
|------|------|---------|
| `GET /api/three-layer/selectors` | ❌ 已移除 | `GET /api/strategy-configs/types` |
| `GET /api/three-layer/entries` | ❌ 已移除 | 无需替代（预定义策略内置） |
| `GET /api/three-layer/exits` | ❌ 已移除 | 无需替代（预定义策略内置） |
| `POST /api/three-layer/validate` | ❌ 已移除 | `POST /api/dynamic-strategies` (自动验证) |
| `POST /api/three-layer/backtest` | ❌ 已移除 | `POST /api/backtest` |

### 新增的API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/strategy-configs/types` | GET | 获取可用的预定义策略类型 |
| `/api/strategy-configs` | POST | 创建策略配置 |
| `/api/strategy-configs` | GET | 获取配置列表 |
| `/api/strategy-configs/{id}` | GET | 获取配置详情 |
| `/api/strategy-configs/{id}` | PUT | 更新配置 |
| `/api/strategy-configs/{id}` | DELETE | 删除配置 |
| `/api/dynamic-strategies` | POST | 创建动态代码策略 |
| `/api/dynamic-strategies` | GET | 获取动态策略列表 |
| `/api/dynamic-strategies/{id}` | GET | 获取动态策略详情 |
| `/api/backtest` | POST | 统一回测接口（支持三种策略类型） |

---

## 实施计划

### Phase 1: 移除Three Layer (1-2天) ✅ 优先

- [x] 标记Three Layer API为deprecated
- [x] 通知前端团队
- [ ] 移除ThreeLayerAdapter及相关文件
- [ ] 移除测试用例
- [ ] 更新文档

### Phase 2: 数据库Migration (0.5天) 🔄 进行中

- [ ] 创建migration脚本
- [ ] 运行migration
- [ ] 验证表结构

### Phase 3: 新增Adapters (2-3天) ⏳ 待开始

- [ ] ConfigStrategyAdapter
- [ ] DynamicStrategyAdapter
- [ ] 重构BacktestAdapter
- [ ] 单元测试

### Phase 4: 新增API端点 (2-3天) ⏳ 待开始

- [ ] 策略配置API
- [ ] 动态策略API
- [ ] 统一回测API
- [ ] API测试

### Phase 5: 更新文档 (1天) ⏳ 待开始

- [ ] 更新Backend README
- [ ] 编写迁移指南
- [ ] 更新API文档
- [ ] 更新架构图

**总工期**: 7-10天
**优先级**: P0 - 必须完成

---

## 风险与缓解

### 风险1: 前端依赖Three Layer API

**影响**: 高
**概率**: 高

**缓解措施**:
1. 提前2周通知前端团队
2. 提供详细迁移文档
3. 保留deprecated API 1个版本周期
4. 提供前端适配支持

### 风险2: 现有回测结果不兼容

**影响**: 中
**概率**: 中

**缓解措施**:
1. 保留旧数据库表结构
2. 新增字段标识策略类型
3. 提供数据迁移脚本

### 风险3: Core v6.0 API变更

**影响**: 高
**概率**: 低

**缓解措施**:
1. 与Core团队保持同步
2. 阅读Core v6.0完整文档
3. 进行端到端测试

### 风险4: 性能回归

**影响**: 中
**概率**: 低

**缓解措施**:
1. 配置Redis缓存（Core v6.0支持）
2. 性能基准测试
3. 监控API响应时间

---

## 测试计划

### 单元测试

| 模块 | 测试用例数 | 覆盖率目标 |
|------|-----------|----------|
| ConfigStrategyAdapter | 15 | 90%+ |
| DynamicStrategyAdapter | 20 | 90%+ |
| BacktestAdapter | 25 | 90%+ |
| 策略配置API | 20 | 95%+ |
| 动态策略API | 25 | 95%+ |
| 回测API | 30 | 95%+ |

### 集成测试

- [ ] 预定义策略回测端到端测试
- [ ] 配置驱动策略回测端到端测试
- [ ] 动态代码策略回测端到端测试
- [ ] 数据库CRUD操作测试
- [ ] API并发测试

### 性能测试

- [ ] 策略创建性能基准
- [ ] 回测性能基准
- [ ] Redis缓存效果验证

---

## 成功标准

- ✅ 所有Three Layer相关代码已移除
- ✅ 新增数据库表已创建并验证
- ✅ 三种策略类型均可正常创建和回测
- ✅ 单元测试覆盖率 >90%
- ✅ 集成测试100%通过
- ✅ API文档已更新
- ✅ 前端团队完成适配
- ✅ 生产环境部署成功

---

**文档维护**: Backend Team
**审核人**: Architecture Team
**下次评审**: Phase 1完成后
