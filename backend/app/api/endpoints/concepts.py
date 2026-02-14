"""
概念板块相关的 API 端点

提供概念管理、查询和更新功能
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import List, Optional
import sys
from pathlib import Path

# 添加 core 模块到路径
core_path = Path(__file__).parent.parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.database.connection_pool_manager import ConnectionPoolManager
from src.concept_fetcher import ConceptFetcher
from src.config.settings import get_settings

router = APIRouter()

# 初始化数据库连接池
settings = get_settings()
db_settings = settings.database

pool_manager = ConnectionPoolManager(
    config={
        'host': db_settings.host,
        'port': db_settings.port,
        'database': db_settings.database,
        'user': db_settings.user,
        'password': db_settings.password
    },
    min_conn=2,
    max_conn=20
)


@router.get("/list")
async def get_concepts_list(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="限制返回数量"),
    search: Optional[str] = Query(None, description="搜索概念名称")
):
    """
    获取概念板块列表

    Args:
        limit: 限制返回数量
        search: 搜索关键词（概念名称）

    Returns:
        概念列表及统计信息
    """
    try:
        fetcher = ConceptFetcher(pool_manager)

        # 如果有搜索关键词，使用模糊查询
        if search:
            conn = pool_manager.get_connection()
            try:
                cursor = conn.cursor()
                query = """
                    SELECT id, code, name, source, stock_count, created_at, updated_at
                    FROM concept
                    WHERE name ILIKE %s
                    ORDER BY stock_count DESC, name
                """
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (f'%{search}%',))

                concepts = []
                for row in cursor.fetchall():
                    concepts.append({
                        'id': row[0],
                        'code': row[1],
                        'name': row[2],
                        'source': row[3],
                        'stock_count': row[4],
                        'created_at': row[5].isoformat() if row[5] else None,
                        'updated_at': row[6].isoformat() if row[6] else None
                    })

                return {
                    "code": 200,
                    "message": f"成功获取 {len(concepts)} 个概念",
                    "data": {
                        "items": concepts,
                        "total": len(concepts)
                    }
                }

            finally:
                cursor.close()
                pool_manager.release_connection(conn)

        else:
            # 获取全部概念
            result = fetcher.get_all_concepts(limit=limit)

            if result.is_success():
                return {
                    "code": 200,
                    "message": result.message,
                    "data": {
                        "items": result.data,
                        "total": len(result.data)
                    }
                }
            else:
                raise HTTPException(status_code=500, detail=result.error)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念列表失败: {str(e)}")


@router.get("/{concept_id}")
async def get_concept_detail(concept_id: int):
    """
    获取概念详情

    Args:
        concept_id: 概念ID

    Returns:
        概念详细信息
    """
    try:
        conn = pool_manager.get_connection()
        try:
            cursor = conn.cursor()

            # 获取概念基本信息
            cursor.execute("""
                SELECT id, code, name, source, description, stock_count, created_at, updated_at
                FROM concept
                WHERE id = %s
            """, (concept_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")

            concept = {
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'source': row[3],
                'description': row[4],
                'stock_count': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None
            }

            return {
                "code": 200,
                "message": "获取概念详情成功",
                "data": concept
            }

        finally:
            cursor.close()
            pool_manager.release_connection(conn)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念详情失败: {str(e)}")


@router.get("/{concept_id}/stocks")
async def get_concept_stocks(
    concept_id: int,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="限制返回数量")
):
    """
    获取概念包含的股票列表

    Args:
        concept_id: 概念ID
        limit: 限制返回数量

    Returns:
        股票列表
    """
    try:
        conn = pool_manager.get_connection()
        try:
            cursor = conn.cursor()

            # 获取概念的股票列表
            query = """
                SELECT
                    sc.stock_code,
                    si.name,
                    si.market,
                    si.industry
                FROM stock_concept sc
                LEFT JOIN stock_info si ON sc.stock_code = si.code
                WHERE sc.concept_id = %s
                ORDER BY sc.stock_code
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (concept_id,))

            stocks = []
            for row in cursor.fetchall():
                stocks.append({
                    'code': row[0],
                    'name': row[1],
                    'market': row[2],
                    'industry': row[3]
                })

            return {
                "code": 200,
                "message": f"获取到 {len(stocks)} 只股票",
                "data": {
                    "items": stocks,
                    "total": len(stocks)
                }
            }

        finally:
            cursor.close()
            pool_manager.release_connection(conn)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概念股票列表失败: {str(e)}")


@router.get("/stock/{stock_code}")
async def get_stock_concepts(stock_code: str):
    """
    获取股票所属的所有概念

    Args:
        stock_code: 股票代码（如 '000001.SZ'）

    Returns:
        概念列表
    """
    try:
        fetcher = ConceptFetcher(pool_manager)
        result = fetcher.get_stock_concepts(stock_code)

        if result.is_success():
            return {
                "code": 200,
                "message": result.message,
                "data": result.data
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票概念失败: {str(e)}")


@router.post("/sync")
async def sync_concepts(
    background_tasks: BackgroundTasks,
    source: str = Query(default='ths', description="数据源：ths（同花顺）或 em（东方财富）")
):
    """
    同步概念数据（后台任务）

    Args:
        source: 数据源（ths 或 em）

    Returns:
        任务提交成功信息
    """
    try:
        def sync_task():
            fetcher = ConceptFetcher(pool_manager)
            result = fetcher.fetch_and_save_concepts(source=source)
            if result.is_success():
                print(f"✅ 概念数据同步完成: {result.message}")
            else:
                print(f"❌ 概念数据同步失败: {result.error}")

        # 添加后台任务
        background_tasks.add_task(sync_task)

        return {
            "code": 200,
            "message": "概念数据同步任务已提交，正在后台执行",
            "data": {
                "source": source,
                "status": "processing"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交同步任务失败: {str(e)}")


@router.put("/stock/{stock_code}/concepts")
async def update_stock_concepts(
    stock_code: str,
    concept_ids: List[int]
):
    """
    更新股票的概念标签

    Args:
        stock_code: 股票代码
        concept_ids: 概念ID列表

    Returns:
        更新结果
    """
    try:
        conn = pool_manager.get_connection()
        try:
            cursor = conn.cursor()

            # 先删除该股票的所有概念关系
            cursor.execute("DELETE FROM stock_concept WHERE stock_code = %s", (stock_code,))

            # 添加新的概念关系
            added_count = 0
            for concept_id in concept_ids:
                # 获取概念信息
                cursor.execute(
                    "SELECT code, name FROM concept WHERE id = %s",
                    (concept_id,)
                )
                concept_row = cursor.fetchone()

                if concept_row:
                    concept_code, concept_name = concept_row
                    cursor.execute("""
                        INSERT INTO stock_concept
                            (stock_code, concept_id, concept_code, concept_name)
                        VALUES (%s, %s, %s, %s)
                    """, (stock_code, concept_id, concept_code, concept_name))
                    added_count += 1

            # 更新概念的股票数量
            for concept_id in concept_ids:
                cursor.execute("""
                    UPDATE concept
                    SET stock_count = (
                        SELECT COUNT(*) FROM stock_concept WHERE concept_id = %s
                    )
                    WHERE id = %s
                """, (concept_id, concept_id))

            conn.commit()

            return {
                "code": 200,
                "message": f"成功更新股票概念，添加了 {added_count} 个概念",
                "data": {
                    "stock_code": stock_code,
                    "concepts_count": added_count
                }
            }

        finally:
            cursor.close()
            pool_manager.release_connection(conn)

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新股票概念失败: {str(e)}")
