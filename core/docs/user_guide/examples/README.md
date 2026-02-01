# 示例代码

**Code Examples for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 📚 示例目录

本目录包含完整的工作流示例，帮助你快速上手Stock-Analysis Core。

### 数据相关示例

- [01_data_download.py](01_data_download.py) - 数据下载示例
- [data_quality_demo.py](data_quality_demo.py) - 数据质量检查示例

### 特征与分析示例

- [complete_factor_analysis_example.py](complete_factor_analysis_example.py) - 完整因子分析工作流

### 模型训练示例

- [model_basic_usage.py](model_basic_usage.py) - 模型基础使用
- [model_comparison_demo.py](model_comparison_demo.py) - 多模型对比
- [model_training_pipeline.py](model_training_pipeline.py) - 完整训练流水线
- [ensemble_example.py](ensemble_example.py) - 模型集成示例

### 回测示例

- [backtest_basic_usage.py](backtest_basic_usage.py) - 回测基础使用
- [backtest_comparison_demo.py](backtest_comparison_demo.py) - 策略对比回测
- [backtest_cost_optimization.py](backtest_cost_optimization.py) - 交易成本优化
- [backtest_market_neutral_demo.py](backtest_market_neutral_demo.py) - 市场中性策略
- [backtest_slippage_models_demo.py](backtest_slippage_models_demo.py) - 滑点模型对比

### 并行计算示例

- [parallel_backtest_demo.py](parallel_backtest_demo.py) - 并行回测
- [parallel_computing_demo.py](parallel_computing_demo.py) - 并行计算基础
- [parallel_optimization_demo.py](parallel_optimization_demo.py) - 并行参数优化

### 可视化示例

- [visualization_demo.py](visualization_demo.py) - 可视化报告生成

### 完整工作流

- [11_complete_workflow.py](11_complete_workflow.py) - 端到端完整交易工作流

---

## 📖 使用说明

### 运行示例

```bash
# 进入示例目录
cd docs/user_guide/examples

# 运行特定示例
python 01_data_download.py

# 使用虚拟环境
source ../../../venv/bin/activate
python 02_feature_calculation.py
```

### 前置条件

运行示例前，请确保：

1. ✅ 已安装所有依赖：`pip install -r requirements.txt`
2. ✅ 已初始化配置：`stock-cli init`
3. ✅ 数据库已启动（如使用TimescaleDB）

---

## 示例详解

### 数据相关

#### 01_data_download.py

**功能**: 演示如何从多个数据源下载A股数据

**学习内容**:
- 使用AkShare获取免费数据
- 使用Tushare Pro（需Token）
- 批量下载多只股票
- 保存到数据库
- 数据质量验证

**运行**:
```bash
python 01_data_download.py --stock 000001.SZ --start 2023-01-01
```

---

#### data_quality_demo.py

**功能**: 数据质量检查和清洗

**学习内容**:
- 6种数据验证器
- 7种缺失值处理方法
- 4种异常值检测
- 数据质量报告
- 自动化清洗流程

**运行**:
```bash
python data_quality_demo.py
```

---

### 特征与分析

#### complete_factor_analysis_example.py

**功能**: 完整的因子分析工作流

**学习内容**:
- IC计算（信息系数）
- 分层回测验证
- 因子单调性检验
- 因子相关性分析
- 因子衰减分析
- 综合评估报告

**运行**:
```bash
python complete_factor_analysis_example.py
```

---

### 模型训练

#### model_basic_usage.py

**功能**: 机器学习模型基础使用

**学习内容**:
- LightGBM基础训练
- 数据准备和特征工程
- 模型评估指标
- 预测结果分析

**运行**:
```bash
python model_basic_usage.py
```

---

#### model_comparison_demo.py

**功能**: 多模型对比分析

**学习内容**:
- LightGBM vs GRU vs Ridge
- 模型性能对比
- 适用场景分析
- 最佳模型选择

**运行**:
```bash
python model_comparison_demo.py
```

---

#### model_training_pipeline.py

**功能**: 完整的模型训练流水线

**学习内容**:
- 数据预处理
- 特征选择
- 超参数调优
- 交叉验证
- 模型持久化
- MLflow跟踪

**运行**:
```bash
python model_training_pipeline.py
```

---

#### ensemble_example.py

**功能**: 模型集成方法

**学习内容**:
- 加权平均集成
- Stacking集成
- 投票法集成
- 集成性能评估
- 模型多样性分析

**运行**:
```bash
python ensemble_example.py
```

---

### 回测分析

#### backtest_basic_usage.py

**功能**: 回测引擎基础使用

**学习内容**:
- 回测引擎初始化
- 单策略回测
- 性能指标计算
- 结果可视化

**运行**:
```bash
python backtest_basic_usage.py
```

---

#### backtest_comparison_demo.py

**功能**: 多策略对比回测

**学习内容**:
- 动量策略 vs 均值回归
- 多策略并行回测
- 性能对比分析
- 最优策略选择

**运行**:
```bash
python backtest_comparison_demo.py
```

---

#### backtest_cost_optimization.py

**功能**: 交易成本优化分析

**学习内容**:
- 佣金影响分析
- 印花税计算
- 滑点成本评估
- 成本优化策略

**运行**:
```bash
python backtest_cost_optimization.py
```

---

#### backtest_market_neutral_demo.py

**功能**: 市场中性策略回测

**学习内容**:
- 多空对冲策略
- Beta中性
- 风险控制
- 绝对收益策略

**运行**:
```bash
python backtest_market_neutral_demo.py
```

---

#### backtest_slippage_models_demo.py

