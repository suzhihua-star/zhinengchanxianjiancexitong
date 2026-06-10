"""产线与工位 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import ProductionLine, WorkStation
from app.schemas import ProductionLineResponse, WorkStationResponse

router = APIRouter(prefix="/api/v1", tags=["产线"])


@router.get("/lines")
async def list_lines(db: AsyncSession = Depends(get_db)):
    """产线列表"""
    result = await db.execute(
        select(ProductionLine).options(selectinload(ProductionLine.stations)).order_by(ProductionLine.id)
    )
    lines = result.scalars().all()
    return {
        "code": 0,
        "message": "success",
        "data": [ProductionLineResponse.model_validate(line).model_dump(mode="json") for line in lines],
    }


@router.get("/lines/{line_id}/stations")
async def list_stations(line_id: int, db: AsyncSession = Depends(get_db)):
    """工位列表"""
    result = await db.execute(
        select(WorkStation)
        .where(WorkStation.line_id == line_id)
        .order_by(WorkStation.sort_order)
    )
    stations = result.scalars().all()
    return {
        "code": 0,
        "message": "success",
        "data": [WorkStationResponse.model_validate(s).model_dump(mode="json") for s in stations],
    }
