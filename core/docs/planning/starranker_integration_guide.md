# StarRanker 集成指南

> **版本**: v1.0
> **日期**: 2026-02-06
> **相关文档**: [三层架构升级方案](./three_layer_architecture_upgrade_plan.md)
> **状态**: 📝 规划中

---

## 📋 目录

- [一、StarRanker 概述](#一starranker-概述)
- [二、集成方案设计](#二集成方案设计)
- [三、详细实施步骤](#三详细实施步骤)
- [四、使用示例](#四使用示例)
- [五、测试方案](#五测试方案)

---

## 一、StarRanker 概述

### 1.1 StarRanker 是什么？

**StarRanker** 是一个**外部选股系统**，提供基于机器学习的股票推荐服务。

**核心功能**：
- 每周输出推荐股票池（通常 10-50 只股票）
- 基于多因子模型和机器学习算法
- 提供股票评分和排名

### 1.2 为什么需要集成 StarRanker？

**业务需求**：
1. **验证 StarRanker 的效果**：
   - 需要对 StarRanker 选出的股票进行回测
   - 评估选股质量和收益潜力

2. **组合策略研究**：
   - StarRanker 负责选股（Layer 1）
   - 用户自定义买卖策略（Layer 2 & 3）
   - 研究最优的入场和退出时机

3. **实盘交易准备**：
   - 回测验证通过后，可用于实盘交易
   - StarRanker 选股 + 自动化交易系统

**当前痛点**：
- ❌ Core v2.x 无法应用外部股票池
- ❌ 必须将 StarRanker 结果转换为评分矩阵（繁琐且不准确）

### 1.3 集成后的效果

```python
# ✅ 集成后的使用方式（简单直观）

from core.strategies.three_layer.selectors import ExternalSelector
from core.strategies.three_layer.entries import MABreakoutEntry
from core.strategies.three_layer.exits import ATRStopLossExit
from core.strategies.three_layer.base import StrategyComposer
from core.backtest import BacktestEngine

# 1. 创建 StarRanker 选股器
selector = ExternalSelector(params={
    'source': 'starranker',
    'api_endpoint': 'http://starranker.internal/api/v1/recommendations'
})

# 2. 创建入场策略（均线突破）
entry = MABreakoutEntry(params={
    'short_window': 5,
    'long_window': 20
})

# 3. 创建退出策略（ATR 止损）
exit_strategy = ATRStopLossExit(params={
    'atr_multiplier': 2.0
})

# 4. 组合策略
composer = StrategyComposer(
    selector=selector,
    entry=entry,
    exit=exit_strategy,
    rebalance_freq='W'  # 每周使用 StarRanker 最新推荐
)

# 5. 执行回测
engine = BacktestEngine(initial_capital=1000000)
results = engine.backtest_three_layer(
    composer=composer,
    prices=prices,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

print(f"总收益率: {results['metrics']['total_return']:.2%}")
print(f"夏普比率: {results['metrics']['sharpe_ratio']:.2f}")
```

---

## 二、集成方案设计

### 2.1 StarRanker 数据接口

#### 方案 A：HTTP API 集成（推荐）

**架构**：
```
Core 项目
    ↓ HTTP Request
StarRanker API Server
    ↓ 查询数据库
StarRanker Database
    ↓ 返回 JSON
Core 项目（获取股票列表）
```

**优点**：
- ✅ 解耦：StarRanker 和 Core 独立部署
- ✅ 可扩展：支持多个客户端
- ✅ 易于维护：接口清晰，版本控制简单

**缺点**：
- ⚠️ 网络延迟：需要 HTTP 调用
- ⚠️ 依赖性：StarRanker API 必须可用

**API 设计规范**：

```yaml
# StarRanker API v1.0 规范

GET /api/v1/recommendations
描述: 获取指定日期的股票推荐列表

请求参数:
  - date (required): 日期，格式 YYYY-MM-DD
  - top_n (optional): 返回股票数量，默认 50
  - min_score (optional): 最低评分，默认 0.0

响应格式:
{
  "date": "2024-02-06",
  "stocks": [
    {
      "code": "600000.SH",
      "name": "浦发银行",
      "score": 0.85,
      "rank": 1
    },
    {
      "code": "000001.SZ",
      "name": "平安银行",
      "score": 0.82,
      "rank": 2
    },
    ...
  ],
  "total_count": 50,
  "generated_at": "2024-02-06T08:00:00Z"
}

错误响应:
{
  "error": "数据不存在",
  "error_code": "DATA_NOT_FOUND",
  "message": "指定日期没有推荐数据"
}
```

#### 方案 B：数据库直连集成

**架构**：
```
Core 项目
    ↓ SQL Query
StarRanker Database
    ↓ 返回数据
Core 项目（解析数据）
```

**优点**：
- ✅ 性能高：无 HTTP 开销
- ✅ 实时性强：直接查询最新数据

**缺点**：
- ❌ 耦合度高：依赖数据库 Schema
- ❌ 安全风险：需要数据库访问权限
- ❌ 维护成本高：Schema 变更需要同步修改

**SQL 查询示例**：

```sql
-- StarRanker 数据库表结构（假设）
CREATE TABLE starranker_recommendations (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    score FLOAT NOT NULL,
    rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date_score (date, score DESC)
);

-- 查询指定日期的推荐股票
SELECT stock_code, stock_name, score, rank
FROM starranker_recommendations
WHERE date = '2024-02-06'
ORDER BY score DESC
LIMIT 50;
```

#### 方案 C：文件交换集成（最简单）

**架构**：
```
StarRanker
    ↓ 生成文件
共享文件系统 (NFS/S3)
    ↓ 读取文件
Core 项目
```

**优点**：
- ✅ 最简单：无需开发 API
- ✅ 零依赖：不需要网络连接

**缺点**：
- ❌ 不实时：需要等待文件生成
- ❌ 文件管理：需要清理旧文件
- ❌ 并发问题：多进程读取可能冲突

**文件格式示例**：

```csv
# starranker_recommendations_20240206.csv
date,stock_code,stock_name,score,rank
2024-02-06,600000.SH,浦发银行,0.85,1
2024-02-06,000001.SZ,平安银行,0.82,2
2024-02-06,600036.SH,招商银行,0.80,3
...
```

### 2.2 推荐方案

**✅ 推荐：方案 A（HTTP API 集成）**

**理由**：
1. 符合微服务架构最佳实践
2. 易于扩展和维护
3. 安全性好（API 认证、限流）
4. 可以支持多个客户端

**实施优先级**：
- **Phase 1**：先实现方案 C（文件交换），快速验证集成效果
- **Phase 2**：开发 StarRanker API，迁移到方案 A
- **备选**：如果 StarRanker 团队无法提供 API，使用方案 B（数据库直连）

---

## 三、详细实施步骤

### 3.1 Phase 1：文件交换集成（快速原型）

**目标**：最快实现 StarRanker 集成，验证效果

**工作量**：2 天

#### Step 1：定义文件格式规范

**文件命名规范**：
```
starranker_recommendations_YYYYMMDD.csv
例如：starranker_recommendations_20240206.csv
```

**文件存储位置**：
```
/data/starranker/recommendations/
├── starranker_recommendations_20240101.csv
├── starranker_recommendations_20240108.csv
├── starranker_recommendations_20240115.csv
...
```

**CSV 格式**：
```csv
date,stock_code,stock_name,score,rank
2024-02-06,600000.SH,浦发银行,0.85,1
2024-02-06,000001.SZ,平安银行,0.82,2
...
```

#### Step 2：实现 FileBasedStarRankerClient

```python
# core/src/integrations/starranker/file_client.py

import os
from datetime import datetime
from typing import List, Optional

import pandas as pd
from loguru import logger


class FileBasedStarRankerClient:
    """
    基于文件的 StarRanker 客户端

    从共享文件系统读取 StarRanker 推荐结果
    """

    def __init__(self, data_dir: str = "/data/starranker/recommendations"):
        """
        初始化客户端

        参数:
            data_dir: StarRanker 推荐文件存储目录
        """
        self.data_dir = data_dir

        if not os.path.exists(data_dir):
            logger.warning(f"StarRanker 数据目录不存在: {data_dir}")

    def get_recommendations(
        self,
        date: datetime,
        top_n: int = 50,
        min_score: float = 0.0
    ) -> List[str]:
        """
        获取指定日期的推荐股票列表

        参数:
            date: 日期
            top_n: 返回前 N 只股票
            min_score: 最低评分过滤

        返回:
            股票代码列表，例如 ['600000.SH', '000001.SZ', ...]
        """
        # 构造文件路径
        date_str = date.strftime("%Y%m%d")
        file_path = os.path.join(
            self.data_dir,
            f"starranker_recommendations_{date_str}.csv"
        )

        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f"StarRanker 推荐文件不存在: {file_path}")
            return []

        try:
            # 读取 CSV 文件
            df = pd.read_csv(file_path)

            # 验证必需列
            required_cols = ['stock_code', 'score']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"文件格式错误，缺少必需列: {required_cols}")
                return []

            # 过滤评分
            df = df[df['score'] >= min_score]

            # 按评分排序
            df = df.sort_values('score', ascending=False)

            # 取前 N 只
            stocks = df.head(top_n)['stock_code'].tolist()

            logger.info(
                f"从 StarRanker 获取推荐: date={date_str}, "
                f"count={len(stocks)}, min_score={min_score}"
            )

            return stocks

        except Exception as e:
            logger.error(f"读取 StarRanker 文件失败: {e}", exc_info=True)
            return []

    def get_latest_recommendations(
        self,
        top_n: int = 50,
        min_score: float = 0.0
    ) -> List[str]:
        """获取最新的推荐股票"""
        # 列出所有文件
        try:
            files = os.listdir(self.data_dir)
            csv_files = [f for f in files if f.startswith("starranker_recommendations_") and f.endswith(".csv")]

            if not csv_files:
                logger.warning("没有找到 StarRanker 推荐文件")
                return []

            # 按日期排序，取最新的
            csv_files.sort(reverse=True)
            latest_file = csv_files[0]

            # 解析日期
            date_str = latest_file.replace("starranker_recommendations_", "").replace(".csv", "")
            date = datetime.strptime(date_str, "%Y%m%d")

            return self.get_recommendations(date, top_n, min_score)

        except Exception as e:
            logger.error(f"获取最新推荐失败: {e}", exc_info=True)
            return []
```

#### Step 3：修改 ExternalSelector 支持文件模式

```python
# core/src/strategies/three_layer/selectors/external_selector.py

from ...integrations.starranker.file_client import FileBasedStarRankerClient


class ExternalSelector(StockSelector):
    def _fetch_from_starranker(self, date: pd.Timestamp) -> List[str]:
        """从 StarRanker 获取股票列表（文件模式）"""
        try:
            # 初始化文件客户端
            client = FileBasedStarRankerClient()

            # 获取推荐
            stocks = client.get_recommendations(
                date=date,
                top_n=self.params.get('top_n', 50),
                min_score=self.params.get('min_score', 0.0)
            )

            logger.info(f"StarRanker 返回 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            logger.error(f"从 StarRanker 获取数据失败: {e}", exc_info=True)
            return []
```

#### Step 4：测试验证

```python
# tests/integration/test_starranker_integration.py

import pytest
from datetime import datetime
from core.integrations.starranker.file_client import FileBasedStarRankerClient


def test_file_based_starranker_client(tmp_path):
    """测试基于文件的 StarRanker 客户端"""
    # 创建测试数据文件
    test_file = tmp_path / "starranker_recommendations_20240206.csv"
    test_file.write_text(
        "date,stock_code,stock_name,score,rank\n"
        "2024-02-06,600000.SH,浦发银行,0.85,1\n"
        "2024-02-06,000001.SZ,平安银行,0.82,2\n"
        "2024-02-06,600036.SH,招商银行,0.80,3\n"
    )

    # 初始化客户端
    client = FileBasedStarRankerClient(data_dir=str(tmp_path))

    # 获取推荐
    stocks = client.get_recommendations(
        date=datetime(2024, 2, 6),
        top_n=2
    )

    # 验证结果
    assert len(stocks) == 2
    assert stocks[0] == "600000.SH"
    assert stocks[1] == "000001.SZ"


def test_external_selector_with_starranker(tmp_path):
    """测试 ExternalSelector 使用 StarRanker"""
    # 创建测试数据
    test_file = tmp_path / "starranker_recommendations_20240206.csv"
    test_file.write_text(
        "date,stock_code,stock_name,score,rank\n"
        "2024-02-06,600000.SH,浦发银行,0.85,1\n"
        "2024-02-06,000001.SZ,平安银行,0.82,2\n"
    )

    # 创建选股器
    selector = ExternalSelector(params={
        'source': 'starranker',
        'data_dir': str(tmp_path),  # 使用测试目录
        'top_n': 2
    })

    # 执行选股
    stocks = selector.select(
        date=pd.Timestamp('2024-02-06'),
        market_data=None  # 不需要
    )

    # 验证结果
    assert len(stocks) == 2
    assert '600000.SH' in stocks
```

**验收标准**：
- ✅ 可以从文件读取 StarRanker 推荐
- ✅ ExternalSelector 正确集成
- ✅ 测试用例通过
- ✅ 可以进行端到端回测

---

### 3.2 Phase 2：HTTP API 集成（生产方案）

**目标**：实现生产级的 StarRanker API 集成

**工作量**：3 天（需要 StarRanker 团队配合）

#### Step 1：StarRanker API 开发（StarRanker 团队）

**技术栈**：FastAPI（推荐）

```python
# StarRanker API 实现（StarRanker 团队负责）

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import date

app = FastAPI(title="StarRanker API", version="1.0.0")


class StockRecommendation(BaseModel):
    """股票推荐"""
    code: str
    name: str
    score: float
    rank: int


class RecommendationResponse(BaseModel):
    """推荐响应"""
    date: str
    stocks: List[StockRecommendation]
    total_count: int
    generated_at: str


@app.get("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    date: str,  # 格式：YYYY-MM-DD
    top_n: int = 50,
    min_score: float = 0.0
):
    """
    获取指定日期的股票推荐

    参数:
        date: 日期，格式 YYYY-MM-DD
        top_n: 返回前 N 只股票，默认 50
        min_score: 最低评分，默认 0.0

    返回:
        推荐股票列表
    """
    # 查询数据库
    # ...

    return RecommendationResponse(
        date=date,
        stocks=[...],
        total_count=len(stocks),
        generated_at=datetime.now().isoformat()
    )
```

#### Step 2：Core 项目 API 客户端开发

```python
# core/src/integrations/starranker/api_client.py

import requests
from datetime import datetime
from typing import List, Optional
from loguru import logger


class StarRankerAPIClient:
    """
    StarRanker API 客户端

    通过 HTTP API 获取股票推荐
    """

    def __init__(
        self,
        base_url: str = "http://starranker.internal",
        api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        初始化客户端

        参数:
            base_url: StarRanker API 基础 URL
            api_key: API 密钥（如果需要认证）
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def get_recommendations(
        self,
        date: datetime,
        top_n: int = 50,
        min_score: float = 0.0
    ) -> List[str]:
        """
        获取指定日期的推荐股票列表

        参数:
            date: 日期
            top_n: 返回前 N 只股票
            min_score: 最低评分过滤

        返回:
            股票代码列表
        """
        url = f"{self.base_url}/api/v1/recommendations"

        # 构造请求参数
        params = {
            "date": date.strftime("%Y-%m-%d"),
            "top_n": top_n,
            "min_score": min_score
        }

        # 添加认证头（如果需要）
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # 发送请求
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            data = response.json()

            # 提取股票代码
            stocks = [stock['code'] for stock in data['stocks']]

            logger.info(
                f"从 StarRanker API 获取推荐: date={date.strftime('%Y-%m-%d')}, "
                f"count={len(stocks)}"
            )

            return stocks

        except requests.Timeout:
            logger.error(f"StarRanker API 请求超时（>{self.timeout}s）")
            return []

        except requests.HTTPError as e:
            logger.error(f"StarRanker API 请求失败: {e.response.status_code} - {e.response.text}")
            return []

        except Exception as e:
            logger.error(f"StarRanker API 调用异常: {e}", exc_info=True)
            return []

    def ping(self) -> bool:
        """检查 API 是否可用"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
```

#### Step 3：配置管理

```python
# core/src/config/starranker_config.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class StarRankerConfig:
    """StarRanker 配置"""

    # API 配置
    api_enabled: bool = False
    api_base_url: str = "http://starranker.internal"
    api_key: Optional[str] = None
    api_timeout: int = 10

    # 文件配置（备用）
    file_enabled: bool = True
    file_data_dir: str = "/data/starranker/recommendations"

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 86400  # 1天

    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        import os
        return cls(
            api_enabled=os.getenv("STARRANKER_API_ENABLED", "false").lower() == "true",
            api_base_url=os.getenv("STARRANKER_API_URL", "http://starranker.internal"),
            api_key=os.getenv("STARRANKER_API_KEY"),
            file_data_dir=os.getenv("STARRANKER_DATA_DIR", "/data/starranker/recommendations")
        )
```

**验收标准**：
- ✅ StarRanker API 开发完成
- ✅ API 客户端实现完成
- ✅ 支持认证和错误处理
- ✅ 集成测试通过

---

## 四、使用示例

### 4.1 基础使用

```python
from core.strategies.three_layer.selectors import ExternalSelector
from core.strategies.three_layer.entries import ImmediateEntry
from core.strategies.three_layer.exits import TimeBasedExit
from core.strategies.three_layer.base import StrategyComposer
from core.backtest import BacktestEngine

# 创建 StarRanker 选股器
selector = ExternalSelector(params={
    'source': 'starranker',  # 使用 StarRanker
    'top_n': 30              # 取前 30 只股票
})

# 立即入场策略（测试 StarRanker 选股效果）
entry = ImmediateEntry()

# 时间止损策略（持有 5 天）
exit_strategy = TimeBasedExit(params={'holding_period': 5})

# 组合策略
composer = StrategyComposer(
    selector=selector,
    entry=entry,
    exit=exit_strategy,
    rebalance_freq='W'  # 每周使用最新 StarRanker 推荐
)

# 执行回测
engine = BacktestEngine(initial_capital=1000000)
results = engine.backtest_three_layer(
    composer=composer,
    prices=prices,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 查看结果
print(f"总收益率: {results['metrics']['total_return']:.2%}")
print(f"夏普比率: {results['metrics']['sharpe_ratio']:.2f}")
print(f"最大回撤: {results['metrics']['max_drawdown']:.2%}")
```

### 4.2 高级使用：StarRanker + 技术指标

```python
# StarRanker 选股 + 均线突破入场 + ATR 止损

selector = ExternalSelector(params={
    'source': 'starranker',
    'min_score': 0.7  # 只取高分股票
})

entry = MABreakoutEntry(params={
    'short_window': 5,
    'long_window': 20,
    'min_breakout_pct': 1.0  # 突破幅度 > 1%
})

exit_strategy = CombinedExit([
    ATRStopLossExit(params={'atr_multiplier': 2.0}),
    FixedStopLossExit(params={'stop_loss_pct': 10.0})
])

composer = StrategyComposer(selector, entry, exit_strategy, rebalance_freq='W')
```

---

## 五、测试方案

### 5.1 单元测试

```python
# tests/unit/integrations/test_starranker_client.py

def test_file_client_basic():
    """测试文件客户端基本功能"""
    pass

def test_file_client_missing_file():
    """测试文件不存在的情况"""
    pass

def test_file_client_invalid_format():
    """测试文件格式错误的情况"""
    pass

def test_api_client_success():
    """测试 API 客户端成功场景"""
    pass

def test_api_client_timeout():
    """测试 API 超时"""
    pass

def test_api_client_auth_failure():
    """测试 API 认证失败"""
    pass
```

### 5.2 集成测试

```python
# tests/integration/test_starranker_backtest.py

def test_starranker_selector_backtest():
    """测试使用 StarRanker 选股器的完整回测"""
    # 创建策略组合
    # 执行回测
    # 验证结果
    pass
```

### 5.3 性能测试

**测试指标**：
- API 调用延迟：< 100ms
- 文件读取速度：< 10ms
- 缓存命中率：> 80%

---

## 六、FAQ

### Q1：StarRanker 每周更新一次，如何处理历史回测？

**A**：保留历史推荐文件，按日期查询。

### Q2：如果 StarRanker API 宕机怎么办？

**A**：实现降级机制，自动切换到文件模式或使用缓存数据。

### Q3：StarRanker 可以集成到 Backend 项目吗？

**A**：可以。Backend 的 ExternalSelector 设计与 Core 一致，直接复用即可。

---

**文档维护者**：Core 开发团队
**创建日期**：2026-02-06
**最后更新**：2026-02-06
