"""
股票列表API端点

功能:
- 查询股票列表（支持按list_status、market、exchange、is_hs、industry、concept_code筛选）
- 获取行业分类列表（动态，来自数据库实际数据）
- 获取概念板块列表（来自 dc_index，只返回 dc_member 中有成分股的板块）
- 获取统计信息
- 异步同步股票列表数据
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from loguru import logger
from src.database.db_manager import DatabaseManager
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.api.error_handler import handle_api_errors
from app.services import TaskHistoryHelper
from app.services.stock_ai_analysis_service import StockAiAnalysisService
from app.services.stock_quote_cache import stock_quote_cache

router = APIRouter()


@router.get("/industries")
@handle_api_errors
async def get_industries():
    """
    获取所有行业分类列表（用于前端筛选器）

    Returns:
        行业列表，按股票数量降序排列
    """
    db = DatabaseManager()

    result = db._execute_query("""
        SELECT industry, COUNT(*) as cnt
        FROM stock_basic
        WHERE industry IS NOT NULL AND industry != ''
          AND list_status = 'L'
        GROUP BY industry
        ORDER BY cnt DESC
    """)

    industries = [{'value': row[0], 'label': row[0], 'count': row[1]} for row in result]

    return ApiResponse.success(data={'industries': industries}).to_dict()


@router.get("/concepts")
@handle_api_errors
async def get_concepts(
    search: Optional[str] = Query(None, description="搜索关键词，模糊匹配概念名称"),
    idx_type: str = Query('概念板块', description="板块类型：概念板块/行业板块/地域板块"),
    limit: int = Query(50, ge=1, le=200, description="每页记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取板块列表（来自 dc_index，用于前端懒加载筛选器）

    支持概念板块/行业板块/地域板块三种类型。
    只返回 dc_member 中有成分股数据的板块，避免用户选到空数据。
    成员数量通过子查询统计，不做跨表 JOIN。
    """
    db = DatabaseManager()

    params: list = [idx_type, idx_type]

    search_clause = ""
    if search:
        search_clause = "AND di.name ILIKE %s"
        params.append(f"%{search}%")

    # 只返回在 dc_member 中实际有成分股记录的板块
    base_sql = f"""
        FROM dc_index di
        WHERE di.idx_type = %s
          AND di.trade_date = (
              SELECT MAX(trade_date) FROM dc_index WHERE idx_type = %s
          )
          AND EXISTS (SELECT 1 FROM dc_member dm WHERE dm.ts_code = di.ts_code)
          {search_clause}
    """

    count_result = db._execute_query(
        f"SELECT COUNT(DISTINCT di.ts_code) {base_sql}",
        tuple(params),
    )
    total = count_result[0][0] if count_result else 0

    params.extend([limit, offset])
    rows = db._execute_query(
        f"""
        SELECT di.ts_code, di.name,
               (SELECT COUNT(DISTINCT dm.con_code) FROM dc_member dm WHERE dm.ts_code = di.ts_code) AS member_count
        {base_sql}
        ORDER BY di.name
        LIMIT %s OFFSET %s
        """,
        tuple(params),
    )

    items = [{'ts_code': row[0], 'name': row[1], 'member_count': row[2]} for row in rows]

    return ApiResponse.success(data={'items': items, 'total': total}).to_dict()


# 多列排序配置：每个 sort key → JOIN 片段 + 排序表达式
#
# 设计要点：
# - join_group：同一子查询被多个 key 引用时只 JOIN 一次（如 cio_* 三个 key 都来自 cio_directive 最新一条）
# - join_group=None 表示无需额外 JOIN（用 sb.* 自带列）
# - JOIN 片段中的 %s 参数按 SORT_SPECS 出现顺序拼到 sort_join_params 里
#
# 新增可排序列：在此追加一项即可，order_clause 构造无需改动
def _ai_score_join(alias: str, analysis_type: str) -> str:
    return f"""LEFT JOIN (
            SELECT DISTINCT ON (ts_code) ts_code, score
            FROM stock_ai_analysis
            WHERE analysis_type = %s
            ORDER BY ts_code, created_at DESC
        ) {alias} ON {alias}.ts_code = sb.ts_code"""


# CIO 三个 key 共享的子查询：一次取出 score / created_at / followup_triggers
_CIO_JOIN = """LEFT JOIN (
            SELECT DISTINCT ON (ts_code) ts_code, score, created_at, followup_triggers
            FROM stock_ai_analysis
            WHERE analysis_type = 'cio_directive'
            ORDER BY ts_code, created_at DESC
        ) sort_cio ON sort_cio.ts_code = sb.ts_code"""


