# 服务接口定义 (Service Interfaces)

本目录包含所有服务的接口定义，使用 Python `Protocol` 提供结构化类型约束和服务契约。

## 目录结构

```
interfaces/
├── __init__.py                    # 统一导出所有接口
├── sync_interfaces.py             # 数据同步服务接口
├── ml_interfaces.py               # 机器学习训练服务接口
├── backtest_interfaces.py         # 回测服务接口
├── experiment_interfaces.py       # 实验管理服务接口
├── config_interfaces.py           # 配置管理服务接口
└── README.md                      # 本文档
```

## 为什么使用 Protocol？

### 优势

1. **类型安全**: 提供编译时类型检查，减少运行时错误
2. **契约定义**: 明确服务的公共API，便于理解和维护
3. **鸭子类型**: 支持结构化子类型（Structural Subtyping），无需显式继承
4. **解耦**: 接口与实现分离，便于测试和替换实现
5. **文档化**: 接口本身就是最好的文档

### Protocol vs ABC

- **Protocol** (推荐): 结构化类型，不需要显式继承，更灵活
- **ABC**: 需要显式继承，更严格但也更繁琐

## 接口分类

### 1. 数据同步服务 (sync_interfaces.py)

- `IStockListSyncService` - 股票列表同步服务
- `IDailySyncService` - 日线数据同步服务
- `IRealtimeSyncService` - 实时行情同步服务
- `ISyncService` - 通用同步服务

### 2. 机器学习服务 (ml_interfaces.py)

- `ITrainingTaskManager` - 训练任务管理器
- `IModelPredictor` - 模型预测服务
- `IMLTrainingService` - ML训练服务Facade

### 3. 回测服务 (backtest_interfaces.py)

- `IBacktestDataLoader` - 回测数据加载器
- `IBacktestExecutor` - 回测执行器
- `IBacktestResultFormatter` - 回测结果格式化器
- `IBacktestService` - 回测服务Facade

### 4. 实验管理服务 (experiment_interfaces.py)

- `IBatchManager` - 批次管理器
- `IExperimentRunner` - 实验运行器
- `IExperimentService` - 实验管理服务Facade

### 5. 配置管理服务 (config_interfaces.py)

- `IDataSourceManager` - 数据源管理器
- `ISyncStatusManager` - 同步状态管理器
- `IConfigService` - 配置管理服务Facade

## 使用示例

### 1. 类型注解

```python
from app.interfaces import IStockListSyncService, IDailySyncService

# 使用接口作为类型注解
async def sync_stocks(service: IStockListSyncService) -> Dict:
    """
    使用接口作为参数类型，提供类型安全
    """
    result = await service.sync_stock_list()
    return result
```

### 2. 依赖注入

```python
from app.interfaces import IMLTrainingService
from app.services.ml_training_service import MLTrainingService

class ModelAPI:
    def __init__(self, ml_service: IMLTrainingService):
        """
        通过构造函数注入服务实例
        接受任何实现了 IMLTrainingService 接口的对象
        """
        self.ml_service = ml_service

    async def train(self, config: Dict) -> str:
        return await self.ml_service.create_task(config)

# 使用
api = ModelAPI(MLTrainingService())
```

### 3. Mock 测试

```python
from app.interfaces import IBacktestService
from typing import Dict, List, Union, Optional

class MockBacktestService:
    """
    Mock 实现，用于测试
    不需要继承，只需要实现接口定义的方法
    """
    async def run_backtest(
        self,
        symbols: Union[str, List[str]],
        start_date: str,
        end_date: str,
        initial_cash: float = 1000000.0,
        strategy_params: Optional[Dict] = None,
        strategy_id: str = "complex_indicator"
    ) -> Dict:
        return {
            "task_id": "mock_task_123",
            "metrics": {"sharpe_ratio": 1.5}
        }

    def get_task_result(self, task_id: str) -> Optional[Dict]:
        return None

# 类型检查通过
service: IBacktestService = MockBacktestService()
```

### 4. 策略模式

