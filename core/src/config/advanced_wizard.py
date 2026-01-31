#!/usr/bin/env python3
"""
高级配置向导

提供性能、特征工程、策略等高级配置的交互式向导。
支持自动检测系统资源并推荐最优配置。
"""

import multiprocessing
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
import platform

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def detect_system_info() -> Dict[str, Any]:
    """检测系统信息"""
    import psutil

    cpu_count = multiprocessing.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024 ** 3)
    disk_free_gb = shutil.disk_usage("/").free / (1024 ** 3)

    # 检测GPU
    gpu_available = False
    gpu_name = "N/A"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_available = True
            gpu_name = "Apple MPS (Metal Performance Shaders)"
    except ImportError:
        pass

    return {
        "cpu_count": cpu_count,
        "memory_gb": memory_gb,
        "disk_free_gb": disk_free_gb,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "platform": platform.system(),
    }


def display_system_info(info: Dict[str, Any]) -> None:
    """显示系统信息"""
    table = Table(title="🖥️  系统资源检测", show_header=False)
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")

    table.add_row("操作系统", info["platform"])
    table.add_row("CPU 核心数", str(info["cpu_count"]))
    table.add_row("内存容量", f"{info['memory_gb']:.1f} GB")
    table.add_row("磁盘可用空间", f"{info['disk_free_gb']:.1f} GB")
    table.add_row("GPU", f"{'可用' if info['gpu_available'] else '不可用'}")
    if info["gpu_available"]:
        table.add_row("GPU 型号", info["gpu_name"])

    console.print(table)
    console.print()


def configure_performance(system_info: Dict[str, Any]) -> Dict[str, Any]:
    """配置性能参数"""
    console.print(Panel.fit(
        "⚡ 性能调优配置\n\n"
        "配置并行计算、GPU加速和内存优化参数",
        border_style="cyan"
    ))

    config = {}

    # 并行计算配置
    console.print("\n[bold cyan]1. 并行计算配置[/bold cyan]")

    # 选择后端
    backend_choices = ["multiprocessing", "threading", "ray", "dask"]
    backend_descriptions = {
        "multiprocessing": "多进程（推荐，适合CPU密集型任务）",
        "threading": "多线程（适合I/O密集型任务）",
        "ray": "Ray框架（适合分布式计算，需安装ray）",
        "dask": "Dask框架（适合大数据处理，需安装dask）",
    }

    console.print("\n可用的并行后端:")
    for i, backend in enumerate(backend_choices, 1):
        console.print(f"  {i}. [cyan]{backend}[/cyan] - {backend_descriptions[backend]}")

    backend = Prompt.ask(
        "\n选择并行后端",
        choices=["1", "2", "3", "4"],
        default="1"
    )
    backend_map = {"1": "multiprocessing", "2": "threading", "3": "ray", "4": "dask"}
    backend = backend_map[backend]

    # Worker数量
    max_workers = system_info["cpu_count"]
    console.print(f"\n[dim]检测到 {max_workers} 个 CPU 核心[/dim]")

    if backend == "multiprocessing":
        recommended_workers = max(1, max_workers - 1)  # 留一个核心给系统
    elif backend == "threading":
        recommended_workers = max_workers * 2  # 线程可以超配
    else:
        recommended_workers = max_workers

    n_workers = IntPrompt.ask(
        f"并行 worker 数量",
        default=recommended_workers
    )

    # Chunk大小
    chunk_size = IntPrompt.ask(
        "数据分块大小（影响任务粒度）",
        default=1000
    )

    config["parallel"] = {
        "backend": backend,
        "n_workers": n_workers,
        "chunk_size": chunk_size,
    }

    # GPU配置
    console.print("\n[bold cyan]2. GPU 加速配置[/bold cyan]")

    if system_info["gpu_available"]:
        console.print(f"✓ 检测到 GPU: [green]{system_info['gpu_name']}[/green]")
        enable_gpu = Confirm.ask("是否启用 GPU 加速?", default=True)

        if enable_gpu:
            device_id = IntPrompt.ask("GPU 设备 ID", default=0)
            mixed_precision = Confirm.ask(
                "是否启用混合精度训练? (可加速1.5-2倍，但需要新GPU支持)",
                default=True
            )

            config["gpu"] = {
                "enable_gpu": True,
                "device_id": device_id,
                "mixed_precision": mixed_precision,
            }
        else:
            config["gpu"] = {"enable_gpu": False}
    else:
        console.print("✗ 未检测到可用 GPU，将使用 CPU 模式")
        config["gpu"] = {"enable_gpu": False}

    # 内存优化
    console.print("\n[bold cyan]3. 内存优化配置[/bold cyan]")

    memory_gb = system_info["memory_gb"]
    console.print(f"系统内存: [green]{memory_gb:.1f} GB[/green]")

    enable_streaming = Confirm.ask(
        "是否启用流式处理? (处理大数据集时节省内存)",
        default=memory_gb < 16
    )

    if enable_streaming:
        memory_limit = IntPrompt.ask(
            "内存使用上限 (GB)",
            default=int(memory_gb * 0.7)  # 使用70%内存
        )
        config["memory"] = {
            "enable_streaming": True,
            "memory_limit_gb": memory_limit,
        }
    else:
        config["memory"] = {
            "enable_streaming": False,
        }

    # 显示性能预估
    console.print("\n" + "="*60)
    display_performance_summary(config, system_info)

    return config


