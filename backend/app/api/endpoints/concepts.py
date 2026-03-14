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
    page: int = Query(default=1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(default=50, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索概念名称")
):
    """
    获取概念板块列表（支持分页）

    Args:
        page: 页码（从1开始）
        page_size: 每页数量（1-100）
        search: 搜索关键词（概念名称）

    Returns:
        概念列表及分页信息
    """
    try:
        conn = pool_manager.get_connection()
        try:
            cursor = conn.cursor()

            # 计算偏移量
            offset = (page - 1) * page_size

            # 构建查询条件
            where_clause = ""
            params = []
            if search:
                where_clause = "WHERE name ILIKE %s"
                params.append(f'%{search}%')

            # 查询总数
            count_query = f"SELECT COUNT(*) FROM concept {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 查询数据
            data_query = f"""
                SELECT id, code, name, source, stock_count, created_at, updated_at
                FROM concept
                {where_clause}
                ORDER BY stock_count DESC, name
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, params + [page_size, offset])

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
                "message": f"成功获取第 {page} 页，共 {total} 个概念",
                "data": {
                    "items": concepts,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }

        finally:
            cursor.close()
            pool_manager.release_connection(conn)

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
    source: Optional[str] = Query(
        None,
        description="数据源（可选）：None=使用系统配置，em=东方财富（推荐），ths=同花顺（成分股API已失效），tushare=Tushare Pro（需5000积分）"
    )
):
    """
    同步概念数据（后台任务）

    Args:
        source: 数据源（可选）
               - None: 使用系统配置的主数据源（推荐）
               - 'em': 强制使用AkShare东方财富（466个概念，完整成分股，免费）
               - 'ths': 强制使用AkShare同花顺（375个概念，成分股API已失效）
               - 'tushare': 强制使用Tushare Pro（需5000积分，数据稳定）

    Returns:
        任务提交成功信息
    """
    try:
        def sync_task():
            fetcher = ConceptFetcher(pool_manager)
            # source=None 时，ConceptFetcher 会自动使用配置的数据源
            result = fetcher.fetch_and_save_concepts(source=source)
            if result.is_success():
                print(f"✅ 概念数据同步完成: {result.message}")
            else:
                print(f"❌ 概念数据同步失败: {result.error}")

        # 添加后台任务
        background_tasks.add_task(sync_task)

        source_display = source or "系统配置的数据源"

        return {
            "code": 200,
            "message": "概念数据同步任务已提交，正在后台执行",
            "data": {
                "source": source_display,
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