SORT_SPECS: dict = {
    "pct_change": {
        "join_group": "realtime",
        "join": "LEFT JOIN stock_realtime sr ON sr.code = sb.code",
        "params": [],
        "expr": "sr.pct_change",
    },
    "score_hot_money": {
        "join_group": "ai_hot_money",
        "join": _ai_score_join("sort_hm", "hot_money_view"),
        "params": ["hot_money_view"],
        "expr": "sort_hm.score",
    },
    "score_midline": {
        "join_group": "ai_midline",
        "join": _ai_score_join("sort_ml", "midline_industry_expert"),
        "params": ["midline_industry_expert"],
        "expr": "sort_ml.score",
    },
    "score_longterm": {
        "join_group": "ai_longterm",
        "join": _ai_score_join("sort_lt", "longterm_value_watcher"),
        "params": ["longterm_value_watcher"],
        "expr": "sort_lt.score",
    },
    "cio_score": {
        "join_group": "ai_cio",
        "join": _CIO_JOIN,
        "params": [],
        "expr": "sort_cio.score",
    },
    "cio_last_date": {
        "join_group": "ai_cio",
        "join": _CIO_JOIN,
        "params": [],
        "expr": "sort_cio.created_at",
    },
    "cio_followup_time": {
        "join_group": "ai_cio",
        "join": _CIO_JOIN,
        "params": [],
        # 从 followup_triggers.time_triggers JSONB 数组里提取最小 expected_date；非 YYYY-MM-DD 字符串过滤
        "expr": r"""(
            SELECT MIN((elem->>'expected_date')::date)
            FROM jsonb_array_elements(COALESCE(sort_cio.followup_triggers->'time_triggers', '[]'::jsonb)) AS elem
            WHERE elem->>'expected_date' IS NOT NULL
              AND elem->>'expected_date' ~ '^\d{4}-\d{2}-\d{2}$'
        )""",
    },
    "code": {
        "join_group": None,
        "join": "",
        "params": [],
        "expr": "sb.code",
    },
}


def _parse_sort_param(
    sort: Optional[str],
    legacy_sort_by: Optional[str],
    legacy_sort_order: Optional[str],
) -> list:
    """
    解析排序参数为 [(key, 'ASC'|'DESC'), ...]

    - 新参数 `sort` 优先；缺省时回退旧 `sort_by`/`sort_order`（仅兼容已发出的 URL）
    - 格式：'key:order,key:order,...'；order 缺省 desc，asc 大小写不敏感
    - 非法 key 跳过（白名单 = SORT_SPECS 的 keys）；重复 key 仅保留首次出现
    """
    raw_pairs: list = []
    if sort:
        for chunk in sort.split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            key, _, order = chunk.partition(':')
            raw_pairs.append((key.strip(), order.strip().lower()))
    elif legacy_sort_by:
        raw_pairs.append((legacy_sort_by.strip(), (legacy_sort_order or 'desc').strip().lower()))

    parsed: list = []
    seen: set = set()
    for key, order in raw_pairs:
        if key not in SORT_SPECS or key in seen:
            continue
        parsed.append((key, 'ASC' if order == 'asc' else 'DESC'))
        seen.add(key)
    return parsed


