# Core 核心代码目录

本目录包含项目的核心业务逻辑代码、脚本和测试。

## 📁 目录结构

```
core/
├── src/                    # 核心业务逻辑代码
│   ├── database/          # 数据库管理模块
│   ├── features/          # 特征工程模块
│   ├── models/            # AI模型模块
│   ├── backtest/          # 回测引擎模块
│   ├── config/            # 配置模块
│   ├── data/              # 数据处理模块
│   ├── strategy/          # 交易策略模块
│   ├── trade/             # 交易执行模块
│   └── utils/             # 工具函数
│
├── scripts/               # 辅助脚本
│   ├── download_data.py          # CSV数据下载（传统方式）
│   ├── download_data_to_db.py    # 数据库数据下载（推荐）
│   ├── test_akshare.py           # AkShare数据源测试
│   ├── run_analysis.sh           # 本地分析脚本
│   └── start_jupyter.sh          # Jupyter启动脚本
│
└── tests/                 # 测试脚本
    ├── test_phase1_data_pipeline.py
    ├── test_phase2_features.py
    ├── test_phase3_models.py
    └── test_phase4_backtest.py
```

## 🎯 用途

### 1. src/ - 核心代码

这是项目的核心业务逻辑库，包含：

- **数据管理**: 股票数据的下载、存储、查询
- **特征工程**: 技术指标计算、Alpha因子生成
- **AI模型**: LightGBM、GRU等机器学习模型
- **回测引擎**: 策略回测和性能评估
- **交易系统**: 策略执行和风险管理

**使用方式**:

1. **本地开发环境**:
   ```bash
   source stock_env/bin/activate
   python core/src/main.py
   ```

2. **Backend容器**:
   - 通过Docker挂载到容器内的`/app/src`
   - Backend服务通过`from src.xxx import yyy`调用

### 2. scripts/ - 辅助脚本

包含各种数据下载、处理和分析脚本。

**使用示例**:

```bash
# 测试AkShare数据源
python core/scripts/test_akshare.py

# 下载数据到数据库（推荐）
python core/scripts/download_data_to_db.py --years 5 --max-stocks 10

# 下载数据到CSV（传统方式）
python core/scripts/download_data.py

# 本地运行分析
./core/scripts/run_analysis.sh

# 启动Jupyter
./core/scripts/start_jupyter.sh
```

### 3. tests/ - 测试脚本

端到端功能测试脚本。

**运行测试**:

```bash
source stock_env/bin/activate

# 测试数据管道
python core/tests/test_phase1_data_pipeline.py

# 测试特征工程
python core/tests/test_phase2_features.py

# 测试模型训练
python core/tests/test_phase3_models.py

# 测试回测功能
python core/tests/test_phase4_backtest.py
```

## 🔄 与Backend的关系

```
core/src/  →  Docker挂载  →  /app/src (容器内)
                              ↓
                    backend/app/services/
                    (调用 from src.xxx)
```

**Backend不复制代码，而是通过Docker挂载访问core/src/**

这种设计的优势：
- ✅ 代码单一来源
- ✅ 本地和容器共享同一份代码
- ✅ 修改立即生效
- ✅ 避免重复和不一致

## 📝 开发指南

### 添加新功能模块

```python
# 在 core/src/mymodule/ 创建新模块
core/src/mymodule/
├── __init__.py
├── processor.py
└── utils.py

# Backend中使用
from src.mymodule.processor import MyProcessor
```

### 添加新脚本

```bash
# 在 core/scripts/ 创建脚本
touch core/scripts/my_script.py
chmod +x core/scripts/my_script.py
```

### 添加新测试

```bash
# 在 core/tests/ 创建测试
touch core/tests/test_my_feature.py
```

## 🚫 注意事项

1. **不要**在项目根目录创建`src/`目录
   - 核心代码在`core/src/`
   - 根目录的`src/`会被`.gitignore`忽略（Docker临时目录）

2. **不要**复制core/src到backend
   - 使用Docker挂载，不是复制

3. **保持**代码单一来源
   - 所有核心逻辑修改都在`core/src/`

## 📚 相关文档

- [项目架构文档](../docs/ARCHITECTURE.md)
- [数据库使用指南](../docs/DATABASE_USAGE.md)
- [Backend README](../backend/README.md)
- [项目根目录 README](../README.md)

---

**最后更新**: 2026-01-20
