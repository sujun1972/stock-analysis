"""
股票列表API端点

功能:
- 查询股票列表（支持按list_status、market、exchange、is_hs筛选）
- 获取统计信息
- 异步同步股票列表数据
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.api.error_handler import handle_api_errors
from app.services import TaskHistoryHelper
from loguru import logger

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_stock_list(
    list_status: Optional[str] = Query(None, description="上市状态: L-上市, D-退市, P-暂停上市, G-过会未交易"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所: SSE-上交所, SZSE-深交所, BSE-北交所"),
    is_hs: Optional[str] = Query(None, description="沪深港通: S-沪股通, H-深股通, N-非港股通"),
    limit: int = Query(30, ge=1, le=100, description="每页记录数"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    查询股票列表

    Args:
        list_status: 上市状态筛选
        market: 市场类型筛选
        exchange: 交易所筛选
        is_hs: 沪深港通筛选
        limit: 每页记录数
        offset: 偏移量

    Returns:
        股票列表和总数
    """
    from src.database.db_manager import DatabaseManager

    db = DatabaseManager()

    try:
        # 构建查询条件
        conditions = []
        params = []

        if list_status:
            conditions.append("list_status = %s")
            params.append(list_status)

        if market:
            conditions.append("market = %s")
            params.append(market)

        if exchange:
            conditions.append("exchange = %s")
            params.append(exchange)

        if is_hs:
            conditions.append("is_hs = %s")
            params.append(is_hs)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM stock_basic WHERE {where_clause}"
        count_result = db._execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0

        # 查询数据
        query = f"""
            SELECT code, name, ts_code, fullname, enname, cnspell,
                   market, exchange, area, industry, curr_type,
                   list_status, list_date, delist_date, is_hs,
                   act_name, act_ent_type, status
            FROM stock_basic
            WHERE {where_clause}
            ORDER BY code
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        result = db._execute_query(query, tuple(params))

        # 转换为字典列表
        items = []
        for row in result:
            items.append({
                'code': row[0],
                'name': row[1],
                'ts_code': row[2],
                'fullname': row[3],
                'enname': row[4],
                'cnspell': row[5],
                'market': row[6],
                'exchange': row[7],
                'area': row[8],
                'industry': row[9],
                'curr_type': row[10],
                'list_status': row[11],
                'list_date': str(row[12]) if row[12] else None,
                'delist_date': str(row[13]) if row[13] else None,
                'is_hs': row[14],
                'act_name': row[15],
                'act_ent_type': row[16],
                'status': row[17]
            })

        return ApiResponse.success(data={
            'items': items,
            'total': total
        }).to_dict()

    except Exception as e:
        logger.error(f"查询股票列表失败: {e}")
        raise


@router.get("/statistics")
@handle_api_errors
async def get_statistics():
    """
    获取股票列表统计信息

    Returns:
        统计数据（总数、上市数、退市数、停牌数、沪深港通数、市场分布、交易所分布）
    """
    from src.database.db_manager import DatabaseManager

    db = DatabaseManager()

    try:
        # 总数
        total_result = db._execute_query("SELECT COUNT(*) FROM stock_basic")
        total_count = total_result[0][0] if total_result else 0

        # 上市数（L）
        listed_result = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")
        listed_count = listed_result[0][0] if listed_result else 0

        # 退市数（D）
        delisted_result = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'D'")
        delisted_count = delisted_result[0][0] if delisted_result else 0

        # 停牌数（P）
        suspended_result = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'P'")
        suspended_count = suspended_result[0][0] if suspended_result else 0

        # 沪深港通数（S或H）
        hs_result = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE is_hs IN ('S', 'H')")
        hs_count = hs_result[0][0] if hs_result else 0

        # 市场分布
        market_dist_result = db._execute_query("""
            SELECT market, COUNT(*)
            FROM stock_basic
            WHERE market IS NOT NULL AND market != ''
            GROUP BY market
        """)
        market_distribution = {row[0]: row[1] for row in market_dist_result}

        # 交易所分布
        exchange_dist_result = db._execute_query("""
            SELECT exchange, COUNT(*)
            FROM stock_basic
            WHERE exchange IS NOT NULL AND exchange != ''
            GROUP BY exchange
        """)
        exchange_distribution = {row[0]: row[1] for row in exchange_dist_result}

        return ApiResponse.success(data={
            'total_count': total_count,
            'listed_count': listed_count,
            'delisted_count': delisted_count,
            'suspended_count': suspended_count,
            'hs_count': hs_count,
            'market_distribution': market_distribution,
            'exchange_distribution': exchange_distribution
        }).to_dict()

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise


@router.post("/sync-async")
@handle_api_errors
async def sync_stock_list_async(
    list_status: Optional[str] = Query(None, description="上市状态筛选（为空则同步全部）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步股票列表数据（使用Celery）

    Args:
        list_status: 上市状态筛选（为空则同步全部状态的股票）
        current_user: 当前用户

    Returns:
        Celery任务信息
    """
    from app.tasks.sync_tasks import sync_stock_list_task

    # 提交 Celery 任务（不传 list_status 参数，同步全部数据）
    celery_task = sync_stock_list_task.delay()

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_stock_list',
        display_name='股票列表同步（全部状态）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='stock_list_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="股票列表同步任务已提交"
    ).to_dict()
