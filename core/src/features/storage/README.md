# 特征存储模块重构说明

## 📋 重构概述

本次重构将原来单一的 `feature_storage.py` 文件按照**存储后端**拆分为模块化结构，采用**策略模式 + 工厂模式**实现，提升代码的可维护性和扩展性。

## 🏗️ 新的模块结构

```
features/
├── feature_storage.py          # 向后兼容的导出模块
├── storage/                    # 存储后端子模块
│   ├── __init__.py            # 模块导出
│   ├── base_storage.py        # 抽象基类
│   ├── parquet_storage.py     # Parquet 格式实现
│   ├── hdf5_storage.py        # HDF5 格式实现
│   ├── csv_storage.py         # CSV 格式实现
│   ├── feature_storage.py     # 主接口类（业务逻辑）
│   └── README.md              # 本文档
```

## 🎯 设计模式

### 1. 策略模式 (Strategy Pattern)

不同的存储格式（Parquet, HDF5, CSV）作为不同的策略实现：

```python
# 抽象基类定义接口
class BaseStorage(ABC):
    @abstractmethod
    def save(self, df, file_path, **kwargs) -> bool:
        pass

    @abstractmethod
    def load(self, file_path, **kwargs) -> Optional[pd.DataFrame]:
        pass

# 具体策略实现
class ParquetStorage(BaseStorage):
    def save(self, df, file_path, **kwargs):
        df.to_parquet(file_path, compression='snappy')
        return True
```

### 2. 工厂模式 (Factory Pattern)

通过工厂方法创建对应的存储后端：

```python
class FeatureStorage:
    STORAGE_BACKENDS = {
        'parquet': ParquetStorage,
        'hdf5': HDF5Storage,
        'csv': CSVStorage
    }

    def _create_backend(self, format: str) -> BaseStorage:
        backend_class = self.STORAGE_BACKENDS[format]
        return backend_class(storage_dir=str(self.storage_dir))
```

## 📦 各模块职责

### base_storage.py - 抽象基类

**职责**：
- 定义所有存储后端必须实现的接口
- 提供通用的文件路径构建、存在性检查、删除等功能
- 作为所有存储后端的基类

**核心方法**：
- `save(df, file_path)` - 保存数据（抽象方法）
- `load(file_path)` - 加载数据（抽象方法）
- `get_file_extension()` - 获取文件扩展名（抽象方法）
- `build_file_path(stock_code, feature_type, version)` - 构建文件路径
- `delete_file(file_path)` - 删除文件

### parquet_storage.py - Parquet 格式

**特点**：
- ✅ 推荐使用的默认格式
- ✅ 高性能读写
- ✅ 优秀的压缩率
- ✅ 支持列式存储

**配置选项**：
- `compression`: 压缩算法 (snappy, gzip, brotli, lz4, zstd)

### hdf5_storage.py - HDF5 格式

**特点**：
- 支持大规模数据
- 支持分层存储
- 适合科学计算场景
- 需要 pytables 依赖

**配置选项**：
- `complevel`: 压缩级别 (0-9)

### csv_storage.py - CSV 格式

**特点**：
- 文本格式，易读易调试
- 兼容性最好
- 适合小规模数据和数据交换

**配置选项**：
- `encoding`: 编码格式 (utf-8-sig, utf-8, gbk)

### feature_storage.py - 主接口类

**职责**：
- 提供统一的特征存储业务接口
- 管理元数据（metadata.json）
- 处理版本控制
- 支持 Scaler 对象的序列化
- 提供统计信息查询

**核心功能**：
- 特征保存/加载
- 批量操作
- 版本管理
- 元数据管理
- Scaler 管理
- 统计信息

## 🔌 使用方式

### 基本使用（与之前完全兼容）