@router.get("")
@handle_api_errors
async def get_stock_list(
    list_status: Optional[str] = Query(None, description="上市状态: L-上市, D-退市, P-暂停上市, G-过会未交易"),
    market: Optional[str] = Query(None, description="市场类型"),
    exchange: Optional[str] = Query(None, description="交易所: SSE-上交所, SZSE-深交所, BSE-北交所"),
    is_hs: Optional[str] = Query(None, description="沪深港通: S-沪股通, H-深股通, N-非港股通"),
    industry: Optional[str] = Query(None, description="行业筛选，如: 电气设备、软件服务、化工原料"),
    concept_code: Optional[str] = Query(None, description="概念板块代码，如: BK0714.DC"),
    search: Optional[str] = Query(None, description="搜索关键词，支持股票代码或名称的模糊匹配"),
    stock_selection_strategy_id: Optional[int] = Query(None, description="选股策略ID，执行策略后仅返回选中的股票"),
    user_stock_list_id: Optional[int] = Query(None, description="自选列表ID，仅返回该列表中的股票"),
    ts_codes: Optional[str] = Query(None, description="ts_code 列表，逗号分隔；传入后仅返回这些股票（用于静默刷新场景，不改变前端显示的行集合）"),
    include_analysis: bool = Query(False, description="是否附带每只股票的最新AI分析摘要（游资观点评分等）"),
    sort: Optional[str] = Query(None, description="多列排序，格式 'key:order,key:order,...'。key 白名单见 SORT_SPECS；order 为 asc/desc，缺省 desc。优先级从前到后递减。"),
    sort_by: Optional[str] = Query(None, description="[已废弃] 单列排序字段，与 sort_order 配对。新代码请用 sort"),
    sort_order: Optional[str] = Query(None, description="[已废弃] 单列排序方向：asc/desc"),
    limit: int = Query(30, ge=1, le=100, description="每页记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    skip: int = Query(0, ge=0, description="偏移量（offset别名，兼容前端）"),
):
    """
    查询股票列表

    - 概念板块筛选通过 JOIN dc_member 最新一天的成分股实现
    - 当 stock_selection_strategy_id 存在时，先通过
      StrategyDynamicLoader.run_stock_selection() 执行选股策略，
      再将选出的 ts_code 追加为 WHERE sb.ts_code IN (...) 条件
    - offset 和 skip 均可作为分页偏移量（前端历史原因同时传了 skip）
    """
    from app.services.strategy_loader import StrategyDynamicLoader
    from app.repositories.strategy_repository import StrategyRepository

    # 前端同时使用 offset 和 skip 两个参数名，取非零的那个
    effective_offset = offset if offset > 0 else skip

    db = DatabaseManager()

    # 执行选股策略，获取选中的 ts_code 列表（失败时降级为全量，记录警告）
    selection_ts_codes: Optional[list] = None
    selection_strategy_name: Optional[str] = None
    if stock_selection_strategy_id is not None:
        strategy_repo = StrategyRepository()
        strategy_record = strategy_repo.get_by_id(stock_selection_strategy_id)
        if strategy_record and strategy_record.get("strategy_type") == "stock_selection":
            selection_strategy_name = strategy_record.get("display_name")
            try:
                selection_ts_codes = await StrategyDynamicLoader.run_stock_selection(
                    strategy_record
                )
            except Exception as e:
                logger.warning(f"选股策略 {stock_selection_strategy_id} 执行失败，返回全量: {e}")

    conditions = []
    params = []

    # 概念板块筛选：JOIN dc_member 取最新一天成分股
    if concept_code:
        from_clause = """
            FROM stock_basic sb
            JOIN (
                SELECT DISTINCT con_code
                FROM dc_member
                WHERE ts_code = %s
                  AND trade_date = (SELECT MAX(trade_date) FROM dc_member WHERE ts_code = %s)
            ) dm ON sb.ts_code = dm.con_code
        """
        params.append(concept_code)
        params.append(concept_code)
        # concept_code JOIN 时所有列需要带 sb. 表别名
        def col(c): return f"sb.{c}"
    else:
        from_clause = "FROM stock_basic sb"
        def col(c): return f"sb.{c}"

    if list_status:
        conditions.append(f"{col('list_status')} = %s")
        params.append(list_status)

    if market:
        conditions.append(f"{col('market')} = %s")
        params.append(market)

    if exchange:
        conditions.append(f"{col('exchange')} = %s")
        params.append(exchange)

    if is_hs:
        conditions.append(f"{col('is_hs')} = %s")
        params.append(is_hs)

    if industry:
        conditions.append(f"{col('industry')} = %s")
        params.append(industry)

    if search:
        conditions.append(f"({col('code')} ILIKE %s OR {col('name')} ILIKE %s)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    # 选股策略过滤：WHERE sb.ts_code IN (...)
    if selection_ts_codes is not None:
        if selection_ts_codes:
            placeholders = ",".join(["%s"] * len(selection_ts_codes))
            conditions.append(f"{col('ts_code')} IN ({placeholders})")
            params.extend(selection_ts_codes)
        else:
            # 策略未选出任何股票，直接返回空
            return ApiResponse.success(data={
                'items': [],
                'total': 0,
                'strategy_name': selection_strategy_name,
            }).to_dict()

    # ts_codes 显式过滤（静默刷新场景：仅更新前端已显示的行）
    if ts_codes:
        ts_code_list = [c.strip().upper() for c in ts_codes.split(',') if c.strip()]
        if ts_code_list:
            placeholders = ",".join(["%s"] * len(ts_code_list))
            conditions.append(f"{col('ts_code')} IN ({placeholders})")
            params.extend(ts_code_list)
        else:
            return ApiResponse.success(data={'items': [], 'total': 0}).to_dict()

    # 自选列表过滤：JOIN user_stock_list_items
    if user_stock_list_id is not None:
        conditions.append(f"""
            {col('ts_code')} IN (
                SELECT ts_code FROM user_stock_list_items WHERE list_id = %s
            )
        """)
        params.append(user_stock_list_id)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 查询总数
    count_result = db._execute_query(
        f"SELECT COUNT(*) {from_clause} {where_clause}",
        tuple(params),
    )
    total = count_result[0][0] if count_result else 0

    # 排序逻辑（多列）：按用户指定优先级拼 ORDER BY，相同 join_group 只 JOIN 一次；
    # 始终追加 sb.code 兜底（避免相同排序值时分页跳行）
    parsed_sort = _parse_sort_param(sort, sort_by, sort_order)
    sort_join_parts: list = []
    sort_join_params: list = []
    order_parts: list = []
    used_groups: set = set()
    for key, direction in parsed_sort:
        spec = SORT_SPECS[key]
        group = spec["join_group"]
        if group and group not in used_groups:
            sort_join_parts.append(spec["join"])
            sort_join_params.extend(spec["params"])
            used_groups.add(group)
        order_parts.append(f"{spec['expr']} {direction} NULLS LAST")
    if not any(k == "code" for k, _ in parsed_sort):
        order_parts.append("sb.code")
    sort_join = "\n".join(sort_join_parts)
    order_clause = "ORDER BY " + ", ".join(order_parts)

    # 组装查询参数：SQL 结构为 FROM(+sort_join) WHERE LIMIT，需按出现顺序排列
    if concept_code:
        from_params = params[:2]
        where_params = params[2:]
    else:
        from_params = []
        where_params = params[:]

    query_params = from_params + sort_join_params + where_params + [limit, effective_offset]
    result = db._execute_query(
        f"""
        SELECT sb.code, sb.name, sb.ts_code, sb.fullname, sb.enname, sb.cnspell,
               sb.market, sb.exchange, sb.area, sb.industry, sb.curr_type,
               sb.list_status, sb.list_date, sb.delist_date, sb.is_hs,
               sb.act_name, sb.act_ent_type, sb.status
        {from_clause}
        {sort_join}
        {where_clause}
        {order_clause}
        LIMIT %s OFFSET %s
        """,
        tuple(query_params),
    )

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

    # 注入实时行情（latest_price, pct_change 等）
    if items:
        ts_codes = [item['ts_code'] for item in items if item.get('ts_code')]
        quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
        for item in items:
            quote = quotes.get(item['ts_code'], {})
            item['latest_price'] = quote.get('latest_price')
            item['pct_change'] = quote.get('pct_change')

    if include_analysis:
        items = await StockAiAnalysisService().enrich_stock_list_multi(items)

    response_data: dict = {'items': items, 'total': total}
    if selection_strategy_name is not None:
        response_data['strategy_name'] = selection_strategy_name
    return ApiResponse.success(data=response_data).to_dict()


@router.get("/statistics")
@handle_api_errors
async def get_statistics():
    """
    获取股票列表统计信息

    Returns:
        统计数据（总数、上市数、退市数、停牌数、沪深港通数、市场分布、交易所分布）
    """
    db = DatabaseManager()

    total_count = db._execute_query("SELECT COUNT(*) FROM stock_basic")[0][0]
    listed_count = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'")[0][0]
    delisted_count = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'D'")[0][0]
    suspended_count = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE list_status = 'P'")[0][0]
    hs_count = db._execute_query("SELECT COUNT(*) FROM stock_basic WHERE is_hs IN ('S', 'H')")[0][0]

    market_distribution = {
        row[0]: row[1]
        for row in db._execute_query("""
            SELECT market, COUNT(*)
            FROM stock_basic
            WHERE market IS NOT NULL AND market != ''
            GROUP BY market
        """)
    }

    exchange_distribution = {
        row[0]: row[1]
        for row in db._execute_query("""
            SELECT exchange, COUNT(*)
            FROM stock_basic
            WHERE exchange IS NOT NULL AND exchange != ''
            GROUP BY exchange
        """)
    }

    return ApiResponse.success(data={
        'total_count': total_count,
        'listed_count': listed_count,
        'delisted_count': delisted_count,
        'suspended_count': suspended_count,
        'hs_count': hs_count,
        'market_distribution': market_distribution,
        'exchange_distribution': exchange_distribution
    }).to_dict()


@router.post("/sync-async")
@handle_api_errors
async def sync_stock_list_async(
    list_status: Optional[str] = Query(None, description="上市状态筛选（为空则同步全部）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步股票列表数据（使用Celery）

    不传 list_status 参数，同步全部状态的股票。
    """
    from app.tasks.sync_tasks import sync_stock_list_task

    celery_task = sync_stock_list_task.delay()

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
