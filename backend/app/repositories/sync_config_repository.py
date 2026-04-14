"""
同步配置 Repository
管理 sync_configs 表的数据访问
"""
from typing import Dict, List, Optional

from app.repositories.base_repository import BaseRepository


class SyncConfigRepository(BaseRepository):
    TABLE_NAME = "sync_configs"

    def __init__(self, db=None):
        super().__init__(db)

    def get_all(self) -> List[Dict]:
        query = """
            SELECT id, table_key, display_name, category, display_order,
                   incremental_task_name, incremental_default_days,
                   full_sync_task_name, full_sync_strategy, full_sync_concurrency,
                   passive_sync_enabled, passive_sync_task_name,
                   page_url, api_prefix, notes,
                   api_name, description, doc_url, data_source, api_limit,
                   incremental_sync_strategy, max_requests_per_minute,
                   updated_at, api_params
            FROM sync_configs
            ORDER BY category, display_order
        """
        rows = self.execute_query(query, ())
        return [self._row_to_dict(r) for r in rows]

    def get_by_table_key(self, table_key: str) -> Optional[Dict]:
        query = """
            SELECT id, table_key, display_name, category, display_order,
                   incremental_task_name, incremental_default_days,
                   full_sync_task_name, full_sync_strategy, full_sync_concurrency,
                   passive_sync_enabled, passive_sync_task_name,
                   page_url, api_prefix, notes,
                   api_name, description, doc_url, data_source, api_limit,
                   incremental_sync_strategy, max_requests_per_minute,
                   updated_at, api_params
            FROM sync_configs
            WHERE table_key = %s
        """
        rows = self.execute_query(query, (table_key,))
        return self._row_to_dict(rows[0]) if rows else None

    def update(self, table_key: str, data: Dict) -> bool:
        allowed = {
            'incremental_default_days', 'incremental_sync_strategy',
            'full_sync_strategy', 'full_sync_concurrency',
            'passive_sync_enabled', 'passive_sync_task_name', 'notes',
            'api_name', 'description', 'doc_url', 'data_source', 'api_limit',
            'max_requests_per_minute',
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return False
        set_clause = ', '.join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [table_key]
        query = f"UPDATE sync_configs SET {set_clause}, updated_at = NOW() WHERE table_key = %s"
        self.execute_update(query, tuple(values))
        return True

    @staticmethod
    def _row_to_dict(row) -> Dict:
        return {
            'id': row[0],
            'table_key': row[1],
            'display_name': row[2],
            'category': row[3],
            'display_order': row[4],
            'incremental_task_name': row[5],
            'incremental_default_days': row[6],
            'full_sync_task_name': row[7],
            'full_sync_strategy': row[8],
            'full_sync_concurrency': row[9],
            'passive_sync_enabled': row[10],
            'passive_sync_task_name': row[11],
            'page_url': row[12],
            'api_prefix': row[13],
            'notes': row[14],
            'api_name': row[15],
            'description': row[16],
            'doc_url': row[17],
            'data_source': row[18],
            'api_limit': row[19],
            'incremental_sync_strategy': row[20],
            'max_requests_per_minute': row[21],
            'updated_at': row[22].isoformat() + 'Z' if row[22] else None,
            'api_params': row[23] if len(row) > 23 else None,
        }
