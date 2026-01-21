"""
配置管理服务
管理系统全局配置，包括数据源设置、Token 等
"""

from typing import Optional, Dict
from loguru import logger
import asyncio

from src.database.db_manager import DatabaseManager


class ConfigService:
    """
    配置管理服务

    负责:
    - 读写系统配置（数据源、Token等）
    - 同步状态管理
    - 配置变更通知
    """

    def __init__(self):
        """初始化配置服务"""
        self.db = DatabaseManager()
        logger.info("✓ ConfigService initialized")

    # ========== 配置读取 ==========

    async def get_config(self, key: str) -> Optional[str]:
        """
        获取单个配置值

        Args:
            key: 配置键名

        Returns:
            Optional[str]: 配置值，不存在则返回 None
        """
        try:
            query = """
                SELECT config_value
                FROM system_config
                WHERE config_key = %s
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query,
                (key,)
            )

            if result and len(result) > 0:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取配置失败 ({key}): {e}")
            raise

    async def get_all_configs(self) -> Dict[str, str]:
        """
        获取所有配置

        Returns:
            Dict[str, str]: 配置字典
        """
        try:
            query = """
                SELECT config_key, config_value, description
                FROM system_config
                ORDER BY config_key
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query
            )

            configs = {}
            for row in result:
                configs[row[0]] = {
                    'value': row[1],
                    'description': row[2]
                }

            return configs

        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            raise

    async def get_data_source_config(self) -> Dict:
        """
        获取数据源配置

        Returns:
            Dict: 包含 data_source 和 tushare_token
        """
        try:
            data_source = await self.get_config('data_source')
            tushare_token = await self.get_config('tushare_token')

            return {
                'data_source': data_source or 'akshare',
                'tushare_token': tushare_token or ''
            }

        except Exception as e:
            logger.error(f"获取数据源配置失败: {e}")
            raise

    # ========== 配置写入 ==========

    async def set_config(self, key: str, value: str) -> bool:
        """
        设置单个配置值

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            bool: 是否成功
        """
        try:
            query = """
                UPDATE system_config
                SET config_value = %s, updated_at = CURRENT_TIMESTAMP
                WHERE config_key = %s
            """

            await asyncio.to_thread(
                self.db._execute_update,
                query,
                (value, key)
            )

            logger.info(f"✓ 更新配置: {key} = {value}")

            return True

        except Exception as e:
            logger.error(f"设置配置失败 ({key}): {e}")
            raise

    async def update_data_source(
        self,
        data_source: str,
        tushare_token: Optional[str] = None
    ) -> Dict:
        """
        更新数据源配置

        Args:
            data_source: 数据源 ('akshare' 或 'tushare')
            tushare_token: Tushare Token (可选)

        Returns:
            Dict: 更新后的配置
        """
        try:
            # 验证数据源
            if data_source not in ['akshare', 'tushare']:
                raise ValueError(f"不支持的数据源: {data_source}")

            # 如果切换到 Tushare，必须提供 Token
            if data_source == 'tushare' and not tushare_token:
                current_token = await self.get_config('tushare_token')
                if not current_token:
                    raise ValueError("切换到 Tushare 需要提供 Token")

            # 更新数据源
            await self.set_config('data_source', data_source)

            # 更新 Token (如果提供)
            if tushare_token:
                await self.set_config('tushare_token', tushare_token)

            logger.info(f"✓ 数据源已切换为: {data_source}")

            return await self.get_data_source_config()

        except Exception as e:
            logger.error(f"更新数据源配置失败: {e}")
            raise

    # ========== 同步状态管理 ==========

    async def get_sync_status(self) -> Dict:
        """
        获取同步状态

        Returns:
            Dict: 同步状态信息
        """
        try:
            sync_status = await self.get_config('sync_status')
            last_sync_date = await self.get_config('last_sync_date')
            sync_progress = await self.get_config('sync_progress')
            sync_total = await self.get_config('sync_total')
            sync_completed = await self.get_config('sync_completed')

            return {
                'status': sync_status or 'idle',
                'last_sync_date': last_sync_date or '',
                'progress': int(sync_progress or 0),
                'total': int(sync_total or 0),
                'completed': int(sync_completed or 0)
            }

        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            raise

    async def update_sync_status(
        self,
        status: Optional[str] = None,
        last_sync_date: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None
    ) -> Dict:
        """
        更新同步状态

        Args:
            status: 同步状态
            last_sync_date: 最后同步日期
            progress: 进度百分比
            total: 总数
            completed: 已完成数

        Returns:
            Dict: 更新后的同步状态
        """
        try:
            if status is not None:
                await self.set_config('sync_status', status)

            if last_sync_date is not None:
                await self.set_config('last_sync_date', last_sync_date)

            if progress is not None:
                await self.set_config('sync_progress', str(progress))

            if total is not None:
                await self.set_config('sync_total', str(total))

            if completed is not None:
                await self.set_config('sync_completed', str(completed))

            return await self.get_sync_status()

        except Exception as e:
            logger.error(f"更新同步状态失败: {e}")
            raise

    async def reset_sync_status(self) -> Dict:
        """
        重置同步状态

        Returns:
            Dict: 重置后的同步状态
        """
        return await self.update_sync_status(
            status='idle',
            progress=0,
            total=0,
            completed=0
        )

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """
        设置同步中止标志

        Args:
            abort: True表示请求中止，False表示清除中止标志
        """
        try:
            await self.set_config('sync_abort_flag', 'true' if abort else 'false')
            logger.info(f"同步中止标志已设置为: {abort}")
        except Exception as e:
            logger.error(f"设置同步中止标志失败: {e}")
            raise

    async def check_sync_abort_flag(self) -> bool:
        """
        检查是否有中止同步的请求

        Returns:
            bool: True表示应该中止，False表示继续
        """
        try:
            flag = await self.get_config('sync_abort_flag')
            return flag == 'true'
        except Exception as e:
            logger.error(f"检查同步中止标志失败: {e}")
            return False

    async def clear_sync_abort_flag(self) -> None:
        """
        清除同步中止标志
        """
        await self.set_sync_abort_flag(False)

    # ========== 模块化同步状态管理 ==========

    async def get_module_sync_status(self, module: str) -> Dict:
        """
        获取特定模块的同步状态（从 sync_log 表）

        Args:
            module: 模块名称 (stock_list, daily, minute, realtime)

        Returns:
            Dict: 模块同步状态信息
        """
        try:
            # 查询该模块最近的同步记录
            query = """
                SELECT
                    status,
                    total_count,
                    success_count,
                    failed_count,
                    progress,
                    error_message,
                    started_at,
                    completed_at
                FROM sync_log
                WHERE data_type = %s
                ORDER BY started_at DESC
                LIMIT 1
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query,
                (module,)
            )

            if result and len(result) > 0:
                row = result[0]
                return {
                    'status': row[0] or 'idle',
                    'total': row[1] or 0,
                    'success': row[2] or 0,
                    'failed': row[3] or 0,
                    'progress': row[4] or 0,
                    'error_message': row[5] or '',
                    'started_at': row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else '',
                    'completed_at': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else ''
                }
            else:
                # 没有记录，返回空闲状态
                return {
                    'status': 'idle',
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'progress': 0,
                    'error_message': '',
                    'started_at': '',
                    'completed_at': ''
                }

        except Exception as e:
            logger.error(f"获取模块同步状态失败 ({module}): {e}")
            raise

    async def create_sync_task(
        self,
        task_id: str,
        module: str,
        data_source: str
    ) -> None:
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
        """
        try:
            query = """
                INSERT INTO sync_log (
                    task_id, task_type, data_type, data_source, status
                ) VALUES (%s, %s, %s, %s, %s)
            """

            await asyncio.to_thread(
                self.db._execute_update,
                query,
                (task_id, 'manual', module, data_source, 'running')
            )

            logger.info(f"✓ 创建同步任务: {task_id} ({module})")

        except Exception as e:
            logger.error(f"创建同步任务失败: {e}")
            raise

    async def update_sync_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        更新同步任务状态

        Args:
            task_id: 任务ID
            status: 状态
            total_count: 总数
            success_count: 成功数
            failed_count: 失败数
            progress: 进度
            error_message: 错误信息
        """
        try:
            # 构建动态更新语句
            updates = []
            params = []

            if status is not None:
                updates.append("status = %s")
                params.append(status)

            if total_count is not None:
                updates.append("total_count = %s")
                params.append(total_count)

            if success_count is not None:
                updates.append("success_count = %s")
                params.append(success_count)

            if failed_count is not None:
                updates.append("failed_count = %s")
                params.append(failed_count)

            if progress is not None:
                updates.append("progress = %s")
                params.append(progress)

            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)

            # 如果状态是完成或失败，设置完成时间和持续时间
            if status in ['completed', 'failed']:
                updates.append("completed_at = CURRENT_TIMESTAMP")
                updates.append("duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))::INTEGER")

            if not updates:
                return

            query = f"""
                UPDATE sync_log
                SET {', '.join(updates)}
                WHERE task_id = %s
            """
            params.append(task_id)

            await asyncio.to_thread(
                self.db._execute_update,
                query,
                tuple(params)
            )

        except Exception as e:
            logger.error(f"更新同步任务失败: {e}")
            raise
