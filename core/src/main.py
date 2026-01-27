import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
try:
    # Prefer package-relative imports when running as a module (python -m src.main)
    from .data_fetcher import DataFetcher
    from .technical_analysis import TechnicalAnalyzer
    from .config.config import DATA_PATH
except ImportError:
    # Fallback for running as a script from project root
    from data_fetcher import DataFetcher
    from technical_analysis import TechnicalAnalyzer
    from config.config import DATA_PATH

from openai import OpenAI  # 确保已安装 openai 库
from loguru import logger

technical_analysis_system_prompt = """
你是一个专业的股票分析师。你的任务是根据用户提供的股票数据和技术指标，进行综合分析。

**请遵循以下步骤进行分析：**
1.  **解读趋势指标**：分析移动平均线（如SMA_20, SMA_50）的关系，判断当前是上涨、下跌还是盘整趋势。
2.  **评估动量指标**：分析RSI是否显示超买（>70）或超卖（<30）状态；判断MACD是否出现金叉或死叉。
3.  **识别关键价位**：结合布林带（BB_upper, BB_lower）分析当前价格所处位置，识别潜在的支撑和阻力位。
4.  **综合判断与建议**：基于以上分析，给出一个简要的结论，并指出需要关注的风险点或关键位置。

请以专业、客观且简洁的口吻进行回复，避免使用过于绝对的预测性词汇。
"""
 
# 初始化 DeepSeek 客户端（从环境变量加载 API Key，例如通过 .env）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

deepseek_client: Optional[OpenAI]
if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
    )
else:
    deepseek_client = None

def get_ai_analysis(symbol, df, trading_signal):
    """
    调用 DeepSeek API 获取对股票数据和交易信号的AI分析。
    """
    # 准备给AI看的数据摘要（取最新几行即可）
    data_preview = df.tail().to_string()

    # 构建用户提问
    user_query = f"""
    请分析以下股票 {symbol} 的数据和技术指标：

    【最新数据预览】
    {data_preview}

    【本地交易信号分析结果】
    {trading_signal}

    请基于以上信息，提供一份分析报告。
    """

    if deepseek_client is None:
        logger.info("未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return None

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",  # 指定使用的模型
            messages=[
                {"role": "system", "content": technical_analysis_system_prompt},
                {"role": "user", "content": user_query}
            ],
            max_tokens=1500,  # 控制回复长度
            temperature=0.3   # 控制创造性，分析类任务可以调低
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.info(f"调用 DeepSeek API 时出错: {e}")
        return None

# 安全获取值的辅助函数

def get_safe_value(df: pd.DataFrame, column_name: str) -> Optional[Any]:
    """从 DataFrame 中安全地获取指定列的最后一个非空值。

    返回 Python 标量类型（如 float、int、str）或 None。
    """
    if column_name not in df.columns:
        return None

    series = df[column_name].dropna()
    if series.empty:
        return None

    value = series.iloc[-1]

    # 如果这里拿到的仍然是一个向量 / Series，尝试再压缩成标量
    if isinstance(value, (pd.Series, pd.DataFrame)):
        try:
            value = value.iloc[-1]
        except Exception:
            return None

    # 统一在这里做缺失值判断，并避免 Series 布尔值歧义
    try:
        is_na = pd.isna(value)
    except Exception:
        return None

    # 如果 is_na 本身还是一个序列（例如 Series），说明这里没有明确的单一标量结果
    if isinstance(is_na, (pd.Series, pd.DataFrame)):
        return None

    if is_na:
        return None

    # 某些 pandas 标量类型（如 numpy 类型）带有 item() 方法
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            # 无法转换为标量时，直接返回原始值
            return value

    return value


def analyze_symbol(
    symbol: str,
    fetcher: DataFetcher,
    analyzer: TechnicalAnalyzer,
    period: str = "6mo",
    use_tushare: bool = False  # 新增参数，控制使用哪个数据源
) -> Optional[Dict[str, Any]]:
    """针对单个股票执行完整的数据获取、技术分析、图表和报告生成流程。"""
    logger.info(f"\n开始分析 {symbol}...")

    # 获取数据 - 根据 use_tushare 参数选择数据源
    if use_tushare:
        # 使用 Tushare 获取 A 股数据
        # 需要将 period 转换为 Tushare 需要的日期格式
        end_date = datetime.now().strftime('%Y%m%d')
        if period == "6mo":
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        elif period == "1y":
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        else:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        
        data = fetcher.fetch_tushare_data(symbol, start_date=start_date, end_date=end_date)
    else:
        # 使用 yfinance 获取数据（默认）
        data = fetcher.fetch_yfinance_data(symbol, period=period)

    if data is None or data.empty:
        logger.info(f"无法获取 {symbol} 的数据")
        return None

    # 技术分析
    analysis_result = analyzer.comprehensive_analysis(data)
    if analysis_result is None or analysis_result.empty:
        logger.info(f"{symbol} 的技术分析结果为空")
        return None

    # 保存结果
    csv_filename = f"{symbol}_analysis.csv"
    csv_path = fetcher.save_data_to_csv(analysis_result, csv_filename)

    if not csv_path:
        logger.error(f"保存 {symbol} 分析结果 CSV 文件失败")
        return None

    # 生成图表
    chart_filename = f"{symbol}_analysis.png"
    chart_path = os.path.join(DATA_PATH, chart_filename)
    analyzer.plot_analysis(analysis_result, symbol, chart_path)

    # 生成简单报告
    generate_report(analysis_result, symbol)

    # 生成交易信号
    trading_signal = generate_trading_signal(analysis_result, symbol)

    return {
        "symbol": symbol,
        "csv_path": csv_path,
        "chart_path": chart_path,
        "trading_signal": trading_signal,
        "analysis_df": analysis_result,
    }


def load_stock_symbols() -> list[str]:
    """从 data/a_stock_list.csv 读取股票代码列表。

    返回一个字符串列表；如果读取失败或结果为空，则返回空列表并打印原因。
    """
    csv_path = os.path.join(DATA_PATH, "a_stock_list.csv")
    try:
        stock_df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"从 {csv_path} 读取 a_stock_list.csv 失败: {e}")
        return []

    symbols = stock_df.iloc[:, 0].dropna().astype(str).tolist()
    if not symbols:
        logger.info("从 a_stock_list.csv 读取到的股票代码列表为空，程序结束。")
        return []

    return symbols


