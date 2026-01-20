"""
股票数据下载和查询API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date
from loguru import logger

from app.services import DatabaseService, DataDownloadService

router = APIRouter()


@router.get("/daily/{code}")
async def get_daily_data(
    code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    获取股票日线数据

    参数:
    - code: 股票代码
    - start_date: 开始日期
    - end_date: 结束日期

    返回:
    - 日线OHLCV数据
    """
    try:
        db_service = DatabaseService()
        df = db_service.get_daily_data(code, start_date, end_date)

        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"股票 {code} 无数据")

        # 重置索引，将date变为列
        df_reset = df.reset_index()

        return {
            "code": code,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(df),
            "data": df_reset.to_dict('records')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日线数据失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download")
async def download_data(
    codes: Optional[List[str]] = None,
    years: int = Query(5, ge=1, le=20, description="下载年数"),
    max_stocks: Optional[int] = Query(None, description="最大下载数量"),
    delay: float = Query(0.5, description="请求间隔（秒）")
):
    """
    下载股票数据

    参数:
    - codes: 股票代码列表（不指定则下载全部）
    - years: 下载年数
    - max_stocks: 最大下载数量
    - delay: 请求间隔

    返回:
    - 下载结果
    """
    try:
        data_service = DataDownloadService()

        logger.info(f"开始下载数据: years={years}, max_stocks={max_stocks}")

        result = await data_service.download_batch(
            codes=codes,
            years=years,
            max_stocks=max_stocks,
            delay=delay
        )

        return {
            "status": "completed",
            "message": f"下载完成: 成功 {result['success']}, 失败 {result['failed']}",
            **result
        }
    except Exception as e:
        logger.error(f"数据下载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/status/{task_id}")
async def get_download_status(task_id: str):
    """
    查询下载任务状态

    参数:
    - task_id: 任务ID

    返回:
    - 任务状态
    """
    try:
        # TODO: 查询任务状态
        return {
            "task_id": task_id,
            "status": "running",
            "progress": 45,
            "total": 100,
            "message": "正在下载第45只股票..."
        }
    except Exception as e:
        logger.error(f"查询下载状态失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
