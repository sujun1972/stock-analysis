"""
统一策略系统 Repository
管理所有策略的数据访问（builtin/ai/custom）

根据 UNIFIED_DYNAMIC_STRATEGY_ARCHITECTURE.md Phase 2 设计

作者: Backend Team
创建日期: 2026-02-09
版本: 2.0.0
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository


class StrategyRepository(BaseRepository):
    """统一策略数据访问层"""

    @staticmethod
    def compute_code_hash(code: str) -> str:
        """计算代码的 SHA256 哈希值"""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建策略

        Args:
            data: 策略数据字典
                - name (str): 策略唯一标识
                - display_name (str): 显示名称
                - code (str): 完整Python代码
                - class_name (str): 类名
                - source_type (str): builtin/ai/custom
                - description (str, optional): 说明
                - category (str, optional): 类别
                - tags (list, optional): 标签
                - default_params (dict, optional): 默认参数
                - validation_status (str, optional): 验证状态
                - validation_errors (dict, optional): 验证错误
                - validation_warnings (dict, optional): 验证警告
                - risk_level (str, optional): 风险等级
                - parent_strategy_id (int, optional): 父策略ID
                - created_by (str, optional): 创建人

        Returns:
            新创建策略的 ID
        """
        code = data['code']
        code_hash = self.compute_code_hash(code)

        query = """
            INSERT INTO strategies (
                name, display_name, code, code_hash, class_name,
                source_type, description, category, tags,
                default_params, validation_status, validation_errors,
                validation_warnings, risk_level, parent_strategy_id,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            data['name'],
            data['display_name'],
            code,
            code_hash,
            data['class_name'],
            data['source_type'],
            data.get('description'),
            data.get('category'),
            data.get('tags', []),
            json.dumps(data.get('default_params')) if data.get('default_params') else None,
            data.get('validation_status', 'pending'),
            json.dumps(data.get('validation_errors')) if data.get('validation_errors') else None,
            json.dumps(data.get('validation_warnings')) if data.get('validation_warnings') else None,
            data.get('risk_level', 'medium'),
            data.get('parent_strategy_id'),
            data.get('created_by'),
        )

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            strategy_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return strategy_id
        finally:
            self.db.release_connection(conn)

    def get_by_id(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取策略详情（包含完整代码）

        Args:
            strategy_id: 策略 ID

        Returns:
            策略详情字典，不存在则返回 None
        """
        query = """
            SELECT
                id, name, display_name, code, code_hash, class_name,
                source_type, description, category, tags,
                default_params, validation_status, validation_errors,
                validation_warnings, risk_level, is_enabled,
                usage_count, backtest_count, avg_sharpe_ratio, avg_annual_return,
                version, parent_strategy_id, created_by,
                created_at, updated_at, last_used_at
            FROM strategies
            WHERE id = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return self._row_to_dict(cursor, row)
        finally:
            self.db.release_connection(conn)

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取策略

        Args:
            name: 策略名称

        Returns:
            策略详情字典，不存在则返回 None
        """
        query = """
            SELECT
                id, name, display_name, code, code_hash, class_name,
                source_type, description, category, tags,
                default_params, validation_status, validation_errors,
                validation_warnings, risk_level, is_enabled,
                usage_count, backtest_count, avg_sharpe_ratio, avg_annual_return,
                version, parent_strategy_id, created_by,
                created_at, updated_at, last_used_at
            FROM strategies
            WHERE name = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (name,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return self._row_to_dict(cursor, row)
        finally:
            self.db.release_connection(conn)

    def list_all(
        self,
        source_type: Optional[str] = None,
        category: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        validation_status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_code: bool = False
    ) -> Dict[str, Any]:
        """
        获取策略列表（支持筛选和分页）

        Args:
            source_type: 来源类型过滤 (builtin/ai/custom)
            category: 类别过滤
            is_enabled: 是否启用过滤
            validation_status: 验证状态过滤
            search: 搜索关键词（名称、描述）
            page: 页码（从1开始）
            page_size: 每页数量
            include_code: 是否包含完整代码（默认不包含）

        Returns:
            {
                'items': [...],
                'meta': {
                    'total': 100,
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 5
                }
            }
        """
        # 构建查询条件
        where_clauses = []
        params = []

        if source_type:
            where_clauses.append("source_type = %s")
            params.append(source_type)

        if category:
            where_clauses.append("category = %s")
            params.append(category)

        if is_enabled is not None:
            where_clauses.append("is_enabled = %s")
            params.append(is_enabled)

        if validation_status:
            where_clauses.append("validation_status = %s")
            params.append(validation_status)

        if search:
            where_clauses.append("(display_name ILIKE %s OR description ILIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern])

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # 选择字段（是否包含完整代码）
        if include_code:
            select_fields = "*"
        else:
            select_fields = """
                id, name, display_name, class_name, source_type,
                description, category, tags, validation_status,
                risk_level, is_enabled, usage_count, backtest_count,
                avg_sharpe_ratio, avg_annual_return, created_at, updated_at
            """

        # 计算总数
        count_query = f"SELECT COUNT(*) FROM strategies WHERE {where_sql}"

        # 查询数据
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT {select_fields}
            FROM strategies
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()

            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 获取数据
            cursor.execute(data_query, params + [page_size, offset])
            rows = cursor.fetchall()
            cursor.close()

            items = [self._row_to_dict(cursor, row) for row in rows]

            total_pages = (total + page_size - 1) // page_size

            return {
                'items': items,
                'meta': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages
                }
            }
        finally:
            self.db.release_connection(conn)

    def update(self, strategy_id: int, data: Dict[str, Any]) -> None:
        """
        更新策略

        Args:
            strategy_id: 策略 ID
            data: 更新数据字典
        """
        update_fields = []
        params = []

        # 可更新字段
        allowed_fields = [
            'display_name', 'description', 'code', 'class_name',
            'tags', 'default_params', 'validation_status',
            'validation_errors', 'validation_warnings', 'risk_level',
            'is_enabled'
        ]

        for field in allowed_fields:
            if field in data:
                value = data[field]

                # JSON 字段特殊处理
                if field in ['default_params', 'validation_errors', 'validation_warnings']:
                    value = json.dumps(value) if value else None
                # 数组字段特殊处理
                elif field == 'tags':
                    value = value if isinstance(value, list) else []

                update_fields.append(f"{field} = %s")
                params.append(value)

        # 如果更新了代码，需要重新计算哈希和增加版本号
        if 'code' in data:
            code_hash = self.compute_code_hash(data['code'])
            update_fields.append("code_hash = %s")
            params.append(code_hash)
            update_fields.append("version = version + 1")

        if not update_fields:
            return

        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        params.append(strategy_id)

        query = f"""
            UPDATE strategies
            SET {', '.join(update_fields)}
            WHERE id = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
        finally:
            self.db.release_connection(conn)

    def delete(self, strategy_id: int) -> None:
        """
        删除策略

        Args:
            strategy_id: 策略 ID
        """
        query = "DELETE FROM strategies WHERE id = %s"

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            conn.commit()
            cursor.close()
        finally:
            self.db.release_connection(conn)

    def increment_usage_count(self, strategy_id: int) -> None:
        """
        增加使用计数

        Args:
            strategy_id: 策略 ID
        """
        query = """
            UPDATE strategies
            SET usage_count = usage_count + 1,
                last_used_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            conn.commit()
            cursor.close()
        finally:
            self.db.release_connection(conn)

    def increment_backtest_count(self, strategy_id: int) -> None:
        """
        增加回测计数

        Args:
            strategy_id: 策略 ID
        """
        query = """
            UPDATE strategies
            SET backtest_count = backtest_count + 1
            WHERE id = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            conn.commit()
            cursor.close()
        finally:
            self.db.release_connection(conn)

    def update_backtest_metrics(
        self,
        strategy_id: int,
        sharpe_ratio: float,
        annual_return: float
    ) -> None:
        """
        更新回测指标（计算移动平均）

        Args:
            strategy_id: 策略 ID
            sharpe_ratio: 本次夏普率
            annual_return: 本次年化收益
        """
        query = """
            UPDATE strategies
            SET avg_sharpe_ratio = COALESCE(
                    (avg_sharpe_ratio * backtest_count + %s) / (backtest_count + 1),
                    %s
                ),
                avg_annual_return = COALESCE(
                    (avg_annual_return * backtest_count + %s) / (backtest_count + 1),
                    %s
                ),
                backtest_count = backtest_count + 1
            WHERE id = %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (sharpe_ratio, sharpe_ratio, annual_return, annual_return, strategy_id)
            )
            conn.commit()
            cursor.close()
        finally:
            self.db.release_connection(conn)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取策略统计信息

        Returns:
            统计数据字典
        """
        query = """
            SELECT
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE is_enabled = TRUE) as enabled_count,
                COUNT(*) FILTER (WHERE is_enabled = FALSE) as disabled_count,
                source_type,
                category,
                validation_status,
                risk_level
            FROM strategies
            GROUP BY GROUPING SETS (
                (),
                (source_type),
                (category),
                (validation_status),
                (risk_level)
            )
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            # 解析统计数据
            stats = {
                'total_count': 0,
                'enabled_count': 0,
                'disabled_count': 0,
                'by_source': {},
                'by_category': {},
                'by_validation': {},
                'by_risk': {}
            }

            for row in rows:
                total, enabled, disabled, source, cat, val, risk = row

                if not any([source, cat, val, risk]):
                    # 总计
                    stats['total_count'] = total or 0
                    stats['enabled_count'] = enabled or 0
                    stats['disabled_count'] = disabled or 0
                elif source:
                    stats['by_source'][source] = total
                elif cat:
                    stats['by_category'][cat] = total
                elif val:
                    stats['by_validation'][val] = total
                elif risk:
                    stats['by_risk'][risk] = total

            return stats
        finally:
            self.db.release_connection(conn)

    def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查策略名称是否已存在

        Args:
            name: 策略名称
            exclude_id: 排除的策略ID（用于更新时检查）

        Returns:
            是否存在
        """
        if exclude_id:
            query = "SELECT EXISTS(SELECT 1 FROM strategies WHERE name = %s AND id != %s)"
            params = (name, exclude_id)
        else:
            query = "SELECT EXISTS(SELECT 1 FROM strategies WHERE name = %s)"
            params = (name,)

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            exists = cursor.fetchone()[0]
            cursor.close()
            return exists
        finally:
            self.db.release_connection(conn)

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        if not row:
            return {}

        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))

        # 解析 JSON 字段
        if 'default_params' in result and result['default_params']:
            result['default_params'] = json.loads(result['default_params']) if isinstance(result['default_params'], str) else result['default_params']

        if 'validation_errors' in result and result['validation_errors']:
            result['validation_errors'] = json.loads(result['validation_errors']) if isinstance(result['validation_errors'], str) else result['validation_errors']

        if 'validation_warnings' in result and result['validation_warnings']:
            result['validation_warnings'] = json.loads(result['validation_warnings']) if isinstance(result['validation_warnings'], str) else result['validation_warnings']

        return result
