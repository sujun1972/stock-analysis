# 统一动态策略架构方案 V2.0

> 设计日期: 2025-02-09
> 状态: 设计方案
> 版本: 2.0

---

## 📋 目录

1. [核心设计原则](#一核心设计原则)
2. [数据库设计](#二数据库设计)
3. [内置策略代码模板](#三内置策略代码模板)
4. [前端统一界面设计](#四前端统一界面设计)
5. [后端API设计](#五后端api设计)
6. [实施路线图](#六实施路线图)
7. [总结](#七总结)

---

## 一、核心设计原则

### 1.1 设计理念

```
┌────────────────────────────────────────────┐
│   所有策略 = Python Class 完整代码存储       │
├────────────────────────────────────────────┤
│                                            │
│  ✓ 单一数据源：strategies 表               │
│  ✓ 统一格式：完整 Python 类代码字符串       │
│  ✓ 统一加载：DynamicCodeLoader            │
│  ✓ 代码可见：前端编辑器完整展示             │
│  ✓ 三种来源：内置/AI生成/用户自定义         │
│                                            │
└────────────────────────────────────────────┘
```

### 1.2 核心要点

- ✅ **所有策略都是动态的** - 没有预定义、配置、动态的区分
- ✅ **统一存储格式** - 所有策略都是完整的 Python 类代码
- ✅ **代码完全可见** - 前端可以查看、复制、下载任何策略的完整代码
- ✅ **三种创建方式**：
  - **内置模板** (builtin): 系统提供的最佳实践策略（动量、均值回归、多因子）
  - **AI 生成** (ai): 通过 AI 自动生成策略代码
  - **用户自定义** (custom): 用户手动编写策略代码

### 1.3 与旧架构的区别

| 对比项 | 旧架构 | 新架构 |
|-------|--------|--------|
| 策略分类 | 预定义/配置/动态 | 统一的动态策略 |
| 数据表 | `strategy_configs` + `ai_strategies` | 单一 `strategies` 表 |
| 预定义策略 | Python 模块代码 | 完整代码存储在数据库 |
| 配置策略 | 参数 JSON + 策略类型引用 | 删除此概念 |
| 前端界面 | 三个独立的管理页面 | 统一的策略列表 |
| 回测选择 | 三个 Tab 分别选择 | 单一选择器 |
| 代码可见性 | 预定义策略代码不可见 | 所有策略代码完全可见 |

---

## 二、数据库设计

### 2.1 `strategies` 表（唯一策略表）

```sql
CREATE TABLE strategies (
    -- 主键和标识
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,              -- 策略唯一标识 (如 'momentum_20d')
    display_name VARCHAR(200) NOT NULL,             -- 显示名称 (如 '动量策略 20日')

    -- 核心代码（完整 Python 类代码）
    code TEXT NOT NULL,                             -- 完整的 Python 类代码
    code_hash VARCHAR(64) NOT NULL,                 -- SHA256 校验值
    class_name VARCHAR(100) NOT NULL,               -- 类名 (如 'MomentumStrategy')

    -- 来源分类
    source_type VARCHAR(20) NOT NULL DEFAULT 'custom',
        -- 'builtin': 系统内置（动量、均值回归、多因子）
        -- 'ai': AI 生成
        -- 'custom': 用户自定义

    -- 策略元信息
    description TEXT,                               -- 策略说明
    category VARCHAR(50),                           -- 类别 (momentum/reversal/factor/ml)
    tags TEXT[],                                    -- 标签数组

    -- 默认参数（用于快速创建变体）
    default_params JSONB,                           -- 默认参数 JSON
        -- 例如: {"lookback_period": 20, "top_n": 50}

    -- 状态和验证
    validation_status VARCHAR(20) DEFAULT 'pending', -- pending/passed/failed/validating
    validation_errors JSONB,                        -- 验证错误详情
    validation_warnings JSONB,                      -- 验证警告
    risk_level VARCHAR(20) DEFAULT 'medium',        -- safe/low/medium/high
    is_enabled BOOLEAN DEFAULT TRUE,

    -- 使用统计
    usage_count INT DEFAULT 0,                      -- 使用次数
    backtest_count INT DEFAULT 0,                   -- 回测次数
    avg_sharpe_ratio DECIMAL(10, 4),                -- 平均夏普率
    avg_annual_return DECIMAL(10, 4),               -- 平均年化收益

    -- 版本和审计
    version INT DEFAULT 1,
    parent_strategy_id INT REFERENCES strategies(id),  -- 父策略ID（变体关系）
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,

    -- 约束
    CONSTRAINT chk_source_type CHECK (source_type IN ('builtin', 'ai', 'custom')),
    CONSTRAINT chk_validation_status CHECK (validation_status IN ('pending', 'passed', 'failed', 'validating')),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('safe', 'low', 'medium', 'high'))
);

-- 索引
CREATE INDEX idx_strategies_source_type ON strategies(source_type);
CREATE INDEX idx_strategies_category ON strategies(category);
CREATE INDEX idx_strategies_enabled_validated ON strategies(is_enabled, validation_status);
CREATE INDEX idx_strategies_created_at ON strategies(created_at DESC);
CREATE INDEX idx_strategies_usage_count ON strategies(usage_count DESC);

-- 全文搜索索引
CREATE INDEX idx_strategies_search ON strategies
    USING gin(to_tsvector('english', display_name || ' ' || COALESCE(description, '')));
```

### 2.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | TEXT | 完整的 Python 类代码，包含所有逻辑 |
| `source_type` | VARCHAR | 来源类型，用于前端图标和筛选 |
| `default_params` | JSONB | 默认参数配置，用于快速创建变体 |
| `validation_status` | VARCHAR | 代码验证状态（AST分析、安全检查） |
| `parent_strategy_id` | INT | 父策略ID，用于追踪策略变体关系 |

### 2.3 迁移策略

由于是开发初期阶段，不需要向后兼容：

1. **删除旧表**：
   - 删除 `strategy_configs` 表
   - 删除 `ai_strategies` 表

2. **创建新表**：
   - 创建 `strategies` 表

3. **初始化内置策略**：
   - 运行 `init_builtin_strategies.py` 脚本
   - 将动量、均值回归、多因子三个策略插入数据库

---

## 三、内置策略代码模板

### 3.1 策略代码结构

所有策略（包括内置）都遵循统一的 Python 类模板：

```python
"""
策略名称: 动量策略
策略说明: 基于价格动量选股，买入近期强势股
类别: momentum
风险等级: medium
创建时间: 2024-01-01
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from core.strategies.base_strategy import BaseStrategy
from core.strategies.signal_generator import SignalGenerator


class MomentumStrategy(BaseStrategy):
    """
    动量策略

    核心逻辑:
    - 计算过去N日的收益率作为动量指标
    - 每期选择动量最高的 top_n 只股票买入
    - 持有 holding_period 天后卖出

    参数说明:
    - lookback_period: 动量计算回看期（默认20天）
    - top_n: 每期选择前N只股票（默认50只）
    - holding_period: 持仓期（默认5天）
    - use_log_return: 是否使用对数收益率（默认False）
    - filter_negative: 是否过滤负动量股票（默认True）
    """

    def __init__(self, name: str = "momentum_strategy", config: Dict[str, Any] = None):
        """初始化策略"""
        # 默认配置
        default_config = {
            'lookback_period': 20,
            'top_n': 50,
            'holding_period': 5,
            'use_log_return': False,
            'filter_negative': True,
        }

        if config:
            default_config.update(config)

        super().__init__(name, default_config)

        # 提取策略参数
        self.lookback_period = self.config.custom_params.get('lookback_period', 20)
        self.use_log_return = self.config.custom_params.get('use_log_return', False)
        self.filter_negative = self.config.custom_params.get('filter_negative', True)

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """计算股票评分（必须实现）"""
        # ... 策略核心逻辑 ...
        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """生成交易信号（必须实现）"""
        # ... 信号生成逻辑 ...
        return signals

    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元信息"""
        return {
            'name': self.name,
            'class_name': self.__class__.__name__,
            'category': 'momentum',
            'parameters': {...},
            'risk_level': 'medium',
        }
```

### 3.2 三个内置策略

| 策略 | 类名 | 类别 | 描述 |
|------|------|------|------|
| 动量策略 | `MomentumStrategy` | momentum | 买入近期强势股 |
| 均值回归策略 | `MeanReversionStrategy` | reversal | 买入超跌股票 |
| 多因子策略 | `MultiFactorStrategy` | factor | 综合多因子选股 |

### 3.3 数据库初始化脚本

```python
# core/scripts/init_builtin_strategies.py
"""初始化内置策略到数据库"""

import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from core.database.models import Strategy


def load_strategy_code(strategy_name: str) -> str:
    """从文件加载策略代码"""
    file_path = Path(__file__).parent / 'builtin_strategies' / f'{strategy_name}.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def calculate_code_hash(code: str) -> str:
    """计算代码 SHA256 哈希"""
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def init_builtin_strategies(db: Session):
    """初始化内置策略"""

    builtin_strategies = [
        {
            'name': 'momentum_builtin',
            'display_name': '动量策略（内置）',
            'class_name': 'MomentumStrategy',
            'description': '基于价格动量选股，买入近期强势股',
            'category': 'momentum',
            'source_type': 'builtin',
            'tags': ['动量', '趋势', '短期'],
            'default_params': {
                'lookback_period': 20,
                'top_n': 50,
                'holding_period': 5,
                'use_log_return': False,
                'filter_negative': True,
            },
            'code_file': 'momentum_strategy',
        },
        {
            'name': 'mean_reversion_builtin',
            'display_name': '均值回归策略（内置）',
            'class_name': 'MeanReversionStrategy',
            'description': '买入超跌股票，等待价格回归均值',
            'category': 'reversal',
            'source_type': 'builtin',
            'tags': ['均值回归', '反转', '震荡市'],
            'default_params': {
                'lookback_period': 20,
                'z_score_threshold': -2.0,
                'top_n': 30,
                'holding_period': 5,
            },
            'code_file': 'mean_reversion_strategy',
        },
        {
            'name': 'multi_factor_builtin',
            'display_name': '多因子策略（内置）',
            'class_name': 'MultiFactorStrategy',
            'description': '综合多个因子进行选股',
            'category': 'factor',
            'source_type': 'builtin',
            'tags': ['多因子', '综合', '稳健'],
            'default_params': {
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': None,
                'normalize_method': 'rank',
                'top_n': 50,
                'holding_period': 5,
            },
            'code_file': 'multi_factor_strategy',
        },
    ]

    for strategy_data in builtin_strategies:
        # 检查是否已存在
        existing = db.query(Strategy).filter(
            Strategy.name == strategy_data['name']
        ).first()

        if existing:
            print(f"策略 {strategy_data['name']} 已存在，跳过")
            continue

        # 加载代码
        code = load_strategy_code(strategy_data['code_file'])
        code_hash = calculate_code_hash(code)

        # 创建策略记录
        strategy = Strategy(
            name=strategy_data['name'],
            display_name=strategy_data['display_name'],
            class_name=strategy_data['class_name'],
            code=code,
            code_hash=code_hash,
            source_type=strategy_data['source_type'],
            description=strategy_data['description'],
            category=strategy_data['category'],
            tags=strategy_data['tags'],
            default_params=strategy_data['default_params'],
            validation_status='passed',
            risk_level='low',
            is_enabled=True,
        )

        db.add(strategy)
        print(f"✓ 创建策略: {strategy_data['display_name']}")

    db.commit()
    print(f"\n✓ 内置策略初始化完成")
```

---

## 四、前端统一界面设计

### 4.1 策略列表页面 (`/strategies`)

**功能特性**：
- 统一的策略卡片展示
- 按来源类型筛选（内置/AI/自定义）
- 按类别筛选（动量/反转/因子等）
- 搜索功能（名称、描述、标签）
- 策略统计面板

**核心组件**：

```tsx
// frontend/src/app/strategies/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Plus, Search, Code, Sparkles, Building2 } from 'lucide-react'
import Link from 'next/link'
import StrategyCard from '@/components/strategies/StrategyCard'

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')

  return (
    <div className="container mx-auto py-6">
      {/* 页面头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">策略中心</h1>
          <p className="text-muted-foreground mt-2">管理和创建您的交易策略</p>
        </div>

        {/* 创建策略按钮 */}
        <div className="flex gap-2">
          <Link href="/strategies/create?source=builtin">
            <Button variant="outline">
              <Building2 className="mr-2 h-4 w-4" />
              基于内置创建
            </Button>
          </Link>
          <Link href="/strategies/create?source=ai">
            <Button variant="outline">
              <Sparkles className="mr-2 h-4 w-4" />
              AI 生成
            </Button>
          </Link>
          <Link href="/strategies/create?source=custom">
            <Button>
              <Code className="mr-2 h-4 w-4" />
              自定义代码
            </Button>
          </Link>
        </div>
      </div>

      {/* 筛选和搜索 */}
      <Card className="mb-6">
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            {/* 搜索框 */}
            <Input
              placeholder="搜索策略..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            {/* 来源筛选 */}
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectItem value="all">全部来源</SelectItem>
              <SelectItem value="builtin">内置策略</SelectItem>
              <SelectItem value="ai">AI 生成</SelectItem>
              <SelectItem value="custom">自定义</SelectItem>
            </Select>

            {/* 类别筛选 */}
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectItem value="all">全部类别</SelectItem>
              <SelectItem value="momentum">动量策略</SelectItem>
              <SelectItem value="reversal">反转策略</SelectItem>
              <SelectItem value="factor">因子策略</SelectItem>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 策略统计 */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{strategies.length}</div>
            <p className="text-xs text-muted-foreground">总策略数</p>
          </CardContent>
        </Card>
        {/* 其他统计卡片 */}
      </div>

      {/* 策略列表 */}
      <div className="grid grid-cols-3 gap-4">
        {filteredStrategies.map(strategy => (
          <StrategyCard key={strategy.id} strategy={strategy} />
        ))}
      </div>
    </div>
  )
}
```

### 4.2 策略卡片组件

```tsx
// frontend/src/components/strategies/StrategyCard.tsx
export default function StrategyCard({ strategy }) {
  const getSourceIcon = () => {
    switch (strategy.source_type) {
      case 'builtin': return <Building2 className="h-4 w-4" />
      case 'ai': return <Sparkles className="h-4 w-4" />
      case 'custom': return <User className="h-4 w-4" />
    }
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle>{strategy.display_name}</CardTitle>
          <Badge variant="outline">
            {getSourceIcon()}
            <span className="ml-1">{strategy.source_type}</span>
          </Badge>
        </div>
        <CardDescription>{strategy.description}</CardDescription>
      </CardHeader>

      <CardContent>
        {/* 标签 */}
        <div className="flex flex-wrap gap-1 mb-3">
          <Badge variant="secondary">{strategy.category}</Badge>
          {strategy.tags?.map(tag => (
            <Badge key={tag} variant="outline">{tag}</Badge>
          ))}
        </div>

        {/* 风险等级 */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">风险等级:</span>
          <Badge>{strategy.risk_level}</Badge>
        </div>
      </CardContent>

      <CardFooter className="flex gap-2">
        <Link href={`/strategies/${strategy.id}/code`} className="flex-1">
          <Button variant="outline" size="sm" className="w-full">
            <Code className="mr-1 h-3 w-3" />
            代码
          </Button>
        </Link>
        <Link href={`/backtest?strategy=${strategy.id}`} className="flex-1">
          <Button size="sm" className="w-full">
            <Play className="mr-1 h-3 w-3" />
            回测
          </Button>
        </Link>
      </CardFooter>
    </Card>
  )
}
```

### 4.3 策略代码查看页面

```tsx
// frontend/src/app/strategies/[id]/code/page.tsx
'use client'

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

export default function StrategyCodePage() {
  const [strategy, setStrategy] = useState(null)

  return (
    <div className="container mx-auto py-6">
      {/* 策略信息 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-2xl">{strategy.display_name}</CardTitle>
              <CardDescription>{strategy.description}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Badge>{strategy.source_type}</Badge>
              <Badge variant="outline">{strategy.category}</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* 代码展示 */}
      <Tabs defaultValue="code">
        <TabsList>
          <TabsTrigger value="code">策略代码</TabsTrigger>
          <TabsTrigger value="params">默认参数</TabsTrigger>
          <TabsTrigger value="info">元信息</TabsTrigger>
        </TabsList>

        <TabsContent value="code">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Python 源代码</CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopyCode}>
                    <Copy className="mr-2 h-4 w-4" />
                    复制
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownload}>
                    <Download className="mr-2 h-4 w-4" />
                    下载
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg overflow-hidden border">
                <SyntaxHighlighter
                  language="python"
                  style={vscDarkPlus}
                  showLineNumbers
                  customStyle={{ margin: 0, fontSize: '0.875rem' }}
                >
                  {strategy.code}
                </SyntaxHighlighter>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="params">
          <Card>
            <CardHeader>
              <CardTitle>默认参数配置</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg">
                {JSON.stringify(strategy.default_params, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 操作按钮 */}
      <Card className="mt-6">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Button className="flex-1" onClick={() => router.push(`/backtest?strategy=${strategy.id}`)}>
              <Play className="mr-2 h-4 w-4" />
              使用此策略进行回测
            </Button>
            <Button variant="outline" onClick={() => router.push(`/strategies/create?clone=${strategy.id}`)}>
              <Copy className="mr-2 h-4 w-4" />
              创建变体
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 4.4 回测页面简化

**改动要点**：
- 移除三个 Tab（预定义/配置/动态）
- 改为单一的策略选择器
- 显示策略来源图标和类别标签

```tsx
// frontend/src/app/backtest/page.tsx
export default function BacktestPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>选择策略</CardTitle>
        <CardDescription>从您的策略库中选择一个策略进行回测</CardDescription>
      </CardHeader>
      <CardContent>
        <Select value={selectedStrategyId} onValueChange={setSelectedStrategyId}>
          <SelectTrigger>
            <SelectValue placeholder="选择策略" />
          </SelectTrigger>
          <SelectContent>
            {strategies.map(strategy => (
              <SelectItem key={strategy.id} value={strategy.id.toString()}>
                <div className="flex items-center gap-2">
                  {/* 来源图标 */}
                  {strategy.source_type === 'builtin' && <Building2 className="h-4 w-4" />}
                  {strategy.source_type === 'ai' && <Sparkles className="h-4 w-4" />}
                  {strategy.source_type === 'custom' && <User className="h-4 w-4" />}

                  {/* 策略名称 */}
                  <span>{strategy.display_name}</span>

                  {/* 类别标签 */}
                  <Badge variant="outline">{strategy.category}</Badge>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* 显示选中策略的详情 */}
        {selectedStrategy && (
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground mb-2">
              {selectedStrategy.description}
            </p>
            <Button
              variant="link"
              size="sm"
              onClick={() => router.push(`/strategies/${selectedStrategy.id}/code`)}
            >
              <Code className="mr-1 h-3 w-3" />
              查看代码
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## 五、后端API设计

### 5.1 统一策略端点

```python
# backend/app/routers/strategies.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

@router.get("", response_model=List[StrategyResponse])
async def get_strategies(
    source_type: Optional[str] = Query(None),  # builtin/ai/custom
    category: Optional[str] = Query(None),
    is_enabled: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取策略列表（支持筛选）"""
    query = db.query(Strategy)

    if source_type:
        query = query.filter(Strategy.source_type == source_type)
    if category:
        query = query.filter(Strategy.category == category)
    if is_enabled is not None:
        query = query.filter(Strategy.is_enabled == is_enabled)
    if search:
        query = query.filter(
            Strategy.display_name.ilike(f'%{search}%') |
            Strategy.description.ilike(f'%{search}%')
        )

    strategies = query.order_by(Strategy.created_at.desc()).all()
    return strategies


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """获取策略详情（包含完整代码）"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        raise HTTPException(404, "策略不存在")

    # 增加使用计数
    strategy.usage_count += 1
    strategy.last_used_at = datetime.now()
    db.commit()

    return strategy


@router.post("", response_model=StrategyResponse)
async def create_strategy(
    data: StrategyCreate,
    db: Session = Depends(get_db)
):
    """创建新策略"""
    # 1. 验证代码
    sanitizer = CodeSanitizer()
    validation_result = sanitizer.sanitize(data.code, strict_mode=True)

    if not validation_result['safe']:
        raise HTTPException(400, {
            'message': '代码验证失败',
            'errors': validation_result['errors']
        })

    # 2. 计算代码哈希
    code_hash = hashlib.sha256(data.code.encode()).hexdigest()

    # 3. 创建策略
    strategy = Strategy(
        name=data.name,
        display_name=data.display_name,
        code=data.code,
        code_hash=code_hash,
        class_name=data.class_name,
        source_type=data.source_type,
        description=data.description,
        category=data.category,
        tags=data.tags,
        default_params=data.default_params,
        validation_status='passed',
        risk_level=validation_result['risk_level'],
    )

    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    return strategy


@router.post("/validate")
async def validate_strategy_code(code: str):
    """验证策略代码（不保存）"""
    sanitizer = CodeSanitizer()
    result = sanitizer.sanitize(code, strict_mode=True)

    return {
        'is_valid': result['safe'],
        'risk_level': result['risk_level'],
        'errors': result.get('errors', []),
        'warnings': result.get('warnings', []),
    }


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    db: Session = Depends(get_db)
):
    """更新策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        raise HTTPException(404, "策略不存在")

    # 内置策略不允许修改
    if strategy.source_type == 'builtin':
        raise HTTPException(403, "内置策略不允许修改")

    # 如果修改了代码，重新验证
    if data.code and data.code != strategy.code:
        sanitizer = CodeSanitizer()
        validation_result = sanitizer.sanitize(data.code, strict_mode=True)

        if not validation_result['safe']:
            raise HTTPException(400, {
                'message': '代码验证失败',
                'errors': validation_result['errors']
            })

        strategy.code = data.code
        strategy.code_hash = hashlib.sha256(data.code.encode()).hexdigest()
        strategy.validation_status = 'passed'
        strategy.risk_level = validation_result['risk_level']
        strategy.version += 1

    # 更新其他字段
    if data.display_name:
        strategy.display_name = data.display_name
    if data.description:
        strategy.description = data.description
    if data.tags is not None:
        strategy.tags = data.tags

    strategy.updated_at = datetime.now()
    db.commit()
    db.refresh(strategy)

    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        raise HTTPException(404, "策略不存在")

    # 内置策略不允许删除
    if strategy.source_type == 'builtin':
        raise HTTPException(403, "内置策略不允许删除")

    db.delete(strategy)
    db.commit()

    return {'message': '策略已删除'}
```

### 5.2 统一回测 API

```python
# backend/app/routers/backtest.py
@router.post("/run")
async def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(get_db)
):
    """运行回测（统一接口）"""
    # 1. 从数据库加载策略
    strategy_record = db.query(Strategy).filter(
        Strategy.id == request.strategy_id,
        Strategy.is_enabled == True,
        Strategy.validation_status == 'passed'
    ).first()

    if not strategy_record:
        raise HTTPException(404, "策略不存在或未启用")

    # 2. 使用 DynamicCodeLoader 加载策略实例
    loader = DynamicCodeLoader()
    strategy_instance = loader.load_strategy(
        strategy_id=request.strategy_id,
        strict_mode=True
    )

    # 3. 加载数据
    prices = load_price_data(request.stock_pool, request.start_date, request.end_date)
    features = load_feature_data(request.stock_pool, request.start_date, request.end_date)

    # 4. 运行回测
    engine = BacktestEngine(
        initial_capital=request.initial_capital,
        rebalance_freq=request.rebalance_freq
    )

    results = strategy_instance.backtest(engine, prices, features)

    # 5. 保存回测记录
    backtest_record = BacktestRecord(
        strategy_id=request.strategy_id,
        stock_pool=request.stock_pool,
        start_date=request.start_date,
        end_date=request.end_date,
        total_return=results['total_return'],
        sharpe_ratio=results['sharpe_ratio'],
    )
    db.add(backtest_record)

    # 更新策略统计
    strategy_record.backtest_count += 1
    db.commit()

    return results
```

### 5.3 回测数据格式

回测系统为策略提供**多层列结构**的价格数据，支持完整的 OHLCV 数据访问：

```python
# 数据结构
prices = pd.DataFrame with MultiIndex columns
    - Level 0: ['open', 'high', 'low', 'close', 'volume']
    - Level 1: stock codes ['600000.SH', '600001.SH', ...]

# 访问方式
prices['close']              # DataFrame: index=dates, columns=stocks
prices['close'].columns      # ['600000.SH', '600001.SH', ...]
prices['close']['600000.SH'] # Series: 600000.SH 的收盘价时间序列
prices['open'][stock]        # 访问开盘价
prices['high'][stock]        # 访问最高价
prices['low'][stock]         # 访问最低价
prices['volume'][stock]      # 访问成交量
```

**实现位置**：`backend/app/api/endpoints/backtest.py`

```python
# 将原始market_data pivot成多层列结构
ohlcv_dfs = {
    'open': market_data.pivot(index='trade_date', columns='code', values='open').sort_index(),
    'high': market_data.pivot(index='trade_date', columns='code', values='high').sort_index(),
    'low': market_data.pivot(index='trade_date', columns='code', values='low').sort_index(),
    'close': market_data.pivot(index='trade_date', columns='code', values='close').sort_index(),
    'volume': market_data.pivot(index='trade_date', columns='code', values='volume').sort_index()
}

# 合并成多层列结构
prices = pd.concat(ohlcv_dfs, axis=1, keys=ohlcv_dfs.keys())
```

**策略使用示例**：

```python
class MyStrategy(BaseStrategy):
    def calculate_scores(self, prices, features=None, date=None):
        # 验证数据格式
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in prices.columns for col in required_columns):
            raise ValueError(f"价格数据必须包含: {required_columns}")

        # 遍历所有股票
        for stock in prices['close'].columns:
            open_price = prices['open'][stock]
            high_price = prices['high'][stock]
            low_price = prices['low'][stock]
            close_price = prices['close'][stock]
            volume = prices['volume'][stock]

            # 计算指标...
```

---

## 六、实施路线图

### Phase 1: 数据库和 Core 层重构 (2-3天)

#### 1.1 数据库迁移
- [ ] 创建新的 `strategies` 表
- [ ] 删除旧的 `strategy_configs` 表
- [ ] 删除旧的 `ai_strategies` 表

#### 1.2 内置策略代码提取
- [ ] 创建 `core/scripts/builtin_strategies/` 目录
- [ ] 提取动量策略完整代码到 `momentum_strategy.py`
- [ ] 提取均值回归策略完整代码到 `mean_reversion_strategy.py`
- [ ] 提取多因子策略完整代码到 `multi_factor_strategy.py`

#### 1.3 初始化脚本
- [ ] 编写 `core/scripts/init_builtin_strategies.py`
- [ ] 运行初始化脚本，将三个内置策略插入数据库
- [ ] 验证策略代码完整性和可执行性

#### 1.4 统一加载器
- [ ] 简化 `DynamicCodeLoader`，移除分支逻辑
- [ ] 更新 `StrategyFactory` 只保留 `load_strategy(strategy_id)` 方法
- [ ] 删除 `ConfigLoader`（不再需要）
- [ ] 更新相关导入和引用

---

### Phase 2: Backend API 重构 (2天) ✅ 已完成

**完成日期**: 2026-02-09

#### 2.1 API 端点统一
- [x] 创建统一的 `GET /api/strategies` 端点（支持筛选）
- [x] 创建 `GET /api/strategies/{id}` 端点（返回完整代码）
- [x] 创建 `POST /api/strategies` 端点（创建策略）
- [x] 创建 `PUT /api/strategies/{id}` 端点（更新策略）
- [x] 创建 `DELETE /api/strategies/{id}` 端点（删除策略）
- [x] 创建 `POST /api/strategies/validate` 端点（验证代码）
- [x] 创建 `GET /api/strategies/statistics` 端点（统计信息）
- [x] 创建 `GET /api/strategies/{id}/code` 端点（获取代码）
- [x] 创建 `POST /api/strategies/{id}/test` 端点（测试策略）

#### 2.2 回测 API 简化
- [x] 创建 `POST /api/backtest/run-v3` 只接受 `strategy_id` 参数
- [x] 移除 `strategy_type` 参数
- [x] 简化参数结构
- [x] 准备统一使用 `DynamicCodeLoader`（等待 Phase 1 完成）

#### 2.3 旧端点兼容
- [x] 保留 `/api/strategy-configs/*` 端点（标记为旧）
- [x] 保留 `/api/dynamic-strategies/*` 端点（标记为旧）
- [x] 确保向后兼容

#### 2.4 实现成果
- ✅ 创建完整的 Pydantic Schema（8个模型）
- ✅ 创建统一的 StrategyRepository
- ✅ 实现 9 个统一策略 API 端点
- ✅ 14 个单元测试，100% 通过
- ✅ 总测试通过率 100% (118/118)
- ✅ 详细实施文档和测试总结

**详细文档**:
- [Backend Phase 2 实施报告](../backend/PHASE2_IMPLEMENTATION.md)
- [Backend Phase 2 测试总结](../backend/PHASE2_TEST_SUMMARY.md)

---

### Phase 3: Frontend 重构 (3-4天)

#### 3.1 类型定义更新
- [ ] 更新 `frontend/src/types/strategy.ts`
- [ ] 定义统一的 `Strategy` 接口
- [ ] 删除 `StrategyConfig` 和 `DynamicStrategy` 旧类型

#### 3.2 策略管理页面
- [ ] 重写 `frontend/src/app/strategies/page.tsx`（策略列表）
- [ ] 创建 `frontend/src/components/strategies/StrategyCard.tsx`
- [ ] 创建 `frontend/src/app/strategies/[id]/code/page.tsx`（代码查看）
- [ ] 创建 `frontend/src/app/strategies/create/page.tsx`（创建策略）
- [ ] 删除旧的 `/strategies/configs` 页面
- [ ] 删除旧的 `/strategies/dynamic` 页面

#### 3.3 回测页面简化
- [ ] 修改 `frontend/src/app/backtest/page.tsx`
- [ ] 移除三个 Tab（预定义/配置/动态）
- [ ] 改为单一的策略选择器
- [ ] 添加策略来源图标和类别标签
- [ ] 添加"查看代码"快捷链接

#### 3.4 API 客户端更新
- [ ] 更新 `frontend/src/lib/api-client.ts`
- [ ] 添加 `getStrategies()` 方法
- [ ] 添加 `getStrategy(id)` 方法
- [ ] 添加 `createStrategy()` 方法
- [ ] 添加 `validateStrategyCode()` 方法
- [ ] 删除旧的 API 方法

---

### Phase 4: 测试和优化 (1-2天)

#### 4.1 功能测试
- [ ] 测试策略列表加载和筛选
- [ ] 测试代码查看功能（内置策略代码可见）
- [ ] 测试回测流程（选择策略 → 运行回测）
- [ ] 测试创建自定义策略
- [ ] 测试策略代码验证功能
- [ ] 测试策略克隆/变体创建

#### 4.2 数据验证
- [ ] 验证内置策略代码完整性
- [ ] 验证策略加载和执行
- [ ] 验证安全检查机制

#### 4.3 清理工作
- [ ] 删除旧的组件和页面文件
- [ ] 删除无用的类型定义
- [ ] 删除旧的 API 路由文件
- [ ] 更新相关文档
- [ ] 代码审查和优化

#### 4.4 文档更新
- [ ] 更新 API 文档
- [ ] 更新用户使用指南
- [ ] 更新开发文档
- [ ] 更新架构图

---

## 七、总结

### 7.1 方案优势

| 优势 | 说明 |
|------|------|
| **架构统一** | 所有策略都是 Python 类代码，存储在单一表中 |
| **代码透明** | 前端可以完整查看、复制、下载任何策略代码 |
| **易于扩展** | 新增策略只需插入新记录，无需修改代码 |
| **安全可控** | 统一的安全验证流程（AST分析、权限检查） |
| **用户友好** | 内置策略提供最佳实践模板 |
| **灵活多样** | 支持三种创建方式（内置/AI/自定义） |
| **数据库简化** | 只需维护一张表，降低维护成本 |
| **前端简化** | 统一的策略列表，单一的回测选择器 |

### 7.2 核心流程图

```
用户创建策略
    ↓
┌────────────┬────────────┬────────────┐
│ 内置模板    │ AI 生成     │ 手写代码    │
│ (builtin)  │ (ai)       │ (custom)   │
└────────────┴────────────┴────────────┘
         ↓
    完整 Python 类代码
         ↓
    代码安全验证
    (AST分析 + 权限检查)
         ↓
    存入 strategies 表
         ↓
┌────────────────────────────┐
│  前端展示                   │
│  - 策略列表（统一界面）      │
│  - 代码查看（完整可见）      │
│  - 回测选择（单一选择器）    │
└────────────────────────────┘
         ↓
    DynamicCodeLoader 加载
         ↓
    策略实例化
         ↓
    运行回测
```

### 7.3 与旧架构对比

| 对比项 | 旧架构 | 新架构 |
|-------|--------|--------|
| **数据表数量** | 2张表 (`strategy_configs` + `ai_strategies`) | 1张表 (`strategies`) |
| **策略分类** | 预定义/配置/动态 | 统一的动态策略 |
| **内置策略** | Python 模块文件 | 数据库中的完整代码 |
| **代码可见性** | 预定义策略不可见 | 所有策略代码完全可见 |
| **前端页面** | 3个独立管理页面 | 1个统一策略列表 |
| **回测选择** | 3个Tab分别选择 | 单一选择器 |
| **API端点** | 分散的多个端点 | 统一的RESTful端点 |
| **加载方式** | ConfigLoader + DynamicCodeLoader | 统一的DynamicCodeLoader |

### 7.4 关键特性

1. **所有策略都是动态的** - 没有"预定义"和"动态"的本质区别，只是代码来源不同
2. **代码完全透明** - 用户可以查看任何策略的完整源代码，包括内置策略
3. **统一管理界面** - 所有策略在同一个列表中，按来源类型和类别筛选
4. **简化回测流程** - 移除复杂的策略类型选择，统一为单一策略选择器
5. **保留灵活性** - 支持三种创建方式，满足不同用户需求

### 7.5 实施时间估算

| 阶段 | 时间 | 工作量 |
|------|------|--------|
| Phase 1: 数据库和Core层 | 2-3天 | 中等 |
| Phase 2: Backend API | 2天 | 中等 |
| Phase 3: Frontend | 3-4天 | 较大 |
| Phase 4: 测试和优化 | 1-2天 | 较小 |
| **总计** | **8-11天** | - |

---

## 附录

### A. 相关文件清单

#### 需要创建的文件
- `core/scripts/builtin_strategies/momentum_strategy.py`
- `core/scripts/builtin_strategies/mean_reversion_strategy.py`
- `core/scripts/builtin_strategies/multi_factor_strategy.py`
- `core/scripts/init_builtin_strategies.py`
- `frontend/src/app/strategies/page.tsx` (重写)
- `frontend/src/app/strategies/[id]/code/page.tsx` (新建)
- `frontend/src/components/strategies/StrategyCard.tsx` (新建)

#### 需要修改的文件
- `backend/app/routers/strategies.py`
- `backend/app/routers/backtest.py`
- `frontend/src/app/backtest/page.tsx`
- `frontend/src/lib/api-client.ts`
- `frontend/src/types/strategy.ts`
- `core/strategies/loaders/dynamic_loader.py`
- `core/strategies/strategy_factory.py`

#### 需要删除的文件
- `core/strategies/loaders/config_loader.py`
- `frontend/src/app/strategies/configs/*`
- `frontend/src/app/strategies/dynamic/*`
- 旧的策略相关组件

### B. 数据库迁移脚本

```sql
-- 1. 删除旧表
DROP TABLE IF EXISTS strategy_configs CASCADE;
DROP TABLE IF EXISTS ai_strategies CASCADE;

-- 2. 创建新表
CREATE TABLE strategies (
    -- 见第二章数据库设计
);

-- 3. 创建索引
CREATE INDEX idx_strategies_source_type ON strategies(source_type);
-- ...其他索引
```

### C. 参考资源

- [STRATEGY_SYSTEM_OVERVIEW.md](./STRATEGY_SYSTEM_OVERVIEW.md) - 策略系统概览
- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - 实施路线图
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构文档

---

**文档版本**: 2.0
**最后更新**: 2025-02-09
**作者**: Claude Code Assistant
