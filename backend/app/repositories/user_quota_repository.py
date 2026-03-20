"""
User Quota Repository
管理用户配额的数据访问
"""

from typing import Optional

from loguru import logger

from .base_repository import BaseRepository


class UserQuotaRepository(BaseRepository):
    """用户配额数据访问层"""

    TABLE_NAME = "user_quota"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ UserQuotaRepository initialized")

    def reset_quota_if_needed(self, user_id: int) -> None:
        """
        重置过期的配额

        该方法调用数据库存储过程来检查和重置用户配额。
        存储过程会自动判断配额是否过期，并在需要时重置。

        Args:
            user_id: 用户 ID

        Examples:
            >>> repo = UserQuotaRepository()
            >>> repo.reset_quota_if_needed(1)
        """
        # 调用存储过程
        query = "SELECT reset_quota_if_needed(%s)"

        try:
            self.execute_query(query, (user_id,))
            logger.debug(f"✓ 用户 {user_id} 配额重置检查完成")
        except Exception as e:
            logger.error(f"重置用户 {user_id} 配额失败: {e}")
            # 不抛出异常，允许配额查询继续执行
            # 如果存储过程不存在或失败，不影响整体流程

    def get_by_user_id(self, user_id: int) -> Optional[dict]:
        """
        根据用户 ID 获取配额信息

        Args:
            user_id: 用户 ID

        Returns:
            配额信息字典，不存在则返回 None

        Examples:
            >>> repo = UserQuotaRepository()
            >>> quota = repo.get_by_user_id(1)
            >>> if quota:
            >>>     print(f"剩余配额: {quota['remaining_quota']}")
        """
        query = """
            SELECT
                id, user_id, total_quota, used_quota,
                quota_reset_date, created_at, updated_at
            FROM user_quota
            WHERE user_id = %s
        """

        results = self.execute_query(query, (user_id,))

        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'user_id': row[1],
            'total_quota': row[2],
            'used_quota': row[3],
            'remaining_quota': row[2] - row[3],  # 计算剩余配额
            'quota_reset_date': row[4].isoformat() if row[4] else None,
            'created_at': row[5].isoformat() if row[5] else None,
            'updated_at': row[6].isoformat() if row[6] else None,
        }

    def update_used_quota(self, user_id: int, used_quota: int) -> int:
        """
        更新已使用的配额

        Args:
            user_id: 用户 ID
            used_quota: 新的已使用配额值

        Returns:
            受影响的行数

        Examples:
            >>> repo = UserQuotaRepository()
            >>> repo.update_used_quota(1, 50)
        """
        query = """
            UPDATE user_quota
            SET used_quota = %s, updated_at = NOW()
            WHERE user_id = %s
        """

        return self.execute_update(query, (used_quota, user_id))

    def increment_used_quota(self, user_id: int, increment: int = 1) -> int:
        """
        增加已使用的配额

        Args:
            user_id: 用户 ID
            increment: 增加的配额量（默认 1）

        Returns:
            受影响的行数

        Examples:
            >>> repo = UserQuotaRepository()
            >>> repo.increment_used_quota(1, 10)  # 增加 10 个配额
        """
        query = """
            UPDATE user_quota
            SET used_quota = used_quota + %s, updated_at = NOW()
            WHERE user_id = %s
        """

        return self.execute_update(query, (increment, user_id))

    def reset_quota(self, user_id: int) -> int:
        """
        手动重置用户配额

        Args:
            user_id: 用户 ID

        Returns:
            受影响的行数

        Examples:
            >>> repo = UserQuotaRepository()
            >>> repo.reset_quota(1)
        """
        query = """
            UPDATE user_quota
            SET used_quota = 0,
                quota_reset_date = NOW() + INTERVAL '1 month',
                updated_at = NOW()
            WHERE user_id = %s
        """

        return self.execute_update(query, (user_id,))
