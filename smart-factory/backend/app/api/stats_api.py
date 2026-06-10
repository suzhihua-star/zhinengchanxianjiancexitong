"""统计分析 API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.stats_service import get_oee_stats, get_yield_stats

router = APIRouter(prefix="/api/v1/stats", tags=["统计"])


@router.get("/oee")
async def oee(line_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """OEE 统计"""
    data = await get_oee_stats(db, line_id)
    return {"code": 0, "message": "success", "data": data}


@router.get("/yield")
async def yield_rate(line_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """良品率统计"""
    data = await get_yield_stats(db, line_id)
    return {"code": 0, "message": "success", "data": data}
