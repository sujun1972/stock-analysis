# Phase 4 测试策略与工作流程

> **版本**: v1.0
> **日期**: 2026-02-06
> **上级文档**: [三层架构实施方案](./backtest_three_layer_architecture_implementation_plan.md)

---

## 📋 目录

- [测试策略](#测试策略)
- [工作量评估与排期](#工作量评估与排期)
- [开发工作流程](#开发工作流程)
- [代码审查清单](#代码审查清单)
- [部署计划](#部署计划)

---

## 测试策略

### 测试金字塔

```
               E2E 测试 (10%)
              ┌────────────┐
             /              \
            /   集成测试      \
           /    (30%)         \
          /____________________\
         /                      \
        /      单元测试 (60%)     \
       /__________________________\
```

### 测试覆盖目标

| 测试类型 | 测试数量 | 覆盖率目标 | 优先级 |
|---------|---------|-----------|--------|
| **单元测试** | 150+ | 90%+ | P0 |
| **集成测试** | 30+ | 100% API | P0 |
| **E2E 测试** | 5+ | 关键流程 | P1 |
| **总计** | 185+ | 75%+ | - |

---

### 单元测试计划

#### 1. 基础类测试（30 个测试用例）

**测试文件位置**：`backend/tests/unit/strategies/three_layer/base/`

| 模块 | 测试文件 | 测试用例 | 重点 |
|------|---------|---------|------|
| StockSelector | `test_stock_selector.py` | 8 | 参数验证、元数据获取 |
| EntryStrategy | `test_entry_strategy.py` | 8 | 参数验证、元数据获取 |
| ExitStrategy | `test_exit_strategy.py` | 8 | 参数验证、元数据获取 |
| StrategyComposer | `test_strategy_composer.py` | 6 | 组合验证、元数据组合 |

**示例测试用例**（StrategyComposer）：

```python
"""
测试策略组合器
"""

import pytest

from backend.app.strategies.three_layer.base.strategy_composer import StrategyComposer
from backend.app.strategies.three_layer.selectors.momentum_selector import MomentumSelector
from backend.app.strategies.three_layer.entries.ma_breakout_entry import MABreakoutEntry
from backend.app.strategies.three_layer.exits.atr_stop_loss_exit import ATRStopLossExit


def test_strategy_composer_initialization():
    """测试组合器初始化"""
    composer = StrategyComposer(
        selector=MomentumSelector(params={'top_n': 50}),
        entry=MABreakoutEntry(params={'short_window': 5}),
        exit=ATRStopLossExit(params={'atr_multiplier': 2.0}),
        rebalance_freq='W'
    )

    assert composer.rebalance_freq == 'W'
    assert composer.selector is not None
    assert composer.entry is not None
    assert composer.exit is not None


def test_strategy_composer_get_metadata():
    """测试获取元数据"""
    composer = StrategyComposer(
        selector=MomentumSelector(params={'top_n': 50}),
        entry=MABreakoutEntry(params={'short_window': 5}),
        exit=ATRStopLossExit(params={'atr_multiplier': 2.0}),
        rebalance_freq='W'
    )

    metadata = composer.get_metadata()

    assert 'selector' in metadata
    assert 'entry' in metadata
    assert 'exit' in metadata
    assert metadata['rebalance_freq'] == 'W'
    assert metadata['rebalance_freq_label'] == '每周'


def test_strategy_composer_validate_valid():
    """测试有效策略组合的验证"""
    composer = StrategyComposer(
        selector=MomentumSelector(params={'top_n': 50, 'lookback_period': 20}),
        entry=MABreakoutEntry(params={'short_window': 5, 'long_window': 20}),
        exit=ATRStopLossExit(params={'atr_multiplier': 2.0, 'atr_period': 14}),
        rebalance_freq='W'
    )

    validation = composer.validate()

    assert validation['valid'] is True
    assert len(validation['errors']) == 0


def test_strategy_composer_validate_invalid_params():
    """测试无效参数的验证"""
    composer = StrategyComposer(
        selector=MomentumSelector(params={'top_n': -50}),  # 负数，无效
        entry=MABreakoutEntry(params={'short_window': 5}),
        exit=ATRStopLossExit(params={'atr_multiplier': 2.0}),
        rebalance_freq='W'
    )

    validation = composer.validate()

    assert validation['valid'] is False
    assert len(validation['errors']) > 0


def test_strategy_composer_validate_invalid_freq():
    """测试无效频率的验证"""
    composer = StrategyComposer(
        selector=MomentumSelector(params={'top_n': 50}),
        entry=MABreakoutEntry(params={'short_window': 5}),
        exit=ATRStopLossExit(params={'atr_multiplier': 2.0}),
        rebalance_freq='INVALID'  # 无效频率
    )

    validation = composer.validate()

    assert validation['valid'] is False
    assert any('无效的选股频率' in err for err in validation['errors'])
```

#### 2. 选股器测试（24 个测试用例）

**测试重点**：
- ✅ 参数验证
- ✅ 选股逻辑正确性
- ✅ 边界条件（数据缺失、空数据等）
- ✅ 性能（大数据量）

**参考**：前面文档中已提供 `test_ma_breakout_entry.py` 示例

#### 3. 入场策略测试（20 个测试用例）

**测试重点**：
- ✅ 信号生成正确性
- ✅ 权重计算准确性
- ✅ 技术指标计算（RSI、MA 等）
- ✅ 边界条件处理

#### 4. 退出策略测试（28 个测试用例）

**测试重点**：
- ✅ 止损止盈触发条件
- ✅ ATR 计算准确性
- ✅ 时间管理正确性
- ✅ 组合策略的 OR 逻辑

#### 5. 回测引擎测试（30 个测试用例）

**测试文件**：`backend/tests/unit/services/test_three_layer_backtest_engine.py`

**测试重点**：
- ✅ 回测循环流程
- ✅ 买卖逻辑执行
- ✅ 持仓管理
- ✅ 资金管理
- ✅ 手续费计算
- ✅ 绩效指标计算

**关键测试用例**：

```python
def test_backtest_engine_buy_sell_flow():
    """测试完整的买卖流程"""
    engine = ThreeLayerBacktestEngine(initial_capital=1000000)

    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    market_data, stock_data = create_test_data(dates)

    # 创建简单策略：立即买入，5天后卖出
    selector = MomentumSelector(params={'top_n': 3})
    entry = ImmediateEntry()
    exit_strategy = TimeBasedExit(params={'holding_period': 5})

    # 执行回测
    result = engine.run_backtest(
        selector=selector,
        entry=entry,
        exit=exit_strategy,
        market_data=market_data,
        stock_data=stock_data,
        start_date='2024-01-01',
        end_date='2024-01-30',
        rebalance_freq='W'
    )

    # 验证结果
    assert len(result['trades']) > 0
    assert len(result['portfolio_value']) == 30
    assert 'total_return' in result['metrics']


def test_backtest_engine_commission_calculation():
    """测试手续费计算"""
    engine = ThreeLayerBacktestEngine(
        initial_capital=1000000,
        commission_rate=0.0003,  # 万三
        tax_rate=0.001  # 千一
    )

    # 模拟一次买卖
    # ... (构造测试数据)

    # 验证买入手续费
    buy_trade = result['trades'][0]
    expected_commission = buy_trade['amount'] * 0.0003
    assert abs(buy_trade['commission'] - expected_commission) < 0.01

    # 验证卖出手续费和印花税
    sell_trade = result['trades'][1]
    expected_commission = sell_trade['amount'] * 0.0003
    expected_tax = sell_trade['amount'] * 0.001
    assert abs(sell_trade['commission'] - expected_commission) < 0.01
    assert abs(sell_trade['tax'] - expected_tax) < 0.01
```

#### 6. API 端点测试（18 个测试用例）

**测试文件**：`backend/tests/unit/api/test_three_layer_strategy.py`

**测试重点**：
- ✅ 所有端点正常响应
- ✅ 参数验证
- ✅ 错误处理
- ✅ 响应格式

---

### 集成测试计划

#### 1. 端到端回测流程测试（10 个测试用例）

**测试文件**：`backend/tests/integration/test_three_layer_end_to_end.py`

**测试场景**：

| 测试场景 | 描述 | 预期结果 |
|---------|------|---------|
| **场景1：完整回测流程** | API调用 → 数据加载 → 回测执行 → 结果返回 | 成功返回完整结果 |
| **场景2：多策略并行** | 同时运行3个不同策略组合 | 所有策略正确执行 |
| **场景3：大数据量回测** | 100只股票 × 365天 | 响应时间 < 10s |
| **场景4：异常数据处理** | 缺失数据、异常值 | 优雅降级，不崩溃 |
| **场景5：参数边界测试** | 极端参数值 | 正确验证并拒绝 |

**示例集成测试**：

```python
"""
端到端集成测试
"""

import pytest
from httpx import AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_full_backtest_flow():
    """测试完整回测流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: 获取选股器列表
        response = await client.get("/api/three-layer-strategy/selectors")
        assert response.status_code == 200
        selectors = response.json()['data']
        assert len(selectors) >= 3

        # Step 2: 获取策略元数据
        response = await client.post(
            "/api/three-layer-strategy/metadata",
            json={
                "selector_id": "momentum",
                "selector_params": {},
                "entry_id": "ma_breakout",
                "entry_params": {},
                "exit_id": "atr_stop_loss",
                "exit_params": {},
                "rebalance_freq": "W"
            }
        )
        assert response.status_code == 200
        metadata = response.json()['data']
        assert 'selector' in metadata

        # Step 3: 执行回测
        response = await client.post(
            "/api/three-layer-strategy/backtest",
            json={
                "strategy": {
                    "selector_id": "momentum",
                    "selector_params": {"top_n": 10, "lookback_period": 20},
                    "entry_id": "ma_breakout",
                    "entry_params": {"short_window": 5, "long_window": 20},
                    "exit_id": "atr_stop_loss",
                    "exit_params": {"atr_multiplier": 2.0},
                    "rebalance_freq": "W"
                },
                "stock_codes": ["600000.SH", "000001.SZ", "000002.SZ"],
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "initial_capital": 1000000.0
            }
        )
        assert response.status_code == 200
        result = response.json()['data']

        # 验证结果结构
        assert 'portfolio_value' in result
        assert 'trades' in result
        assert 'metrics' in result
        assert len(result['portfolio_value']) > 0

        # 验证绩效指标
        metrics = result['metrics']
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
```

#### 2. 数据库集成测试（8 个测试用例）

**测试重点**：
- ✅ 策略配置持久化
- ✅ 回测历史记录保存
- ✅ 数据一致性

#### 3. 缓存集成测试（6 个测试用例）

**测试重点**：
- ✅ Redis 缓存命中
- ✅ 缓存失效机制
- ✅ 缓存穿透保护

#### 4. 性能测试（6 个测试用例）

**测试工具**：Locust

**测试场景**：
- 并发回测：10 个用户同时请求
- 负载测试：50 QPS 持续 5 分钟
- 压力测试：逐步增加负载直到系统崩溃

---

### E2E 测试计划

#### 用户故事测试（5 个测试用例）

| 用户故事 | 测试步骤 | 验收标准 |
|---------|---------|---------|
| **故事1：新手用户探索策略** | 1. 浏览策略列表<br>2. 查看策略详情<br>3. 使用默认参数回测 | 回测成功，看到净值曲线 |
| **故事2：专业用户自定义组合** | 1. 选择动量选股<br>2. 配置均线入场<br>3. 组合多个退出策略<br>4. 执行回测 | 复杂组合正确执行 |
| **故事3：使用外部选股** | 1. 选择外部选股器<br>2. 手动输入股票池<br>3. 配置入场和退出<br>4. 回测 | 正确应用外部股票池 |
| **故事4：对比多个策略** | 1. 分别运行 3 个策略<br>2. 查看对比结果 | 可以横向对比绩效 |
| **故事5：保存和复用策略** | 1. 配置策略组合<br>2. 保存为模板<br>3. 下次使用时加载 | 配置正确保存和加载 |

---

## 工作量评估与排期

### Phase 4.0 任务明细

| 任务 | 工作量（人天） | 依赖 | 负责人 | 开始日期 | 结束日期 |
|------|--------------|------|--------|---------|---------|
| **4.0.1 创建三层基类** | 3 | - | Backend | Day 1 | Day 3 |
| **4.0.2 实现基础选股器** | 3 | 4.0.1 | Backend | Day 4 | Day 6 |
| **4.0.3 实现基础入场策略** | 3 | 4.0.1 | Backend | Day 4 | Day 6 |
| **4.0.4 实现基础退出策略** | 4 | 4.0.1 | Backend | Day 7 | Day 10 |
| **4.0.5 实现回测适配器** | 4 | 4.0.1-4 | Backend | Day 11 | Day 14 |
| **4.0.6 创建 API 端点** | 2 | 4.0.5 | Backend | Day 15 | Day 16 |
| **4.0.7 单元测试** | 5 | 4.0.1-6 | Backend | Day 7 | Day 16 |
| **4.0.8 集成测试** | 3 | 4.0.6 | Backend | Day 17 | Day 19 |
| **4.0.9 文档编写** | 2 | 4.0.1-8 | Backend | Day 18 | Day 19 |
| **合计** | **29 人天** | - | - | - | **~4 周** |

**注**：部分任务可并行执行（如选股器、入场、退出策略可同时开发）

### Phase 4.1：策略库扩展（可选）

| 任务 | 工作量（人天） | 优先级 |
|------|--------------|--------|
| **迁移 Core 动量策略** | 2 | P1 |
| **迁移 Core 均值回归策略** | 2 | P1 |
| **迁移 Core 多因子策略** | 3 | P2 |
| **适配现有 2 个策略** | 3 | P2 |
| **合计** | **10 人天** | - |

### 总体工作量

```
Phase 4.0（核心）: 29 人天 ≈ 4 周（1人）或 2 周（2人并行）
Phase 4.1（扩展）: 10 人天 ≈ 1.5 周（1人）

总计：39 人天 ≈ 5.5 周（1人）或 3 周（2人）
```

---

## 开发工作流程

### Git 分支策略

```
main (生产分支)
  ↑
  merge after review
  ↑
develop (开发分支)
  ↑
  merge after testing
  ↑
feature/three-layer-architecture (功能分支)
  ├── feature/three-layer-base (子分支：基础类)
  ├── feature/three-layer-selectors (子分支：选股器)
  ├── feature/three-layer-entries (子分支：入场策略)
  ├── feature/three-layer-exits (子分支：退出策略)
  ├── feature/three-layer-backtest (子分支：回测引擎)
  └── feature/three-layer-api (子分支：API 端点)
```

### 提交规范

**格式**：`<type>(<scope>): <subject>`

**类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试用例
- `refactor`: 重构
- `style`: 代码格式

**示例**：
```bash
feat(three-layer): add MomentumSelector implementation
test(three-layer): add unit tests for MABreakoutEntry
docs(three-layer): add API usage examples
```

### 代码审查流程

1. **自检清单**（开发者）
   - ✅ 代码通过 `black` 格式化
   - ✅ 代码通过 `flake8` 检查
   - ✅ 单元测试覆盖率 ≥ 90%
   - ✅ 所有测试通过
   - ✅ 添加必要的文档字符串

2. **提交 PR**
   - 填写 PR 模板
   - 关联相关 Issue
   - 请求代码审查

3. **代码审查**（审查者）
   - 检查代码逻辑正确性
   - 检查边界条件处理
   - 检查性能影响
   - 检查安全性

4. **合并**
   - 审查通过后合并到 `develop`
   - 删除功能分支

---

## 代码审查清单

### 通用检查项

- [ ] 代码符合 PEP 8 规范
- [ ] 无明显的性能问题
- [ ] 无安全漏洞（SQL 注入、XSS 等）
- [ ] 异常处理完善
- [ ] 日志记录充分
- [ ] 文档字符串完整

### 三层架构特定检查项

- [ ] 继承正确的基类
- [ ] 实现所有抽象方法
- [ ] 参数验证完整
- [ ] 元数据定义正确
- [ ] ID 和 name 唯一
- [ ] 测试覆盖关键逻辑

### API 特定检查项

- [ ] 使用正确的 HTTP 方法
- [ ] 响应格式符合 ApiResponse 规范
- [ ] 参数验证使用 Pydantic
- [ ] 错误处理规范
- [ ] API 文档完整（Swagger）

---

## 部署计划

### 部署环境

| 环境 | 用途 | 分支 | URL |
|------|------|------|-----|
| **开发环境** | 日常开发测试 | `develop` | http://dev-api.stock-analysis.local |
| **测试环境** | QA 测试 | `develop` | http://test-api.stock-analysis.local |
| **生产环境** | 正式服务 | `main` | http://api.stock-analysis.com |

### 部署步骤

**1. 开发环境部署**（自动）

```bash
# Git push 后自动触发 CI/CD
git push origin develop

# Jenkins / GitHub Actions 自动执行：
# - 运行测试
# - 构建 Docker 镜像
# - 部署到开发环境
```

**2. 测试环境部署**（自动）

```bash
# develop 分支合并后自动部署
# - 运行完整测试套件
# - 构建生产镜像
# - 部署到测试环境
# - 执行冒烟测试
```

**3. 生产环境部署**（手动）

```bash
# Step 1: 创建 Release 分支
git checkout -b release/v2.1.0 develop

# Step 2: 更新版本号
# 修改 backend/app/__init__.py 中的 __version__

# Step 3: 合并到 main
git checkout main
git merge --no-ff release/v2.1.0

# Step 4: 打标签
git tag -a v2.1.0 -m "Release v2.1.0: Three-layer architecture"
git push origin main --tags

# Step 5: 触发生产部署（手动审批）
# Jenkins / GitHub Actions 等待审批后执行部署
```

### 回滚计划

```bash
# 如果生产环境出现问题，立即回滚到上一版本

# 方法1：回滚 Docker 容器
docker service update --rollback backend-api

# 方法2：重新部署上一版本
git checkout v2.0.0
# 触发部署流程
```

### 数据库迁移

**三层架构需要的数据库变更**（如有）：

```sql
-- 创建策略模板表（用户保存的策略组合）
CREATE TABLE IF NOT EXISTS strategy_templates (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    selector_id VARCHAR(50) NOT NULL,
    selector_params JSONB,
    entry_id VARCHAR(50) NOT NULL,
    entry_params JSONB,
    exit_id VARCHAR(50) NOT NULL,
    exit_params JSONB,
    rebalance_freq VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategy_templates_user_id ON strategy_templates(user_id);

-- 创建回测历史表
CREATE TABLE IF NOT EXISTS backtest_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    strategy_template_id INTEGER REFERENCES strategy_templates(id),
    stock_codes TEXT[],
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital NUMERIC,
    total_return NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    result_data JSONB,  -- 完整回测结果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_backtest_history_user_id ON backtest_history(user_id);
CREATE INDEX idx_backtest_history_created_at ON backtest_history(created_at DESC);
```

---

## 验收标准

### Phase 4.0 整体验收标准

- ✅ 所有单元测试通过（150+ 测试）
- ✅ 所有集成测试通过（30+ 测试）
- ✅ 测试覆盖率 ≥ 75%
- ✅ 代码通过 `black` 和 `flake8` 检查
- ✅ API 文档完整（Swagger）
- ✅ 用户文档完整（使用指南）
- ✅ 性能达标：P95 响应时间 < 5s
- ✅ 无已知 Bug
- ✅ 代码审查通过

### 上线检查清单

**功能检查**：
- [ ] 所有 6 个 API 端点正常工作
- [ ] 前端可以正确调用 API
- [ ] 回测结果准确
- [ ] 参数验证有效

**性能检查**：
- [ ] 单次回测响应时间 < 5s（100股票×180天）
- [ ] 并发 20 QPS 无错误
- [ ] 内存使用稳定

**安全检查**：
- [ ] 无 SQL 注入漏洞
- [ ] 参数验证完善
- [ ] 错误信息不泄漏敏感信息

**监控检查**：
- [ ] Prometheus 指标正常采集
- [ ] Grafana 仪表板显示正常
- [ ] 日志系统工作正常
- [ ] 告警规则配置完成

---

## 风险管理

### 风险识别

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| **回测性能不达标** | 中 | 高 | 并行化、缓存优化 |
| **策略逻辑 Bug** | 中 | 高 | 充分的单元测试、代码审查 |
| **API 响应超时** | 低 | 中 | 异步处理、超时设置 |
| **数据库性能问题** | 低 | 中 | 索引优化、连接池调优 |
| **前后端协议不一致** | 低 | 高 | 明确 API 文档、集成测试 |

### 应急预案

**问题 1：回测性能不达标**

- **应对措施**：
  1. 短期：限制回测参数范围（如最多 50 只股票、最长 365 天）
  2. 中期：实现并行回测、增加缓存
  3. 长期：考虑使用 C++ 扩展或 Rust 重写性能热点

**问题 2：策略逻辑 Bug**

- **应对措施**：
  1. 立即回滚到上一版本
  2. 修复 Bug 并补充测试用例
  3. 重新部署并验证

**问题 3：生产环境崩溃**

- **应对措施**：
  1. 立即回滚
  2. 分析日志和监控数据
  3. 在测试环境复现问题
  4. 修复后重新部署

---

## 持续改进

### 技术债务管理

**当前技术债务**：
- ValueSelector 仅为简化实现，需要集成真实基本面数据
- ExternalSelector 的 StarRanker 集成待实现
- 缺少做空策略支持
- 缺少高频回测支持

**优先级排序**：
1. P0：完成 StarRanker 集成（业务需求）
2. P1：ValueSelector 集成真实基本面数据（提升可用性）
3. P2：做空策略支持（扩展功能）
4. P3：高频回测（高级特性）

### 性能优化路线图

**短期（1-2 个月）**：
- 优化数据加载性能（并行加载）
- 实现选股器结果缓存
- 数据库查询优化

**中期（3-6 个月）**：
- 实现分布式回测（Celery）
- 优化回测算法（向量化计算）
- 增加 GPU 加速支持

**长期（6-12 个月）**：
- 微服务化（回测服务独立）
- 实时流式回测
- 机器学习模型集成

---

**文档维护者**：开发团队
**创建日期**：2026-02-06
**最后更新**：2026-02-06
