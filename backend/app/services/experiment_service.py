"""
实验管理服务
管理批量训练和回测实验的生命周期
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from loguru import logger

# 导入core模块
import sys
sys.path.insert(0, '/app/src')

from src.data_pipeline import DataPipeline
from src.models.model_trainer import ModelTrainer
from src.database.db_manager import DatabaseManager

from app.services.parameter_grid import ParameterGrid
from app.services.ml_training_service import MLTrainingService
from app.services.backtest_service import BacktestService


class ExperimentService:
    """实验管理服务"""

    def __init__(self):
        self.db = DatabaseManager()
        self.ml_service = MLTrainingService()
        self.backtest_service = BacktestService()

        # 任务队列
        self.running_batches: Dict[int, asyncio.Task] = {}

    # ==================== 批次管理 ====================

    async def create_batch(
        self,
        batch_name: str,
        param_space: Dict[str, Any],
        strategy: str = 'grid',
        max_experiments: Optional[int] = None,
        description: Optional[str] = None,
        config: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        创建实验批次

        Args:
            batch_name: 批次名称（唯一）
            param_space: 参数空间定义
            strategy: 参数生成策略 ('grid', 'random', 'bayesian')
            max_experiments: 最大实验数（仅对random/bayesian有效）
            description: 批次描述
            config: 批次级别配置（并行度、回测设置等）
            tags: 标签列表

        Returns:
            batch_id
        """
        logger.info(f"📦 创建实验批次: {batch_name}")

        try:
            # 1. 生成参数组合
            param_grid = ParameterGrid(param_space)
            experiment_configs = param_grid.generate(
                strategy=strategy,
                max_experiments=max_experiments
            )

            total_experiments = len(experiment_configs)
            logger.info(f"✅ 生成了 {total_experiments} 个实验配置")

            # 2. 创建批次记录
            batch_config = config or {}
            batch_config.setdefault('auto_backtest', True)
            batch_config.setdefault('max_workers', 3)
            batch_config.setdefault('save_models', True)

            insert_query = """
                INSERT INTO experiment_batches (
                    batch_name, description, strategy, param_space,
                    total_experiments, config, tags
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
                RETURNING id
            """

            # 使用手动事务管理
            conn = self.db.get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    insert_query,
                    (
                        batch_name,
                        description,
                        strategy,
                        json.dumps(param_space),
                        total_experiments,
                        json.dumps(batch_config),
                        tags or []
                    )
                )
                result = cursor.fetchone()
                batch_id = result[0]
                conn.commit()
                logger.info(f"✅ 批次ID: {batch_id}")
            except Exception as e:
                conn.rollback()
                error_msg = str(e)
                logger.error(f"❌ 创建批次记录失败: {error_msg}")

                # 检查是否是唯一性约束冲突
                if 'experiment_batches_batch_name_key' in error_msg or 'duplicate key value' in error_msg:
                    raise ValueError(f"批次名称 '{batch_name}' 已存在，请使用其他名称")
                raise
            finally:
                cursor.close()
                self.db.release_connection(conn)

            # 3. 创建实验记录
            await self._create_experiments(batch_id, experiment_configs)

            return batch_id

        except Exception as e:
            logger.error(f"❌ 创建批次失败: {e}")
            raise

    async def _create_experiments(self, batch_id: int, configs: List[Dict]):
        """批量创建实验记录"""

        logger.info(f"📝 创建 {len(configs)} 个实验记录...")

        insert_query = """
            INSERT INTO experiments (
                batch_id, experiment_name, experiment_hash, config, status
            )
            VALUES (%s, %s, %s, %s::jsonb, 'pending')
        """

        values = []
        for config in configs:
            exp_name = self._generate_experiment_name(config)
            exp_hash = config.pop('experiment_hash', None)  # 移除哈希字段

            values.append((
                batch_id,
                exp_name,
                exp_hash,
                json.dumps(config)
            ))

        # 批量插入
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.executemany(insert_query, values)
            conn.commit()
            logger.info(f"✅ 成功创建 {len(values)} 个实验记录")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 批量插入失败: {e}")
            raise
        finally:
            cursor.close()
            self.db.release_connection(conn)

    def _generate_experiment_name(self, config: Dict) -> str:
        """生成实验名称"""
        symbol = config.get('symbol', 'unknown')
        model_type = config.get('model_type', 'unknown')
        target_period = config.get('target_period', 0)
        scaler = config.get('scaler_type', 'unknown')

        return f"{symbol}_{model_type}_T{target_period}_{scaler}"

    # ==================== 批次执行 ====================

    async def run_batch(
        self,
        batch_id: int,
        max_workers: Optional[int] = None
    ):
        """
        运行实验批次

        Args:
            batch_id: 批次ID
            max_workers: 最大并行Worker数（覆盖批次配置）
        """
        logger.info(f"🚀 启动批次 {batch_id}")

        try:
            # 1. 更新批次状态
            await self._update_batch_status(batch_id, 'running', started_at=datetime.now())

            # 2. 获取批次配置
            batch_config = await self._get_batch_config(batch_id)
            workers = max_workers or batch_config.get('max_workers', 3)
            auto_backtest = batch_config.get('auto_backtest', True)

            logger.info(f"⚙️  配置: {workers} 个Worker, 自动回测={auto_backtest}")

            # 3. 获取待执行实验
            experiments = await self._get_pending_experiments(batch_id)
            logger.info(f"📋 待执行实验: {len(experiments)} 个")

            if not experiments:
                logger.warning("⚠️  没有待执行的实验")
                await self._update_batch_status(batch_id, 'completed', completed_at=datetime.now())
                return

            # 4. 创建任务队列
            queue = asyncio.Queue()
            for exp in experiments:
                await queue.put(exp)

            # 5. 启动Worker池
            tasks = []
            for i in range(workers):
                task = asyncio.create_task(
                    self._experiment_worker(
                        worker_id=i,
                        batch_id=batch_id,
                        queue=queue,
                        auto_backtest=auto_backtest
                    )
                )
                tasks.append(task)

            # 6. 等待所有任务完成
            await queue.join()

            # 7. 停止Workers
            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

            # 8. 计算排名
            await self._calculate_rankings(batch_id)

            # 9. 更新批次状态
            await self._update_batch_status(batch_id, 'completed', completed_at=datetime.now())

            logger.info(f"🎉 批次 {batch_id} 执行完成！")

        except Exception as e:
            logger.error(f"❌ 批次执行失败: {e}")
            await self._update_batch_status(batch_id, 'failed')
            raise

    async def _experiment_worker(
        self,
        worker_id: int,
        batch_id: int,
        queue: asyncio.Queue,
        auto_backtest: bool
    ):
        """实验执行Worker"""

        logger.info(f"🔧 Worker-{worker_id} 启动")

        while True:
            try:
                # 从队列获取实验
                experiment = await queue.get()

                exp_id = experiment[0]
                # config字段是JSONB类型，数据库已自动转换为dict，无需json.loads
                exp_config = experiment[3] if isinstance(experiment[3], dict) else json.loads(experiment[3])

                logger.info(f"[Worker-{worker_id}] 🔬 开始实验 {exp_id}: {experiment[2]}")

                # 执行实验
                await self._run_single_experiment(
                    exp_id=exp_id,
                    config=exp_config,
                    auto_backtest=auto_backtest,
                    worker_id=worker_id
                )

                # 更新批次统计
                await self._increment_batch_counter(batch_id, 'completed')

            except asyncio.CancelledError:
                logger.info(f"🛑 Worker-{worker_id} 停止")
                break
            except Exception as e:
                logger.error(f"[Worker-{worker_id}] ❌ 实验失败: {e}")
                await self._mark_experiment_failed(exp_id, str(e))
                await self._increment_batch_counter(batch_id, 'failed')
            finally:
                queue.task_done()

    async def _run_single_experiment(
        self,
        exp_id: int,
        config: Dict,
        auto_backtest: bool,
        worker_id: int
    ):
        """执行单个实验"""

        start_time = datetime.now()

        try:
            # 1. 更新状态为训练中
            await self._update_experiment_status(exp_id, 'training', train_started_at=start_time)

            # 2. 训练模型
            logger.info(f"[Worker-{worker_id}] 🏋️  训练模型...")
            model_id, train_metrics, feature_importance, model_path = await self._train_model_async(config)

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
                train_duration=int(train_duration)
            )

            logger.info(f"[Worker-{worker_id}] ✅ 训练完成: {model_id}")

            # 4. 自动回测（可选）
            if auto_backtest:
                await self._update_experiment_status(exp_id, 'backtesting', backtest_started_at=datetime.now())

                logger.info(f"[Worker-{worker_id}] 📊 回测中...")
                backtest_result = await self._run_backtest_async(model_id, config)

                backtest_end_time = datetime.now()
                backtest_duration = (backtest_end_time - train_end_time).total_seconds()

                # 5. 保存回测结果
                await self._update_experiment_backtest_result(
                    exp_id=exp_id,
                    backtest_metrics=backtest_result,
                    backtest_completed_at=backtest_end_time,
                    backtest_duration=int(backtest_duration)
                )

                logger.info(f"[Worker-{worker_id}] ✅ 回测完成")

            # 6. 标记实验完成
            total_duration = (datetime.now() - start_time).total_seconds()
            await self._update_experiment_status(
                exp_id,
                'completed',
                total_duration=int(total_duration)
            )

            logger.info(f"[Worker-{worker_id}] 🎉 实验 {exp_id} 完成！")

        except Exception as e:
            logger.error(f"[Worker-{worker_id}] ❌ 实验 {exp_id} 失败: {e}")
            await self._mark_experiment_failed(exp_id, str(e))
            raise

    async def _train_model_async(self, config: Dict) -> tuple:
        """异步训练模型（包装同步代码）"""

        def _train():
            # 使用现有的训练服务
            pipeline = DataPipeline()

            # 使用统一的模型保存目录（与MLTrainingService一致）
            models_dir = Path('/data/models/ml_models')
            models_dir.mkdir(parents=True, exist_ok=True)

            # 创建训练器（model_type在构造函数中传递）
            trainer = ModelTrainer(
                model_type=config['model_type'],
                model_params=config.get('model_params', {}),
                output_dir=str(models_dir)
            )

            # 准备训练数据
            X, y = pipeline.get_training_data(
                symbol=config['symbol'],
                start_date=config['start_date'],
                end_date=config['end_date'],
                target_period=config['target_period']
            )

            # 准备模型训练数据（分割训练集/验证集/测试集，并缩放特征）
            # 这一步会fit scaler
            X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
                X, y,
                train_ratio=config.get('train_ratio', 0.7),
                valid_ratio=config.get('valid_ratio', 0.15),
                scale_features=True,
                balance_samples=config.get('balance_samples', False)
            )

            # 训练模型（直接调用对应的训练方法）
            if config['model_type'] == 'lightgbm':
                trainer.train_lightgbm(
                    X_train=X_train,
                    y_train=y_train,
                    X_valid=X_valid,
                    y_valid=y_valid
                )
            elif config['model_type'] == 'gru':
                trainer.train_gru(
                    X_train=X_train,
                    y_train=y_train,
                    X_valid=X_valid,
                    y_valid=y_valid
                )
            else:
                raise ValueError(f"不支持的模型类型: {config['model_type']}")

            # 训练后，模型保存在trainer.model中
            # 评估训练集性能
            metrics = trainer.evaluate(X_train, y_train, dataset_name='train', verbose=False)

            # 生成模型ID并保存模型
            model_id = f"{config['symbol']}_{config['model_type']}_T{config['target_period']}_{config.get('scaler_type', 'robust')}"
            trainer.save_model(model_name=model_id, save_metrics=True)

            # 获取模型文件路径（必须在save_model之后，确保文件已保存）
            model_path = models_dir / f"{model_id}.txt" if config['model_type'] == 'lightgbm' else models_dir / f"{model_id}.pth"

            # 保存scaler（与手动训练保持一致）
            import pickle
            scaler_path = models_dir / f"{model_id}_scaler.pkl"
            with open(scaler_path, 'wb') as f:
                pickle.dump(pipeline.get_scaler(), f)
            logger.info(f"✅ Scaler已保存: {scaler_path}")

            # 获取特征重要性（LightGBM模型有这个方法）
            # 使用字典格式 {feature: gain}，与手动训练保持一致
            feature_importance = {}
            if hasattr(trainer.model, 'get_feature_importance'):
                try:
                    fi_df = trainer.model.get_feature_importance(top_n=20)
                    if fi_df is not None and not fi_df.empty:
                        # 转换为字典格式：{feature: gain}
                        feature_importance = dict(zip(
                            fi_df['feature'].tolist(),
                            fi_df['gain'].tolist()
                        ))
                except Exception as e:
                    logger.warning(f"获取特征重要性失败: {e}")

            # 注册模型到MLTrainingService，使回测能找到模型
            from app.services.ml_training_service import MLTrainingService
            ml_service = MLTrainingService()

            # 创建任务元数据
            ml_service.tasks[model_id] = {
                'task_id': model_id,
                'status': 'completed',
                'model_path': str(model_path),
                'config': {
                    'model_type': config['model_type'],
                    'target_period': config['target_period'],
                    'symbol': config['symbol'],
                    'scaler_type': config.get('scaler_type', 'robust'),
                },
                'metrics': metrics,  # 训练指标
                'feature_importance': feature_importance,  # 特征重要性
                'created_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat(),
            }
            ml_service._save_metadata()
            logger.info(f"✅ 模型已注册到MLTrainingService: {model_id}")

            return model_id, metrics, feature_importance, str(model_path)

        # 在线程池中执行（避免阻塞事件循环）
        return await asyncio.to_thread(_train)

    async def _run_backtest_async(self, model_id: str, config: Dict) -> Dict:
        """异步回测"""

        # 调用回测服务（使用ML策略）
        result = await self.backtest_service.run_backtest(
            symbols=config['symbol'],
            start_date=config['start_date'],
            end_date=config['end_date'],
            strategy_id='ml_model',
            strategy_params={'model_id': model_id}
        )

        return result.get('metrics', {})

    # ==================== 数据库操作 ====================

    async def _update_batch_status(
        self,
        batch_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        """更新批次状态"""

        updates = ["status = %s"]
        params = [status]

        if started_at:
            updates.append("started_at = %s")
            params.append(started_at)

        if completed_at:
            updates.append("completed_at = %s")
            params.append(completed_at)

        query = f"UPDATE experiment_batches SET {', '.join(updates)} WHERE id = %s"
        params.append(batch_id)

        await asyncio.to_thread(self.db._execute_update, query, tuple(params))

    async def _get_batch_config(self, batch_id: int) -> Dict:
        """获取批次配置"""

        query = "SELECT config FROM experiment_batches WHERE id = %s"
        result = await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

        if result:
            return result[0][0] or {}
        return {}

    async def _get_pending_experiments(self, batch_id: int) -> List:
        """获取待执行的实验"""

        query = """
            SELECT id, batch_id, experiment_name, config
            FROM experiments
            WHERE batch_id = %s AND status = 'pending'
            ORDER BY id
        """

        return await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

    async def _update_experiment_status(
        self,
        exp_id: int,
        status: str,
        train_started_at: Optional[datetime] = None,
        backtest_started_at: Optional[datetime] = None,
        total_duration: Optional[int] = None
    ):
        """更新实验状态"""

        updates = ["status = %s"]
        params = [status]

        if train_started_at:
            updates.append("train_started_at = %s")
            params.append(train_started_at)

        if backtest_started_at:
            updates.append("backtest_started_at = %s")
            params.append(backtest_started_at)

        if total_duration is not None:
            updates.append("total_duration_seconds = %s")
            params.append(total_duration)

        query = f"UPDATE experiments SET {', '.join(updates)} WHERE id = %s"
        params.append(exp_id)

        await asyncio.to_thread(self.db._execute_update, query, tuple(params))

    async def _update_experiment_train_result(
        self,
        exp_id: int,
        model_id: str,
        train_metrics: Dict,
        feature_importance: Dict,
        model_path: str,
        train_completed_at: datetime,
        train_duration: int
    ):
        """更新训练结果"""

        query = """
            UPDATE experiments
            SET model_id = %s,
                train_metrics = %s::jsonb,
                feature_importance = %s::jsonb,
                model_path = %s,
                train_completed_at = %s,
                train_duration_seconds = %s
            WHERE id = %s
        """

        await asyncio.to_thread(
            self.db._execute_update,
            query,
            (
                model_id,
                json.dumps(train_metrics),
                json.dumps(feature_importance),
                model_path,
                train_completed_at,
                train_duration,
                exp_id
            )
        )

    async def _update_experiment_backtest_result(
        self,
        exp_id: int,
        backtest_metrics: Dict,
        backtest_completed_at: datetime,
        backtest_duration: int
    ):
        """更新回测结果"""

        query = """
            UPDATE experiments
            SET backtest_status = 'completed',
                backtest_metrics = %s::jsonb,
                backtest_completed_at = %s,
                backtest_duration_seconds = %s
            WHERE id = %s
        """

        await asyncio.to_thread(
            self.db._execute_update,
            query,
            (
                json.dumps(backtest_metrics),
                backtest_completed_at,
                backtest_duration,
                exp_id
            )
        )

    async def _mark_experiment_failed(self, exp_id: int, error_message: str):
        """标记实验失败"""

        query = """
            UPDATE experiments
            SET status = 'failed',
                error_message = %s,
                retry_count = retry_count + 1
            WHERE id = %s
        """

        await asyncio.to_thread(self.db._execute_update, query, (error_message, exp_id))

    async def _increment_batch_counter(self, batch_id: int, counter_type: str):
        """增加批次计数器"""

        if counter_type == 'completed':
            field = 'completed_experiments'
        elif counter_type == 'failed':
            field = 'failed_experiments'
        else:
            return

        query = f"UPDATE experiment_batches SET {field} = {field} + 1 WHERE id = %s"
        await asyncio.to_thread(self.db._execute_update, query, (batch_id,))

    async def _calculate_rankings(self, batch_id: int):
        """计算实验排名"""

        logger.info(f"📊 计算批次 {batch_id} 的排名...")

        # 导入排名器
        from app.services.model_ranker import ModelRanker
        ranker = ModelRanker(self.db)

        # 获取所有完成的实验
        query = """
            SELECT id, train_metrics, backtest_metrics
            FROM experiments
            WHERE batch_id = %s AND status = 'completed' AND backtest_status = 'completed'
        """

        experiments = await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

        # 计算评分
        for exp in experiments:
            exp_id = exp[0]
            train_metrics = exp[1] or {}
            backtest_metrics = exp[2] or {}

            rank_score = ranker.calculate_rank_score(train_metrics, backtest_metrics)

            # 更新评分
            update_query = "UPDATE experiments SET rank_score = %s WHERE id = %s"
            await asyncio.to_thread(self.db._execute_update, update_query, (rank_score, exp_id))

        # 更新排名位置
        rank_query = """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY rank_score DESC NULLS LAST) as position
                FROM experiments
                WHERE batch_id = %s AND status = 'completed'
            )
            UPDATE experiments e
            SET rank_position = r.position
            FROM ranked r
            WHERE e.id = r.id
        """

        await asyncio.to_thread(self.db._execute_update, rank_query, (batch_id,))

        logger.info("✅ 排名计算完成")

    # ==================== 查询接口 ====================

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """获取批次信息"""

        query = "SELECT * FROM batch_statistics WHERE batch_id = %s"
        result = await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

        if result:
            row = result[0]
            return {
                'batch_id': row[0],
                'batch_name': row[1],
                'strategy': row[2],
                'status': row[3],
                'total_experiments': row[4],
                'completed_experiments': row[5],
                'failed_experiments': row[6],
                'running_experiments': row[7],
                'success_rate_pct': float(row[8]) if row[8] else 0,
                'created_at': row[9].isoformat() if row[9] else None,
                'started_at': row[10].isoformat() if row[10] else None,
                'completed_at': row[11].isoformat() if row[11] else None,
                'duration_hours': float(row[12]) if row[12] else None,
                'avg_rank_score': float(row[13]) if row[13] else None,
                'max_rank_score': float(row[14]) if row[14] else None,
                'top_model_id': row[15]
            }

        return None

    async def get_top_models(
        self,
        batch_id: int,
        top_n: int = 10,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_annual_return: Optional[float] = None
    ) -> List[Dict]:
        """获取Top模型"""

        query = "SELECT * FROM get_top_models(%s, %s, %s, %s, %s)"

        result = await asyncio.to_thread(
            self.db._execute_query,
            query,
            (batch_id, top_n, min_sharpe, max_drawdown, min_annual_return)
        )

        models = []
        for row in result:
            models.append({
                'experiment_id': row[0],
                'model_id': row[1],
                'rank_score': float(row[2]) if row[2] else None,
                'annual_return': float(row[3]) if row[3] else None,
                'sharpe_ratio': float(row[4]) if row[4] else None,
                'max_drawdown': float(row[5]) if row[5] else None,
                'config': row[6]
            })

        return models

    async def list_batches(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """
        列出所有批次

        Args:
            limit: 返回数量限制
            status: 状态过滤 (pending/running/completed/failed)

        Returns:
            批次列表
        """
        # 构建查询
        conditions = []
        params = []

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT * FROM batch_statistics
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)

        # 执行查询
        results = await asyncio.to_thread(self.db._execute_query, query, tuple(params))

        batches = []
        for row in results:
            batches.append({
                'batch_id': row[0],
                'batch_name': row[1],
                'strategy': row[2],
                'status': row[3],
                'total_experiments': row[4],
                'completed_experiments': row[5],
                'failed_experiments': row[6],
                'running_experiments': row[7],
                'success_rate_pct': float(row[8]) if row[8] else 0,
                'created_at': row[9].isoformat() if row[9] else None,
                'started_at': row[10].isoformat() if row[10] else None,
                'completed_at': row[11].isoformat() if row[11] else None,
                'duration_hours': float(row[12]) if row[12] else None,
                'avg_rank_score': float(row[13]) if row[13] else None,
                'max_rank_score': float(row[14]) if row[14] else None,
                'top_model_id': row[15]
            })

        return batches

    async def get_batch_experiments(self, batch_id: int, status: Optional[str] = None, limit: int = 500) -> List[Dict]:
        """
        获取批次下的所有实验

        Args:
            batch_id: 批次ID
            status: 状态过滤 (completed/failed/running/pending)
            limit: 返回数量限制

        Returns:
            实验列表
        """
        conditions = ["batch_id = %s"]
        params = [batch_id]

        if status:
            conditions.append("status = %s")
            params.append(status)

        query = f"""
            SELECT id, experiment_name, model_id, config, train_metrics, backtest_metrics,
                   rank_score, rank_position, status, error_message
            FROM experiments
            WHERE {' AND '.join(conditions)}
            ORDER BY rank_score DESC NULLS LAST
            LIMIT %s
        """
        params.append(limit)

        results = await asyncio.to_thread(self.db._execute_query, query, tuple(params))

        experiments = []
        for row in results:
            experiments.append({
                'id': row[0],
                'experiment_name': row[1],
                'model_id': row[2],
                'config': row[3],
                'train_metrics': row[4],
                'backtest_metrics': row[5],
                'rank_score': float(row[6]) if row[6] else None,
                'rank_position': row[7],
                'status': row[8],
                'error_message': row[9]
            })

        return experiments