def display_performance_summary(config: Dict[str, Any], system_info: Dict[str, Any]) -> None:
    """显示性能配置摘要"""
    table = Table(title="⚡ 性能配置摘要")
    table.add_column("配置项", style="cyan")
    table.add_column("当前值", style="green")
    table.add_column("预估加速", style="yellow")

    # 并行配置
    parallel = config["parallel"]
    table.add_row(
        "并行后端",
        parallel["backend"],
        "-"
    )
    table.add_row(
        "Worker 数量",
        str(parallel["n_workers"]),
        f"~{parallel['n_workers']}x" if parallel["backend"] == "multiprocessing" else "~2-3x"
    )
    table.add_row(
        "数据分块",
        str(parallel["chunk_size"]),
        "-"
    )

    # GPU配置
    gpu = config["gpu"]
    if gpu["enable_gpu"]:
        speedup = "5-10x (混合精度)" if gpu.get("mixed_precision") else "3-5x"
        table.add_row("GPU 加速", "启用", speedup)
    else:
        table.add_row("GPU 加速", "禁用", "-")

    # 内存配置
    memory = config["memory"]
    if memory["enable_streaming"]:
        table.add_row(
            "流式处理",
            f"启用 (限制 {memory['memory_limit_gb']} GB)",
            "节省内存 50-70%"
        )
    else:
        table.add_row("流式处理", "禁用", "-")

    console.print(table)


def configure_features() -> Dict[str, Any]:
    """配置特征工程参数"""
    console.print(Panel.fit(
        "🔧 特征工程配置\n\n"
        "选择要计算的技术指标和Alpha因子",
        border_style="cyan"
    ))

    config = {}

    # 技术指标配置
    console.print("\n[bold cyan]1. 技术指标配置[/bold cyan]")

    all_indicators = {
        "MA": "移动平均线",
        "EMA": "指数移动平均",
        "MACD": "异同移动平均线",
        "RSI": "相对强弱指标",
        "BOLL": "布林带",
        "KDJ": "随机指标",
        "CCI": "顺势指标",
        "ATR": "真实波幅",
    }

    console.print("\n可用技术指标:")
    for code, name in all_indicators.items():
        console.print(f"  • [cyan]{code}[/cyan] - {name}")

    use_all = Confirm.ask("\n是否启用所有技术指标?", default=True)

    if use_all:
        enabled_indicators = list(all_indicators.keys())
    else:
        console.print("\n请输入要启用的指标代码，用逗号分隔 (如: MA,EMA,MACD)")
        indicators_input = Prompt.ask("启用的指标")
        enabled_indicators = [ind.strip().upper() for ind in indicators_input.split(",")]

    # MA周期配置
    if "MA" in enabled_indicators or "EMA" in enabled_indicators:
        console.print("\n配置移动平均线周期")
        use_default_periods = Confirm.ask(
            "使用默认周期 [5, 10, 20, 60]?",
            default=True
        )

        if use_default_periods:
            ma_periods = [5, 10, 20, 60]
        else:
            periods_input = Prompt.ask(
                "输入周期（逗号分隔）",
                default="5,10,20,60"
            )
            ma_periods = [int(p.strip()) for p in periods_input.split(",")]
    else:
        ma_periods = []

    config["technical_indicators"] = {
        "enabled": enabled_indicators,
        "ma_periods": ma_periods,
        "ema_periods": ma_periods if "EMA" in enabled_indicators else [],
    }

    # Alpha因子配置
    console.print("\n[bold cyan]2. Alpha 因子配置[/bold cyan]")

    alpha_categories = {
        "momentum": "动量类因子（价格趋势、动量指标）",
        "reversal": "反转类因子（均值回归、超买超卖）",
        "volatility": "波动率因子（价格波动、风险指标）",
        "volume": "成交量因子（量价关系、资金流向）",
        "technical": "技术形态因子（图形识别、突破信号）",
    }

    console.print("\nAlpha 因子分类:")
    for cat, desc in alpha_categories.items():
        console.print(f"  • [cyan]{cat}[/cyan] - {desc}")

    enable_all_alpha = Confirm.ask("\n是否启用所有Alpha因子?", default=True)

    if enable_all_alpha:
        enabled_alpha = list(alpha_categories.keys())
    else:
        console.print("\n请输入要启用的因子类别，用逗号分隔 (如: momentum,reversal)")
        alpha_input = Prompt.ask("启用的因子类别")
        enabled_alpha = [cat.strip().lower() for cat in alpha_input.split(",")]

    # 动量周期配置
    if "momentum" in enabled_alpha:
        use_default_momentum = Confirm.ask(
            "\n使用默认动量周期 [5, 10, 20]?",
            default=True
        )
        momentum_periods = [5, 10, 20] if use_default_momentum else [
            int(p.strip()) for p in Prompt.ask("输入动量周期（逗号分隔）", default="5,10,20").split(",")
        ]
    else:
        momentum_periods = []

    config["alpha_factors"] = {
        "enabled": True,
        "categories": enabled_alpha,
        "momentum_periods": momentum_periods,
    }

    # 显示特征摘要
    display_features_summary(config)

    return config


