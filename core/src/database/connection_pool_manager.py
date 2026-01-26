#!/usr/bin/env python3
"""
数据库连接池管理器

负责管理数据库连接池的创建、获取和释放连接。
"""

import psycopg2
from psycopg2 import pool
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    数据库连接池管理器

    职责：
    - 创建和管理数据库连接池
    - 提供连接的获取和释放接口
    - 管理连接池的生命周期
    """

    def __init__(self, config: Dict[str, Any], min_conn: int = 1, max_conn: int = 10):
        """
        初始化连接池管理器

        Args:
            config: 数据库配置字典
            min_conn: 最小连接数
            max_conn: 最大连接数
        """
        self.config = config
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.connection_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
        self._init_connection_pool()

    def _init_connection_pool(self):
        """初始化连接池"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=self.min_conn,
                maxconn=self.max_conn,
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            logger.info(f"数据库连接池创建成功 (min={self.min_conn}, max={self.max_conn})")
        except Exception as e:
            logger.error(f"数据库连接池创建失败: {e}")
            raise

    def get_connection(self):
        """
        从连接池获取连接

        Returns:
            数据库连接对象
        """
        if not self.connection_pool:
            raise RuntimeError("连接池未初始化")
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        """
        释放连接回连接池

        Args:
            conn: 数据库连接对象
        """
        if not self.connection_pool:
            logger.warning("连接池未初始化，无法释放连接")
            return
        self.connection_pool.putconn(conn)

    def close_all_connections(self):
        """关闭所有连接"""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("所有数据库连接已关闭")
            except Exception as e:
                # 连接池可能已经关闭，忽略错误
                logger.debug(f"关闭连接池时出现异常（可忽略）: {e}")

    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态信息

        Returns:
            包含连接池状态的字典
        """
        if not self.connection_pool:
            return {
                'initialized': False,
                'min_conn': self.min_conn,
                'max_conn': self.max_conn
            }

        # 注意：SimpleConnectionPool 没有直接获取当前连接数的方法
        # 这里只返回配置信息
        return {
            'initialized': True,
            'min_conn': self.min_conn,
            'max_conn': self.max_conn
        }