**功能**: 滑点模型对比

**学习内容**:
- 固定滑点模型
- 比例滑点模型
- 成交量滑点模型
- 波动率滑点模型
- 真实成本模拟

**运行**:
```bash
python backtest_slippage_models_demo.py
```

---

### 并行计算

#### parallel_backtest_demo.py

**功能**: 并行回测多个策略

**学习内容**:
- 多进程并行
- 策略对比分析
- 性能基准测试
- 结果聚合

**运行**:
```bash
python parallel_backtest_demo.py --n-jobs 4
```

**性能提升**:
- 单进程：120秒（100只股票）
- 4进程：15秒（**8倍加速**）

---

#### parallel_computing_demo.py

**功能**: 并行计算基础

**学习内容**:
- 多进程并行计算
- 任务分发与收集
- 性能监控
- 错误处理

**运行**:
```bash
python parallel_computing_demo.py
```

---

#### parallel_optimization_demo.py

**功能**: 并行参数优化

**学习内容**:
- 网格搜索并行化
- 贝叶斯优化
- 参数空间探索
- 最优参数选择

**运行**:
```bash
python parallel_optimization_demo.py
```

---

### 可视化

#### visualization_demo.py

**功能**: 生成专业的可视化报告

**学习内容**:
- 净值曲线
- 回撤曲线
- 因子分析图表
- 月度收益热力图
- 交互式HTML报告
- 30+图表类型

**运行**:
```bash
python visualization_demo.py
```

---

### 完整工作流

#### 11_complete_workflow.py

**功能**: 端到端完整交易工作流

**学习内容**:
- 数据获取→特征工程→模型训练→策略回测→报告生成
- 错误处理
- 日志记录
- 结果持久化
- 生产级实现

**运行**:
```bash
python 11_complete_workflow.py --stock 000001.SZ
```

**工作流程**:
```
数据下载 → 质量检查 → 特征计算 → 模型训练 →
信号生成 → 回测执行 → 性能评估 → 报告生成
```

---

## 🎯 学习路径

### 初学者路径（1-3天）

1. `01_data_download.py` - 理解数据获取
2. `data_quality_demo.py` - 数据质量检查
3. `backtest_basic_usage.py` - 学习策略回测
4. `visualization_demo.py` - 生成可视化报告

### 进阶路径（3-5天）

5. `model_basic_usage.py` - 机器学习建模基础
6. `model_comparison_demo.py` - 多模型对比
7. `complete_factor_analysis_example.py` - 深度因子分析
8. `backtest_comparison_demo.py` - 策略对比

### 专家路径（5-7天）

9. `model_training_pipeline.py` - 完整训练流水线
10. `ensemble_example.py` - 模型集成
11. `parallel_backtest_demo.py` - 并行回测优化
12. `parallel_optimization_demo.py` - 参数优化
13. `11_complete_workflow.py` - 端到端工作流

### 专题学习

**交易成本与滑点**:
- `backtest_cost_optimization.py`
- `backtest_slippage_models_demo.py`

**市场中性策略**:
- `backtest_market_neutral_demo.py`

**并行计算优化**:
- `parallel_computing_demo.py`
- `parallel_backtest_demo.py`
- `parallel_optimization_demo.py`

---

## 💡 最佳实践

### 代码风格

所有示例遵循以下规范：

```python
# ✅ 好的实践
from src.api.feature_api import calculate_alpha_factors
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """主函数"""
    try:
        # 使用统一API
        response = calculate_alpha_factors(data)
        if response.is_success():
            logger.info("✅ 特征计算成功")
        else:
            logger.error(f"❌ 失败: {response.message}")
    except Exception as e:
        logger.exception(f"❌ 异常: {e}")

if __name__ == '__main__':
    main()
```

### 配置管理

```python
# ✅ 使用配置文件
from src.config import load_config

config = load_config('config/default_config.yaml')
model_params = config.model.lightgbm

# ❌ 避免硬编码
model = LightGBM(n_estimators=100, learning_rate=0.05)
```

---

## 📚 相关文档

- 📖 [快速开始](../quick_start.md)
- 🔧 [CLI指南](../CLI_GUIDE.md)
- 🤖 [模型使用指南](../MODEL_USAGE_GUIDE.md)
- 🔙 [回测使用指南](../BACKTEST_USAGE_GUIDE.md)

---

## 🤝 贡献示例

欢迎贡献新的示例代码！

### 贡献指南

1. 示例应完整可运行
2. 包含详细注释
3. 遵循项目代码规范
4. 提供README说明
5. 通过测试验证

### 提交方式

```bash
# 1. Fork项目
# 2. 添加新示例
cp template.py examples/13_your_example.py

# 3. 更新README
# 在本文件中添加示例说明

# 4. 提交PR
git add examples/13_your_example.py
git commit -m "docs: add example for XYZ"
git push origin feature/add-example
```

---

## ❓ 常见问题

### Q: 示例运行失败怎么办？

**A**: 检查以下几点：

1. 确保已安装所有依赖
2. 检查数据库是否启动
3. 验证配置文件是否正确
4. 查看日志文件排查错误

### Q: 如何修改示例参数？

**A**: 大多数示例支持命令行参数：

```bash
python 01_data_download.py --help  # 查看参数说明
```

或直接修改代码中的参数。

### Q: 示例数据从哪里获取？

**A**:
- 示例自动下载：运行示例时自动下载测试数据
- 手动下载：`stock-cli download --stock 000001.SZ --start 2023-01-01`
- 使用样本数据：`data/samples/` 目录下的示例数据

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
