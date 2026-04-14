"""股票AI分析结果 Repository"""
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class StockAiAnalysisRepository(BaseRepository):
    TABLE_NAME = "stock_ai_analysis"

    # 所有 SELECT 查询共用的列列表，保持与 _row_to_dict 索引一致
    _SELECT_COLS = (
        "id, ts_code, analysis_type, analysis_text, score, "
        "prompt_text, ai_provider, ai_model, version, created_by, "
        "created_at, updated_at, trade_date"
    )

    def __init__(self, db=None):
        super().__init__(db)

    def save(
        self,
        ts_code: str,
        analysis_type: str,
        analysis_text: str,
        score: Optional[float],
        prompt_text: Optional[str],
        ai_provider: Optional[str],
        ai_model: Optional[str],
        created_by: Optional[int],
        trade_date: Optional[str] = None,
    ) -> Dict:
        """插入一条新的分析记录，版本号自动递增（同一 ts_code + analysis_type 下 MAX(version)+1）"""
        query = """
            INSERT INTO stock_ai_analysis
                (ts_code, analysis_type, analysis_text, score, prompt_text,
                 ai_provider, ai_model, version, created_by, trade_date)
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                COALESCE((
                    SELECT MAX(version) FROM stock_ai_analysis
                    WHERE ts_code = %s AND analysis_type = %s
                ), 0) + 1,
                %s, %s
            )
            RETURNING id, version, created_at, trade_date
        """
        params = (
            ts_code, analysis_type, analysis_text, score, prompt_text,
            ai_provider, ai_model,
            ts_code, analysis_type,  # for subquery
            created_by, trade_date,
        )
        try:
            result = self.execute_query_returning(query, params)
            if not result:
                raise QueryError("保存分析结果失败：未返回记录", error_code="AI_ANALYSIS_SAVE_FAILED")
            row = result[0]
            return {
                "id": row[0],
                "version": row[1],
                "created_at": row[2],
                "trade_date": row[3],
                "ts_code": ts_code,
                "analysis_type": analysis_type,
            }
        except QueryError:
            raise
        except Exception as e:
            logger.error(f"保存股票AI分析失败: {e}")
            raise QueryError("保存股票AI分析失败", error_code="AI_ANALYSIS_SAVE_FAILED", reason=str(e))

    def update(self, record_id: int, analysis_text: str, score: Optional[float]) -> Optional[Dict]:
        """更新指定记录的分析文本和评分，返回更新后的记录"""
        query = f"""
            UPDATE stock_ai_analysis
            SET analysis_text = %s, score = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING {self._SELECT_COLS}
        """
        try:
            result = self.execute_query_returning(query, (analysis_text, score, record_id))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"更新股票AI分析失败: {e}")
            raise QueryError("更新股票AI分析失败", error_code="AI_ANALYSIS_UPDATE_FAILED", reason=str(e))

    def delete(self, record_id: int) -> bool:
        """删除指定记录，返回是否成功"""
        query = "DELETE FROM stock_ai_analysis WHERE id = %s"
        try:
            affected = self.execute_update(query, (record_id,))
            return affected > 0
        except Exception as e:
            logger.error(f"删除股票AI分析失败: {e}")
            raise QueryError("删除股票AI分析失败", error_code="AI_ANALYSIS_DELETE_FAILED", reason=str(e))

    def get_by_id(self, record_id: int) -> Optional[Dict]:
        """按 id 查单条记录（用于权限校验）"""
        query = f"SELECT {self._SELECT_COLS} FROM stock_ai_analysis WHERE id = %s"
        try:
            result = self.execute_query(query, (record_id,))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            raise QueryError("查询AI分析记录失败", error_code="AI_ANALYSIS_QUERY_FAILED", reason=str(e))

    def get_latest(self, ts_code: str, analysis_type: str) -> Optional[Dict]:
        """获取指定股票+类型的最新一条分析记录"""
        query = f"""
            SELECT {self._SELECT_COLS}
            FROM stock_ai_analysis
            WHERE ts_code = %s AND analysis_type = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        try:
            result = self.execute_query(query, (ts_code, analysis_type))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"查询最新AI分析失败: {e}")
            raise QueryError("查询最新AI分析失败", error_code="AI_ANALYSIS_QUERY_FAILED", reason=str(e))

    def get_history(
        self,
        ts_code: str,
        analysis_type: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict]:
        """获取指定股票+类型的所有版本（按时间倒序，分页）"""
        query = f"""
            SELECT {self._SELECT_COLS}
            FROM stock_ai_analysis
            WHERE ts_code = %s AND analysis_type = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        try:
            result = self.execute_query(query, (ts_code, analysis_type, limit, offset))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询AI分析历史失败: {e}")
            raise QueryError("查询AI分析历史失败", error_code="AI_ANALYSIS_HISTORY_FAILED", reason=str(e))

    def get_history_count(self, ts_code: str, analysis_type: str) -> int:
        """获取指定股票+类型的历史记录总数"""
        query = """
            SELECT COUNT(*) FROM stock_ai_analysis
            WHERE ts_code = %s AND analysis_type = %s
        """
        try:
            result = self.execute_query(query, (ts_code, analysis_type))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"查询AI分析历史总数失败: {e}")
            raise QueryError("查询AI分析历史总数失败", error_code="AI_ANALYSIS_COUNT_FAILED", reason=str(e))

    def get_by_trade_date(self, ts_code: str, analysis_type: str, trade_date: str) -> Optional[Dict]:
        """获取指定股票+类型+交易日的最新一条分析记录，无则返回 None"""
        query = f"""
            SELECT {self._SELECT_COLS}
            FROM stock_ai_analysis
            WHERE ts_code = %s AND analysis_type = %s AND trade_date = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        try:
            result = self.execute_query(query, (ts_code, analysis_type, trade_date))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"按交易日查询AI分析失败: {e}")
            raise QueryError("按交易日查询AI分析失败", error_code="AI_ANALYSIS_QUERY_FAILED", reason=str(e))

    def get_latest_batch(self, ts_codes: List[str], analysis_type: str) -> Dict[str, Dict]:
        """
        批量获取多只股票的最新分析摘要（DISTINCT ON，高效索引查询）。
        返回 ts_code -> 分析记录 的映射，用于股票列表接口注入摘要数据。
        """
        if not ts_codes:
            return {}
        query = f"""
            SELECT DISTINCT ON (ts_code)
                {self._SELECT_COLS}
            FROM stock_ai_analysis
            WHERE ts_code = ANY(%s) AND analysis_type = %s
            ORDER BY ts_code, created_at DESC
        """
        try:
            result = self.execute_query(query, (ts_codes, analysis_type))
            return {row[1]: self._row_to_dict(row) for row in result}
        except Exception as e:
            logger.error(f"批量查询AI分析摘要失败: {e}")
            raise QueryError("批量查询AI分析摘要失败", error_code="AI_ANALYSIS_BATCH_FAILED", reason=str(e))

    _ALLOWED_SORT_COLUMNS = {"created_at", "score", "version", "ts_code", "analysis_type", "trade_date"}

    @staticmethod
    def _build_filters(
        ts_code: Optional[str] = None,
        analysis_type: Optional[str] = None,
        ai_provider: Optional[str] = None,
        trade_date: Optional[str] = None,
    ) -> tuple:
        """构建 WHERE 子句和参数，供 list_all / count_all 共用"""
        conditions: List[str] = []
        params: list = []
        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        if analysis_type:
            conditions.append("analysis_type = %s")
            params.append(analysis_type)
        if ai_provider:
            conditions.append("ai_provider = %s")
            params.append(ai_provider)
        if trade_date:
            conditions.append("trade_date = %s")
            params.append(trade_date)
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params

    def list_all(
        self,
        ts_code: Optional[str] = None,
        analysis_type: Optional[str] = None,
        ai_provider: Optional[str] = None,
        trade_date: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict]:
        """查询所有分析记录（支持过滤、排序、分页）"""
        where_clause, params = self._build_filters(ts_code, analysis_type, ai_provider, trade_date)

        if sort_by not in self._ALLOWED_SORT_COLUMNS:
            sort_by = "created_at"
        order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

        query = f"""
            SELECT {self._SELECT_COLS}
            FROM stock_ai_analysis
            {where_clause}
            ORDER BY {sort_by} {order_dir}
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        try:
            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询AI分析列表失败: {e}")
            raise QueryError("查询AI分析列表失败", error_code="AI_ANALYSIS_LIST_FAILED", reason=str(e))

    def count_all(
        self,
        ts_code: Optional[str] = None,
        analysis_type: Optional[str] = None,
        ai_provider: Optional[str] = None,
        trade_date: Optional[str] = None,
    ) -> int:
        """统计分析记录总数（支持过滤）"""
        where_clause, params = self._build_filters(ts_code, analysis_type, ai_provider, trade_date)
        query = f"SELECT COUNT(*) FROM stock_ai_analysis {where_clause}"
        try:
            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"统计AI分析记录总数失败: {e}")
            raise QueryError("统计AI分析记录总数失败", error_code="AI_ANALYSIS_COUNT_FAILED", reason=str(e))

    def _row_to_dict(self, row: tuple) -> Dict:
        return {
            "id": row[0],
            "ts_code": row[1],
            "analysis_type": row[2],
            "analysis_text": row[3],
            "score": float(row[4]) if row[4] is not None else None,
            "prompt_text": row[5],
            "ai_provider": row[6],
            "ai_model": row[7],
            "version": row[8],
            "created_by": row[9],
            "created_at": row[10].isoformat() if hasattr(row[10], 'isoformat') else row[10],
            "updated_at": row[11].isoformat() if hasattr(row[11], 'isoformat') else row[11],
            "trade_date": row[12] if len(row) > 12 else None,
        }
