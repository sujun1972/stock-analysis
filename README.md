# 股票技术分析系统（stock-analysis）

一个用于批量获取股票行情、计算常用技术指标并输出分析结果的 Python 项目，支持：

- 通过 **Tushare** 或 **yfinance** 拉取历史行情数据；
- 使用 **TA-Lib** 计算趋势、动量、波动率等技术指标；
- 生成带有移动均线 / RSI / MACD 等指标的图表（PNG）；
- 将分析结果保存为 CSV 文件，便于进一步加工；
- （可选）调用 **DeepSeek** 模型，对本地技术指标结果做自然语言分析（需配置 API Key）。

## 功能概览

核心模块：

- `src/data_fetcher.py`
  - `DataFetcher`：
    - `fetch_yfinance_data(...)`：使用 yfinance 获取股票数据；
    - `fetch_tushare_data(...)`：使用 Tushare Pro 接口获取 A 股日线数据；
    - `save_data_to_csv(...)` / `load_data_from_csv(...)`：将 DataFrame 保存/读取为 CSV。

- `src/technical_analysis.py`
  - `TechnicalAnalyzer`：基于 TA-Lib 计算常见技术指标：
    - 趋势：SMA5/20/50、EMA12/26、布林带（BBANDS）；
    - 动量：MACD、RSI14、随机指标（STOCH）、OBV 等；
    - 波动率：ATR14；
  - `comprehensive_analysis(df)`：合并原始行情 + 所有指标 + 交易信号；
  - `plot_analysis(df, symbol, save_path)`：绘制价格 + RSI + MACD 图表并保存为 PNG 文件。

- `src/a_stock_list_fetcher.py`
  - 提供从 Tushare 获取 **全市场 A 股列表** 的工具函数，生成 `data/a_stock_list.csv` 等股票代码列表文件，用于批量分析。

- `src/main.py`
  - 入口函数 `main()`：
    1. 从 `DATA_PATH/a_stock_list.csv` 读入待分析的股票代码列表；
    2. 逐个股票调用 `analyze_symbol(...)`：
       - 通过 `DataFetcher` 获取行情数据（当前默认使用 Tushare）；
       - 使用 `TechnicalAnalyzer` 计算技术指标和综合信号；
       - 将结果保存为 `data/<symbol>_analysis.csv` 与 `data/<symbol>_analysis.png`；
       - 打印简要技术分析报告与交易信号统计；
    3. 如配置了 `DEEPSEEK_API_KEY`，可以进一步调用 DeepSeek 对结果进行自然语言分析（目前相应代码默认是注释状态，按需开启）。

- `src/config/config.py`
  - 统一管理：
    - `BASE_DIR`：项目根目录路径；
    - `DATA_PATH`：数据与结果输出目录（默认为 `./data`）；
    - `TUSHARE_TOKEN`：从环境变量读取的 Tushare Token；
    - `DEFAULT_PERIOD` / `DEFAULT_INTERVAL`：默认时间区间与 K 线周期（目前主要在数据获取函数中使用）。

## 环境与依赖

### Python 版本

建议使用 **Python 3.9+**（本项目在 macOS + venv 环境下开发和运行）。

### 必要依赖

`requirements.txt` 中包含核心依赖：

```text
pandas>=1.5.0
numpy>=1.21.0
yfinance>=0.2.18
tushare>=1.2.89
TA-Lib>=0.4.28
matplotlib>=3.5.0
seaborn>=0.11.0
plotly>=5.0.0
jupyter>=1.0.0
python-dateutil>=2.8.2
python-dotenv>=1.0.0
```