def main() -> None:
    logger.info("=== 股票技术分析系统启动 ===")

    # 初始化组件（可以在多个股票之间复用）
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()

    # 从 data/a_stock_list.csv 读取股票代码列表（第一列为股票代码，包含表头）
    symbols = load_stock_symbols()
    if not symbols:
        logger.info("未获取到任何股票代码，程序结束。")
        return

    for symbol in symbols:
        # # 使用 analyze_symbol 执行完整分析流程（数据获取、技术指标、保存结果、基础报告等）
        result = analyze_symbol(symbol, fetcher, analyzer, period="6mo", use_tushare=True)

        if not result:
            # analyze_symbol 内部已经打印了失败原因，这里直接跳过该 symbol
            continue

        trading_signal = result.get("trading_signal")
        analysis_result = result.get("analysis_df")

        # # 3. 调用 AI 进行分析（保持与原先逻辑一致）
        # if trading_signal and analysis_result is not None:
        #     logger.info(f"\n=== 正在请求 DeepSeek AI 进行综合分析 ===")
        #     ai_report = get_ai_analysis(symbol, analysis_result, trading_signal)

        #     if ai_report:
        #         logger.info("\n🤖 **DeepSeek AI 分析报告:**")
        #         logger.info(f"{ai_report}")
        #         # 你也可以选择将AI报告保存到文件
        #         # with open(f"{DATA_PATH}/{symbol}_ai_report.txt", "w") as f:
        #         #     f.write(ai_report)
        #     else:
        #         logger.error("AI 分析报告生成失败。")
        # else:
        #     logger.info("由于未生成有效的数据或交易信号，跳过AI分析步骤。")


