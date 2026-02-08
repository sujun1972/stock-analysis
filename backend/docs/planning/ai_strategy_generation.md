# AI驱动的策略代码生成系统设计方案

**文档版本**: v1.0.0
**创建日期**: 2026-02-08
**作者**: Architecture Team
**状态**: 📋 设计阶段 - 待评审

---

## 📋 目录

- [概述](#概述)
- [需求分析](#需求分析)
- [核心流程](#核心流程)
- [架构设计](#架构设计)
- [数据库设计](#数据库设计)
- [AI代码生成](#ai代码生成)
- [代码验证与执行](#代码验证与执行)
- [API设计](#api设计)
- [前端集成](#前端集成)
- [安全性设计](#安全性设计)
- [实施计划](#实施计划)

---

## 概述

### 背景

用户希望通过**自然语言描述**来创建量化交易策略，系统自动生成可执行的策略代码。

**示例输入**:
> "小盘股，市盈率在30以下，股价格在20日均线以下"

**期望输出**:
- 生成符合 Core 策略框架的 Python 代码
- 代码可直接加载到系统中运行
- 支持回测和实盘交易

### 核心目标

1. ✅ **自然语言输入**: 用户通过Web UI用文字描述策略逻辑
2. ✅ **AI代码生成**: 调用 DeepSeek API 生成策略类代码
3. ✅ **代码验证**: 自动验证生成的代码语法、安全性和逻辑正确性
4. ✅ **动态加载**: 将生成的代码动态加载到系统中
5. ✅ **版本管理**: 保存策略代码的历史版本
6. ✅ **迭代优化**: 支持用户反馈和AI迭代改进

### 与原方案的区别

| 维度 | 原方案(参数配置) | 新方案(AI代码生成) |
|------|-----------------|-------------------|
| **输入方式** | 调整预定义参数 | 自然语言描述 |
| **输出结果** | 配置JSON | Python策略类代码 |
| **灵活性** | 受限于预定义策略类型 | 可生成任意逻辑的策略 |
| **技术栈** | 参数验证 | AI代码生成 + 沙箱执行 |
| **适用场景** | 标准策略快速调参 | 创新策略快速实现 |

**结论**: 两个方案互补，建议**同时保留**:
- 新手用户/标准策略 → 参数配置方案
- 高级用户/创新策略 → AI代码生成方案

---

## 需求分析

### 功能需求

#### 1. 策略生成 (P0)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 自然语言输入 | 用户用文字描述策略逻辑 | P0 |
| AI代码生成 | 调用DeepSeek API生成策略代码 | P0 |
| 代码预览 | 显示生成的代码供用户审核 | P0 |
| 代码编辑 | 允许用户手动修改生成的代码 | P0 |
| 代码保存 | 保存策略代码到数据库 | P0 |

#### 2. 代码验证 (P0)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 语法检查 | 验证Python语法正确性 | P0 |
| 安全检查 | 检测危险操作(文件IO、网络、系统调用) | P0 |
| 接口检查 | 验证是否符合BaseStrategy接口 | P0 |
| 依赖检查 | 检查依赖库是否可用 | P1 |
| 逻辑测试 | 用示例数据测试代码逻辑 | P1 |

#### 3. 策略管理 (P1)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 策略列表 | 查看所有AI生成的策略 | P0 |
| 策略详情 | 查看策略代码、生成提示、测试结果 | P0 |
| 策略启用/禁用 | 控制策略是否可用 | P1 |
| 策略删除 | 删除不需要的策略 | P1 |
| 策略导出 | 导出策略代码为.py文件 | P2 |

#### 4. 迭代优化 (P2)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 用户反馈 | 标记生成结果是否满意 | P1 |
| 重新生成 | 基于反馈重新生成代码 | P1 |
| Prompt优化 | 根据成功案例优化Prompt | P2 |
| 代码片段库 | 积累常用代码片段 | P2 |

### 非功能需求

| 需求 | 指标 | 优先级 |
|------|------|--------|
| AI响应速度 | < 30秒 | P0 |
| 代码生成成功率 | > 80% | P0 |
| 安全性 | 无恶意代码执行 | P0 |
| 可扩展性 | 支持切换不同AI模型 | P1 |
| 成本控制 | API调用成本可控 | P1 |

---

## 核心流程

### 策略生成流程

```
┌─────────────────────────────────────────────────────────────┐
│                      用户输入                                 │
│  "小盘股，市盈率在30以下，股价格在20日均线以下"                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│              Frontend: 提交生成请求                          │
│  POST /api/ai-strategies/generate                          │
│  {                                                         │
│    "description": "小盘股，市盈率...",                       │
│    "strategy_name": "SmallCapValue_v1"                     │
│  }                                                         │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│            Backend: AI Strategy Service                    │
│  1. 构建AI Prompt (使用模板)                                │
│  2. 调用 DeepSeek API                                      │
│  3. 解析返回的代码                                          │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                DeepSeek API                                │
│  - 模型: deepseek-chat / deepseek-coder                    │
│  - 输入: System Prompt + User Description                 │
│  - 输出: Python 策略类代码                                  │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│              Backend: 代码验证模块                           │
│  1. 语法检查 (ast.parse)                                   │
│  2. 安全检查 (AST分析)                                      │
│  3. 接口检查 (inspect模块)                                  │
│  4. 沙箱测试 (RestrictedPython)                            │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
        ┌────┴────┐
        │验证通过?│
        └────┬────┘
             │
      ┌──────┴──────┐
      │YES          │NO
      ▼             ▼
┌─────────┐    ┌─────────────┐
│保存代码  │    │返回错误信息  │
│到数据库  │    │建议修改      │
└────┬────┘    └─────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│           Frontend: 展示生成结果                              │
│  - 代码高亮显示                                               │
│  - 允许用户编辑                                               │
│  - 提供"测试回测"按钮                                         │
└─────────────────────────────────────────────────────────────┘
```

### 策略执行流程

```
用户请求回测
    ↓
Backend 加载策略代码
    ↓
动态导入策略类 (importlib)
    ↓
实例化策略对象
    ↓
传递给 BacktestEngine
    ↓
执行回测
    ↓
返回结果
```

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  - AI策略编辑器                                               │
│  - 代码预览/编辑器 (Monaco Editor)                            │
│  - 策略管理界面                                               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP API
┌────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        AI Strategy Service Layer                     │   │
│  │  - AIStrategyService                                 │   │
│  │  - PromptBuilder                                     │   │
│  │  - CodeGenerator (DeepSeek API)                      │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │        Code Validation Layer                         │   │
│  │  - SyntaxValidator                                   │   │
│  │  - SecurityValidator                                 │   │
│  │  - InterfaceValidator                                │   │
│  │  - SandboxTester                                     │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │        AI Strategy Repository                        │   │
│  │  - 读写 ai_strategies 表                             │   │
│  │  - 版本管理                                           │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │              PostgreSQL                              │   │
│  │  - ai_strategies (策略代码)                          │   │
│  │  - ai_generation_logs (生成日志)                     │   │
│  │  - ai_strategy_executions (执行记录)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 动态加载
┌────────────────────────▼────────────────────────────────────┐
│                      Core (Python)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Dynamic Strategy Loader                     │   │
│  │  - 从数据库读取策略代码                               │   │
│  │  - 动态编译和导入                                     │   │
│  │  - 缓存策略类                                         │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │         BacktestEngine                               │   │
│  │  - 执行AI生成的策略                                   │   │
│  │  - 与参数配置策略统一接口                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 组件 | 技术选型 |
|------|------|---------|
| **AI模型** | 代码生成 | DeepSeek API (deepseek-coder) |
| **Backend** | Web框架 | FastAPI |
| **Backend** | 代码验证 | ast, RestrictedPython, bandit |
| **Backend** | 动态导入 | importlib, types |
| **Frontend** | 代码编辑器 | Monaco Editor (VSCode内核) |
| **Frontend** | 语法高亮 | Prism.js / Highlight.js |
| **数据库** | 代码存储 | PostgreSQL (TEXT字段) |
| **缓存** | 策略缓存 | Redis |

---

## 数据库设计

### 表结构

#### 1. AI生成策略表 (ai_strategies)

```sql
CREATE TABLE ai_strategies (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 基本信息
    strategy_name VARCHAR(200) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- 用户输入
    user_prompt TEXT NOT NULL,                     -- 用户的自然语言描述
    generation_context JSONB,                      -- 生成上下文(如市场条件、风险偏好等)

    -- 生成的代码
    generated_code TEXT NOT NULL,                  -- Python策略类代码
    code_hash VARCHAR(64),                         -- 代码的MD5哈希
    class_name VARCHAR(100),                       -- 策略类名(如 SmallCapValueStrategy)

    -- AI相关
    ai_model VARCHAR(50) DEFAULT 'deepseek-coder', -- 使用的AI模型
    ai_prompt TEXT,                                -- 发送给AI的完整Prompt
    ai_response_raw TEXT,                          -- AI返回的原始响应
    generation_tokens INT,                         -- 消耗的Token数
    generation_cost DECIMAL(10, 4),                -- 生成成本(美元)

    -- 验证状态
    validation_status VARCHAR(20) DEFAULT 'pending', -- pending, passed, failed
    validation_errors JSONB,                       -- 验证错误信息
    validation_warnings JSONB,                     -- 验证警告信息

    -- 测试结果
    test_status VARCHAR(20),                       -- untested, passed, failed
    test_results JSONB,                            -- 测试结果(语法、沙箱、逻辑测试)

    -- 性能指标(最近一次回测)
    last_backtest_metrics JSONB,
    last_backtest_date TIMESTAMP,

    -- 用户反馈
    user_rating INT CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    is_satisfactory BOOLEAN,

    -- 状态
    status VARCHAR(20) DEFAULT 'draft',            -- draft, active, archived, deprecated
    is_enabled BOOLEAN DEFAULT TRUE,

    -- 版本
    version INT DEFAULT 1,
    parent_id INT REFERENCES ai_strategies(id),    -- 如果是迭代版本，指向父策略

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
CREATE INDEX idx_ai_strat_name ON ai_strategies(strategy_name);
CREATE INDEX idx_ai_strat_status ON ai_strategies(status);
CREATE INDEX idx_ai_strat_enabled ON ai_strategies(is_enabled);
CREATE INDEX idx_ai_strat_validation ON ai_strategies(validation_status);
CREATE INDEX idx_ai_strat_created ON ai_strategies(created_at DESC);
CREATE INDEX idx_ai_strat_tags ON ai_strategies USING GIN(tags);
CREATE INDEX idx_ai_strat_class ON ai_strategies(class_name);
```

#### 2. AI生成日志表 (ai_generation_logs)

```sql
CREATE TABLE ai_generation_logs (
    id BIGSERIAL PRIMARY KEY,

    -- 关联策略
    strategy_id INT REFERENCES ai_strategies(id) ON DELETE SET NULL,

    -- 生成请求
    user_prompt TEXT NOT NULL,
    generation_params JSONB,                       -- {temperature, max_tokens, etc.}

    -- AI响应
    ai_model VARCHAR(50),
    ai_prompt TEXT,
    ai_response TEXT,
    generation_time_ms INT,                        -- 生成耗时(毫秒)
    tokens_used INT,
    cost DECIMAL(10, 4),

    -- 结果
    success BOOLEAN,
    error_message TEXT,

    -- 审计
    requested_by VARCHAR(100),
    requested_at TIMESTAMP DEFAULT NOW(),

    -- 元数据
    request_ip VARCHAR(45),
    user_agent TEXT
);

-- 索引
CREATE INDEX idx_gen_log_strategy ON ai_generation_logs(strategy_id);
CREATE INDEX idx_gen_log_time ON ai_generation_logs(requested_at DESC);
CREATE INDEX idx_gen_log_success ON ai_generation_logs(success);
```

#### 3. AI策略执行记录表 (ai_strategy_executions)

```sql
CREATE TABLE ai_strategy_executions (
    id BIGSERIAL PRIMARY KEY,

    -- 关联策略
    strategy_id INT NOT NULL REFERENCES ai_strategies(id) ON DELETE CASCADE,

    -- 执行类型
    execution_type VARCHAR(20) NOT NULL,           -- backtest, live_trading, paper_trading, validation

    -- 执行参数
    execution_params JSONB NOT NULL,               -- {stock_codes, start_date, end_date, initial_capital, ...}

    -- 执行结果
    status VARCHAR(20) DEFAULT 'pending',          -- pending, running, completed, failed
    result JSONB,                                  -- 执行结果数据
    metrics JSONB,                                 -- 性能指标
    error_message TEXT,

    -- 性能
    execution_duration_ms INT,
    code_version INT,                              -- 执行时的策略版本

    -- 审计
    executed_by VARCHAR(100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT valid_exec_type CHECK (
        execution_type IN ('backtest', 'live_trading', 'paper_trading', 'validation', 'sandbox_test')
    ),
    CONSTRAINT valid_exec_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    )
);

-- 索引
CREATE INDEX idx_exec_strategy ON ai_strategy_executions(strategy_id, created_at DESC);
CREATE INDEX idx_exec_type ON ai_strategy_executions(execution_type);
CREATE INDEX idx_exec_status ON ai_strategy_executions(status);
```

#### 4. Prompt模板表 (ai_prompt_templates)

```sql
CREATE TABLE ai_prompt_templates (
    id SERIAL PRIMARY KEY,

    -- 模板信息
    template_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- 模板内容
    system_prompt TEXT NOT NULL,                   -- System级别的Prompt
    user_prompt_template TEXT NOT NULL,            -- User Prompt模板(支持变量)
    example_inputs JSONB,                          -- 示例输入
    example_outputs JSONB,                         -- 示例输出

    -- AI配置
    recommended_model VARCHAR(50),
    recommended_params JSONB,                      -- {temperature, max_tokens, top_p, ...}

    -- 统计
    usage_count INT DEFAULT 0,
    success_rate FLOAT,                            -- 成功率
    avg_tokens INT,                                -- 平均Token消耗

    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,

    -- 审计
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 版本
    version INT DEFAULT 1
);

-- 索引
CREATE INDEX idx_prompt_active ON ai_prompt_templates(is_active);
CREATE INDEX idx_prompt_default ON ai_prompt_templates(is_default);
```

---

## AI代码生成

### Prompt工程

#### System Prompt模板

```python
SYSTEM_PROMPT = """
你是一个专业的Python量化交易策略开发助手。你的任务是根据用户的自然语言描述，生成符合指定框架的Python策略类代码。

## 目标框架

所有策略必须继承自 `BaseStrategy` 类，并实现以下接口：

```python
from typing import Dict, Any, Optional
import pandas as pd
from core.strategies.base_strategy import BaseStrategy

class YourStrategy(BaseStrategy):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # 初始化策略特有参数

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        \"\"\"
        计算股票评分

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes)
            features: 特征DataFrame (可选，包含技术指标、财务指标等)
            date: 指定日期

        Returns:
            股票评分Series (index=stock_codes, values=scores)
            分数越高越好
        \"\"\"
        # 实现评分逻辑
        pass

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        \"\"\"
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame (可选)
            volumes: 成交量DataFrame (可选)

        Returns:
            信号DataFrame (index=date, columns=stock_codes)
            值: 1 = 买入, 0 = 持有, -1 = 卖出
        \"\"\"
        # 实现信号生成逻辑
        pass
```

## 可用的数据字段

### prices DataFrame
- index: 日期 (pd.DatetimeIndex)
- columns: 股票代码 (如 '000001.SZ', '600000.SH')
- values: 收盘价

### features DataFrame (如果提供)
- index: 日期
- columns: MultiIndex [(feature_name, stock_code)]
- 可用特征:
  - 技术指标: 'MA5', 'MA10', 'MA20', 'MA60', 'RSI14', 'MACD', 'KDJ_K', 'ATR', 'BOLL_UPPER', 'BOLL_LOWER'
  - Alpha因子: 'MOM20' (动量), 'REV5' (反转), 'VOLATILITY20' (波动率), 'VOLUME_RATIO5' (量比)
  - 基本面: 'PE' (市盈率), 'PB' (市净率), 'PS' (市销率), 'MARKET_CAP' (市值), 'TURNOVER_RATE' (换手率)

### volumes DataFrame (如果提供)
- index: 日期
- columns: 股票代码
- values: 成交量

## 代码要求

1. **必须继承BaseStrategy**: 类定义必须是 `class XXXStrategy(BaseStrategy):`
2. **实现必要方法**: 必须实现 `calculate_scores()` 和 `generate_signals()`
3. **使用pandas/numpy**: 使用向量化操作，避免循环
4. **错误处理**: 使用 try-except 处理可能的错误
5. **日志记录**: 使用 `from loguru import logger` 记录关键步骤
6. **参数化**: 将魔法数字提取为配置参数
7. **文档字符串**: 添加清晰的docstring
8. **导入语句**: 只使用标准库和已安装的库 (pandas, numpy, loguru)

## 禁止操作

- ❌ 不要使用文件IO操作 (open, with open, pathlib)
- ❌ 不要使用网络请求 (requests, urllib, socket)
- ❌ 不要使用系统命令 (os.system, subprocess)
- ❌ 不要使用eval/exec
- ❌ 不要导入未知的第三方库

## 输出格式

只输出Python代码，不要包含任何额外的解释文本。代码必须包含在代码块中:

```python
# 你的策略代码
```

## 示例

用户输入: "选择动量最强的50只股票"
你的输出:
```python
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from core.strategies.base_strategy import BaseStrategy
from core.strategies.signal_generator import SignalGenerator


class TopMomentumStrategy(BaseStrategy):
    \"\"\"
    动量策略 - 选择动量最强的股票
    \"\"\"

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {
            'lookback_period': 20,
            'top_n': 50,
            'holding_period': 5
        }
        default_config.update(config)
        super().__init__(name, default_config)

        self.lookback_period = self.config.custom_params.get('lookback_period', 20)

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        \"\"\"计算动量评分\"\"\"
        # 计算收益率作为动量指标
        momentum = prices.pct_change(self.lookback_period) * 100

        if date is None:
            date = momentum.index[-1]

        scores = momentum.loc[date]
        scores[scores < 0] = np.nan  # 过滤负动量

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        \"\"\"生成交易信号\"\"\"
        logger.info("生成动量策略信号...")

        # 计算动量
        momentum = prices.pct_change(self.lookback_period) * 100
        momentum[momentum < 0] = np.nan

        # 生成排名信号
        signals_response = SignalGenerator.generate_rank_signals(
            scores=momentum,
            top_n=self.config.top_n
        )

        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")

        signals = signals_response.data

        # 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，买入信号数: {(signals == 1).sum().sum()}")

        return signals
```

现在，请根据用户的描述生成策略代码。
"""
```

#### User Prompt构建

```python
def build_user_prompt(description: str, context: Dict[str, Any]) -> str:
    """
    构建用户Prompt

    Args:
        description: 用户的策略描述
        context: 额外上下文信息
    """
    prompt_parts = [
        f"请根据以下描述生成量化交易策略代码:\n",
        f"\n## 策略描述\n{description}\n"
    ]

    # 添加额外上下文
    if context.get('market_type'):
        prompt_parts.append(f"\n市场类型: {context['market_type']}")

    if context.get('risk_level'):
        prompt_parts.append(f"\n风险偏好: {context['risk_level']}")

    if context.get('holding_period'):
        prompt_parts.append(f"\n持仓周期: {context['holding_period']}天")

    if context.get('stock_count'):
        prompt_parts.append(f"\n选股数量: {context['stock_count']}只")

    # 添加特殊要求
    prompt_parts.append("\n## 特殊要求")
    prompt_parts.append("- 策略类名应该简洁且有意义")
    prompt_parts.append("- 代码必须包含详细的注释")
    prompt_parts.append("- 使用config参数化所有可调参数")

    return "".join(prompt_parts)
```

### DeepSeek API集成

```python
# backend/app/services/deepseek_client.py

import httpx
from typing import Dict, Any, Optional
from loguru import logger


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "deepseek-coder",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用DeepSeek API生成代码

        Args:
            system_prompt: System级别的Prompt
            user_prompt: 用户Prompt
            model: 模型名称
            temperature: 温度参数 (0-1)
            max_tokens: 最大Token数

        Returns:
            {
                'code': str,           # 生成的代码
                'raw_response': str,   # 原始响应
                'tokens_used': int,    # 消耗的Token
                'cost': float,         # 成本
                'success': bool
            }
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        try:
            logger.info(f"调用DeepSeek API, model={model}, temperature={temperature}")

            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            # 解析响应
            generated_text = result['choices'][0]['message']['content']
            tokens_used = result['usage']['total_tokens']

            # 提取代码块
            code = self._extract_code_block(generated_text)

            # 计算成本 (假设 $0.001 / 1K tokens)
            cost = tokens_used * 0.001 / 1000

            logger.success(f"代码生成成功, tokens={tokens_used}, cost=${cost:.4f}")

            return {
                'code': code,
                'raw_response': generated_text,
                'tokens_used': tokens_used,
                'cost': cost,
                'success': True
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"API请求失败: {e.response.status_code} - {e.response.text}")
            return {
                'code': None,
                'raw_response': None,
                'tokens_used': 0,
                'cost': 0,
                'success': False,
                'error': str(e)
            }

        except Exception as e:
            logger.error(f"代码生成异常: {e}")
            return {
                'code': None,
                'raw_response': None,
                'tokens_used': 0,
                'cost': 0,
                'success': False,
                'error': str(e)
            }

    def _extract_code_block(self, text: str) -> str:
        """
        从Markdown代码块中提取Python代码

        Args:
            text: 包含代码块的文本

        Returns:
            提取的代码
        """
        import re

        # 匹配 ```python ... ``` 或 ``` ... ```
        pattern = r'```(?:python)?\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            # 返回最大的代码块
            return max(matches, key=len).strip()
        else:
            # 如果没有代码块标记，返回整个文本
            logger.warning("未找到代码块标记，返回原始文本")
            return text.strip()

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
```

### 代码生成服务

```python
# backend/app/services/ai_strategy_service.py

from typing import Dict, Any, Optional
from loguru import logger

from app.services.deepseek_client import DeepSeekClient
from app.services.code_validator import CodeValidator
from app.repositories.ai_strategy_repository import AIStrategyRepository
from app.core.config import settings


class AIStrategyService:
    """AI策略生成服务"""

    def __init__(self):
        self.deepseek = DeepSeekClient(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.validator = CodeValidator()
        self.repo = AIStrategyRepository()

    async def generate_strategy(
        self,
        strategy_name: str,
        user_description: str,
        display_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            strategy_name: 策略名称 (唯一标识)
            user_description: 用户的自然语言描述
            display_name: 显示名称
            context: 额外上下文
            created_by: 创建人

        Returns:
            {
                'strategy_id': int,
                'code': str,
                'validation': {...},
                'test_result': {...}
            }
        """
        logger.info(f"开始生成策略: {strategy_name}")
        logger.debug(f"用户描述: {user_description}")

        # 1. 构建Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_description, context or {})

        # 2. 调用DeepSeek API
        generation_result = await self.deepseek.generate_code(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="deepseek-coder",
            temperature=0.7,
            max_tokens=4000
        )

        if not generation_result['success']:
            raise Exception(f"代码生成失败: {generation_result.get('error')}")

        generated_code = generation_result['code']

        # 3. 提取类名
        class_name = self._extract_class_name(generated_code)

        # 4. 验证代码
        validation_result = await self.validator.validate(generated_code)

        # 5. 保存到数据库
        strategy_data = {
            'strategy_name': strategy_name,
            'display_name': display_name or strategy_name,
            'description': user_description,
            'user_prompt': user_description,
            'generation_context': context,
            'generated_code': generated_code,
            'code_hash': self._calculate_hash(generated_code),
            'class_name': class_name,
            'ai_model': 'deepseek-coder',
            'ai_prompt': system_prompt + "\n\n" + user_prompt,
            'ai_response_raw': generation_result['raw_response'],
            'generation_tokens': generation_result['tokens_used'],
            'generation_cost': generation_result['cost'],
            'validation_status': validation_result['status'],
            'validation_errors': validation_result.get('errors'),
            'validation_warnings': validation_result.get('warnings'),
            'status': 'draft' if validation_result['status'] == 'failed' else 'active',
            'created_by': created_by
        }

        strategy_id = await self.repo.create(strategy_data)

        # 6. 记录生成日志
        await self._log_generation(
            strategy_id=strategy_id,
            user_prompt=user_description,
            ai_model='deepseek-coder',
            ai_prompt=system_prompt + "\n\n" + user_prompt,
            ai_response=generation_result['raw_response'],
            tokens_used=generation_result['tokens_used'],
            cost=generation_result['cost'],
            success=True,
            requested_by=created_by
        )

        # 7. 如果验证通过，执行沙箱测试
        test_result = None
        if validation_result['status'] == 'passed':
            test_result = await self._run_sandbox_test(strategy_id, generated_code)
            await self.repo.update(strategy_id, {
                'test_status': 'passed' if test_result['success'] else 'failed',
                'test_results': test_result
            })

        logger.success(f"策略生成完成: ID={strategy_id}, 验证={validation_result['status']}")

        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy_name,
            'class_name': class_name,
            'code': generated_code,
            'validation': validation_result,
            'test_result': test_result,
            'tokens_used': generation_result['tokens_used'],
            'cost': generation_result['cost']
        }

    def _build_system_prompt(self) -> str:
        """构建System Prompt"""
        # 使用上面定义的 SYSTEM_PROMPT 常量
        return SYSTEM_PROMPT

    def _build_user_prompt(self, description: str, context: Dict[str, Any]) -> str:
        """构建User Prompt"""
        # 使用上面定义的 build_user_prompt 函数
        return build_user_prompt(description, context)

    def _extract_class_name(self, code: str) -> Optional[str]:
        """提取策略类名"""
        import re
        match = re.search(r'class\s+(\w+)\s*\(.*BaseStrategy.*\):', code)
        return match.group(1) if match else None

    def _calculate_hash(self, code: str) -> str:
        """计算代码哈希"""
        import hashlib
        return hashlib.md5(code.encode()).hexdigest()

    async def _log_generation(self, **kwargs):
        """记录生成日志"""
        # 保存到 ai_generation_logs 表
        pass

    async def _run_sandbox_test(self, strategy_id: int, code: str) -> Dict[str, Any]:
        """在沙箱中测试代码"""
        from app.services.sandbox_tester import SandboxTester
        tester = SandboxTester()
        return await tester.test(code)
```

---

## 代码验证与执行

### 代码验证器

```python
# backend/app/services/code_validator.py

import ast
import re
from typing import Dict, Any, List
from loguru import logger


class CodeValidator:
    """代码验证器"""

    # 危险的模块和函数
    DANGEROUS_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'http', 'ftplib', 'smtplib', 'telnetlib',
        'pickle', 'shelve', 'marshal',
        '__builtin__', 'builtins'
    }

    DANGEROUS_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input'
    }

    async def validate(self, code: str) -> Dict[str, Any]:
        """
        验证代码

        Returns:
            {
                'status': 'passed' | 'warning' | 'failed',
                'errors': [...],
                'warnings': [...]
            }
        """
        errors = []
        warnings = []

        # 1. 语法检查
        syntax_result = self._check_syntax(code)
        if not syntax_result['valid']:
            errors.append({
                'type': 'syntax',
                'message': syntax_result['error']
            })

        # 2. 安全检查
        security_result = self._check_security(code)
        if security_result['dangerous_imports']:
            errors.append({
                'type': 'security',
                'message': f"检测到危险导入: {', '.join(security_result['dangerous_imports'])}"
            })
        if security_result['dangerous_functions']:
            errors.append({
                'type': 'security',
                'message': f"检测到危险函数: {', '.join(security_result['dangerous_functions'])}"
            })

        # 3. 接口检查
        interface_result = self._check_interface(code)
        if not interface_result['inherits_base']:
            errors.append({
                'type': 'interface',
                'message': "策略类必须继承自 BaseStrategy"
            })
        if not interface_result['implements_calculate_scores']:
            errors.append({
                'type': 'interface',
                'message': "必须实现 calculate_scores() 方法"
            })
        if not interface_result['implements_generate_signals']:
            errors.append({
                'type': 'interface',
                'message': "必须实现 generate_signals() 方法"
            })

        # 4. 依赖检查
        dependency_result = self._check_dependencies(code)
        if dependency_result['unknown_imports']:
            warnings.append({
                'type': 'dependency',
                'message': f"检测到未知导入: {', '.join(dependency_result['unknown_imports'])}"
            })

        # 5. 代码质量检查
        quality_result = self._check_code_quality(code)
        if quality_result['warnings']:
            warnings.extend([
                {'type': 'quality', 'message': w}
                for w in quality_result['warnings']
            ])

        # 确定状态
        if errors:
            status = 'failed'
        elif warnings:
            status = 'warning'
        else:
            status = 'passed'

        return {
            'status': status,
            'errors': errors,
            'warnings': warnings
        }

    def _check_syntax(self, code: str) -> Dict[str, Any]:
        """检查语法"""
        try:
            ast.parse(code)
            return {'valid': True}
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"语法错误: {e.msg} at line {e.lineno}"
            }

    def _check_security(self, code: str) -> Dict[str, Any]:
        """安全检查"""
        dangerous_imports = []
        dangerous_functions = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # 检查导入
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.DANGEROUS_IMPORTS:
                            dangerous_imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.DANGEROUS_IMPORTS:
                        dangerous_imports.append(node.module)

                # 检查函数调用
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.DANGEROUS_FUNCTIONS:
                            dangerous_functions.append(node.func.id)

        except Exception as e:
            logger.error(f"安全检查异常: {e}")

        return {
            'dangerous_imports': dangerous_imports,
            'dangerous_functions': dangerous_functions
        }

    def _check_interface(self, code: str) -> Dict[str, Any]:
        """接口检查"""
        result = {
            'inherits_base': False,
            'implements_calculate_scores': False,
            'implements_generate_signals': False,
            'class_name': None
        }

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 检查是否继承BaseStrategy
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'BaseStrategy':
                            result['inherits_base'] = True
                            result['class_name'] = node.name

                    # 检查方法
                    if result['inherits_base']:
                        method_names = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                        result['implements_calculate_scores'] = 'calculate_scores' in method_names
                        result['implements_generate_signals'] = 'generate_signals' in method_names

        except Exception as e:
            logger.error(f"接口检查异常: {e}")

        return result

    def _check_dependencies(self, code: str) -> Dict[str, Any]:
        """依赖检查"""
        known_modules = {
            'pandas', 'numpy', 'loguru', 'typing',
            'core.strategies.base_strategy',
            'core.strategies.signal_generator'
        }

        imported_modules = set()

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name.split('.')[0])

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module.split('.')[0])

        except Exception as e:
            logger.error(f"依赖检查异常: {e}")

        unknown_imports = imported_modules - known_modules

        return {
            'imported_modules': list(imported_modules),
            'unknown_imports': list(unknown_imports)
        }

    def _check_code_quality(self, code: str) -> Dict[str, Any]:
        """代码质量检查"""
        warnings = []

        # 检查代码长度
        lines = code.split('\n')
        if len(lines) > 500:
            warnings.append("代码超过500行，建议拆分")

        # 检查是否有docstring
        if '"""' not in code and "'''" not in code:
            warnings.append("建议添加文档字符串")

        # 检查是否有日志
        if 'logger' not in code:
            warnings.append("建议添加日志记录")

        return {'warnings': warnings}
```

### 动态代码加载器

```python
# core/src/strategies/dynamic_loader.py

import importlib.util
import types
from typing import Type, Dict, Any
from loguru import logger

from .base_strategy import BaseStrategy


class DynamicStrategyLoader:
    """动态策略加载器"""

    def __init__(self):
        self._loaded_strategies: Dict[str, Type[BaseStrategy]] = {}

    def load_from_code(
        self,
        code: str,
        class_name: str,
        module_name: str = "dynamic_strategy"
    ) -> Type[BaseStrategy]:
        """
        从代码字符串动态加载策略类

        Args:
            code: Python代码字符串
            class_name: 策略类名
            module_name: 模块名

        Returns:
            策略类

        Raises:
            Exception: 加载失败
        """
        cache_key = f"{module_name}.{class_name}"

        # 检查缓存
        if cache_key in self._loaded_strategies:
            logger.debug(f"从缓存加载策略类: {cache_key}")
            return self._loaded_strategies[cache_key]

        try:
            # 创建模块
            module = types.ModuleType(module_name)
            module.__file__ = f"<dynamic:{module_name}>"

            # 执行代码
            exec(code, module.__dict__)

            # 获取策略类
            if not hasattr(module, class_name):
                raise AttributeError(f"模块中未找到类: {class_name}")

            strategy_class = getattr(module, class_name)

            # 验证是BaseStrategy的子类
            if not issubclass(strategy_class, BaseStrategy):
                raise TypeError(f"{class_name} 必须继承自 BaseStrategy")

            # 缓存
            self._loaded_strategies[cache_key] = strategy_class

            logger.success(f"成功加载策略类: {cache_key}")

            return strategy_class

        except Exception as e:
            logger.error(f"加载策略类失败: {e}")
            raise

    def load_from_db(
        self,
        strategy_id: int,
        db_manager
    ) -> Type[BaseStrategy]:
        """
        从数据库加载策略代码并实例化

        Args:
            strategy_id: 策略ID
            db_manager: 数据库管理器

        Returns:
            策略类
        """
        # 查询数据库
        query = """
            SELECT strategy_name, class_name, generated_code
            FROM ai_strategies
            WHERE id = %s AND is_enabled = TRUE
        """

        result = db_manager.execute_query(query, (strategy_id,))

        if not result:
            raise ValueError(f"策略不存在或已禁用: {strategy_id}")

        row = result[0]

        # 动态加载
        return self.load_from_code(
            code=row['generated_code'],
            class_name=row['class_name'],
            module_name=row['strategy_name']
        )

    def clear_cache(self):
        """清除缓存"""
        self._loaded_strategies.clear()
        logger.debug("已清除策略类缓存")
```

### 沙箱测试器

```python
# backend/app/services/sandbox_tester.py

import asyncio
from typing import Dict, Any
from loguru import logger


class SandboxTester:
    """沙箱测试器"""

    async def test(self, code: str) -> Dict[str, Any]:
        """
        在沙箱环境中测试代码

        Returns:
            {
                'success': bool,
                'output': str,
                'errors': List[str],
                'execution_time': float
            }
        """
        import time
        start_time = time.time()

        errors = []
        output = []

        try:
            # 1. 动态加载策略类
            from core.strategies.dynamic_loader import DynamicStrategyLoader

            loader = DynamicStrategyLoader()

            # 提取类名
            import re
            match = re.search(r'class\s+(\w+)\s*\(.*BaseStrategy.*\):', code)
            if not match:
                errors.append("未找到策略类定义")
                return {
                    'success': False,
                    'output': '',
                    'errors': errors,
                    'execution_time': time.time() - start_time
                }

            class_name = match.group(1)

            # 加载策略类
            strategy_class = loader.load_from_code(code, class_name)
            output.append(f"✓ 策略类加载成功: {class_name}")

            # 2. 实例化策略
            strategy = strategy_class('test_strategy', {})
            output.append(f"✓ 策略实例化成功")

            # 3. 测试calculate_scores方法
            import pandas as pd
            import numpy as np

            # 创建测试数据
            dates = pd.date_range('2023-01-01', periods=30, freq='D')
            stocks = ['000001.SZ', '600000.SH']
            test_prices = pd.DataFrame(
                np.random.randn(30, 2) + 10,
                index=dates,
                columns=stocks
            )

            scores = strategy.calculate_scores(test_prices)
            output.append(f"✓ calculate_scores() 测试通过")

            # 4. 测试generate_signals方法
            signals = strategy.generate_signals(test_prices)
            output.append(f"✓ generate_signals() 测试通过")

            # 5. 验证输出格式
            if not isinstance(signals, pd.DataFrame):
                errors.append("generate_signals() 必须返回 DataFrame")
            else:
                output.append(f"✓ 信号格式验证通过")

        except Exception as e:
            logger.error(f"沙箱测试失败: {e}")
            errors.append(str(e))

        execution_time = time.time() - start_time

        return {
            'success': len(errors) == 0,
            'output': '\n'.join(output),
            'errors': errors,
            'execution_time': execution_time
        }
```

---

## API设计

### API端点

#### 1. 生成策略

```http
POST /api/v1/ai-strategies/generate

Request Body:
{
  "strategy_name": "SmallCapValue_v1",
  "display_name": "小盘价值策略",
  "description": "小盘股，市盈率在30以下，股价格在20日均线以下",
  "context": {
    "market_type": "A股",
    "risk_level": "medium",
    "holding_period": 10,
    "stock_count": 30
  }
}

Response 201:
{
  "success": true,
  "data": {
    "strategy_id": 1,
    "strategy_name": "SmallCapValue_v1",
    "class_name": "SmallCapValueStrategy",
    "code": "from typing import Dict...",
    "validation": {
      "status": "passed",
      "errors": [],
      "warnings": []
    },
    "test_result": {
      "success": true,
      "output": "✓ 策略类加载成功...",
      "execution_time": 0.5
    },
    "tokens_used": 1250,
    "cost": 0.00125
  }
}
```

#### 2. 获取策略列表

```http
GET /api/v1/ai-strategies
Query Parameters:
  - status: string (draft|active|archived)
  - validation_status: string (passed|failed|warning)
  - page: int
  - page_size: int

Response 200:
{
  "success": true,
  "data": [
    {
      "id": 1,
      "strategy_name": "SmallCapValue_v1",
      "display_name": "小盘价值策略",
      "description": "小盘股，市盈率在30以下...",
      "class_name": "SmallCapValueStrategy",
      "validation_status": "passed",
      "test_status": "passed",
      "status": "active",
      "created_at": "2026-02-08T10:00:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "page_size": 20
  }
}
```

#### 3. 获取策略详情

```http
GET /api/v1/ai-strategies/:strategy_id

Response 200:
{
  "success": true,
  "data": {
    "id": 1,
    "strategy_name": "SmallCapValue_v1",
    "display_name": "小盘价值策略",
    "description": "小盘股，市盈率在30以下...",
    "user_prompt": "小盘股，市盈率在30以下，股价格在20日均线以下",
    "generated_code": "from typing import Dict...",
    "class_name": "SmallCapValueStrategy",
    "validation": {...},
    "test_results": {...},
    "last_backtest_metrics": {...},
    "tokens_used": 1250,
    "cost": 0.00125,
    "created_at": "2026-02-08T10:00:00Z"
  }
}
```

#### 4. 更新策略代码

```http
PUT /api/v1/ai-strategies/:strategy_id/code

Request Body:
{
  "code": "修改后的代码...",
  "change_summary": "优化了选股逻辑"
}

Response 200:
{
  "success": true,
  "data": {
    "strategy_id": 1,
    "version": 2,
    "validation": {...}
  }
}
```

#### 5. 重新生成策略

```http
POST /api/v1/ai-strategies/:strategy_id/regenerate

Request Body:
{
  "feedback": "希望增加成交量过滤条件",
  "temperature": 0.8
}

Response 201:
{
  "success": true,
  "data": {
    "strategy_id": 2,  // 新版本ID
    "parent_id": 1,
    "code": "...",
    "validation": {...}
  }
}
```

#### 6. 执行回测

```http
POST /api/v1/ai-strategies/:strategy_id/backtest

Request Body:
{
  "stock_codes": ["000001.SZ", "600000.SH"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000
}

Response 200:
{
  "success": true,
  "data": {
    "execution_id": 123,
    "status": "completed",
    "metrics": {
      "annual_return": 0.18,
      "sharpe_ratio": 1.45,
      "max_drawdown": -0.12
    },
    "equity_curve": [...],
    "trades": [...]
  }
}
```

#### 7. 用户反馈

```http
POST /api/v1/ai-strategies/:strategy_id/feedback

Request Body:
{
  "rating": 4,
  "feedback": "策略逻辑不错，但选股数量可以增加",
  "is_satisfactory": true
}

Response 200:
{
  "success": true,
  "message": "反馈已记录"
}
```

---

## 前端集成

### UI组件

#### 1. AI策略生成器

```tsx
// AIStrategyGenerator.tsx
import React, { useState } from 'react';
import { Form, Input, Button, Modal, Spin } from 'antd';
import { Editor } from '@monaco-editor/react';

export const AIStrategyGenerator: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [generatedCode, setGeneratedCode] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const handleGenerate = async (values: any) => {
    setLoading(true);

    try {
      const response = await fetch('/api/v1/ai-strategies/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      });

      const result = await response.json();

      if (result.success) {
        setGeneratedCode(result.data.code);
        setShowPreview(true);
      } else {
        // 错误处理
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>AI策略生成器</h2>

      <Form form={form} layout="vertical" onFinish={handleGenerate}>
        <Form.Item
          name="strategy_name"
          label="策略名称"
          rules={[{ required: true }]}
        >
          <Input placeholder="如: SmallCapValue_v1" />
        </Form.Item>

        <Form.Item
          name="description"
          label="策略描述"
          rules={[{ required: true }]}
        >
          <Input.TextArea
            rows={6}
            placeholder="请用自然语言描述你的策略逻辑，例如：

小盘股，市盈率在30以下，股价格在20日均线以下

或者：

选择最近20日涨幅前50的股票，持有5天后卖出"
          />
        </Form.Item>

        <Form.Item name={['context', 'stock_count']} label="选股数量">
          <Input type="number" placeholder="30" />
        </Form.Item>

        <Form.Item name={['context', 'holding_period']} label="持仓周期(天)">
          <Input type="number" placeholder="10" />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            生成策略
          </Button>
        </Form.Item>
      </Form>

      {/* 代码预览Modal */}
      <Modal
        title="生成的策略代码"
        visible={showPreview}
        onCancel={() => setShowPreview(false)}
        width={1000}
        footer={[
          <Button key="edit" onClick={() => {/* 进入编辑模式 */}}>
            编辑代码
          </Button>,
          <Button key="test" type="primary" onClick={() => {/* 测试回测 */}}>
            测试回测
          </Button>
        ]}
      >
        <Editor
          height="600px"
          language="python"
          value={generatedCode}
          options={{ readOnly: true }}
        />
      </Modal>
    </div>
  );
};
```

#### 2. 代码编辑器

```tsx
// StrategyCodeEditor.tsx
import React, { useState } from 'react';
import { Editor } from '@monaco-editor/react';
import { Button, Space, message } from 'antd';

export const StrategyCodeEditor: React.FC<{
  strategyId: number;
  initialCode: string;
}> = ({ strategyId, initialCode }) => {
  const [code, setCode] = useState(initialCode);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);

    try {
      const response = await fetch(`/api/v1/ai-strategies/${strategyId}/code`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      const result = await response.json();

      if (result.success) {
        message.success('代码保存成功');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={handleSave} loading={saving}>
          保存代码
        </Button>
        <Button onClick={() => {/* 验证代码 */}}>
          验证代码
        </Button>
        <Button onClick={() => {/* 格式化 */}}>
          格式化
        </Button>
      </Space>

      <Editor
        height="600px"
        language="python"
        value={code}
        onChange={(value) => setCode(value || '')}
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          tabSize: 4
        }}
      />
    </div>
  );
};
```

---

## 安全性设计

### 安全措施

| 层级 | 措施 | 说明 |
|------|------|------|
| **代码生成** | Prompt过滤 | 过滤用户输入中的恶意Prompt |
| **代码验证** | AST分析 | 检测危险操作 (文件IO、网络、系统调用) |
| **代码执行** | 沙箱隔离 | 使用RestrictedPython限制权限 |
| **资源限制** | 超时控制 | 回测/测试超时自动终止 |
| **访问控制** | 用户权限 | 只允许创建者修改策略 |
| **审计日志** | 完整记录 | 记录所有代码生成和执行日志 |

### 沙箱执行环境

```python
# backend/app/services/sandbox_executor.py

from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import guarded_iter_unpack_sequence


class SandboxExecutor:
    """沙箱执行器"""

    def __init__(self):
        self.safe_globals = {
            **safe_globals,
            '__builtins__': {
                'range': range,
                'len': len,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
            },
            '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        }

    def execute(self, code: str, timeout: int = 30) -> dict:
        """
        在沙箱中执行代码

        Args:
            code: Python代码
            timeout: 超时时间(秒)

        Returns:
            执行结果
        """
        import multiprocessing
        import time

        # 编译受限代码
        byte_code = compile_restricted(code, '<string>', 'exec')

        # 准备执行环境
        exec_globals = self.safe_globals.copy()
        exec_locals = {}

        # 在独立进程中执行(防止阻塞)
        def _execute():
            try:
                exec(byte_code, exec_globals, exec_locals)
                return {'success': True, 'locals': exec_locals}
            except Exception as e:
                return {'success': False, 'error': str(e)}

        # 使用进程池执行(带超时)
        with multiprocessing.Pool(1) as pool:
            result = pool.apply_async(_execute)
            try:
                output = result.get(timeout=timeout)
                return output
            except multiprocessing.TimeoutError:
                return {'success': False, 'error': 'Execution timeout'}
```

---

## 实施计划

### Phase 1: 基础设施 (1周)

**任务**:
1. 创建数据库表 (ai_strategies, ai_generation_logs, ai_prompt_templates)
2. 集成 DeepSeek API
3. 实现基础的 AIStrategyService
4. 实现 CodeValidator

**交付物**:
- SQL migration 脚本
- DeepSeek API 客户端
- 基础服务层代码

### Phase 2: 代码生成与验证 (1-2周)

**任务**:
1. 完善 Prompt 模板
2. 实现代码验证器 (语法、安全、接口)
3. 实现沙箱测试器
4. 实现动态代码加载器
5. API 端点实现

**交付物**:
- 完整的代码生成流程
- 验证和测试模块
- Backend API

### Phase 3: 前端集成 (1-2周)

**任务**:
1. AI策略生成器UI
2. 代码编辑器 (Monaco Editor)
3. 策略列表和详情页
4. 回测集成
5. 用户反馈机制

**交付物**:
- 前端UI组件
- 完整的用户交互流程

### Phase 4: 优化与迭代 (1周)

**任务**:
1. Prompt 优化 (基于实际使用反馈)
2. 性能优化 (缓存、并发)
3. 安全加固
4. 监控和日志
5. 文档完善

**交付物**:
- 优化后的系统
- 运维文档
- 用户手册

---

## 总结

本方案设计了一个完整的**AI驱动的策略代码生成系统**，核心特点:

1. ✅ **自然语言输入**: 用户用文字描述策略逻辑
2. ✅ **AI代码生成**: DeepSeek API 生成完整的策略类代码
3. ✅ **多层验证**: 语法、安全、接口、逻辑全面检查
4. ✅ **动态加载**: 生成的代码可直接在系统中运行
5. ✅ **安全隔离**: 沙箱执行，防止恶意代码
6. ✅ **用户友好**: Web UI 编辑、预览、测试一体化
7. ✅ **可追溯**: 完整的生成日志和版本管理

### 与参数配置方案的关系

两个方案**互补共存**:

| 方案 | 适用场景 | 优势 |
|------|---------|------|
| **参数配置** | 标准策略、新手用户、快速调参 | 简单、安全、快速 |
| **AI代码生成** | 创新策略、高级用户、定制需求 | 灵活、强大、创新 |

建议实施优先级: **先实现参数配置方案** (更成熟稳定) → **再实现AI代码生成方案** (更创新前沿)

---

**文档状态**: ✅ 已完成初稿，待评审

**下一步**:
1. 评估技术可行性
2. 申请 DeepSeek API 密钥
3. 搭建开发环境
4. 启动 Phase 1 开发

**联系人**: Architecture Team
**更新日期**: 2026-02-08