def display_features_summary(config: Dict[str, Any]) -> None:
    """显示特征配置摘要"""
    console.print("\n" + "="*60)

    table = Table(title="🔧 特征工程摘要")
    table.add_column("类别", style="cyan")
    table.add_column("已启用", style="green")
    table.add_column("数量估算", style="yellow")

    # 技术指标
    tech_indicators = config["technical_indicators"]
    indicator_count = len(tech_indicators["enabled"]) * len(tech_indicators["ma_periods"]) if tech_indicators["ma_periods"] else len(tech_indicators["enabled"]) * 3
    table.add_row(
        "技术指标",
        ", ".join(tech_indicators["enabled"]),
        f"~{indicator_count} 个特征"
    )

    # Alpha因子
    alpha_factors = config["alpha_factors"]
    if alpha_factors["enabled"]:
        factor_count = len(alpha_factors["categories"]) * 20  # 每类约20个因子
        table.add_row(
            "Alpha 因子",
            ", ".join(alpha_factors["categories"]),
            f"~{factor_count} 个特征"
        )

    total_features = indicator_count + (factor_count if alpha_factors["enabled"] else 0)
    table.add_row(
        "[bold]总计[/bold]",
        "",
        f"[bold]~{total_features} 个特征[/bold]"
    )

    console.print(table)