```python
from features.feature_storage import FeatureStorage

# 初始化存储管理器
storage = FeatureStorage(
    storage_dir='data/features',
    format='parquet'  # 支持: parquet, hdf5, csv
)

# 保存特征
storage.save_features(
    df=feature_df,
    stock_code='000001',
    feature_type='technical',
    version='v1'
)

# 加载特征
df = storage.load_features('000001', feature_type='technical')
```

### 直接使用存储后端

```python
from features.storage import ParquetStorage
from pathlib import Path

# 直接使用 Parquet 后端
backend = ParquetStorage(storage_dir='data/features')
file_path = backend.build_file_path('000001', 'technical', 'v1')
backend.save(df, file_path)
df = backend.load(file_path)
```

## 🔄 向后兼容性

重构后的代码**完全向后兼容**，原有的导入和使用方式无需修改：

```python
# ✅ 原有导入方式仍然有效
from features.feature_storage import FeatureStorage
from features import FeatureStorage

# ✅ 所有公共 API 保持不变
storage = FeatureStorage(storage_dir='data/features', format='parquet')
storage.save_features(...)
storage.load_features(...)
storage.list_stocks(...)
```

## 📊 测试验证

所有现有测试用例均已通过验证：

```bash
✅ 基本导入测试
✅ 实例创建测试
✅ Parquet 格式读写测试
✅ CSV 格式读写测试
✅ 元数据管理测试
✅ 批量操作测试
✅ 版本控制测试
✅ 删除操作测试
```

## 🚀 优势和改进

### 代码质量提升

1. **单一职责原则**：每个类只负责一种存储格式
2. **开闭原则**：新增存储格式无需修改现有代码
3. **可测试性**：每个存储后端可独立测试
4. **代码复用**：通用逻辑抽取到基类

### 扩展性增强

添加新的存储格式只需三步：

```python
# 1. 创建新的存储后端类
class NewStorage(BaseStorage):
    def save(self, df, file_path, **kwargs):
        # 实现保存逻辑
        pass

    def load(self, file_path, **kwargs):
        # 实现加载逻辑
        pass

    def get_file_extension(self):
        return 'new'

# 2. 注册到工厂
FeatureStorage.STORAGE_BACKENDS['new'] = NewStorage

# 3. 开始使用
storage = FeatureStorage(format='new')
```

### 日志系统统一

所有存储后端统一使用项目日志系统：

```python
from utils.logger import logger

logger.info("特征保存成功")
logger.error("特征加载失败")
```

## 📝 对 Backend 项目的影响

经过完整分析，**backend 项目未直接使用 FeatureStorage**，因此本次重构：

- ✅ 不影响 backend 项目的任何功能
- ✅ 保持所有公共 API 完全兼容
- ✅ 所有测试用例继续有效

## 🎓 最佳实践

### 选择存储格式

| 格式 | 适用场景 | 性能 | 压缩率 |
|------|---------|------|--------|
| **Parquet** | 生产环境、大规模数据 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **HDF5** | 科学计算、复杂查询 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **CSV** | 调试、数据交换、小数据 | ⭐⭐ | ⭐ |

### 版本管理建议

```python
# 增量更新
storage.update_features(
    stock_code='000001',
    new_df=new_data,
    mode='append'  # 追加新数据并去重
)

# 完全替换
storage.update_features(
    stock_code='000001',
    new_df=new_data,
    mode='replace'  # 创建新版本
)
```

## 🐛 故障排查

### 导入错误

如果遇到 `ModuleNotFoundError: No module named 'utils.logger'`：

- 检查 loguru 是否安装：`pip install loguru`
- 代码已包含 fallback 机制，会自动降级到简单日志

### HDF5 不可用

如果需要使用 HDF5 格式：

```bash
pip install tables  # 或 pytables
```

## 📚 更多信息

- 原始实现：`features/feature_storage.py` (已重构为兼容导出模块)
- 测试文件：`tests/test_phase2_features.py`
- 相关文档：`features/FEATURE_STRATEGY_GUIDE.md`

---

**重构日期**：2026-01-26
**重构版本**：v2.0
**兼容性**：完全向后兼容
