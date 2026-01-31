"""
数据版本管理器 - DataVersionManager

负责数据版本的创建、追踪、对比和回滚
支持类似Git的版本控制功能

功能:
- 版本创建: 每次数据更新自动生成版本号
- 版本追踪: 记录版本元数据(时间、数据范围、来源、校验和)
- 版本对比: 比较不同版本的数据差异
- 版本回滚: 恢复到历史版本
- 版本清理: 清理过期版本(保留策略可配置)

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger
import json

try:
    from ..database.db_manager import DatabaseManager, get_database
except ImportError:
    from src.database.db_manager import DatabaseManager, get_database


class DataVersionManager:
    """
    数据版本管理器

    提供类似Git的版本控制功能,用于追踪和管理股票数据的版本变化

    特性:
    1. 自动版本号生成 (格式: v20260130_001)
    2. 版本链追踪 (parent_version_id)
    3. 活跃版本管理 (每个股票只有一个活跃版本)
    4. 版本对比和回滚
    5. 旧版本清理
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据版本管理器

        参数:
            db_manager: 数据库管理器实例,None则使用全局单例
        """
        self.db = db_manager if db_manager else get_database()
        logger.debug("DataVersionManager 初始化完成")

    def create_version(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data_source: str,
        checksum: str,
        record_count: int,
        parent_version_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建新版本

        参数:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            data_source: 数据源 (akshare/tushare)
            checksum: 数据校验和
            record_count: 记录数量
            parent_version_id: 父版本ID (用于增量更新)
            metadata: 其他元数据

        返回:
            版本信息字典
        """
        conn = None
        try:
            # 生成版本号
            version_number = self._generate_version_number(symbol)

            # 准备元数据
            meta_json = json.dumps(metadata) if metadata else None

            # 获取数据库连接，手动管理事务
            conn = self.db.get_connection()
            cursor = conn.cursor()

            try:
                # 将旧版本标记为非活跃
                deactivate_query = """
                    UPDATE data_versions
                    SET is_active = FALSE
                    WHERE symbol = %s AND is_active = TRUE
                """
                cursor.execute(deactivate_query, (symbol,))

                # 插入版本记录
                insert_query = """
                    INSERT INTO data_versions (
                        symbol, start_date, end_date, version_number,
                        data_source, record_count, checksum,
                        parent_version_id, metadata, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, TRUE)
                    RETURNING version_id, created_at
                """

                cursor.execute(
                    insert_query,
                    (
                        symbol, start_date, end_date, version_number,
                        data_source, record_count, checksum,
                        parent_version_id, meta_json
                    )
                )

                result = cursor.fetchone()

                if result:
                    version_id, created_at = result

                    # 提交事务
                    conn.commit()

                    version_info = {
                        'version_id': version_id,
                        'symbol': symbol,
                        'version_number': version_number,
                        'start_date': start_date,
                        'end_date': end_date,
                        'data_source': data_source,
                        'record_count': record_count,
                        'checksum': checksum,
                        'created_at': created_at,
                        'is_active': True,
                        'parent_version_id': parent_version_id,
                        'metadata': metadata
                    }

                    logger.info(
                        f"创建版本成功: {symbol} - {version_number} "
                        f"({record_count}条记录, 校验和: {checksum[:8]}...)"
                    )

                    return version_info
                else:
                    conn.rollback()
                    raise ValueError("版本创建失败: 无返回结果")

            except Exception as e:
                conn.rollback()
                raise

            finally:
                cursor.close()

        except Exception as e:
            logger.error(f"创建版本失败: {symbol} - {e}")
            raise

        finally:
            if conn:
                self.db.release_connection(conn)

    def get_active_version(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取当前活跃版本

        参数:
            symbol: 股票代码

        返回:
            版本信息字典,不存在则返回None
        """
        try:
            query = """
                SELECT
                    version_id, symbol, start_date, end_date,
                    version_number, created_at, data_source,
                    record_count, checksum, parent_version_id, metadata
                FROM data_versions
                WHERE symbol = %s AND is_active = TRUE
                LIMIT 1
            """

            result = self.db._execute_query(query, (symbol,))

            if result:
                row = result[0]
                return {
                    'version_id': row[0],
                    'symbol': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'version_number': row[4],
                    'created_at': row[5],
                    'data_source': row[6],
                    'record_count': row[7],
                    'checksum': row[8],
                    'parent_version_id': row[9],
                    'metadata': row[10]
                }
            else:
                logger.debug(f"股票 {symbol} 无活跃版本")
                return None

        except Exception as e:
            logger.error(f"获取活跃版本失败: {symbol} - {e}")
            raise

    def get_version_by_number(
        self,
        symbol: str,
        version_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据版本号获取版本信息

        参数:
            symbol: 股票代码
            version_number: 版本号

        返回:
            版本信息字典
        """
        try:
            query = """
                SELECT
                    version_id, symbol, start_date, end_date,
                    version_number, created_at, data_source,
                    record_count, checksum, is_active,
                    parent_version_id, metadata
                FROM data_versions
                WHERE symbol = %s AND version_number = %s
                LIMIT 1
            """

            result = self.db._execute_query(query, (symbol, version_number))

            if result:
                row = result[0]
                return {
                    'version_id': row[0],
                    'symbol': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'version_number': row[4],
                    'created_at': row[5],
                    'data_source': row[6],
                    'record_count': row[7],
                    'checksum': row[8],
                    'is_active': row[9],
                    'parent_version_id': row[10],
                    'metadata': row[11]
                }
            else:
                return None

        except Exception as e:
            logger.error(f"获取版本失败: {symbol} - {version_number} - {e}")
            raise

    def get_version_history(
        self,
        symbol: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取��本历史

        参数:
            symbol: 股票代码
            limit: 返回最近N个版本

        返回:
            版本列表 (按创建时间倒序)
        """
        try:
            query = """
                SELECT
                    version_id, symbol, start_date, end_date,
                    version_number, created_at, data_source,
                    record_count, checksum, is_active,
                    parent_version_id, metadata
                FROM data_versions
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT %s
            """

            result = self.db._execute_query(query, (symbol, limit))

            versions = []
            for row in result:
                versions.append({
                    'version_id': row[0],
                    'symbol': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'version_number': row[4],
                    'created_at': row[5],
                    'data_source': row[6],
                    'record_count': row[7],
                    'checksum': row[8],
                    'is_active': row[9],
                    'parent_version_id': row[10],
                    'metadata': row[11]
                })

            logger.debug(f"获取版本历史: {symbol} - {len(versions)}个版本")
            return versions

        except Exception as e:
            logger.error(f"获取版本历史失败: {symbol} - {e}")
            raise

    def compare_versions(
        self,
        symbol: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        比较两个版本的差异

        参数:
            symbol: 股票代码
            version1: 版本号1
            version2: 版本号2

        返回:
            差异字典
        """
        try:
            v1 = self.get_version_by_number(symbol, version1)
            v2 = self.get_version_by_number(symbol, version2)

            if not v1:
                raise ValueError(f"版本不存在: {version1}")
            if not v2:
                raise ValueError(f"版本不存在: {version2}")

            comparison = {
                'version1': version1,
                'version2': version2,
                'differences': {
                    'record_count': v2['record_count'] - v1['record_count'],
                    'checksum_changed': v1['checksum'] != v2['checksum'],
                    'data_source': {
                        'v1': v1['data_source'],
                        'v2': v2['data_source'],
                        'changed': v1['data_source'] != v2['data_source']
                    },
                    'date_range': {
                        'v1': f"{v1['start_date']} ~ {v1['end_date']}",
                        'v2': f"{v2['start_date']} ~ {v2['end_date']}",
                        'changed': (v1['start_date'] != v2['start_date'] or
                                  v1['end_date'] != v2['end_date'])
                    }
                },
                'metadata': {
                    'v1_created': v1['created_at'],
                    'v2_created': v2['created_at']
                }
            }

            logger.info(f"版本对比: {symbol} - {version1} vs {version2}")
            return comparison

        except Exception as e:
            logger.error(f"版本对比失败: {symbol} - {e}")
            raise

    def set_active_version(self, symbol: str, version_number: str) -> bool:
        """
        设置活跃版本 (回滚功能)

        参数:
            symbol: 股票代码
            version_number: 要激活的版本号

        返回:
            是否成功
        """
        try:
            # 检查版本是否存在
            version = self.get_version_by_number(symbol, version_number)
            if not version:
                raise ValueError(f"版本不存在: {version_number}")

            # 先将该symbol的所有版本设为非活跃
            query_deactivate = """
                UPDATE data_versions
                SET is_active = FALSE
                WHERE symbol = %s
            """
            self.db._execute_update(query_deactivate, (symbol,))

            # 再将指定版本设为活跃
            query_activate = """
                UPDATE data_versions
                SET is_active = TRUE
                WHERE symbol = %s AND version_number = %s
            """
            self.db._execute_update(query_activate, (symbol, version_number))

            logger.info(f"设置活跃版本: {symbol} - {version_number}")
            return True

        except Exception as e:
            logger.error(f"设置活跃版本失败: {symbol} - {version_number} - {e}")
            raise

    def cleanup_old_versions(
        self,
        symbol: Optional[str] = None,
        keep_recent: int = 5,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        清理旧版本

        参数:
            symbol: 股票代码,None则清理所有股票
            keep_recent: 保留最近N个版本
            dry_run: 仅模拟,不实际删除

        返回:
            清理统计
        """
        try:
            if symbol:
                # 单个股票清理
                versions = self.get_version_history(symbol, limit=1000)
                symbols_to_clean = {symbol: versions}
            else:
                # 所有股票清理
                query = "SELECT DISTINCT symbol FROM data_versions"
                result = self.db._execute_query(query)
                symbols_to_clean = {}
                for row in result:
                    sym = row[0]
                    versions = self.get_version_history(sym, limit=1000)
                    symbols_to_clean[sym] = versions

            total_deleted = 0
            total_kept = 0
            cleaned_symbols = []

            for sym, versions in symbols_to_clean.items():
                if len(versions) <= keep_recent:
                    total_kept += len(versions)
                    continue

                # 保留最近N个版本
                to_delete = versions[keep_recent:]

                if not dry_run:
                    for v in to_delete:
                        query = "DELETE FROM data_versions WHERE version_id = %s"
                        self.db._execute_update(query, (v['version_id'],))
                        total_deleted += 1
                else:
                    total_deleted += len(to_delete)

                total_kept += keep_recent
                cleaned_symbols.append(sym)

            result = {
                'total_deleted': total_deleted,
                'total_kept': total_kept,
                'cleaned_symbols': cleaned_symbols,
                'dry_run': dry_run
            }

            logger.info(
                f"版本清理完成: 删除{total_deleted}个版本, "
                f"保留{total_kept}个版本 (dry_run={dry_run})"
            )

            return result

        except Exception as e:
            logger.error(f"版本清理失败: {e}")
            raise

    def get_version_chain(self, symbol: str, version_number: str) -> List[Dict[str, Any]]:
        """
        获取版本链 (从指定版本追溯到根版本)

        参数:
            symbol: 股票代码
            version_number: 起始版本号

        返回:
            版本链列表 (从根到当前)
        """
        try:
            chain = []
            current_version = self.get_version_by_number(symbol, version_number)

            if not current_version:
                return chain

            chain.append(current_version)

            # 递归追溯父版本
            while current_version and current_version['parent_version_id']:
                query = """
                    SELECT
                        version_id, symbol, start_date, end_date,
                        version_number, created_at, data_source,
                        record_count, checksum, is_active,
                        parent_version_id, metadata
                    FROM data_versions
                    WHERE version_id = %s
                """

                result = self.db._execute_query(
                    query,
                    (current_version['parent_version_id'],)
                )

                if result:
                    row = result[0]
                    parent = {
                        'version_id': row[0],
                        'symbol': row[1],
                        'start_date': row[2],
                        'end_date': row[3],
                        'version_number': row[4],
                        'created_at': row[5],
                        'data_source': row[6],
                        'record_count': row[7],
                        'checksum': row[8],
                        'is_active': row[9],
                        'parent_version_id': row[10],
                        'metadata': row[11]
                    }
                    chain.insert(0, parent)  # 插入到开头
                    current_version = parent
                else:
                    break

            logger.debug(f"获取版本链: {symbol} - {version_number} - {len(chain)}层")
            return chain

        except Exception as e:
            logger.error(f"获取版本链失败: {symbol} - {version_number} - {e}")
            raise

    def _generate_version_number(self, symbol: str) -> str:
        """
        生成版本号

        格式: v20260130_001 或 v20260130_123456789 (带微秒时间戳)

        参数:
            symbol: 股票代码

        返回:
            版本号字符串

        策略:
        1. 查询当天该symbol的最大序号
        2. 如果<999,使用递增序号(max+1)
        3. 如果>=999或发生冲突,使用微秒时间戳
        """
        try:
            now = datetime.now()
            today = now.strftime('%Y%m%d')
            # 使用微秒时间戳确保唯一性
            timestamp = int(now.timestamp() * 1000000) % 1000000000  # 取后9位

            # 查询当天该symbol的最大序号 (不区分active状态，查所有版本)
            # 使用正则表达式匹配格式为 v20260130_001 的版本号
            query = """
                SELECT COALESCE(MAX(
                    CASE
                        WHEN version_number ~ '^v[0-9]{8}_[0-9]{3}$'
                             AND version_number LIKE %s
                        THEN CAST(SUBSTRING(version_number FROM 12 FOR 3) AS INTEGER)
                        ELSE 0
                    END
                ), 0) AS max_seq
                FROM data_versions
                WHERE symbol = %s
            """

            result = self.db._execute_query(query, (f"v{today}_%", symbol))
            max_seq = result[0][0] if result and result[0][0] is not None else 0

            logger.debug(f"版本号生成: {symbol} - {today} - 当前最大序号: {max_seq}")

            # 生成版本号: 如果同一天少于999个,用递增序号;否则用时间戳
            if max_seq < 999:
                # 使用递增序号
                next_seq = max_seq + 1
                version_number = f"v{today}_{next_seq:03d}"

                # 双重检查：验证版本号是否已存在(处理极端并发情况)
                check_query = """
                    SELECT 1 FROM data_versions
                    WHERE symbol = %s AND version_number = %s
                    LIMIT 1
                """
                exists = self.db._execute_query(check_query, (symbol, version_number))

                # 如果已存在(极端并发情况),使用时间戳作为fallback
                if exists:
                    logger.warning(
                        f"版本号冲突检测: {symbol} - {version_number} 已存在，"
                        f"切换到时间戳模式"
                    )
                    version_number = f"v{today}_{timestamp}"
            else:
                # 超过999个版本,使用时间戳
                logger.info(f"版本数量过多({max_seq}>=999),使用时间戳: {symbol}")
                version_number = f"v{today}_{timestamp}"

            logger.debug(f"生成版本号: {symbol} - {version_number}")
            return version_number

        except Exception as e:
            logger.error(f"生成版本号失败: {symbol} - {e}")
            raise


# ==================== 便捷函数 ====================


def get_active_version(symbol: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数: 获取活跃版本

    参数:
        symbol: 股票代码

    返回:
        版本信息字典
    """
    manager = DataVersionManager()
    return manager.get_active_version(symbol)


def create_version(
    symbol: str,
    start_date: str,
    end_date: str,
    data_source: str,
    checksum: str,
    record_count: int,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷函数: 创建版本
    """
    manager = DataVersionManager()
    return manager.create_version(
        symbol, start_date, end_date, data_source,
        checksum, record_count, **kwargs
    )


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 测试代码
    manager = DataVersionManager()

    # 创建版本
    version = manager.create_version(
        symbol='000001.SZ',
        start_date='2026-01-01',
        end_date='2026-01-30',
        data_source='akshare',
        checksum='abc123def456',
        record_count=20,
        metadata={'source': 'test', 'quality': 'high'}
    )

    print(f"创建版本: {version}")

    # 获取活跃版本
    active = manager.get_active_version('000001.SZ')
    print(f"活跃版本: {active}")

    # 获取历史
    history = manager.get_version_history('000001.SZ', limit=5)
    print(f"版本历史: {len(history)}个版本")
