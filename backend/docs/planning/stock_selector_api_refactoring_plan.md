# Backend 项目：选股器 API 改造规划

**文档版本**: v1.0.0
**创建日期**: 2026-02-07
**规划阶段**: v3.1.0 - API 扩展

---

## 📋 改造目的

### 问题分析

当前 Backend 的三层架构 API（`/api/three-layer/*`）将选股、入场、退出策略耦合在一起，导致以下问题：

1. **API 复杂度过高**
   - 用户必须同时配置三层策略才能使用
   - 无法独立调用选股功能
   - 回测参数过多，易出错

2. **不符合实际使用场景**
   ```
   实际需求：
   1. 周末：调用选股 API → 获取本周推荐股票
   2. 平时：调用交易策略回测 API → 基于推荐股票回测
   3. 实盘：根据推荐股票 + 交易信号决策

   当前 API：
   1. 必须同时提供选股器 + 入场策略 + 退出策略
   2. 无法单独获取推荐股票列表
   3. 回测时重复计算选股逻辑
   ```

3. **前端集成困难**
   - 无法展示"今日推荐股票"页面
   - 回测配置表单过于复杂
   - 用户体验不友好

### 改造目标

**核心目标**：将选股器 API 与回测 API 解耦，提供独立的选股推荐服务

**具体目标**：
1. ✅ 新增独立的选股推荐 API
2. ✅ 新增基于固定股票池的策略回测 API
3. ✅ 保留三层架构 API（向后兼容）
4. ✅ 简化前端集成
5. ✅ 提升 API 性能

---

## 🎯 改造大纲

### 1. 新增选股推荐 API

#### 1.1 API 端点设计

**模块路径**: `/api/stock-selector/*`

| 端点 | 方法 | 功能 | 响应时间 |
|------|------|------|---------|
| `/api/stock-selector/selectors` | GET | 获取可用选股器列表 | <50ms |
| `/api/stock-selector/select` | POST | 运行选股器，获取推荐列表 | <2s |
| `/api/stock-selector/history` | GET | 查询历史选股记录 | <100ms |
| `/api/stock-selector/save` | POST | 保存选股结果 | <50ms |

#### 1.2 数据模型

**请求模型** (`SelectStocksRequest`):
```python
class SelectStocksRequest(BaseModel):
    """选股请求"""
    selector_id: str = Field(..., description="选股器ID (momentum/value/ml/external)")
    selector_params: Dict[str, Any] = Field(default_factory=dict, description="选股器参数")
    date: str = Field(..., description="选股日期 (YYYY-MM-DD)")
    stock_pool: Optional[List[str]] = Field(None, description="候选股票池（可选，默认全市场）")
```

**响应模型** (`SelectStocksResponse`):
```python
class StockRecommendation(BaseModel):
    """单个股票推荐"""
    stock_code: str
    stock_name: str
    score: float
    rank: int
    reason: Optional[str] = None  # 推荐理由
    metadata: Optional[Dict[str, Any]] = None  # 额外信息（如因子值）

class SelectStocksResponse(BaseModel):
    """选股响应"""
    date: str
    selector_id: str
    selector_params: Dict[str, Any]
    recommendations: List[StockRecommendation]
    total_count: int
    metadata: Optional[Dict[str, Any]] = None
```

#### 1.3 示例请求/响应

**请求示例**:
```bash
POST /api/stock-selector/select
```

```json
{
  "selector_id": "momentum",
  "selector_params": {
    "lookback_period": 20,
    "top_n": 50
  },
  "date": "2024-02-07",
  "stock_pool": null
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "选股成功",
  "data": {
    "date": "2024-02-07",
    "selector_id": "momentum",
    "selector_params": {
      "lookback_period": 20,
      "top_n": 50
    },
    "recommendations": [
      {
        "stock_code": "600519.SH",
        "stock_name": "贵州茅台",
        "score": 0.95,
        "rank": 1,
        "reason": "20日涨幅15.2%，动量强劲",
        "metadata": {
          "momentum_20d": 0.152,
          "volume_ratio": 1.35
        }
      },
      {
        "stock_code": "000858.SZ",
        "stock_name": "五粮液",
        "score": 0.92,
        "rank": 2,
        "reason": "20日涨幅13.8%",
        "metadata": {
          "momentum_20d": 0.138,
          "volume_ratio": 1.28
        }
      }
      // ... 其他 48 只股票
    ],
    "total_count": 50,
    "metadata": {
      "market_total": 5247,
      "selection_time_ms": 450
    }
  }
}
```

---

### 2. 新增简化回测 API

