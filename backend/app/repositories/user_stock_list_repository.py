"""
用户股票列表 Repository
管理用户自选股列表及其成分股的数据访问
"""

from typing import Dict, List, Optional

from loguru import logger

from app.repositories.base_repository import BaseRepository


class UserStockListRepository(BaseRepository):
    """
    用户股票列表数据访问层

    管理 user_stock_lists 和 user_stock_list_items 两张表。
    所有写操作都带 user_id 校验，防止越权访问。
    """

    TABLE_NAME = "user_stock_lists"
    ITEMS_TABLE = "user_stock_list_items"

    # 每个用户最多列表数
    MAX_LISTS_PER_USER = 20
    # 每个列表最多股票数
    MAX_ITEMS_PER_LIST = 500

    def __init__(self, db=None):
        super().__init__(db)

    # ------------------------------------------------------------------
    # 列表 CRUD
    # ------------------------------------------------------------------

    def get_lists_by_user(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有股票列表（含每个列表的股票数量）

        Args:
            user_id: 用户ID

        Returns:
            列表信息列表，每项含 id, name, description, stock_count, created_at, updated_at
        """
        query = """
            SELECT
                l.id,
                l.name,
                l.description,
                COUNT(i.id) AS stock_count,
                l.created_at,
                l.updated_at
            FROM user_stock_lists l
            LEFT JOIN user_stock_list_items i ON i.list_id = l.id
            WHERE l.user_id = %s
            GROUP BY l.id, l.name, l.description, l.created_at, l.updated_at
            ORDER BY l.created_at ASC
        """
        rows = self.execute_query(query, (user_id,))
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "stock_count": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

    def get_list_by_id(self, list_id: int, user_id: int) -> Optional[Dict]:
        """
        按 ID 获取列表（校验归属）

        Args:
            list_id: 列表ID
            user_id: 用户ID（用于权限校验）

        Returns:
            列表信息，不存在或不属于该用户时返回 None
        """
        query = """
            SELECT id, name, description, created_at, updated_at
            FROM user_stock_lists
            WHERE id = %s AND user_id = %s
        """
        rows = self.execute_query(query, (list_id, user_id))
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }

    def count_user_lists(self, user_id: int) -> int:
        """统计用户列表数量"""
        query = "SELECT COUNT(*) FROM user_stock_lists WHERE user_id = %s"
        rows = self.execute_query(query, (user_id,))
        return rows[0][0] if rows else 0

    def name_exists(self, user_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """检查同名列表是否已存在"""
        if exclude_id is not None:
            query = "SELECT COUNT(*) FROM user_stock_lists WHERE user_id = %s AND name = %s AND id != %s"
            rows = self.execute_query(query, (user_id, name, exclude_id))
        else:
            query = "SELECT COUNT(*) FROM user_stock_lists WHERE user_id = %s AND name = %s"
            rows = self.execute_query(query, (user_id, name))
        return (rows[0][0] if rows else 0) > 0

    def create_list(self, user_id: int, name: str, description: Optional[str] = None) -> Dict:
        """
        创建新列表

        Args:
            user_id: 用户ID
            name: 列表名称
            description: 列表描述（可选）

        Returns:
            新建列表的完整信息
        """
        query = """
            INSERT INTO user_stock_lists (user_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id, name, description, created_at, updated_at
        """
        rows = self.execute_query_returning(query, (user_id, name, description))
        row = rows[0]
        logger.info(f"✓ 用户 {user_id} 创建股票列表: {name} (id={row[0]})")
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "stock_count": 0,
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }

    def update_list(self, list_id: int, user_id: int, name: str, description: Optional[str] = None) -> Optional[Dict]:
        """
        更新列表名称/描述

        Args:
            list_id: 列表ID
            user_id: 用户ID（权限校验）
            name: 新名称
            description: 新描述

        Returns:
            更新后的列表信息，不存在时返回 None
        """
        query = """
            UPDATE user_stock_lists
            SET name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            RETURNING id, name, description, created_at, updated_at
        """
        rows = self.execute_query_returning(query, (name, description, list_id, user_id))
        if not rows:
            return None
        row = rows[0]
        logger.info(f"✓ 用户 {user_id} 更新股票列表 {list_id}: {name}")
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "updated_at": row[4].isoformat() if row[4] else None,
        }

    def delete_list(self, list_id: int, user_id: int) -> bool:
        """
        删除列表（级联删除成分股）

        Args:
            list_id: 列表ID
            user_id: 用户ID（权限校验）

        Returns:
            是否删除成功
        """
        query = "DELETE FROM user_stock_lists WHERE id = %s AND user_id = %s"
        affected = self.execute_update(query, (list_id, user_id))
        if affected > 0:
            logger.info(f"✓ 用户 {user_id} 删除股票列表 {list_id}")
        return affected > 0

    # ------------------------------------------------------------------
    # 成分股操作
    # ------------------------------------------------------------------

    def get_list_items(self, list_id: int, user_id: int) -> List[Dict]:
        """
        获取列表中的所有股票（含股票名称、最新价、涨跌幅）

        通过 stock_basic LEFT JOIN stock_realtime 注入行情，
        无行情数据时相关字段返回 None。

        Args:
            list_id: 列表ID
            user_id: 用户ID（校验列表归属）

        Returns:
            股票列表
        """
        # 先校验列表归属
        check_query = "SELECT id FROM user_stock_lists WHERE id = %s AND user_id = %s"
        if not self.execute_query(check_query, (list_id, user_id)):
            return []

        query = """
            SELECT
                i.ts_code,
                sb.code,
                sb.name,
                sb.market,
                sb.industry,
                sr.latest_price,
                sr.pct_change,
                sr.change_amount,
                i.added_at
            FROM user_stock_list_items i
            LEFT JOIN stock_basic sb ON sb.ts_code = i.ts_code
            LEFT JOIN stock_realtime sr ON sr.code = sb.code
            WHERE i.list_id = %s
            ORDER BY i.added_at ASC
        """
        rows = self.execute_query(query, (list_id,))
        return [
            {
                "ts_code": row[0],
                "code": row[1] or row[0].split(".")[0],
                "name": row[2] or "",
                "market": row[3] or "",
                "industry": row[4] or "",
                "latest_price": float(row[5]) if row[5] is not None else None,
                "pct_change": float(row[6]) if row[6] is not None else None,
                "change_amount": float(row[7]) if row[7] is not None else None,
                "added_at": row[8].isoformat() if row[8] else None,
            }
            for row in rows
        ]

    def get_list_ts_codes(self, list_id: int, user_id: int) -> List[str]:
        """获取列表中所有股票的 ts_code（轻量接口，用于前端状态同步）"""
        check_query = "SELECT id FROM user_stock_lists WHERE id = %s AND user_id = %s"
        if not self.execute_query(check_query, (list_id, user_id)):
            return []
        query = "SELECT ts_code FROM user_stock_list_items WHERE list_id = %s ORDER BY added_at ASC"
        rows = self.execute_query(query, (list_id,))
        return [row[0] for row in rows]

    def count_list_items(self, list_id: int) -> int:
        """统计列表中股票数量"""
        query = "SELECT COUNT(*) FROM user_stock_list_items WHERE list_id = %s"
        rows = self.execute_query(query, (list_id,))
        return rows[0][0] if rows else 0

    def add_stocks(self, list_id: int, user_id: int, ts_codes: List[str]) -> int:
        """
        批量添加股票到列表（忽略已存在的）

        Args:
            list_id: 列表ID
            user_id: 用户ID（权限校验）
            ts_codes: 股票代码列表

        Returns:
            实际新增的股票数量
        """
        # 校验列表归属
        check_query = "SELECT id FROM user_stock_lists WHERE id = %s AND user_id = %s"
        if not self.execute_query(check_query, (list_id, user_id)):
            return 0

        if not ts_codes:
            return 0

        query = """
            INSERT INTO user_stock_list_items (list_id, ts_code)
            VALUES (%s, %s)
            ON CONFLICT (list_id, ts_code) DO NOTHING
        """
        values = [(list_id, code) for code in ts_codes]
        count = self.execute_batch(query, values)

        # 更新列表 updated_at
        self.execute_update(
            "UPDATE user_stock_lists SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (list_id,)
        )

        logger.info(f"✓ 列表 {list_id} 新增 {count} 只股票")
        return count

    def remove_stocks(self, list_id: int, user_id: int, ts_codes: List[str]) -> int:
        """
        批量从列表移除股票

        Args:
            list_id: 列表ID
            user_id: 用户ID（权限校验）
            ts_codes: 要移除的股票代码列表

        Returns:
            实际删除的股票数量
        """
        # 校验列表归属
        check_query = "SELECT id FROM user_stock_lists WHERE id = %s AND user_id = %s"
        if not self.execute_query(check_query, (list_id, user_id)):
            return 0

        if not ts_codes:
            return 0

        # 使用 ANY 实现批量删除
        query = """
            DELETE FROM user_stock_list_items
            WHERE list_id = %s AND ts_code = ANY(%s)
        """
        affected = self.execute_update(query, (list_id, ts_codes))

        if affected > 0:
            self.execute_update(
                "UPDATE user_stock_lists SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (list_id,)
            )

        logger.info(f"✓ 列表 {list_id} 移除 {affected} 只股票")
        return affected
