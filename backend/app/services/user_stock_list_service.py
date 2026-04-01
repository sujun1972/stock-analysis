"""
用户股票列表 Service
封装自选股列表的业务逻辑
"""

import asyncio
from typing import Dict, List, Optional

from app.repositories.user_stock_list_repository import UserStockListRepository


class UserStockListService:
    """
    用户股票列表业务逻辑层

    - 列表数量/股票数量上限校验
    - 名称重复校验
    - 批量添加/移除股票
    """

    MAX_LISTS = UserStockListRepository.MAX_LISTS_PER_USER
    MAX_ITEMS = UserStockListRepository.MAX_ITEMS_PER_LIST

    def __init__(self):
        self.repo = UserStockListRepository()

    # ------------------------------------------------------------------
    # 列表管理
    # ------------------------------------------------------------------

    async def get_lists(self, user_id: int) -> List[Dict]:
        """获取用户所有列表"""
        return await asyncio.to_thread(self.repo.get_lists_by_user, user_id)

    async def create_list(self, user_id: int, name: str, description: Optional[str] = None) -> Dict:
        """
        创建新列表

        Raises:
            ValueError: 名称重复 / 超出上限
        """
        name = name.strip()
        if not name:
            raise ValueError("列表名称不能为空")
        if len(name) > 50:
            raise ValueError("列表名称不能超过50个字符")

        count = await asyncio.to_thread(self.repo.count_user_lists, user_id)
        if count >= self.MAX_LISTS:
            raise ValueError(f"最多只能创建 {self.MAX_LISTS} 个列表")

        exists = await asyncio.to_thread(self.repo.name_exists, user_id, name)
        if exists:
            raise ValueError(f"列表名称「{name}」已存在")

        return await asyncio.to_thread(self.repo.create_list, user_id, name, description)

    async def update_list(self, list_id: int, user_id: int, name: str, description: Optional[str] = None) -> Dict:
        """
        重命名/修改描述

        Raises:
            ValueError: 列表不存在 / 名称重复
        """
        name = name.strip()
        if not name:
            raise ValueError("列表名称不能为空")
        if len(name) > 50:
            raise ValueError("列表名称不能超过50个字符")

        exists = await asyncio.to_thread(self.repo.name_exists, user_id, name, exclude_id=list_id)
        if exists:
            raise ValueError(f"列表名称「{name}」已存在")

        result = await asyncio.to_thread(self.repo.update_list, list_id, user_id, name, description)
        if result is None:
            raise ValueError("列表不存在或无权操作")
        return result

    async def delete_list(self, list_id: int, user_id: int) -> None:
        """
        删除列表

        Raises:
            ValueError: 列表不存在
        """
        deleted = await asyncio.to_thread(self.repo.delete_list, list_id, user_id)
        if not deleted:
            raise ValueError("列表不存在或无权操作")

    # ------------------------------------------------------------------
    # 成分股管理
    # ------------------------------------------------------------------

    async def get_items(self, list_id: int, user_id: int) -> List[Dict]:
        """获取列表中的股票（含行情信息）"""
        return await asyncio.to_thread(self.repo.get_list_items, list_id, user_id)

    async def get_ts_codes(self, list_id: int, user_id: int) -> List[str]:
        """获取列表中所有 ts_code（轻量接口）"""
        return await asyncio.to_thread(self.repo.get_list_ts_codes, list_id, user_id)

    async def add_stocks(self, list_id: int, user_id: int, ts_codes: List[str]) -> Dict:
        """
        批量添加股票

        Args:
            list_id: 列表ID
            user_id: 用户ID
            ts_codes: 要添加的股票 ts_code 列表

        Returns:
            {"added": N, "skipped": M}

        Raises:
            ValueError: 列表不存在 / 超出股票上限
        """
        # 校验列表存在
        lst = await asyncio.to_thread(self.repo.get_list_by_id, list_id, user_id)
        if lst is None:
            raise ValueError("列表不存在或无权操作")

        # 去重
        ts_codes = list(dict.fromkeys(ts_codes))

        # 检查上限
        current_count = await asyncio.to_thread(self.repo.count_list_items, list_id)
        if current_count + len(ts_codes) > self.MAX_ITEMS:
            raise ValueError(f"列表最多只能包含 {self.MAX_ITEMS} 只股票（当前 {current_count} 只）")

        added = await asyncio.to_thread(self.repo.add_stocks, list_id, user_id, ts_codes)
        return {"added": added, "skipped": len(ts_codes) - added}

    async def remove_stocks(self, list_id: int, user_id: int, ts_codes: List[str]) -> Dict:
        """
        批量移除股票

        Returns:
            {"removed": N}
        """
        lst = await asyncio.to_thread(self.repo.get_list_by_id, list_id, user_id)
        if lst is None:
            raise ValueError("列表不存在或无权操作")

        removed = await asyncio.to_thread(self.repo.remove_stocks, list_id, user_id, ts_codes)
        return {"removed": removed}
