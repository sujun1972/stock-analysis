# Stock-CLI 使用指南

**Stock-CLI** 是 A股量化交易系统的命令行工具，提供便捷的命令行接口访问核心功能。

---

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [命令详解](#命令详解)
  - [init - 初始化配置](#init---初始化配置)
  - [download - 下载数据](#download---下载数据)
  - [features - 计算特征](#features---计算特征)
  - [train - 训练模型](#train---训练模型)
  - [backtest - 运行回测](#backtest---运行回测)
  - [analyze - 因子分析](#analyze---因子分析)
- [常见问题](#常见问题)
- [高级用法](#高级用法)

---

## 安装

### 方法一：开发模式安装（推荐）

```bash
cd /path/to/stock-analysis/core
pip install -e .
```

### 方法二：直接使用脚本

```bash
cd /path/to/stock-analysis/core
/path/to/venv/bin/python ./bin/stock-cli --help
```

### 验证安装

```bash
# 方法一
stock-cli --version

# 方法二
/path/to/venv/bin/python ./bin/stock-cli --version
```

---

## 快速开始

### 1. 初始化配置

首次使用需要配置数据库和数据源：

```bash
./bin/stock-cli init
```

交互式向导会引导您配置：
- 数据库连接信息（TimescaleDB）
- 数据源设置（AkShare/Tushare）
- 存储路径配置

### 2. 下载数据

```bash
# 下载最近30天数据
./bin/stock-cli download --days 30

# 下载指定股票
./bin/stock-cli download --symbols 000001,600000 --days 60
```

### 3. 计算特征

```bash
# 计算指定股票的特征
./bin/stock-cli features --symbols 000001,600000

# 计算所有股票的特征
./bin/stock-cli features --symbols all --format parquet
```

### 4. 其他命令

```bash
# 查看所有可用命令
./bin/stock-cli --help

# 查看特定命令的帮助
./bin/stock-cli download --help
```

---

## 命令详解

### init - 初始化配置

**功能**: 交互式配置向导，帮助您快速配置系统

**用法**:
```bash
./bin/stock-cli init
```

**配置项**:
- 数据库主机、端口、用户名、密码
- 数据源选择（AkShare/Tushare）
- Tushare Token（可选）
- DeepSeek API Key（可选）
- 数据存储路径

**示例**:
```bash
$ ./bin/stock-cli init

欢迎使用 Stock-CLI!
让我们一起配置您的环境...

1. 数据库配置
数据库主机 [localhost]:
数据库端口 [5432]:
数据库名称 [stock_analysis]:
数据库用户名 [stock_user]:
数据库密码: ********

是否测试数据库连接? [Y/n]: y
✓ 数据库连接成功！

2. 数据源配置
默认数据源 [akshare/tushare] (akshare): akshare

配置文件已保存: /path/to/.env
```

---

### download - 下载数据

**功能**: 从数据源下载股票历史数据到TimescaleDB

**用法**:
```bash
./bin/stock-cli download [OPTIONS]
```

**选项**:

| 选项 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--symbols` | TEXT | 股票代码（逗号分隔）或 "all" | 必填 |
| `--days` | INTEGER | 下载最近N天数据 | 30 |
| `--start` | DATE | 开始日期 (YYYY-MM-DD) | - |
| `--end` | DATE | 结束日期 (YYYY-MM-DD) | - |
| `--provider` | CHOICE | 数据源（akshare/tushare） | 配置文件 |
| `--limit` | INTEGER | 限制下载数量（测试用） | - |
| `--workers` | INTEGER | 并行下载线程数 | 4 |

**示例**:

```bash
# 下载所有股票最近30天数据
./bin/stock-cli download --days 30

# 下载指定股票指定时间段
./bin/stock-cli download --symbols 000001,600000 \
  --start 2024-01-01 --end 2024-12-31

# 使用Tushare数据源
./bin/stock-cli download --provider tushare --days 60

# 测试：下载前10只股票
./bin/stock-cli download --limit 10 --days 7 --workers 2

# 下载单只股票
./bin/stock-cli download --symbols 000001 --days 90
```

**输出示例**:
```
✓ 开始下载任务

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  指标               值
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  股票数量           2
  时间范围           2024-01-01 ~ 2024-12-31
  数据源             akshare
  并行线程           4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⠋ 000001 完成 ━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:05

✓ 下载完成!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  指标               值
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  总计               2
  成功               2
  失败               0
  成功率             100.0%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### features - 计算特征

**功能**: 计算技术指标和Alpha因子

**支持的特征**:
- **60+ 技术指标**: MA, EMA, RSI, MACD, Bollinger, KDJ, CCI, ATR等
- **125+ Alpha因子**: 动量、反转、波动率、成交量、量价关系、技术形态等

**用法**:
```bash
./bin/stock-cli features [OPTIONS]
```

**选项**:

| 选项 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--symbols` | TEXT | 股票代码（逗号分隔）或 "all" | 必填 |
| `--start` | DATE | 开始日期 (YYYY-MM-DD) | 全部 |
| `--end` | DATE | 结束日期 (YYYY-MM-DD) | 全部 |
| `--format` | CHOICE | 输出格式（csv/parquet/hdf5） | parquet |
| `--output` | PATH | 输出目录 | /data/features |
| `--workers` | INTEGER | 并行计算线程数 | 4 |

**示例**:

```bash
# 计算指定股票的所有特征
./bin/stock-cli features --symbols 000001,600000

# 计算所有股票的特征
./bin/stock-cli features --symbols all --format parquet

# 指定时间范围
./bin/stock-cli features --symbols 000001 \
  --start 2024-01-01 --end 2024-12-31

# 自定义输出目录和格式
./bin/stock-cli features --symbols all \
  --format csv --output /data/my_features

# 使用更多线程加速
./bin/stock-cli features --symbols all --workers 8
```

**输出文件**:
```
/data/features/
├── 000001.parquet  # 平安银行特征文件
├── 600000.parquet  # 浦发银行特征文件
└── ...
```

---

### train - 训练模型

**功能**: 训练机器学习模型

**支持的模型**:
- **lightgbm**: LightGBM梯度提升树（推荐，速度快、精度高）
- **gru**: GRU循环神经网络（适合序列数据）
- **ridge**: Ridge线性回归（基线模型）

**用法**:
```bash
./bin/stock-cli train [OPTIONS]
```

**选项**:

| 选项 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--model` | CHOICE | 模型类型 | lightgbm |
| `--data` | PATH | 训练数据路径 | - |
| `--output` | PATH | 模型保存路径 | - |
| `--tune` | FLAG | 是否进行超参数调优 | False |
| `--trials` | INTEGER | 超参数调优次数 | 50 |

**示例**:

```bash
# 训练默认LightGBM模型
./bin/stock-cli train --data /data/features/

# 训练GRU模型并进行超参数调优
./bin/stock-cli train --model gru --tune --trials 100

# 指定模型保存路径
./bin/stock-cli train --output /data/models/my_model.pkl
```

**注意**: 此功能正在开发中，当前请使用 Python API 进行模型训练（见 `examples/model_training_example.py`）

---

### backtest - 运行回测

**功能**: 运行策略回测

**支持的策略**:
- **momentum**: 动量策略（追涨杀跌）
- **mean_reversion**: 均值回归策略（低买高卖）
- **multi_factor**: 多因子策略（综合多个因子）
- **ml**: 机器学习策略（基于模型预测）

**用法**:
```bash
./bin/stock-cli backtest [OPTIONS]
```

**选项**:

| 选项 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `--strategy` | CHOICE | 策略类型 | 必填 |
| `--start` | DATE | 回测开始日期 | - |
| `--end` | DATE | 回测结束日期 | - |
| `--capital` | FLOAT | 初始资金 | 1000000 |
| `--report` | CHOICE | 报告格式（text/html/json） | text |
| `--output` | PATH | 报告保存路径 | - |

**示例**:

```bash
# 运行动量策略回测
./bin/stock-cli backtest --strategy momentum --capital 1000000

# 指定回测时间范围
./bin/stock-cli backtest --strategy multi_factor \
  --start 2023-01-01 --end 2024-12-31

# 生成HTML报告
./bin/stock-cli backtest --strategy ml \
  --report html --output results/backtest.html
```

**注意**: 此功能正在开发中，当前请使用 Python API 进行回测（见 `examples/backtest_basic_usage.py`）

---

### analyze - 因子分析

**功能**: 进行因子分析

**子命令**:
- **ic**: 计算因子IC（信息系数）
- **quantiles**: 因子分层回测
- **corr**: 因子相关性分析
- **batch**: 批量分析所有因子

**用法**:
```bash
./bin/stock-cli analyze SUBCOMMAND [OPTIONS]
```

#### analyze ic - IC分析

计算因子的信息系数（IC），评估因子预测能力

```bash
./bin/stock-cli analyze ic --factor MOM_20 \
  --start 2023-01-01 --end 2024-12-31
```

#### analyze quantiles - 分层回测

将股票按因子值分层，回测各层收益

```bash
./bin/stock-cli analyze quantiles --factor MOM_20 --layers 5
```

#### analyze corr - 相关性分析

分析因子之间的相关性

```bash
./bin/stock-cli analyze corr --factors MOM_20,VOL_20,RSI_14
```

#### analyze batch - 批量分析

批量分析所有因子

```bash
./bin/stock-cli analyze batch --output reports/factor_analysis.html
```

**注意**: 此功能正在开发中，当前请使用 Python API 进行因子分析（见 `examples/factor_analysis_example.py`）

---

## 常见问题

### Q: 如何查看详细日志？

A: 使用 `--log-level DEBUG` 选项：

```bash
./bin/stock-cli --log-level DEBUG download --days 30
```

### Q: 如何禁用彩色输出？

A: 使用 `--no-color` 选项：

```bash
./bin/stock-cli --no-color download --days 30
```

### Q: 如何使用自定义配置文件？

A: 使用 `--config` 选项：

```bash
./bin/stock-cli --config /path/to/custom.env download --days 30
```

### Q: 下载数据失败怎么办？

A:
1. 检查数据库连接是否正常
2. 检查数据源配置（Tushare需要TOKEN）
3. 查看日志文件 `logs/stock_cli.log`
4. 尝试减少并行线程数 `--workers 1`

### Q: 如何批量处理？

A: 使用脚本批量调用：

```bash
# 批量下载多只股票
for symbol in 000001 600000 000002; do
    ./bin/stock-cli download --symbols $symbol --days 30
done
```

---

## 高级用法

### 1. 与其他工具集成

#### 与 Cron 定时任务集成

```bash
# 每天凌晨2点下载前一天数据
0 2 * * * cd /path/to/core && ./bin/stock-cli download --days 1
```

#### 与 CI/CD 集成

```yaml
# .github/workflows/daily-update.yml
name: Daily Data Update
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Download data
        run: ./bin/stock-cli download --days 1
```

### 2. 脚本化使用

```bash
#!/bin/bash
# daily_update.sh - 每日数据更新和特征计算

set -e

echo "=== 开始每日更新 ==="

# 1. 下载最新数据
echo "步骤 1/3: 下载数据..."
./bin/stock-cli download --days 1

# 2. 计算特征
echo "步骤 2/3: 计算特征..."
./bin/stock-cli features --symbols all --format parquet

# 3. 训练模型（可选）
echo "步骤 3/3: 训练模型..."
# ./bin/stock-cli train --model lightgbm

echo "=== 更新完成 ==="
```

### 3. 性能调优

```bash
# 增加并行线程数（根据CPU核心数调整）
./bin/stock-cli download --days 30 --workers 8

# 分批处理大量股票
./bin/stock-cli download --limit 100 --days 30
./bin/stock-cli download --limit 100 --days 30 --offset 100
```

### 4. 数据验证

```bash
# 下载后验证数据完整性
./bin/stock-cli download --days 30
./bin/stock-cli features --symbols 000001 # 测试是否能正常计算特征
```

---

## 附录

### 配置文件格式

`.env` 文件示例：

```env
# 数据库配置
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=stock_analysis
DATABASE_USER=stock_user
DATABASE_PASSWORD=your_password

# 数据源配置
DATA_PROVIDER=akshare
DATA_TUSHARE_TOKEN=your_token_here

# 路径配置
PATH_DATA_DIR=/data
PATH_MODELS_DIR=/data/models
PATH_CACHE_DIR=/data/cache
PATH_RESULTS_DIR=/data/results

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/stock_cli.log
```

### 环境变量

所有配置项都可以通过环境变量覆盖：

```bash
export DATABASE_HOST=remote.host.com
export DATABASE_PORT=5432
./bin/stock-cli download --days 30
```

### 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 130 | 用户中断（Ctrl+C） |

---

## 更多资源

- **项目文档**: [README.md](../README.md)
- **架构分析**: [ARCHITECTURE_ANALYSIS.md](../ARCHITECTURE_ANALYSIS.md)
- **开发路线图**: [DEVELOPMENT_ROADMAP.md](../DEVELOPMENT_ROADMAP.md)
- **示例代码**: [examples/](../examples/)
- **GitHub**: https://github.com/yourusername/stock-analysis

---

**文档版本**: v1.0.0
**更新日期**: 2026-01-30
**作者**: Stock Analysis Core Team