```python
from app.interfaces import ISyncService

def execute_sync(service: ISyncService, module: str):
    """
    接受任何实现了 ISyncService 的服务
    支持策略模式，可以轻松替换不同的实现
    """
    status = await service.get_module_sync_status(module)
    if status.get('status') == 'running':
        await service.abort_sync()
```

## 实现规范

### 1. 服务类应该隐式实现接口

**推荐** (使用 Protocol，无需显式继承):
```python
from app.interfaces import IStockListSyncService

class StockListSyncService:
    """
    自动满足 IStockListSyncService 接口
    无需显式继承，只要方法签名匹配即可
    """
    async def sync_stock_list(self) -> Dict:
        # 实现逻辑
        return {"total": 100}

    async def sync_new_stocks(self, days: int = 30) -> Dict:
        return {"total": 10}

    async def sync_delisted_stocks(self) -> Dict:
        return {"total": 5}
```

### 2. 类型检查

使用 mypy 进行类型检查：

```bash
# 检查单个文件
mypy backend/app/services/stock_list_sync_service.py

# 检查整个项目
mypy backend/app
```

### 3. IDE 支持

现代 IDE (PyCharm, VSCode) 会自动识别 Protocol 并提供：
- 代码补全
- 类型检查
- 重构支持
- 跳转到定义

## 设计原则

### 1. 接口隔离原则 (ISP)

接口应该小而专注，不要强迫客户端依赖它们不使用的方法。

**Good**:
```python
class IStockListSyncService(Protocol):
    # 只包含股票列表同步相关的方法
    async def sync_stock_list(self) -> Dict: ...
    async def sync_new_stocks(self, days: int = 30) -> Dict: ...
```

**Bad**:
```python
class ISyncService(Protocol):
    # 包含太多不相关的方法
    async def sync_stock_list(self) -> Dict: ...
    async def sync_daily_batch(self, ...) -> Dict: ...
    async def sync_realtime(self, ...) -> Dict: ...
```

### 2. 依赖倒置原则 (DIP)

高层模块不应该依赖低层模块，两者都应该依赖抽象。

```python
# API 层依赖接口，不依赖具体实现
from app.interfaces import IStockListSyncService

@router.post("/stock-list")
async def sync_stock_list(service: IStockListSyncService):
    result = await service.sync_stock_list()
    return result
```

### 3. 里氏替换原则 (LSP)

任何接口的实现都应该可以互相替换，而不影响程序的正确性。

```python
# 两个不同的实现可以互换
service1: IStockListSyncService = StockListSyncService()
service2: IStockListSyncService = MockStockListSyncService()

# 都可以正常工作
result1 = await service1.sync_stock_list()
result2 = await service2.sync_stock_list()
```

## 迁移指南

### 现有服务如何采用接口

1. **无需修改服务类**: Protocol 是结构化类型，只要方法签名匹配即可
2. **添加类型注解**: 在依赖注入点使用接口类型
3. **逐步迁移**: 可以渐进式地为服务添加接口约束

示例：

```python
# Before
class SyncAPI:
    def __init__(self):
        self.service = StockListSyncService()

# After
from app.interfaces import IStockListSyncService

class SyncAPI:
    def __init__(self, service: IStockListSyncService = None):
        self.service = service or StockListSyncService()
```

## 最佳实践

1. **使用接口作为参数类型**: 函数和方法应该接受接口而不是具体类
2. **不要在接口中包含实现**: Protocol 只定义方法签名
3. **保持接口稳定**: 接口一旦发布，应该尽量保持不变
4. **文档化接口**: 为每个接口方法添加详细的 docstring
5. **版本化接口**: 如果需要破坏性变更，创建新版本接口

## 工具支持

### mypy 配置

在 `pyproject.toml` 或 `mypy.ini` 中配置：

```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True

[mypy-app.services.*]
# 服务模块启用严格类型检查
strict = True
```

### VSCode 配置

在 `.vscode/settings.json` 中：

```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.enabled": true,
  "python.analysis.typeCheckingMode": "strict"
}
```

## 参考资源

- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [typing.Protocol Documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [mypy - Protocols and structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html)