def configure_strategies() -> Dict[str, Any]:
    """配置策略参数"""
    console.print(Panel.fit(
        "📈 策略配置\n\n"
        "配置回测、风控和优化参数",
        border_style="cyan"
    ))

    config = {}

    # 回测参数
    console.print("\n[bold cyan]1. 回测参数配置[/bold cyan]")

    initial_capital = IntPrompt.ask(
        "初始资金（元）",
        default=1000000
    )

    commission_rate = FloatPrompt.ask(
        "手续费率（如 0.0003 表示万三）",
        default=0.0003
    )

    slippage_choices = {
        "1": ("fixed", "固定滑点（每笔固定金额）"),
        "2": ("percentage", "百分比滑点（成交额的百分比）"),
        "3": ("volume_based", "基于成交量（根据成交量动态计算）"),
    }

    console.print("\n滑点模型:")
    for key, (model, desc) in slippage_choices.items():
        console.print(f"  {key}. [cyan]{model}[/cyan] - {desc}")

    slippage_choice = Prompt.ask("选择滑点模型", choices=["1", "2", "3"], default="3")
    slippage_model = slippage_choices[slippage_choice][0]

    config["backtest"] = {
        "initial_capital": initial_capital,
        "commission_rate": commission_rate,
        "slippage_model": slippage_model,
    }

    # 风控参数
    console.print("\n[bold cyan]2. 风控参数配置[/bold cyan]")

    max_drawdown = FloatPrompt.ask(
        "最大回撤限制（如 0.20 表示20%）",
        default=0.20
    )

    stop_loss = FloatPrompt.ask(
        "止损比例（如 0.10 表示10%）",
        default=0.10
    )

    position_limit = FloatPrompt.ask(
        "单只股票最大仓位（如 0.30 表示30%）",
        default=0.30
    )

    config["risk"] = {
        "max_drawdown": max_drawdown,
        "stop_loss": stop_loss,
        "take_profit": stop_loss * 2,  # 止盈为止损的2倍
        "position_limit": position_limit,
    }

    # 优化参数
    console.print("\n[bold cyan]3. 参数优化配置[/bold cyan]")

    enable_optimization = Confirm.ask(
        "是否启用参数优化?",
        default=False
    )

    if enable_optimization:
        optimizer_choices = {
            "1": ("grid_search", "网格搜索（全面但慢）"),
            "2": ("random_search", "随机搜索（快速探索）"),
            "3": ("bayesian", "贝叶斯优化（智能搜索）"),
            "4": ("optuna", "Optuna优化（需安装optuna）"),
        }

        console.print("\n优化器类型:")
        for key, (opt, desc) in optimizer_choices.items():
            console.print(f"  {key}. [cyan]{opt}[/cyan] - {desc}")

        optimizer_choice = Prompt.ask("选择优化器", choices=["1", "2", "3", "4"], default="3")
        optimizer_type = optimizer_choices[optimizer_choice][0]

        n_trials = IntPrompt.ask(
            "优化迭代次数",
            default=100
        )

        config["optimization"] = {
            "enabled": True,
            "optimizer_type": optimizer_type,
            "n_trials": n_trials,
        }
    else:
        config["optimization"] = {"enabled": False}

    # 显示策略摘要
    display_strategies_summary(config)

    return config


def display_strategies_summary(config: Dict[str, Any]) -> None:
    """显示策略配置摘要"""
    console.print("\n" + "="*60)

    table = Table(title="📈 策略配置摘要")
    table.add_column("类别", style="cyan")
    table.add_column("参数", style="green")
    table.add_column("值", style="yellow")

    # 回测参数
    backtest = config["backtest"]
    table.add_row("回测", "初始资金", f"{backtest['initial_capital']:,} 元")
    table.add_row("", "手续费率", f"{backtest['commission_rate']:.4f}")
    table.add_row("", "滑点模型", backtest['slippage_model'])

    # 风控参数
    risk = config["risk"]
    table.add_row("风控", "最大回撤", f"{risk['max_drawdown']:.1%}")
    table.add_row("", "止损比例", f"{risk['stop_loss']:.1%}")
    table.add_row("", "止盈比例", f"{risk['take_profit']:.1%}")
    table.add_row("", "仓位限制", f"{risk['position_limit']:.1%}")

    # 优化参数
    opt = config["optimization"]
    if opt["enabled"]:
        table.add_row("优化", "优化器", opt['optimizer_type'])
        table.add_row("", "迭代次数", str(opt['n_trials']))
    else:
        table.add_row("优化", "状态", "禁用")

    console.print(table)


def configure_monitoring() -> Dict[str, Any]:
    """配置监控参数"""
    console.print(Panel.fit(
        "📊 监控配置\n\n"
        "配置日志、指标收集和错误追踪",
        border_style="cyan"
    ))

    config = {}

    # 日志配置
    console.print("\n[bold cyan]1. 日志配置[/bold cyan]")

    log_level_choices = {
        "1": ("DEBUG", "调试级别（最详细）"),
        "2": ("INFO", "信息级别（推荐）"),
        "3": ("WARNING", "警告级别"),
        "4": ("ERROR", "错误级别（仅错误）"),
    }

    console.print("\n日志级别:")
    for key, (level, desc) in log_level_choices.items():
        console.print(f"  {key}. [cyan]{level}[/cyan] - {desc}")

    log_choice = Prompt.ask("选择日志级别", choices=["1", "2", "3", "4"], default="2")
    log_level = log_level_choices[log_choice][0]

    structured_logging = Confirm.ask(
        "是否启用结构化日志? (JSON格式，便于分析)",
        default=True
    )

    config["logging"] = {
        "level": log_level,
        "structured": structured_logging,
        "file_output": True,
        "console_output": True,
    }

    # 指标收集
    console.print("\n[bold cyan]2. 性能指标收集[/bold cyan]")

    enable_metrics = Confirm.ask(
        "是否启用性能指标收集?",
        default=True
    )

    if enable_metrics:
        collection_interval = IntPrompt.ask(
            "指标收集间隔（秒）",
            default=60
        )

        config["metrics"] = {
            "enabled": True,
            "collection_interval": collection_interval,
            "track_cpu": True,
            "track_memory": True,
            "track_disk": True,
        }
    else:
        config["metrics"] = {"enabled": False}

    # 错误追踪
    console.print("\n[bold cyan]3. 错误追踪配置[/bold cyan]")

    enable_error_tracking = Confirm.ask(
        "是否启用错误追踪?",
        default=True
    )

    if enable_error_tracking:
        config["error_tracking"] = {
            "enabled": True,
            "capture_locals": True,  # 捕获局部变量
            "max_breadcrumbs": 100,
        }
    else:
        config["error_tracking"] = {"enabled": False}

    # 显示监控摘要
    display_monitoring_summary(config)

    return config


