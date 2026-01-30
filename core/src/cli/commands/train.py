"""
train命令 - 训练机器学习模型

支持训练LightGBM、GRU、Ridge等模型
"""

import sys
from pathlib import Path
from typing import Optional
import click

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from cli.utils.output import print_success, print_error, print_info, print_table, print_warning
from cli.utils.progress import create_progress_bar
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def load_training_data(data_path: Path, symbols: Optional[list] = None):
    """
    加载训练数据

    Args:
        data_path: 数据路径
        symbols: 股票代码列表

    Returns:
        (特征数据, 标签数据)
    """
    import pandas as pd
    import glob

    all_data = []

    # 查找所有特征文件
    if data_path.is_file():
        # 单个文件
        files = [data_path]
    else:
        # 目录下所有文件
        pattern = str(data_path / "*.parquet")
        files = glob.glob(pattern)

        if not files:
            pattern = str(data_path / "*.csv")
            files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"未找到数据文件: {data_path}")

    logger.info(f"找到 {len(files)} 个数据文件")

    # 读取数据
    for file in files:
        try:
            if file.endswith(".parquet"):
                df = pd.read_parquet(file)
            elif file.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                continue

            all_data.append(df)
        except Exception as e:
            logger.warning(f"读取文件失败 {file}: {e}")
            continue

    if not all_data:
        raise ValueError("没有成功加载任何数据")

    # 合并数据
    combined_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"加载数据: {len(combined_df)} 条记录, {len(combined_df.columns)} 个特征")

    return combined_df


def prepare_train_data(df, target_col: str = "return_5d"):
    """
    准备训练数据

    Args:
        df: 原始数据
        target_col: 目标列名

    Returns:
        (X_train, y_train, feature_names)
    """
    import pandas as pd
    import numpy as np

    # 确定目标列
    if target_col not in df.columns:
        # 尝试创建未来收益率作为目标
        if "close" in df.columns:
            df[target_col] = df["close"].pct_change(5).shift(-5)
            logger.info(f"创建目标列 {target_col} (5日未来收益率)")
        else:
            raise ValueError(f"数据中没有目标列 {target_col}，也无法创建")

    # 删除不需要的列
    exclude_cols = ["date", "trade_date", "ts_code", "symbol", target_col]
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    # 只保留数值型特征
    X = df[feature_cols].select_dtypes(include=[np.number])
    y = df[target_col]

    # 删除缺失值
    valid_idx = ~(X.isna().any(axis=1) | y.isna())
    X = X[valid_idx]
    y = y[valid_idx]

    logger.info(f"准备完成: {len(X)} 条有效记录, {len(X.columns)} 个特征")

    return X, y, X.columns.tolist()