def generate_trading_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict[str, Any]]:
    """生成交易信号并以人类可读的形式打印。"""
    logger.info(f"\n=== {symbol} 交易信号分析 ===")

    # 初始化信号计数器
    buy_signals = 0
    sell_signals = 0
    neutral_signals = 0

    # 1. 趋势分析
    sma_20 = get_safe_value(df, "SMA_20")
    sma_50 = get_safe_value(df, "SMA_50")
    if sma_20 is not None and sma_50 is not None:
        if sma_20 > sma_50:
            logger.success("✅ 趋势信号: 上涨趋势 (SMA20 > SMA50)")
            buy_signals += 1
        else:
            logger.error("❌ 趋势信号: 下跌趋势 (SMA20 < SMA50)")
            sell_signals += 1

    # 2. RSI 分析
    rsi = get_safe_value(df, "RSI_14")
    if rsi is not None:
        if rsi < 30:
            logger.success("✅ RSI信号: 超卖区域，可能反弹")
            buy_signals += 1
        elif rsi > 70:
            logger.error("❌ RSI信号: 超买区域，可能回调")
            sell_signals += 1
        else:
            logger.info("➡️ RSI信号: 正常区域")
            neutral_signals += 1

    # 3. MACD 分析
    macd = get_safe_value(df, "MACD")
    macd_signal = get_safe_value(df, "MACD_signal")
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            logger.success("✅ MACD信号: 金叉买入信号")
            buy_signals += 1
        else:
            logger.error("❌ MACD信号: 死叉卖出信号")
            sell_signals += 1

    # 4. 布林带分析
    bb_upper = get_safe_value(df, "BB_upper")
    bb_lower = get_safe_value(df, "BB_lower")
    close_price = get_safe_value(df, "Close")
    if bb_upper is not None and bb_lower is not None and close_price is not None:
        if close_price <= bb_lower:
            logger.success("✅ 布林带信号: 价格触及下轨，可能反弹")
            buy_signals += 1
        elif close_price >= bb_upper:
            logger.error("❌ 布林带信号: 价格触及上轨，可能回调")
            sell_signals += 1
        else:
            logger.info("➡️ 布林带信号: 价格在轨道内运行")
            neutral_signals += 1

    # 综合决策
    total_signals = buy_signals + sell_signals + neutral_signals
    if total_signals > 0:
        buy_ratio = buy_signals / total_signals
        sell_ratio = sell_signals / total_signals

        logger.info("\n📊 信号统计:")
        logger.info(f"买入信号: {buy_signals} 个")
        logger.info(f"卖出信号: {sell_signals} 个")
        logger.info(f"中性信号: {neutral_signals} 个")

        if buy_ratio >= 0.6:
            recommendation = "🟢 STRONG BUY - 强烈买入"
            confidence = "高"
        elif buy_ratio >= 0.4:
            recommendation = "🟡 WEAK BUY - 谨慎买入"
            confidence = "中"
        elif sell_ratio >= 0.6:
            recommendation = "🔴 STRONG SELL - 强烈卖出"
            confidence = "高"
        elif sell_ratio >= 0.4:
            recommendation = "🟠 WEAK SELL - 谨慎卖出"
            confidence = "中"
        else:
            recommendation = "⚪ HOLD - 持有观望"
            confidence = "低"

        logger.info(f"\n🎯 交易建议: {recommendation}")
        logger.info(f"📈 置信度: {confidence}")

        return {
            "recommendation": recommendation,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "neutral_signals": neutral_signals,
            "confidence": confidence,
        }

    return None


def generate_report(df: pd.DataFrame, symbol: str) -> None:
    """生成分析报告并打印关键信息。"""
    if df.empty:
        logger.info("No data to generate report")
        return

    logger.info(f"\n=== {symbol} Technical Analysis Report ===")

    # 获取最新数据
    latest = df.iloc[-1]

    # 价格信息
    if "Close" in latest:
        close_price = latest["Close"]
    elif "close" in latest:
        close_price = latest["close"]
    else:
        close_price = "N/A"
    logger.info(f"Latest Close Price: {close_price}")

    # 趋势判断
    sma_20 = get_safe_value(df, "SMA_20")
    sma_50 = get_safe_value(df, "SMA_50")
    if sma_20 is not None and sma_50 is not None:
        trend = "Uptrend" if sma_20 > sma_50 else "Downtrend"
        logger.info(f"Trend: {trend} (SMA20: {sma_20:.2f} vs SMA50: {sma_50:.2f})")

    # RSI状态
    rsi = get_safe_value(df, "RSI_14")
    if rsi is not None:
        if rsi > 70:
            status = "Overbought 🔴"
        elif rsi < 30:
            status = "Oversold 🟢"
        else:
            status = "Neutral ⚪"
        logger.info(f"RSI(14): {rsi:.1f} - {status}")

    # MACD信号
    macd = get_safe_value(df, "MACD")
    macd_signal = get_safe_value(df, "MACD_signal")
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            signal = "Buy Signal 🟢"
        else:
            signal = "Sell Signal 🔴"
        logger.info(f"MACD Signal: {signal} (MACD: {macd:.4f}, Signal: {macd_signal:.4f})")

    # 综合信号
    composite = get_safe_value(df, "composite_signal")
    if composite is not None:
        if composite > 0:
            overall = "Bullish 📈"
        elif composite < 0:
            overall = "Bearish 📉"
        else:
            overall = "Neutral ➡️"
        logger.info(f"Overall Signal: {overall} (Score: {composite})")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
