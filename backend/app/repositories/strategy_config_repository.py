"""
Strategy Config Repository
管理配置驱动策略的数据访问
"""

import json
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository


class StrategyConfigRepository(BaseRepository):
    """配置驱动策略数据访问层"""

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建策略配置

        Args:
            data: 配置数据字典
                - strategy_type (str): 策略类型
                - config (dict): 策略参数
                - name (str, optional): 配置名称
                - description (str, optional): 配置说明
                - category (str, optional): 分类
                - tags (list, optional): 标签列表
                - created_by (str, optional): 创建人

        Returns:
            新创建配置的 ID
        """
        query = """
            INSERT INTO strategy_configs (
                strategy_type, config, name, description,
                category, tags, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            data['strategy_type'],
            json.dumps(data['config']),
            data.get('name'),
            data.get('description'),
            data.get('category'),
            data.get('tags', []),
            data.get('created_by'),
        )

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            config_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return config_id
        finally:
            self.db.release_connection(conn)

    def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取配置

        Args:
            config_id: 配置 ID

        Returns:
            配置字典，不存在则返回 None
        """
        query = """
            SELECT
                id, strategy_type, config, name, description,
                category, tags, is_enabled, status, version, parent_id,
                last_backtest_metrics, last_backtest_date,
                created_by, created_at, updated_by, updated_at
            FROM strategy_configs
            WHERE id = %s
        """

        results = self.execute_query(query, (config_id,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'strategy_type': row[1],
            'config': row[2],
            'name': row[3],
            'description': row[4],
            'category': row[5],
            'tags': row[6] if row[6] else [],
            'is_enabled': row[7],
            'status': row[8],
            'version': row[9],
            'parent_id': row[10],
            'last_backtest_metrics': row[11],
            'last_backtest_date': row[12].isoformat() if row[12] else None,
            'created_by': row[13],
            'created_at': row[14].isoformat() if row[14] else None,
            'updated_by': row[15],
            'updated_at': row[16].isoformat() if row[16] else None,
        }

    def list(
        self,
        strategy_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        获取配置列表

        Args:
            strategy_type: 策略类型过滤
            is_enabled: 是否启用过滤
            status: 状态过滤
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            包含 items 和 meta 的字典
        """
        conditions = []
        params = []

        if strategy_type:
            conditions.append("strategy_type = %s")
            params.append(strategy_type)

        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(is_enabled)

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 统计总数
        count_query = f"SELECT COUNT(*) FROM strategy_configs {where_clause}"
        total = self.execute_query(count_query, tuple(params))[0][0]

        # 查询数据
        offset = (page - 1) * page_size
        query = f"""
            SELECT
                id, strategy_type, config, name, description,
                category, tags, is_enabled, status,
                last_backtest_metrics, last_backtest_date,
                created_at, updated_at
            FROM strategy_configs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])

        results = self.execute_query(query, tuple(params))

        items = []
        for row in results:
            items.append({
                'id': row[0],
                'strategy_type': row[1],
                'config': row[2],
                'name': row[3],
                'description': row[4],
                'category': row[5],
                'tags': row[6] if row[6] else [],
                'is_enabled': row[7],
                'status': row[8],
                'last_backtest_metrics': row[9],
                'last_backtest_date': row[10].isoformat() if row[10] else None,
                'created_at': row[11].isoformat() if row[11] else None,
                'updated_at': row[12].isoformat() if row[12] else None,
            })

        return {
            'items': items,
            'meta': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    def update(self, config_id: int, data: Dict[str, Any]) -> int:
        """
        更新配置

        Args:
            config_id: 配置 ID
            data: 更新数据字典

        Returns:
            受影响的行数
        """
        set_clauses = []
        params = []

        allowed_fields = [
            'config', 'name', 'description', 'category',
            'tags', 'is_enabled', 'status', 'updated_by'
        ]

        for field in allowed_fields:
            if field in data:
                value = data[field]
                # config 需要转换为 JSON
                if field == 'config' and isinstance(value, dict):
                    value = json.dumps(value)
                set_clauses.append(f"{field} = %s")
                params.append(value)

        if not set_clauses:
            return 0

        params.append(config_id)
        query = f"""
            UPDATE strategy_configs
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        return self.execute_update(query, tuple(params))

    def delete(self, config_id: int) -> int:
        """
        删除配置

        Args:
            config_id: 配置 ID

        Returns:
            删除的行数
        """
        query = "DELETE FROM strategy_configs WHERE id = %s"
        return self.execute_update(query, (config_id,))

    def update_backtest_metrics(
        self,
        config_id: int,
        metrics: Dict[str, Any]
    ) -> int:
        """
        更新回测指标

        Args:
            config_id: 配置 ID
            metrics: 回测指标字典

        Returns:
            受影响的行数
        """
        query = """
            UPDATE strategy_configs
            SET last_backtest_metrics = %s,
                last_backtest_date = NOW()
            WHERE id = %s
        """
        return self.execute_update(query, (json.dumps(metrics), config_id))

    def get_by_strategy_type(self, strategy_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        根据策略类型获取配置列表

        Args:
            strategy_type: 策略类型
            limit: 限制数量

        Returns:
            配置列表
        """
        query = """
            SELECT
                id, strategy_type, config, name, description,
                category, tags, last_backtest_metrics, last_backtest_date
            FROM strategy_configs
            WHERE strategy_type = %s AND is_enabled = TRUE
            ORDER BY last_backtest_date DESC NULLS LAST
            LIMIT %s
        """

        results = self.execute_query(query, (strategy_type, limit))

        items = []
        for row in results:
            items.append({
                'id': row[0],
                'strategy_type': row[1],
                'config': row[2],
                'name': row[3],
                'description': row[4],
                'category': row[5],
                'tags': row[6] if row[6] else [],
                'last_backtest_metrics': row[7],
                'last_backtest_date': row[8].isoformat() if row[8] else None,
            })

        return items
