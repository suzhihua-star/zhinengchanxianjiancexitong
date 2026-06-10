"""统计分析服务"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import SensorData


async def get_oee_stats(db: AsyncSession, line_id: int) -> dict:
    """OEE 统计（简化版）"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    q = (
        select(func.count(SensorData.id))
        .where(
            SensorData.line_id == line_id,
            SensorData.time >= cutoff,
            SensorData.metric_name == "speed",
            SensorData.metric_value > 0,
        )
    )
    total_q = (
        select(func.count(SensorData.id))
        .where(
            SensorData.line_id == line_id,
            SensorData.time >= cutoff,
            SensorData.metric_name == "speed",
        )
    )
    avail_result = await db.execute(q)
    total_result = await db.execute(total_q)
    avail = avail_result.scalar() or 0
    total = total_result.scalar() or 1
    availability = round(avail / max(total, 1), 4)
    performance = 0.85
    quality = 0.95
    oee = round(availability * performance * quality, 4)
    return {
        "line_id": line_id,
        "line_name": "",
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "oee": oee,
    }


async def get_yield_stats(db: AsyncSession, line_id: int) -> dict:
    """良品率统计"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cnt_q = (
        select(func.count(SensorData.id))
        .where(SensorData.line_id == line_id, SensorData.time >= cutoff)
    )
    result = await db.execute(cnt_q)
    total = result.scalar() or 0
    good = total  # 简化：全部计为良品
    defect = 0
    rate = round(good / max(total, 1), 4)
    return {
        "line_id": line_id,
        "line_name": "",
        "total_count": total,
        "good_count": good,
        "defect_count": defect,
        "yield_rate": rate,
    }
