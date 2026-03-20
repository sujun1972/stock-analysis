"""
训练任务管理器
负责训练任务的生命周期管理
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from app.core.exceptions import BackendError
from app.repositories.experiment_repository import ExperimentRepository
from app.services.core_training import CoreTrainingService


class TrainingTaskManager:
    """
    训练任务管理器

    职责：
    - 创建和管理训练任务
    - 跟踪任务状态
    - 存储任务元数据
    - 执行训练流程
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        初始化任务管理器

        Args:
            models_dir: 模型存储目录
        """
        self.tasks: Dict[str, Dict[str, Any]] = {}  # 内存中的任务状态
        self.models_dir = models_dir or Path("/data/models/ml_models")

        # 尝试创建目录，如果失败则警告但不中断
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.warning(f"无法创建模型目录 {self.models_dir}: {e}，某些功能可能受限")

        # 任务元数据存储
        self.metadata_file = self.models_dir / "tasks_metadata.json"
        self._load_metadata()

        # Repository 实例
        self.experiment_repo = ExperimentRepository()

    def _load_metadata(self):
        """加载任务元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.tasks = json.load(f)
                logger.info(f"✓ 加载了 {len(self.tasks)} 个历史任务")
            except (json.JSONDecodeError, IOError) as e:
                # 文件损坏或不存在
                logger.warning(f"元数据文件加载失败，使用空字典: {e}")
                self.tasks = {}
            except Exception as e:
                # 其他未预期错误
                logger.error(f"加载元数据失败: {e}")
                self.tasks = {}

    def _save_metadata(self):
        """保存任务元数据"""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.tasks, f, indent=2, default=str)
        except (IOError, OSError) as e:
            # 文件写入失败
            logger.error(f"保存元数据失败 (文件写入错误): {e}")
        except Exception as e:
            # 其他未预期错误
            logger.error(f"保存元数据失败: {e}")

    async def create_task(self, config: Dict[str, Any]) -> str:
        """
        创建训练任务

        Args:
            config: 训练配置

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())

        task = {
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "config": config,
            "progress": 0,
            "current_step": "准备训练...",
            "metrics": {},
            "error": None,
            "error_message": None,
            "has_baseline": False,
            "baseline_metrics": None,
            "comparison_result": None,
            "recommendation": None,
            "total_samples": None,
            "successful_symbols": None,
        }

        self.tasks[task_id] = task
        self._save_metadata()

        logger.info(f"✓ 创建训练任务: {task_id}")
        return task_id

    async def run_training(self, task_id: str):
        """
        执行训练任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        # 更新任务状态
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        self._save_metadata()

        logger.info(f"🚀 开始训练任务: {task_id}")

        try:
            await self._run_training(task_id)

            # 训练成功
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["progress"] = 100

            logger.info(f"✓ 训练任务完成: {task_id}")

        except BackendError as e:
            # 已知业务异常
            task["status"] = "failed"
            task["error"] = str(e)
            task["error_message"] = str(e)
            task["failed_at"] = datetime.now().isoformat()

            logger.error(f"✗ 训练任务失败 (业务异常): {task_id} - {e}")
            raise
        except Exception as e:
            # 未预期错误
            task["status"] = "failed"
            task["error"] = str(e)
            task["error_message"] = str(e)
            task["failed_at"] = datetime.now().isoformat()

            logger.error(f"✗ 训练任务失败 (未预期错误): {task_id} - {e}")
            raise BackendError(
                f"训练任务执行失败: {task_id}",
                error_code="TRAINING_TASK_FAILED",
                task_id=task_id,
                reason=str(e),
            )
        finally:
            self._save_metadata()

    async def _run_training(self, task_id: str):
        """
        执行实际的训练过程

        Args:
            task_id: 任务ID
        """
        task = self.tasks[task_id]
        config = task["config"]

        # 检测是否启用池化训练
        enable_pooled = config.get("enable_pooled_training", False)
        symbols = config.get("symbols", [])

        if enable_pooled and len(symbols) > 1:
            # 使用池化训练Pipeline
            await self._run_pooled_training(task_id)
        else:
            # 使用单股票训练
            await self._run_single_stock_training(task_id)

    async def _run_single_stock_training(self, task_id: str):
        """
        执行单股票训练（原有逻辑）

        Args:
            task_id: 任务ID
        """
        task = self.tasks[task_id]
        config = task["config"]

        # 使用 CoreTrainingService 统一训练流程
        core_service = CoreTrainingService()

        # 准备训练配置
        training_config = {
            "symbol": config.get("symbol") or (config.get("symbols", [None])[0]),
            "start_date": config.get("start_date"),
            "end_date": config.get("end_date"),
            "model_type": config.get("model_type", "lightgbm"),
            "target_period": config.get("target_period", 5),
            "scaler_type": config.get("scaler_type", "robust"),
            "balance_samples": config.get("balance_samples", False),
            "model_params": config.get("model_params", {}),
            "use_async": True,  # 使用异步模式
        }

        # 添加可选参数
        if "seq_length" in config:
            training_config["seq_length"] = config["seq_length"]
        if "epochs" in config:
            training_config["epochs"] = config["epochs"]

        logger.info(f"[单股票训练] 配置: {training_config}")

        # 执行训练
        result = await asyncio.to_thread(core_service.train_model, **training_config)

        # 保存训练结果
        task["metrics"] = result.get("metrics", {})
        task["model_path"] = str(result.get("model_path", ""))
        task["feature_importance"] = result.get("feature_importance", {})
        task["has_baseline"] = False

        # 更新进度
        task["progress"] = 100

        logger.info(f"✓ 单股票训练完成，模型路径: {task['model_path']}")

        self._save_metadata()

    async def _run_pooled_training(self, task_id: str):
        """
        执行池化训练（多股票 + Ridge基准对比）

        Args:
            task_id: 任务ID
        """
        task = self.tasks[task_id]
        config = task["config"]

        logger.info(f"[池化训练] 开始多股票池化训练")

        # 导入池化训练Pipeline
        from src.data_pipeline.pooled_training_pipeline import PooledTrainingPipeline

        # 准备参数
        symbol_list = config.get("symbols", [])
        start_date = config.get("start_date")
        end_date = config.get("end_date")
        target_period = config.get("target_period", 10)
        config.get("model_type", "lightgbm")
        enable_ridge_baseline = config.get("enable_ridge_baseline", True)

        # 模型参数
        lightgbm_params = config.get(
            "model_params",
            {
                "max_depth": 3,
                "num_leaves": 7,
                "n_estimators": 200,
                "learning_rate": 0.03,
                "min_child_samples": 100,
                "reg_alpha": 2.0,
                "reg_lambda": 2.0,
            },
        )

        ridge_params = config.get("ridge_params", {"alpha": 1.0})

        logger.info(f"[池化训练] 股票数: {len(symbol_list)}, Ridge基准: {enable_ridge_baseline}")

        # 更新进度
        task["progress"] = 10
        task["current_step"] = f"加载 {len(symbol_list)} 只股票数据..."
        self._save_metadata()

        # 创建Pipeline
        pipeline = PooledTrainingPipeline(
            scaler_type=config.get("scaler_type", "robust"), verbose=True
        )

        # 执行完整Pipeline
        result = await asyncio.to_thread(
            pipeline.run_full_pipeline,
            symbol_list=symbol_list,
            start_date=start_date,
            end_date=end_date,
            target_period=target_period,
            lightgbm_params=lightgbm_params,
            ridge_params=ridge_params,
            enable_ridge_baseline=enable_ridge_baseline,
        )

        # 保存结果
        task["metrics"] = {
            "ic": result["lgb_metrics"]["test_ic"],
            "rank_ic": result["lgb_metrics"]["test_rank_ic"],
            "mae": result["lgb_metrics"]["test_mae"],
            "r2": result["lgb_metrics"]["test_r2"],
            "train_ic": result["lgb_metrics"]["train_ic"],
            "valid_ic": result["lgb_metrics"]["valid_ic"],
        }

        task["has_baseline"] = result.get("has_baseline", False)
        task["baseline_metrics"] = result.get("ridge_metrics", {})
        task["comparison_result"] = result.get("comparison_result", {})
        task["recommendation"] = result.get("recommendation", "")
        task["total_samples"] = result.get("total_samples", 0)
        task["successful_symbols"] = result.get("successful_symbols", [])
        task["feature_importance"] = result.get("feature_importance", {})

        # 模型路径（取LightGBM的路径）
        task["model_path"] = str(result.get("lgb_model_path", ""))

        # 更新进度
        task["progress"] = 100
        task["current_step"] = "训练完成"

        logger.info(f"✓ 池化训练完成，推荐: {task['recommendation']}")

        self._save_metadata()

        # 保存到数据库的 experiments 表（先保存训练结果，再更新回测结果）
        experiment_id = await self._save_pooled_experiment_to_db(task_id, result, config)

        # 执行回测（与单股票训练一致）
        if experiment_id:
            logger.info(f"[池化训练] 开始回测...")
            task["current_step"] = "回测中..."
            task["progress"] = 95
            self._save_metadata()

            try:
                from app.services.backtest_service import BacktestService

                backtest_service = BacktestService(self.db)

                # 使用第一个成功的股票代码进行回测（池化模型可以用于任意股票）
                symbol_for_backtest = (
                    task["successful_symbols"][0]
                    if task["successful_symbols"]
                    else config.get("symbols", [])[0]
                )

                # 执行回测（注意：BacktestService.run_backtest是async方法）
                # 使用ML模型策略进行回测，而不是默认的技术指标策略
                backtest_result_full = await backtest_service.run_backtest(
                    symbols=symbol_for_backtest,  # 参数名是 symbols
                    start_date=config.get("start_date"),
                    end_date=config.get("end_date"),
                    strategy_id="ml_model",  # ✅ 使用ML模型策略
                    strategy_params={
                        "model_id": task_id,  # 传入训练生成的model_id
                        "buy_threshold": 0.15,  # 预测收益率超过0.15%时买入
                        "sell_threshold": -0.3,  # 预测收益率低于-0.3%时卖出
                    },
                )

                # 提取 metrics 部分作为回测指标
                backtest_result = backtest_result_full.get("metrics", {})

                # 更新数据库中的回测结果
                await self._update_pooled_backtest_result(experiment_id, backtest_result)

                # 计算并更新综合评分
                from app.services.model_ranker import ModelRanker

                ranker = ModelRanker(self.db)
                rank_score = ranker.calculate_rank_score(
                    train_metrics=task.get("metrics", {}), backtest_metrics=backtest_result
                )
                await self._update_rank_score(experiment_id, rank_score)

                # 更新任务状态
                task["backtest_metrics"] = backtest_result
                task["rank_score"] = rank_score
                task["current_step"] = "回测完成"
                task["progress"] = 100

                logger.info(
                    f"✓ 池化训练回测完成，年化收益: {backtest_result.get('annualized_return', 0):.2%}, 评分: {rank_score:.2f}"
                )

            except Exception as e:
                logger.error(f"✗ 池化训练回测失败: {e}")
                # 回测失败不影响训练结果
                task["backtest_error"] = str(e)
                task["current_step"] = "训练完成（回测失败）"
                task["progress"] = 100

        self._save_metadata()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(
        self, status: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """
        列出任务

        Args:
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            任务列表和总数
        """
        # 过滤任务
        filtered_tasks = []
        for task in self.tasks.values():
            if status is None or task.get("status") == status:
                filtered_tasks.append(task)

        # 排序（按创建时间倒序）
        filtered_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 分页
        total = len(filtered_tasks)
        paginated_tasks = filtered_tasks[offset : offset + limit]

        return {"tasks": paginated_tasks, "total": total, "limit": limit, "offset": offset}

    def cancel_task(self, task_id: str):
        """
        取消任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        if task["status"] not in ["pending", "running"]:
            raise ValueError(f"任务无法取消，当前状态: {task['status']}")

        task["status"] = "cancelled"
        task["cancelled_at"] = datetime.now().isoformat()
        self._save_metadata()

        logger.info(f"✓ 任务已取消: {task_id}")

    def delete_task(self, task_id: str):
        """
        删除任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        del self.tasks[task_id]
        self._save_metadata()

        logger.info(f"✓ 任务已删除: {task_id}")

    async def _save_pooled_experiment_to_db(
        self, task_id: str, result: Dict[str, Any], config: Dict[str, Any]
    ) -> Optional[int]:
        """
        保存池化训练结果到数据库的 experiments 表（使用 Repository）

        Args:
            task_id: 任务ID
            result: 训练结果
            config: 训练配置

        Returns:
            实验ID (experiment.id)，如果保存失败则返回None
        """
        try:
            # 生成模型名称：POOLED_symbols_modeltype_period
            symbols = config.get("symbols", [])
            symbols_str = "_".join(symbols[:3]) + (
                f"_plus{len(symbols)-3}" if len(symbols) > 3 else ""
            )
            model_type = config.get("model_type", "lightgbm")
            target_period = config.get("target_period", 10)
            experiment_name = f"POOLED_{symbols_str}_{model_type}_{target_period}d"

            # 准备扩展配置
            extended_config = config.copy()
            extended_config["feature_cols"] = result.get("feature_cols", [])
            extended_config["scaler_path"] = result.get("scaler_path", "")
            extended_config["feature_count"] = result.get("feature_count", 0)

            # 准备训练指标
            train_metrics = {
                "ic": result["lgb_metrics"]["test_ic"],
                "rank_ic": result["lgb_metrics"]["test_rank_ic"],
                "mae": result["lgb_metrics"]["test_mae"],
                "r2": result["lgb_metrics"]["test_r2"],
                "rmse": result["lgb_metrics"].get("test_rmse", 0),
                "train_ic": result["lgb_metrics"]["train_ic"],
                "valid_ic": result["lgb_metrics"]["valid_ic"],
                "test_ic": result["lgb_metrics"]["test_ic"],
            }

            # 使用 ExperimentRepository 创建实验
            exp_id = await asyncio.to_thread(
                self.experiment_repo.create_experiment,
                batch_id=None,  # 手动训练不属于批次
                experiment_name=experiment_name,
                model_id=task_id,  # 使用task_id作为model_id
                model_path=result.get("lgb_model_path", ""),
                config=extended_config,
                train_metrics=train_metrics,
                status="completed",
                has_baseline=result.get("has_baseline", False),
                baseline_metrics=result.get("ridge_metrics", {}),
                comparison_result=result.get("comparison_result", {}),
                recommendation=result.get("recommendation", ""),
                total_samples=result.get("total_samples", 0),
                successful_symbols=result.get("successful_symbols", []),
            )

            logger.info(f"✓ 池化训练结果已保存到数据库，实验ID: {exp_id}")
            return exp_id

        except Exception as e:
            logger.error(f"✗ 保存池化训练结果到数据库时出错: {e}")
            # 不抛出异常，避免影响训练流程
            return None

    async def _update_pooled_backtest_result(self, exp_id: int, backtest_metrics: Dict[str, Any]):
        """
        更新池化训练实验的回测结果（使用 Repository）

        Args:
            exp_id: 实验ID
            backtest_metrics: 回测指标
        """
        try:
            # 使用 ExperimentRepository 更新回测结果
            await asyncio.to_thread(
                self.experiment_repo.update_backtest_result,
                exp_id,
                backtest_metrics,
                datetime.now(),
                0  # backtest_duration_seconds (暂时设为0)
            )

            logger.info(f"✓ 池化训练回测结果已更新到数据库，实验ID: {exp_id}")

        except Exception as e:
            logger.error(f"✗ 更新池化训练回测结果时出错: {e}")
            # 不抛出异常，避免影响训练流程

    async def _update_rank_score(self, exp_id: int, rank_score: float):
        """
        更新实验的综合评分（使用 Repository）

        Args:
            exp_id: 实验ID
            rank_score: 综合评分
        """
        try:
            # 使用 ExperimentRepository 更新排名
            # 注意：这里只更新rank_score，不更新rank_position（设为0表示未计算位置）
            await asyncio.to_thread(
                self.experiment_repo.update_rank,
                exp_id,
                rank_score,
                0  # rank_position (0表示未计算位置)
            )

            logger.info(
                f"✓ 综合评分已更新到数据库，实验ID: {exp_id}, 评分: {rank_score:.2f}"
            )

        except Exception as e:
            logger.error(f"✗ 更新综合评分时出错: {e}")
            # 不抛出异常，避免影响训练流程