> 注意：
> - `TA-Lib` 在不同平台上的安装可能需要预先安装系统级依赖（如 `brew install ta-lib` 等），请根据自己的系统手动处理；
> - `tushare` 使用前需要到 [tushare.pro](https://tushare.pro/) 注册并获取 Token；
> - `python-dotenv` 用于从 `.env` 文件加载本地敏感配置。

## 配置环境变量（.env）

项目使用 `.env` 文件管理本地敏感配置，代码通过 `python-dotenv` 自动加载：

- 示例文件：`/.env.example`
- 实际使用：在项目根目录复制一份并命名为 `.env`：

```bash
cp .env.example .env
```

然后编辑 `.env`，填入自己的真实值：

```ini
# DeepSeek AI API key used in src/main.py
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Tushare token used in src/config/config.py and data fetchers
TUSHARE_TOKEN=your_tushare_token_here
```

> `.env` 已经被 `.gitignore` 忽略，不会被提交到 git 仓库，请放心填写真实密钥。

## 初始化虚拟环境与安装依赖

以 `stock_env` 为项目虚拟环境名的一个典型流程：

```bash
cd /path/to/stock-analysis

# 创建虚拟环境（如尚未创建）
python -m venv stock_env

# 激活虚拟环境（macOS / Linux）
source stock_env/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 准备股票代码列表

项目默认从 `data/a_stock_list.csv` 读取待分析的股票代码：

- 文件格式：
  - 第一列为股票代码（如 `000001.SZ`、`601318.SH`），包含表头；
  - 其他列可以是股票名称、行业等，可选。

你可以通过以下方式获得或更新该文件：

1. **手动维护**：
   - 自己在 `data/a_stock_list.csv` 中维护一个想要分析的股票代码列表；

2. **使用 `a_stock_list_fetcher` 自动生成**（需配置好 `TUSHARE_TOKEN`）：
   - 直接运行：

     ```bash
     source stock_env/bin/activate
     python -m src.a_stock_list_fetcher
     ```

   - 该脚本会在 `data/` 目录下生成/更新：
     - `a_stock_list.csv`：基础 A 股列表；
     - `a_stock_list_detailed.csv`、`a_stock_list_basic.csv`：更详细的扩展信息（可选）。

## 运行分析

### 方式一：使用脚本 `run_analysis.sh`

```bash
cd /path/to/stock-analysis
chmod +x run_analysis.sh  # 如有需要
./run_analysis.sh
```

该脚本会：

1. 激活 `stock_env` 虚拟环境；
2. 运行 `python src/main.py`；
3. 分析完成后在终端停留，等待按任意键退出。

### 方式二：直接运行模块入口

在已激活虚拟环境的前提下：

```bash
cd /path/to/stock-analysis
python -m src.main
```

或：

```bash
python src/main.py
```

> 默认情况下，`main()` 会：
> - 使用 **Tushare** 作为数据源（`use_tushare=True`）；
> - 分析周期默认为最近约 6 个月（`period="6mo"`）。

## 分析结果输出

所有分析结果会写入 `data/` 目录下（已在 `.gitignore` 中忽略，不会进入 git 仓库）：

- `data/<symbol>_analysis.csv`
  - 包含原始行情数据以及各类技术指标列：SMA、EMA、RSI、MACD、布林带、ATR、综合信号 `composite_signal` 等；

- `data/<symbol>_analysis.png`
  - 图表包含：
    - K 线或收盘价 + 移动平均线（SMA20、SMA50 等）；
    - RSI 曲线及超买/超卖阈值线；
    - MACD、信号线及柱状图；

- 终端输出：
  - 每只股票会在命令行中打印：
    - 简要技术分析报告（价格、趋势、RSI 状态、MACD 信号、综合信号等）；
    - 交易信号统计（买入/卖出/中性信号数量、综合建议与置信度）。

## 可选：DeepSeek AI 分析

如果在 `.env` 中配置了 `DEEPSEEK_API_KEY`，可以在 `src/main.py` 中开启 AI 分析相关的代码段：

- `get_ai_analysis(symbol, df, trading_signal)` 会：
  - 取最近一段技术指标数据；
  - 将本地技术分析结果 `trading_signal` 一并作为上下文；
  - 调用 DeepSeek 的 `deepseek-chat` 模型，生成一段自然语言分析报告。

目前这部分调用默认是注释掉的，你可以按需要解开注释：

```python
# if trading_signal and analysis_result is not None:
#     print(f"\n=== 正在请求 DeepSeek AI 进行综合分析 ===")
#     ai_report = get_ai_analysis(symbol, analysis_result, trading_signal)
#     ...
```

> 提示：AI 分析只是对本地技术指标的一种补充解读，不应被视为投资建议。

## 开发与扩展建议

- 可以在 `src/technical_analysis.py` 中继续添加自定义指标，或引入新的信号合成逻辑；
- 可以在 `src/main.py` 中增加命令行参数（如时间区间、数据源切换、单只股票调试模式等）；
- 可以将结果上传到数据库 / Web 可视化前端，做一个简单的量化看板；
- 如需长期运行，建议增加日志记录与异常重试机制。

## 许可与声明

- 本项目主要用于个人学习与技术实验；
- 代码中涉及的任何信号和指标 **不构成任何形式的投资建议**，请勿据此进行实际交易决策。