#### 2.1 API 端点设计

**模块路径**: `/api/backtest/strategy`（新增）

| 端点 | 方法 | 功能 | 响应时间 |
|------|------|------|---------|
| `/api/backtest/strategy` | POST | 基于固定股票池的策略回测 | <5s |

#### 2.2 数据模型

**请求模型** (`StrategyBacktestRequest`):
```python
class StrategyBacktestRequest(BaseModel):
    """策略回测请求（基于固定股票池）"""
    stock_pool: List[str] = Field(..., description="股票池（固定列表）")
    entry_id: str = Field(..., description="入场策略ID")
    entry_params: Dict[str, Any] = Field(default_factory=dict)
    exit_id: str = Field(..., description="退出策略ID")
    exit_params: Dict[str, Any] = Field(default_factory=dict)
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    initial_capital: float = Field(1000000.0, description="初始资金")
    rebalance_freq: str = Field('D', description="调仓频率 (D/W/M)")
    benchmark: Optional[str] = Field(None, description="基准（可选）")
```

#### 2.3 示例请求/响应

**请求示例**:
```bash
POST /api/backtest/strategy
```

```json
{
  "stock_pool": ["600519.SH", "000858.SZ", "600036.SH"],
  "entry_id": "immediate",
  "entry_params": {},
  "exit_id": "fixed_stop_loss",
  "exit_params": {
    "stop_loss_pct": -5.0
  },
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000.0,
  "rebalance_freq": "D",
  "benchmark": "000300.SH"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "回测完成",
  "data": {
    "success": true,
    "data": {
      "metrics": {
        "total_return": 0.28,
        "annual_return": 0.28,
        "sharpe_ratio": 1.65,
        "max_drawdown": -0.08,
        "win_rate": 0.58,
        "total_trades": 85
      },
      "trades": [...],
      "daily_portfolio": [...],
      "benchmark_comparison": {
        "strategy_return": 0.28,
        "benchmark_return": 0.15,
        "alpha": 0.13,
        "beta": 0.85
      }
    }
  }
}
```

---

### 3. 新增 Adapter 层

#### 3.1 StockSelectorAdapter

**文件**: `app/core_adapters/stock_selector_adapter.py`

```python
class StockSelectorAdapter:
    """
    选股器适配器

    职责：
    - 封装 Core 的 StockSelectionEngine
    - 异步调用支持
    - 结果格式转换
    - Redis 缓存
    """

    def __init__(self):
        self.data_adapter = DataAdapter()

    async def get_selectors(self) -> List[Dict[str, Any]]:
        """获取可用选股器列表（复用 three_layer_adapter）"""

    async def select_stocks(
        self,
        selector_id: str,
        selector_params: dict,
        date: str,
        stock_pool: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行选股器

        Returns:
            {
                'date': '2024-02-07',
                'selector_id': 'momentum',
                'recommendations': [
                    {
                        'stock_code': '600519.SH',
                        'score': 0.95,
                        'rank': 1,
                        ...
                    }
                ]
            }
        """
```

#### 3.2 简化回测 Adapter

**文件**: `app/core_adapters/strategy_backtest_adapter.py`

```python
class StrategyBacktestAdapter:
    """
    策略回测适配器（基于固定股票池）

    职责：
    - 封装 Core 的 BacktestEngine.backtest_trading_strategy()
    - 异步调用支持
    - 结果格式转换
    - Redis 缓存
    """

    async def run_backtest(
        self,
        entry_id: str,
        entry_params: dict,
        exit_id: str,
        exit_params: dict,
        stock_pool: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float,
        rebalance_freq: str
    ) -> Dict[str, Any]:
        """
        运行策略回测

        Returns:
            {
                'success': True,
                'data': {
                    'metrics': {...},
                    'trades': [...],
                    'daily_portfolio': [...]
                }
            }
        """
```

---

### 4. 文件结构调整

```
backend/
├── app/
│   ├── core_adapters/
│   │   ├── three_layer_adapter.py        # 保留（三层架构）
│   │   ├── stock_selector_adapter.py     # 新增（选股推荐）
│   │   └── strategy_backtest_adapter.py  # 新增（策略回测）
│   │
│   ├── api/endpoints/
│   │   ├── three_layer.py                # 保留（三层架构API）
│   │   ├── stock_selector.py             # 新增（选股推荐API）
│   │   └── backtest_strategy.py          # 新增（策略回测API，或扩展 backtest.py）
│   │
│   └── monitoring/
│       ├── stock_selector_monitor.py     # 新增（选股监控）
│       └── ...
```

