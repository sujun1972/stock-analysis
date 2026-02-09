"""
Dynamic Strategy Repository
管理动态代码策略的数据访问
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository


class DynamicStrategyRepository(BaseRepository):
    """动态代码策略数据访问层"""

    @staticmethod
    def compute_code_hash(code: str) -> str:
        """计算代码的 SHA256 哈希值"""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建动态策略

        Args:
            data: 策略数据字典
                - strategy_name (str): 策略名称（唯一）
                - class_name (str): Python类名
                - generated_code (str): 策略代码
                - display_name (str, optional): 显示名称
                - description (str, optional): 说明
                - user_prompt (str, optional): 用户提示
                - ai_model (str, optional): AI模型
                - ai_prompt (str, optional): AI提示
                - generation_tokens (int, optional): Token消耗
                - generation_cost (float, optional): 生成成本
                - validation_status (str, optional): 验证状态
                - validation_errors (dict, optional): 验证错误
                - validation_warnings (dict, optional): 验证警告
                - tags (list, optional): 标签列表
                - category (str, optional): 分类
                - created_by (str, optional): 创建人

        Returns:
            新创建策略的 ID
        """
        code = data['generated_code']
        code_hash = self.compute_code_hash(code)

        query = """
            INSERT INTO dynamic_strategies (
                strategy_name, display_name, description, class_name,
                generated_code, code_hash,
                user_prompt, ai_model, ai_prompt, generation_tokens, generation_cost,
                validation_status, validation_errors, validation_warnings,
                tags, category, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            data['strategy_name'],
            data.get('display_name'),
            data.get('description'),
            data['class_name'],
            code,
            code_hash,
            data.get('user_prompt'),
            data.get('ai_model'),
            data.get('ai_prompt'),
            data.get('generation_tokens'),
            data.get('generation_cost'),
            data.get('validation_status', 'pending'),
            json.dumps(data.get('validation_errors')) if data.get('validation_errors') else None,
            json.dumps(data.get('validation_warnings')) if data.get('validation_warnings') else None,
            data.get('tags', []),
            data.get('category'),
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
        根据 ID 获取动态策略

        Args:
            strategy_id: 策略 ID

        Returns:
            策略字典，不存在则返回 None
        """
        query = """
            SELECT
                id, strategy_name, display_name, description, class_name,
                generated_code, code_hash,
                user_prompt, ai_model, ai_prompt, generation_tokens, generation_cost,
                validation_status, validation_errors, validation_warnings,
                test_status, test_results,
                last_backtest_metrics, last_backtest_date,
                is_enabled, status, version, parent_id,
                tags, category,
                created_by, created_at, updated_by, updated_at
            FROM dynamic_strategies
            WHERE id = %s
        """

        results = self.execute_query(query, (strategy_id,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'strategy_name': row[1],
            'display_name': row[2],
            'description': row[3],
            'class_name': row[4],
            'generated_code': row[5],
            'code_hash': row[6],
            'user_prompt': row[7],
            'ai_model': row[8],
            'ai_prompt': row[9],
            'generation_tokens': row[10],
            'generation_cost': float(row[11]) if row[11] else None,
            'validation_status': row[12],
            'validation_errors': row[13],
            'validation_warnings': row[14],
            'test_status': row[15],
            'test_results': row[16],
            'last_backtest_metrics': row[17],
            'last_backtest_date': row[18].isoformat() if row[18] else None,
            'is_enabled': row[19],
            'status': row[20],
            'version': row[21],
            'parent_id': row[22],
            'tags': row[23] if row[23] else [],
            'category': row[24],
            'created_by': row[25],
            'created_at': row[26].isoformat() if row[26] else None,
            'updated_by': row[27],
            'updated_at': row[28].isoformat() if row[28] else None,
        }

    def get_by_name(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        根据策略名称获取动态策略

        Args:
            strategy_name: 策略名称

        Returns:
            策略字典，不存在则返回 None
        """
        query = """
            SELECT
                id, strategy_name, display_name, description, class_name,
                generated_code, code_hash, validation_status,
                is_enabled, status, created_at
            FROM dynamic_strategies
            WHERE strategy_name = %s
        """

        results = self.execute_query(query, (strategy_name,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'strategy_name': row[1],
            'display_name': row[2],
            'description': row[3],
            'class_name': row[4],
            'generated_code': row[5],
            'code_hash': row[6],
            'validation_status': row[7],
            'is_enabled': row[8],
            'status': row[9],
            'created_at': row[10].isoformat() if row[10] else None,
        }

    def list(
        self,
        validation_status: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        获取动态策略列表

        Args:
            validation_status: 验证状态过滤
            is_enabled: 是否启用过滤
            status: 状态过滤
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            包含 items 和 meta 的字典
        """
        conditions = []
        params = []

        if validation_status:
            conditions.append("validation_status = %s")
            params.append(validation_status)

        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(is_enabled)

        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 统计总数
        count_query = f"SELECT COUNT(*) FROM dynamic_strategies {where_clause}"
        total = self.execute_query(count_query, tuple(params))[0][0]

        # 查询数据
        offset = (page - 1) * page_size
        query = f"""
            SELECT
                id, strategy_name, display_name, description, class_name,
                validation_status, test_status, is_enabled, status,
                last_backtest_metrics, last_backtest_date,
                ai_model, tags, category,
                created_at, updated_at
            FROM dynamic_strategies
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
                'strategy_name': row[1],
                'display_name': row[2],
                'description': row[3],
                'class_name': row[4],
                'validation_status': row[5],
                'test_status': row[6],
                'is_enabled': row[7],
                'status': row[8],
                'last_backtest_metrics': row[9],
                'last_backtest_date': row[10].isoformat() if row[10] else None,
                'ai_model': row[11],
                'tags': row[12] if row[12] else [],
                'category': row[13],
                'created_at': row[14].isoformat() if row[14] else None,
                'updated_at': row[15].isoformat() if row[15] else None,
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

    def update(self, strategy_id: int, data: Dict[str, Any]) -> int:
        """
        更新动态策略

        Args:
            strategy_id: 策略 ID
            data: 更新数据字典

        Returns:
            受影响的行数
        """
        set_clauses = []
        params = []

        allowed_fields = [
            'display_name', 'description', 'generated_code',
            'validation_status', 'validation_errors', 'validation_warnings',
            'test_status', 'test_results',
            'is_enabled', 'status', 'tags', 'category', 'updated_by'
        ]

        for field in allowed_fields:
            if field in data:
                value = data[field]

                # 如果更新代码，需要重新计算哈希
                if field == 'generated_code':
                    set_clauses.append("code_hash = %s")
                    params.append(self.compute_code_hash(value))

                # JSON 字段需要序列化
                if field in ['validation_errors', 'validation_warnings', 'test_results']:
                    if value is not None:
                        value = json.dumps(value)

                set_clauses.append(f"{field} = %s")
                params.append(value)

        if not set_clauses:
            return 0

        params.append(strategy_id)
        query = f"""
            UPDATE dynamic_strategies
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        return self.execute_update(query, tuple(params))

    def delete(self, strategy_id: int) -> int:
        """
        删除动态策略

        Args:
            strategy_id: 策略 ID

        Returns:
            删除的行数
        """
        query = "DELETE FROM dynamic_strategies WHERE id = %s"
        return self.execute_update(query, (strategy_id,))

    def update_backtest_metrics(
        self,
        strategy_id: int,
        metrics: Dict[str, Any]
    ) -> int:
        """
        更新回测指标

        Args:
            strategy_id: 策略 ID
            metrics: 回测指标字典

        Returns:
            受影响的行数
        """
        query = """
            UPDATE dynamic_strategies
            SET last_backtest_metrics = %s,
                last_backtest_date = NOW()
            WHERE id = %s
        """
        return self.execute_update(query, (json.dumps(metrics), strategy_id))

    def update_validation_status(
        self,
        strategy_id: int,
        validation_status: str,
        validation_errors: Optional[Dict] = None,
        validation_warnings: Optional[Dict] = None
    ) -> int:
        """
        更新验证状态

        Args:
            strategy_id: 策略 ID
            validation_status: 验证状态
            validation_errors: 验证错误
            validation_warnings: 验证警告

        Returns:
            受影响的行数
        """
        query = """
            UPDATE dynamic_strategies
            SET validation_status = %s,
                validation_errors = %s,
                validation_warnings = %s
            WHERE id = %s
        """
        return self.execute_update(
            query,
            (
                validation_status,
                json.dumps(validation_errors) if validation_errors else None,
                json.dumps(validation_warnings) if validation_warnings else None,
                strategy_id
            )
        )

    def check_name_exists(self, strategy_name: str, exclude_id: Optional[int] = None) -> bool:
        """
        检查策略名称是否已存在

        Args:
            strategy_name: 策略名称
            exclude_id: 排除的策略ID（用于更新时检查）

        Returns:
            是否存在
        """
        if exclude_id:
            query = "SELECT COUNT(*) FROM dynamic_strategies WHERE strategy_name = %s AND id != %s"
            params = (strategy_name, exclude_id)
        else:
            query = "SELECT COUNT(*) FROM dynamic_strategies WHERE strategy_name = %s"
            params = (strategy_name,)

        result = self.execute_query(query, params)
        return result[0][0] > 0
