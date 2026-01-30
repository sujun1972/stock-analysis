"""
批量下载协调器

协调批量数据下载任务，支持：
- 批量下载多只股票数据
- 断点续传
- 并发控制
- 进度追踪
"""

import hashlib
from typing import List, Optional, Callable, Dict, Any
from datetime import date, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.providers.base_provider import BaseDataProvider
from src.data_pipeline.download_state_manager import DownloadStateManager, DownloadCheckpoint
from src.utils.logger import get_logger
from src.utils.decorators import retry_enhanced
from src.utils.retry_strategy import ExponentialBackoffStrategy

logger = get_logger(__name__)


class BatchDownloadCoordinator:
    """
    批量下载协调器

    功能：
    - 协调批量数据下载
    - 支持断点续传
    - 并发下载控制
    - 进度回调
    """

    def __init__(
        self,
        provider: BaseDataProvider,
        state_manager: Optional[DownloadStateManager] = None,
        max_workers: int = 3,
        enable_checkpoint: bool = True
    ):
        """
        初始化批量下载协调器

        Args:
            provider: 数据提供者
            state_manager: 状态管理器
            max_workers: 最大并发工作线程数
            enable_checkpoint: 是否启用检查点
        """
        self.provider = provider
        self.state_manager = state_manager or DownloadStateManager()
        self.max_workers = max_workers
        self.enable_checkpoint = enable_checkpoint

    def generate_task_id(
        self,
        data_type: str,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> str:
        """
        生成任务ID

        Args:
            data_type: 数据类型
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            任务ID
        """
        # 使用MD5生成唯一ID
        content = f"{data_type}_{'-'.join(sorted(symbols))}_{start_date}_{end_date}"
        return hashlib.md5(content.encode()).hexdigest()

    def download_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        data_type: str = 'daily',
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        resume_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        批量下载股票数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
            progress_callback: 进度回调函数(completed, total, symbol)
            resume_if_exists: 是否从已有检查点恢复

        Returns:
            下载结果统计
        """
        # 生成任务ID
        task_id = self.generate_task_id(data_type, symbols, start_date, end_date)
        logger.info(f"开始批量下载任务: {task_id}, 股票数: {len(symbols)}")

        # 检查是否有现有检查点
        checkpoint = None
        if self.enable_checkpoint and resume_if_exists:
            checkpoint = self.state_manager.load_checkpoint(task_id)

        # 确定需要下载的股票
        if checkpoint and checkpoint.status in ['running', 'failed', 'paused']:
            logger.info(f"从检查点恢复任务: {task_id}, 进度: {checkpoint.progress_percent:.1f}%")
            completed_symbols = set(checkpoint.completed_symbols or [])
            remaining_symbols = [s for s in symbols if s not in completed_symbols]

            # 记录恢复事件
            self.state_manager.log_event(
                task_id,
                'resumed',
                f'从检查点恢复，剩余 {len(remaining_symbols)} 只股票'
            )
        else:
            # 创建新检查点
            remaining_symbols = symbols.copy()
            completed_symbols = set()

            if self.enable_checkpoint:
                checkpoint = DownloadCheckpoint(
                    task_id=task_id,
                    data_type=data_type,
                    symbols=symbols,
                    start_date=datetime.strptime(start_date, '%Y%m%d').date(),
                    end_date=datetime.strptime(end_date, '%Y%m%d').date(),
                    total_items=len(symbols),
                    completed_items=0,
                    status='running'
                )
                self.state_manager.save_checkpoint(checkpoint)
                self.state_manager.log_event(task_id, 'started', f'开始下载 {len(symbols)} 只股票')

        # 下载统计
        stats = {
            'total': len(symbols),
            'completed': len(completed_symbols),
            'success': len(completed_symbols),
            'failed': 0,
            'errors': {}
        }

        # 如果已全部完成
        if not remaining_symbols:
            logger.info(f"任务已完成: {task_id}")
            if self.enable_checkpoint:
                self.state_manager.mark_completed(task_id)
            return stats

        try:
            # 并发下载
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交下载任务
                future_to_symbol = {
                    executor.submit(
                        self._download_single_with_retry,
                        symbol,
                        start_date,
                        end_date,
                        data_type
                    ): symbol
                    for symbol in remaining_symbols
                }

                # 处理完成的任务
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]

                    try:
                        success = future.result()

                        if success:
                            stats['success'] += 1
                            completed_symbols.add(symbol)
                        else:
                            stats['failed'] += 1
                            stats['errors'][symbol] = "下载失败"

                    except Exception as e:
                        logger.error(f"下载失败: {symbol}, 错误: {e}")
                        stats['failed'] += 1
                        stats['errors'][symbol] = str(e)

                    finally:
                        stats['completed'] += 1

                        # 更新进度
                        if self.enable_checkpoint and checkpoint:
                            self.state_manager.update_progress(
                                task_id,
                                completed_items=stats['completed'],
                                total_items=stats['total'],
                                completed_symbols=list(completed_symbols)
                            )

                        # 进度回调
                        if progress_callback:
                            try:
                                progress_callback(stats['completed'], stats['total'], symbol)
                            except Exception as e:
                                logger.error(f"进度回调失败: {e}")

            # 任务完成
            if self.enable_checkpoint:
                if stats['failed'] == 0:
                    self.state_manager.mark_completed(task_id)
                    logger.info(f"任务完成: {task_id}, 成功: {stats['success']}")
                else:
                    error_msg = f"部分失败: 成功 {stats['success']}, 失败 {stats['failed']}"
                    self.state_manager.mark_failed(task_id, error_msg)
                    logger.warning(f"任务部分失败: {task_id}, {error_msg}")

        except Exception as e:
            logger.error(f"批量下载失败: {task_id}, 错误: {e}")
            if self.enable_checkpoint:
                self.state_manager.mark_failed(task_id, str(e))
            raise

        return stats

    @retry_enhanced(
        max_attempts=3,
        strategy=ExponentialBackoffStrategy(base_delay=1.0, backoff_factor=2.0, max_delay=30.0),
        collect_metrics=False
    )
    def _download_single_with_retry(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data_type: str
    ) -> bool:
        """
        下载单只股票数据（带重试）

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型

        Returns:
            是否下载成功
        """
        try:
            logger.debug(f"下载数据: {symbol}, {start_date} ~ {end_date}")

            if data_type == 'daily':
                df = self.provider.get_daily_data(symbol, start_date, end_date)
            else:
                logger.warning(f"不支持的数据类型: {data_type}")
                return False

            if df is None or df.empty:
                logger.warning(f"未获取到数据: {symbol}")
                return False

            # 保存数据到数据库（由provider内部处理）
            logger.debug(f"下载成功: {symbol}, 记录数: {len(df)}")
            return True

        except Exception as e:
            logger.error(f"下载失败: {symbol}, 错误: {e}")
            raise

    def resume_failed_downloads(
        self,
        data_type: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        恢复所有失败的下载任务

        Args:
            data_type: 数据类型过滤
            progress_callback: 进度回调函数

        Returns:
            恢复结果列表
        """
        # 获取待处理任务
        pending_tasks = self.state_manager.get_pending_tasks(data_type)

        if not pending_tasks:
            logger.info("没有待恢复的任务")
            return []

        logger.info(f"找到 {len(pending_tasks)} 个待恢复的任务")

        results = []
        for checkpoint in pending_tasks:
            try:
                logger.info(f"恢复任务: {checkpoint.task_id}")

                # 转换日期格式
                start_date = checkpoint.start_date.strftime('%Y%m%d')
                end_date = checkpoint.end_date.strftime('%Y%m%d')

                # 重新下载
                stats = self.download_batch(
                    symbols=checkpoint.symbols or [checkpoint.symbol],
                    start_date=start_date,
                    end_date=end_date,
                    data_type=checkpoint.data_type,
                    progress_callback=progress_callback,
                    resume_if_exists=True
                )

                results.append({
                    'task_id': checkpoint.task_id,
                    'success': True,
                    'stats': stats
                })

            except Exception as e:
                logger.error(f"恢复任务失败: {checkpoint.task_id}, 错误: {e}")
                results.append({
                    'task_id': checkpoint.task_id,
                    'success': False,
                    'error': str(e)
                })

        return results

    def get_download_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取下载进度

        Args:
            task_id: 任务ID

        Returns:
            进度信息
        """
        checkpoint = self.state_manager.load_checkpoint(task_id)
        if not checkpoint:
            return None

        return {
            'task_id': task_id,
            'data_type': checkpoint.data_type,
            'total_items': checkpoint.total_items,
            'completed_items': checkpoint.completed_items,
            'progress_percent': checkpoint.progress_percent,
            'status': checkpoint.status,
            'error_message': checkpoint.error_message,
            'retry_count': checkpoint.retry_count,
            'created_at': checkpoint.created_at,
            'updated_at': checkpoint.updated_at
        }

    def cancel_task(self, task_id: str) -> bool:
        """
        取消下载任务

        Args:
            task_id: 任务ID

        Returns:
            是否取消成功
        """
        checkpoint = self.state_manager.load_checkpoint(task_id)
        if not checkpoint:
            logger.warning(f"任务不存在: {task_id}")
            return False

        # 只能取消running或paused状态的任务
        if checkpoint.status not in ['running', 'paused']:
            logger.warning(f"任务状态不允许取消: {checkpoint.status}")
            return False

        # 标记为已取消（使用failed状态）
        self.state_manager.mark_failed(task_id, "用户取消")
        self.state_manager.log_event(task_id, 'cancelled', '用户取消任务')
        logger.info(f"任务已取消: {task_id}")
        return True
