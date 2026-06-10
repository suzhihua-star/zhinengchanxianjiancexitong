"""数据 API 路由"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import ComparisonTrendRequest
from app.services.data_service import (
    get_comparison_trend,
    get_history,
    get_latest_data,
    get_minute_aggregation,
)

router = APIRouter(prefix="/api/v1/data", tags=["数据"])
# 注: POST /api/v1/data/ingest 由 main.py 的 ingest_data_full 统一处理
# （含 存储 + 告警评估 + WebSocket 广播），此处不再重复注册


@router.get("/latest")
async def latest_data(
    line_id: int | None = Query(None, description="产线ID，不传则返回全部"),
    db: AsyncSession = Depends(get_db),
):
    """获取最新传感器值"""
    data = await get_latest_data(db, line_id)
    return {"code": 0, "message": "success", "data": data}


@router.get("/history")
async def history_data(
    line_id: int | None = Query(None),
    metric_name: str | None = Query(None),
    start_time: str | None = Query(None, description="ISO8601 开始时间"),
    end_time: str | None = Query(None, description="ISO8601 结束时间"),
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """历史数据查询"""
    start = datetime.fromisoformat(start_time) if start_time else None
    end = datetime.fromisoformat(end_time) if end_time else None
    data = await get_history(db, line_id, metric_name, start, end, limit)
    return {"code": 0, "message": "success", "data": data}


@router.get("/trend")
async def trend_data(
    line_id: int = Query(...),
    metric_name: str = Query(...),
    minutes: int = Query(60, ge=1, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """趋势数据（分钟级聚合）"""
    data = await get_minute_aggregation(db, line_id, metric_name, minutes)
    return {"code": 0, "message": "success", "data": data}


@router.post("/comparison")
async def comparison_trend(
    req: ComparisonTrendRequest,
    db: AsyncSession = Depends(get_db),
):
    """多产线对比趋势"""
    data = await get_comparison_trend(db, req.line_ids, req.metric_name, req.minutes)
    return {"code": 0, "message": "success", "data": data}