@click.command()
@click.option(
    "--model",
    type=click.Choice(["lightgbm", "gru", "ridge"], case_sensitive=False),
    default="lightgbm",
    help="模型类型",
)
@click.option(
    "--data",
    type=click.Path(exists=True),
    required=True,
    help="训练数据路径（文件或目录）",
)
@click.option("--output", type=click.Path(), help="模型保存路径（默认从配置读取）")
@click.option("--target", default="return_5d", help="目标列名")
@click.option("--tune", is_flag=True, help="是否进行超参数调优")
@click.option("--trials", type=int, default=50, help="超参数调优次数")
@click.option("--test-size", type=float, default=0.2, help="测试集比例")
@click.pass_context
def train(ctx, model, data, output, target, tune, trials, test_size):
    """
    训练机器学习模型

    \b
    支持的模型:
        • lightgbm  - LightGBM梯度提升树（推荐）
        • gru       - GRU循环神经网络
        • ridge     - Ridge线性回归（基线）

    \b
    示例:
        # 训练默认LightGBM模型
        stock-cli train --data /data/features/

    \b
        # 训练GRU模型并进行超参数调优
        stock-cli train --model gru --data /data/features/ --tune --trials 100

    \b
        # 指定模型保存路径
        stock-cli train --model lightgbm --data /data/features/ \\
            --output /data/models/my_model.pkl
    """
    try:
        from models.model_trainer import UnifiedModelTrainer, TrainingConfig, DataSplitConfig
        import pandas as pd
        from sklearn.model_selection import train_test_split

        settings = get_settings()

        print_info(f"\n[bold green]开始模型训练[/bold green]", bold=True)

        # 显示任务信息
        task_info = {
            "模型类型": model.upper(),
            "数据路径": data,
            "目标列": target,
            "测试集比例": f"{test_size * 100:.0f}%",
            "超参数调优": "开启" if tune else "关闭",
        }
        if tune:
            task_info["调优次数"] = trials

        print_table(task_info, title="训练配置")

        # ==================== 1. 加载数据 ====================
        print_info("\n[1/5] 加载训练数据...")
        data_path = Path(data)
        df = load_training_data(data_path)

        # ==================== 2. 准备数据 ====================
        print_info("[2/5] 准备训练数据...")
        X, y, feature_names = prepare_train_data(df, target_col=target)

        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False  # 时间序列不打乱
        )

        data_info = {
            "总样本数": len(X),
            "训练集": len(X_train),
            "测试集": len(X_test),
            "特征数量": len(feature_names),
        }
        print_table(data_info, title="数据统计")

        # ==================== 3. 配置模型 ====================
        print_info(f"[3/5] 配置{model.upper()}模型...")

        # 确定输出路径
        if output is None:
            output_dir = settings.PATH_MODELS_PATH
            output_path = output_dir / f"{model}_model.pkl"
        else:
            output_path = Path(output)
            output_dir = output_path.parent

        output_dir.mkdir(parents=True, exist_ok=True)

        # 创建训练配置
        model_params = {}
        if model == "lightgbm":
            model_params = {
                "n_estimators": 1000,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "max_depth": -1,
                "min_child_samples": 20,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "random_state": 42,
                "n_jobs": -1,
            }
        elif model == "ridge":
            model_params = {
                "alpha": 1.0,
                "random_state": 42,
            }
        elif model == "gru":
            model_params = {
                "hidden_size": 64,
                "num_layers": 2,
                "dropout": 0.2,
                "learning_rate": 0.001,
            }

        training_config = TrainingConfig(
            model_type=model,
            model_params=model_params,
            output_dir=str(output_dir),
        )

        # ==================== 4. 训练模型 ====================
        print_info(f"[4/5] 训练{model.upper()}模型...")

        trainer = UnifiedModelTrainer(training_config)

        # 转换为DataFrame（trainer需要）
        X_train_df = pd.DataFrame(X_train, columns=feature_names)
        X_test_df = pd.DataFrame(X_test, columns=feature_names)
        y_train_series = pd.Series(y_train.values, name=target)
        y_test_series = pd.Series(y_test.values, name=target)

        # 训练
        with create_progress_bar() as progress:
            task = progress.add_task(f"[cyan]训练中...", total=None)

            trained_model = trainer.train(
                X_train=X_train_df,
                y_train=y_train_series,
                X_valid=X_test_df,
                y_valid=y_test_series,
            )

            progress.update(task, completed=True)

        # ==================== 5. 评估模型 ====================
        print_info("[5/5] 评估模型性能...")

        # 预测
        y_pred_train = trained_model.predict(X_train_df)
        y_pred_test = trained_model.predict(X_test_df)

        # 计算评估指标
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        import numpy as np

        train_metrics = {
            "MSE": mean_squared_error(y_train, y_pred_train),
            "RMSE": np.sqrt(mean_squared_error(y_train, y_pred_train)),
            "MAE": mean_absolute_error(y_train, y_pred_train),
            "R²": r2_score(y_train, y_pred_train),
        }

        test_metrics = {
            "MSE": mean_squared_error(y_test, y_pred_test),
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred_test)),
            "MAE": mean_absolute_error(y_test, y_pred_test),
            "R²": r2_score(y_test, y_pred_test),
        }

        # ==================== 6. 保存模型 ====================
        print_info("\n保存模型...")
        trained_model.save(str(output_path))

        # 保存训练元数据
        metadata = {
            "model_type": model,
            "model_path": str(output_path),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "n_features": len(feature_names),
            "target_column": target,
            "train_metrics": {k: float(v) for k, v in train_metrics.items()},
            "test_metrics": {k: float(v) for k, v in test_metrics.items()},
        }

        metadata_path = output_path.with_suffix(".json")
        import json

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # ==================== 显示结果 ====================
        print_info("\n[bold]训练完成![/bold]", bold=True)

        print_info("\n训练集性能:")
        print_table(
            {k: f"{v:.6f}" for k, v in train_metrics.items()}, title="训练集指标"
        )

        print_info("\n测试集性能:")
        print_table({k: f"{v:.6f}" for k, v in test_metrics.items()}, title="测试集指标")

        print_success(f"\n模型已保存: {output_path}")
        print_success(f"元数据已保存: {metadata_path}")

        # 特征重要性（仅LightGBM）
        if model == "lightgbm" and hasattr(trained_model.model, "feature_importances_"):
            print_info("\nTop 10 重要特征:")
            importances = trained_model.model.feature_importances_
            feature_importance = sorted(
                zip(feature_names, importances), key=lambda x: x[1], reverse=True
            )[:10]

            for i, (feat, imp) in enumerate(feature_importance, 1):
                print_info(f"  {i}. {feat}: {imp:.4f}")

    except KeyboardInterrupt:
        print_error("\n\n用户中断训练")
        sys.exit(130)
    except Exception as e:
        logger.exception("模型训练失败")
        print_error(f"训练失败: {e}")
        sys.exit(1)