---

## 📊 API 对比

### 改造前（三层架构 API）

```bash
POST /api/three-layer/backtest
```

```json
{
  "selector": {"id": "momentum", "params": {"top_n": 50}},
  "entry": {"id": "immediate", "params": {}},
  "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
  "rebalance_freq": "W",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "stock_codes": null  // 全市场5000+股票
}
```

**问题**：
- ❌ 必须同时配置三层策略
- ❌ 无法单独获取推荐股票
- ❌ 回测时加载全市场数据

### 改造后（分离式 API）

**步骤 1：选股**
```bash
POST /api/stock-selector/select
```

```json
{
  "selector_id": "momentum",
  "selector_params": {"lookback_period": 20, "top_n": 50},
  "date": "2024-02-07"
}
```

**响应**：推荐股票列表（50 只）

**步骤 2：回测**
```bash
POST /api/backtest/strategy
```

```json
{
  "stock_pool": ["600519.SH", "000858.SZ", ...],  // 使用步骤1的推荐列表
  "entry_id": "immediate",
  "exit_id": "fixed_stop_loss",
  "exit_params": {"stop_loss_pct": -5.0},
  "start_date": "2023-01-01",
  "end_date": "2023-12-31"
}
```

**优势**：
- ✅ 功能解耦，职责清晰
- ✅ 可独立查看推荐股票
- ✅ 回测只需加载50只股票数据
- ✅ 前端可展示推荐列表

---

## 🔄 实施计划

### Phase 1: Adapter 层开发（3天）

- [ ] 创建 `StockSelectorAdapter`
- [ ] 创建 `StrategyBacktestAdapter`
- [ ] 单元测试（40+ 用例）
- [ ] 缓存机制实现

### Phase 2: API 端点开发（3天）

- [ ] 实现 `/api/stock-selector/*` 端点
- [ ] 实现 `/api/backtest/strategy` 端点
- [ ] Pydantic 模型定义
- [ ] 参数验证和错误处理

### Phase 3: 监控和日志（1天）

- [ ] 实现 `StockSelectorMonitor`
- [ ] 添加 Prometheus 指标
- [ ] 结构化日志

### Phase 4: API 测试（2天）

- [ ] API 单元测试（30+ 用例）
- [ ] API 集成测试（20+ 用例）
- [ ] 性能测试
- [ ] 向后兼容性测试

### Phase 5: 文档更新（1天）

- [ ] 更新 API 参考文档
- [ ] 编写 API 使用指南
- [ ] 更新 Swagger 文档
- [ ] 编写迁移指南

---

## 📈 预期收益

### 性能提升

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 选股API响应时间 | - | <2s | 新功能 |
| 回测API响应时间 | 15s | <5s | ↓ 67% |
| 数据库查询 | 5000+ 股票 | 50 股票 | ↓ 99% |
| API调用次数 | 1次 | 2次 | 增加但更灵活 |

### 前端集成收益

1. ✅ 可展示"今日推荐股票"页面
2. ✅ 简化回测配置表单
3. ✅ 更好的用户体验
4. ✅ 支持保存/导出推荐列表

---

## ⚠️ 风险与挑战

### 风险点

1. **API 兼容性**
   - 缓解：保留所有旧 API
   - 缓解：版本标注（v1/v2）

2. **数据一致性**
   - 风险：选股结果和回测数据不一致
   - 缓解：时间戳验证
   - 缓解：数据快照机制

3. **缓存策略**
   - 风险：选股结果缓存过期
   - 缓解：合理的 TTL 设置（选股结果1天，回测结果1小时）

---

## ✅ 验收标准

1. **功能完整性**
   - ✅ 选股 API 正常工作
   - ✅ 策略回测 API 正常工作
   - ✅ 三层架构 API 不受影响

2. **性能达标**
   - ✅ 选股 API 响应 <2s
   - ✅ 回测 API 响应 <5s
   - ✅ QPS >= 500

3. **测试覆盖**
   - ✅ 新增代码测试覆盖率 70%+
   - ✅ 所有现有测试通过（380+ 用例）

4. **文档完整**
   - ✅ API 文档更新
   - ✅ Swagger 文档自动生成
   - ✅ 使用示例清晰

---

## 📚 相关文档

- [Core 改造规划](../../core/docs/planning/stock_selector_decoupling_plan.md)
- [Backend 架构总览](../architecture/overview.md)
- [API 参考文档](../api_reference/README.md)

---

**文档维护**: Backend Team
**最后更新**: 2026-02-07
**状态**: 📋 待审批
