"""
实验运行器（重构版）
负责执行实验的训练和回测
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from app.core.exceptions import BackendError, DatabaseError
from app.repositories.experiment_repository import ExperimentRepository
from app.services.backtest_service import BacktestService
from app.services.core_training import CoreTrainingService
from app.services.training_task_manager import TrainingTaskManager


class ExperimentRunner:
    """
    实验运行器

    职责：
    - 执行批次实验
    - Worker 管理和调度
    - 单个实验的训练和回测
    - 实验状态更新
    """

    def __init__(self, db=None):
        """
        初始化实验运行器

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入，传递给 Repository 和 Service）
        """
        self.backtest_service = BacktestService(db)
        self.experiment_repo = ExperimentRepository(db)

        # 运行中的批次
        self.running_batches: Dict[int, asyncio.Task] = {}

    async def run_batch(
        self, batch_id: int, max_workers: Optional[int] = None, auto_backtest: bool = True
    ):
        """
        运行批次实验

        Args:
            batch_id: 批次ID
            max_workers: 最大并行Worker数
            auto_backtest: 是否自动回测
        """
        logger.info(f"🚀 开始批次 {batch_id}，Worker数: {max_workers or 4}")

        # 更新批次状态
        await self._update_batch_status(batch_id, "running", started_at=datetime.now())

        try:
            # 获取待执行的实验
            experiments = await self._get_pending_experiments(batch_id)

            if not experiments:
                logger.warning(f"批次 {batch_id} 没有待执行的实验")
                await self._update_batch_status(batch_id, "completed")
                return

            # 创建任务队列
            queue = asyncio.Queue()
            for exp in experiments:
                await queue.put(exp)

            # 创建Worker池
            workers = []
            num_workers = min(max_workers or 4, len(experiments))

            for worker_id in range(num_workers):
                task = asyncio.create_task(
                    self._experiment_worker(
                        worker_id=worker_id,
                        batch_id=batch_id,
                        queue=queue,
                        auto_backtest=auto_backtest,
                    )
                )
                workers.append(task)

            # 等待所有实验完成
            await queue.join()

            # 停止所有Worker
            for task in workers:
                task.cancel()

            await asyncio.gather(*workers, return_exceptions=True)

            # 计算排名
            from app.services.batch_manager import BatchManager

            batch_manager = BatchManager()
            await batch_manager.calculate_rankings(batch_id)

            # 更新批次状态为完成
            await self._update_batch_status(batch_id, "completed", completed_at=datetime.now())

            logger.info(f"✅ 批次 {batch_id} 完成")

        except (DatabaseError, BackendError):
            # 已知业务异常向上传播
            await self._update_batch_status(batch_id, "failed")
            raise
        except Exception as e:
            logger.error(f"批次 {batch_id} 执行失败: {e}")
            await self._update_batch_status(batch_id, "failed")
            raise BackendError(
                f"批次执行失败: {batch_id}",
                error_code="BATCH_EXECUTION_FAILED",
                batch_id=batch_id,
                reason=str(e),
            )

    async def _experiment_worker(
        self, worker_id: int, batch_id: int, queue: asyncio.Queue, auto_backtest: bool
    ):
        """
        实验执行Worker

        Args:
            worker_id: Worker ID
            batch_id: 批次ID
            queue: 任务队列
            auto_backtest: 是否自动回测
        """
        logger.info(f"🔧 Worker-{worker_id} 启动")

        while True:
            try:
                # 从队列获取实验
                experiment = await queue.get()

                exp_id = experiment[0]
                exp_config = (
                    experiment[3] if isinstance(experiment[3], dict) else json.loads(experiment[3])
                )

                logger.info(f"[Worker-{worker_id}] 🔬 开始实验 {exp_id}")

                # 执行实验
                await self._run_single_experiment(
                    exp_id=exp_id,
                    config=exp_config,
                    auto_backtest=auto_backtest,
                    worker_id=worker_id,
                )

                # 更新批次计数器
                await self._increment_batch_counter(batch_id, "completed")

            except asyncio.CancelledError:
                logger.info(f"🛑 Worker-{worker_id} 停止")
                break
            except (DatabaseError, BackendError) as e:
                # 已知业务异常
                logger.error(f"[Worker-{worker_id}] ❌ 实验失败 (业务异常): {e}")
                await self._mark_experiment_failed(exp_id, str(e))
                await self._increment_batch_counter(batch_id, "failed")
            except Exception as e:
                # 未预期错误
                logger.error(f"[Worker-{worker_id}] ❌ 实验失败 (未预期错误): {e}")
                await self._mark_experiment_failed(exp_id, str(e))
                await self._increment_batch_counter(batch_id, "failed")
            finally:
                queue.task_done()

    async def _run_single_experiment(
        self, exp_id: int, config: Dict, auto_backtest: bool, worker_id: int
    ):
        """
        执行单个实验

        Args:
            exp_id: 实验ID
            config: 实验配置
            auto_backtest: 是否自动回测
            worker_id: Worker ID
        """
        start_time = datetime.now()

        try:
            # 1. 更新状态为训练中
            await self._update_experiment_status(exp_id, "training", train_started_at=start_time)

            # 2. 训练模型
            logger.info(f"[Worker-{worker_id}] 🏋️  训练模型...")
            model_id, train_metrics, feature_importance, model_path = await self._train_model_async(
                config
            )

            train_end_time = datetime.now()
            train_duration = (train_end_time - start_time).total_seconds()

            # 3. 保存训练结果
            await self._update_experiment_train_result(
                exp_id=exp_id,
                model_id=model_id,
                train_metrics=train_metrics,
                feature_importance=feature_importance,
                model_path=model_path,
                train_completed_at=train_end_time,
                train_duration=int(train_duration),
            )

            logger.info(f"[Worker-{worker_id}] ✅ 训练完成: {model_id}")

            # 4. 自动回测（可选）
            if auto_backtest:
                await self._update_experiment_status(
                    exp_id, "backtesting", backtest_started_at=datetime.now()
                )

                logger.info(f"[Worker-{worker_id}] 📊 回测中...")
                backtest_result = await self._run_backtest_async(model_id, config)

                backtest_end_time = datetime.now()
                backtest_duration = (backtest_end_time - train_end_time).total_seconds()

                # 5. 保存回测结果
                await self._update_experiment_backtest_result(
                    exp_id=exp_id,
                    backtest_metrics=backtest_result,
                    backtest_completed_at=backtest_end_time,
                    backtest_duration=int(backtest_duration),
                )

                logger.info(f"[Worker-{worker_id}] ✅ 回测完成")

            # 6. 标记实验完成
            total_duration = (datetime.now() - start_time).total_seconds()
            await self._update_experiment_status(
                exp_id, "completed", total_duration_seconds=int(total_duration)
            )

        except (DatabaseError, BackendError):
            # 已知业务异常向上传播
            raise
        except Exception as e:
            logger.error(f"[Worker-{worker_id}] 实验 {exp_id} 失败: {e}")
            await self._mark_experiment_failed(exp_id, str(e))
            raise BackendError(
                f"实验执行失败: {exp_id}",
                error_code="EXPERIMENT_EXECUTION_FAILED",
                exp_id=exp_id,
                worker_id=worker_id,
                reason=str(e),
            )

    async def _train_model_async(self, config: Dict) -> tuple:
        """
        异步训练模型

        Args:
            config: 训练配置

        Returns:
            (model_id, metrics, feature_importance, model_path)
        """

        async def _train():
            # 使用 CoreTrainingService 统一训练流程
            core_service = CoreTrainingService()

            # CoreTrainingService.train_model() 是异步方法，接受 config 字典作为第一个参数
            result = await core_service.train_model(
                config=config,
                save_features=True,
                save_training_history=True,
                use_async=False,  # 在 worker 线程中运行，不需要再次异步
            )

            model_id = f"{config['symbol']}_{config.get('model_type')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            metrics = result["metrics"]
            feature_importance = result.get("feature_importance", {})
            model_path = result["model_path"]

            # 注册模型到TrainingTaskManager
            task_manager = TrainingTaskManager()
            task_manager.tasks[model_id] = {
                "task_id": model_id,
                "status": "completed",
                "model_path": model_path,
                "config": {
                    "model_type": config["model_type"],
                    "target_period": config["target_period"],
                    "symbol": config["symbol"],
                    "scaler_type": config.get("scaler_type", "robust"),
                },
                "metrics": metrics,
                "feature_importance": feature_importance,
                "created_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
            }
            task_manager._save_metadata()
            logger.info(f"✅ 模型已注册到TrainingTaskManager: {model_id}")

            return model_id, metrics, feature_importance, model_path

        # _train 是异步函数，直接 await 执行
        return await _train()

    async def _run_backtest_async(self, model_id: str, config: Dict) -> Dict:
        """
        异步运行回测

        Args:
            model_id: 模型ID
            config: 配置

        Returns:
            回测结果
        """
        result = await self.backtest_service.run_backtest(
            symbols=config["symbol"], start_date=config["start_date"], end_date=config["end_date"]
        )
        # 提取 metrics 部分作为回测指标
        return result.get("metrics", {})

    # ==================== 数据库操作 ====================

    async def _update_batch_status(self, batch_id: int, status: str, **kwargs):
        """更新批次状态"""
        from app.services.batch_manager import BatchManager

        batch_manager = BatchManager()
        await batch_manager.update_batch_status(batch_id, status, **kwargs)

    async def _get_pending_experiments(self, batch_id: int) -> List:
        """获取待执行的实验（使用 Repository）"""
        experiments = await asyncio.to_thread(
            self.experiment_repo.find_experiments_by_batch, batch_id=batch_id, status='pending'
        )

        # 转换为元组格式（与原逻辑兼容）
        result = []
        for exp in experiments:
            result.append((exp['id'], exp['batch_id'], exp['experiment_name'], exp['config']))

        return result

    async def _update_experiment_status(self, exp_id: int, status: str, **kwargs):
        """更新实验状态"""
        await asyncio.to_thread(
            self.experiment_repo.update_experiment_status, exp_id, status, **kwargs
        )

    async def _update_experiment_train_result(
        self,
        exp_id: int,
        model_id: str,
        train_metrics: Dict,
        feature_importance: Dict,
        model_path: str,
        train_completed_at: datetime,
        train_duration: int,
    ):
        """更新实验训练结果（使用 Repository）"""
        await asyncio.to_thread(
            self.experiment_repo.update_train_result,
            exp_id,
            model_id,
            train_metrics,
            feature_importance,
            model_path,
            train_completed_at,
            train_duration,
        )

    async def _update_experiment_backtest_result(
        self,
        exp_id: int,
        backtest_metrics: Dict,
        backtest_completed_at: datetime,
        backtest_duration: int,
    ):
        """更新实验回测结果（使用 Repository）"""
        await asyncio.to_thread(
            self.experiment_repo.update_backtest_result,
            exp_id,
            backtest_metrics,
            backtest_completed_at,
            backtest_duration,
        )

    async def _mark_experiment_failed(self, exp_id: int, error_message: str):
        """标记实验失败"""
        await asyncio.to_thread(
            self.experiment_repo.update_experiment_status,
            exp_id,
            "failed",
            error_message=error_message,
        )

    async def _increment_batch_counter(self, batch_id: int, counter_type: str):
        """增加批次计数器"""
        from app.services.batch_manager import BatchManager

        batch_manager = BatchManager()
        await batch_manager.increment_batch_counter(batch_id, counter_type)