def display_monitoring_summary(config: Dict[str, Any]) -> None:
    """显示监控配置摘要"""
    console.print("\n" + "="*60)

    table = Table(title="📊 监控配置摘要")
    table.add_column("类别", style="cyan")
    table.add_column("配置", style="green")
    table.add_column("状态", style="yellow")

    # 日志
    logging = config["logging"]
    table.add_row("日志", "级别", logging['level'])
    table.add_row("", "结构化", "启用" if logging['structured'] else "禁用")

    # 指标
    metrics = config["metrics"]
    if metrics["enabled"]:
        table.add_row("指标", "收集间隔", f"{metrics['collection_interval']} 秒")
        table.add_row("", "监控项", "CPU, 内存, 磁盘")
    else:
        table.add_row("指标", "状态", "禁用")

    # 错误追踪
    error_tracking = config["error_tracking"]
    table.add_row(
        "错误追踪",
        "状态",
        "启用" if error_tracking["enabled"] else "禁用"
    )

    console.print(table)


def save_advanced_config(config: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
    """保存高级配置到YAML文件"""
    import yaml

    if output_path is None:
        output_path = Path.cwd() / "config" / "advanced.yaml"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return output_path


def run_advanced_wizard(output_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    运行高级配置向导

    Args:
        output_path: 配置文件输出路径，默认为 config/advanced.yaml

    Returns:
        完整的高级配置字典
    """
    console.print(Panel.fit(
        "[bold cyan]🚀 高级配置向导[/bold cyan]\n\n"
        "本向导将帮助您配置性能、特征工程、策略和监控参数\n"
        "所有配置都会根据您的硬件自动优化建议",
        border_style="cyan",
        title="Stock-CLI Advanced Configuration Wizard"
    ))

    # 检测系统信息
    console.print("\n[bold]正在检测系统资源...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("检测中...", total=None)
        system_info = detect_system_info()
        progress.update(task, completed=True)

    console.print()
    display_system_info(system_info)

    # 收集各部分配置
    config = {}

    # 1. 性能配置
    if Confirm.ask("\n是否配置性能参数?", default=True):
        config["performance"] = configure_performance(system_info)
        console.print("\n[green]✓ 性能配置完成[/green]\n")

    # 2. 特征工程配置
    if Confirm.ask("是否配置特征工程参数?", default=True):
        config["features"] = configure_features()
        console.print("\n[green]✓ 特征工程配置完成[/green]\n")

    # 3. 策略配置
    if Confirm.ask("是否配置策略参数?", default=True):
        config["strategies"] = configure_strategies()
        console.print("\n[green]✓ 策略配置完成[/green]\n")

    # 4. 监控配置
    if Confirm.ask("是否配置监控参数?", default=True):
        config["monitoring"] = configure_monitoring()
        console.print("\n[green]✓ 监控配置完成[/green]\n")

    # 保存配置
    if Confirm.ask("\n是否保存配置到文件?", default=True):
        saved_path = save_advanced_config(config, output_path)
        console.print(f"\n[green]✓ 配置已保存到: {saved_path}[/green]")

    # 显示完整摘要
    console.print("\n" + "="*60)
    console.print(Panel.fit(
        "[bold green]🎉 高级配置完成![/bold green]\n\n"
        f"已配置模块: {', '.join(config.keys())}\n"
        "您可以随时运行向导重新配置",
        border_style="green"
    ))

    return config


if __name__ == "__main__":
    # 测试运行
    run_advanced_wizard()
