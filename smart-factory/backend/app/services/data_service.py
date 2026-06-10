"""数据处理服务"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import SensorData


async def ingest_sensor_data(db: AsyncSession, data: list[dict]) -> list[SensorData]:
    """批量写入传感器数据"""
    records = [
        SensorData(
            time=item.get("time") or datetime.now(timezone.utc),
            line_id=item["line_id"],
            station_id=item.get("station_id"),
            metric_name=item["metric_name"],
            metric_value=item["metric_value"],
            unit=item.get("unit"),
        )
        for item in data
    ]
    db.add_all(records)
    await db.flush()
    return records


async def get_latest_data(db: AsyncSession, line_id: int | None = None) -> list[dict]:
    """获取各指标最新值"""
    # 子查询：每组最大 time
    subq = (
        select(
            SensorData.line_id,
            func.coalesce(SensorData.station_id, 0).label("station_key"),
            SensorData.metric_name,
            func.max(SensorData.time).label("max_time"),
        )
        .group_by(
            SensorData.line_id,
            func.coalesce(SensorData.station_id, 0),
            SensorData.metric_name,
        )
    )
    if line_id is not None:
        subq = subq.where(SensorData.line_id == line_id)
    subq = subq.subquery()

    query = select(SensorData).join(
        subq,
        (SensorData.line_id == subq.c.line_id)
        & (func.coalesce(SensorData.station_id, 0) == subq.c.station_key)
        & (SensorData.metric_name == subq.c.metric_name)
        & (SensorData.time == subq.c.max_time),
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        {
            "line_id": r.line_id,
            "station_id": r.station_id,
            "metric_name": r.metric_name,
            "metric_value": r.metric_value,
            "unit": r.unit,
            "time": r.time.isoformat(),
        }
        for r in rows
    ]


async def get_history(
    db: AsyncSession,
    line_id: int | None = None,
    metric_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 500,
) -> list[dict]:
    """查询历史数据"""
    query = select(SensorData).order_by(SensorData.time.desc()).limit(limit)
    if line_id is not None:
        query = query.where(SensorData.line_id == line_id)
    if metric_name:
        query = query.where(SensorData.metric_name == metric_name)
    if start_time:
        query = query.where(SensorData.time >= start_time)
    if end_time:
        query = query.where(SensorData.time <= end_time)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "time": r.time.isoformat(),
            "line_id": r.line_id,
            "station_id": r.station_id,
            "metric_name": r.metric_name,
            "metric_value": r.metric_value,
            "unit": r.unit,
        }
        for r in rows
    ]


async def get_minute_aggregation(
    db: AsyncSession,
    line_id: int,
    metric_name: str,
    minutes: int = 60,
) -> list[dict]:
    """分钟级聚合查询（兼容 SQLite 和 PostgreSQL）"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    if settings.is_postgres:
        query = text("""
            SELECT
                date_trunc('minute', time) AS bucket,
                AVG(metric_value) AS avg_value,
                MIN(metric_value) AS min_value,
                MAX(metric_value) AS max_value
            FROM sensor_data
            WHERE line_id = :line_id
              AND metric_name = :metric_name
              AND time >= :cutoff
            GROUP BY bucket
            ORDER BY bucket ASC
        """)
    else:
        query = text("""
            SELECT
                strftime('%Y-%m-%d %H:%M:00', time) AS bucket,
                AVG(metric_value) AS avg_value,
                MIN(metric_value) AS min_value,
                MAX(metric_value) AS max_value
            FROM sensor_data
            WHERE line_id = :line_id
              AND metric_name = :metric_name
              AND time >= :cutoff
            GROUP BY bucket
            ORDER BY bucket ASC
        """)
    result = await db.execute(
        query, {"line_id": line_id, "metric_name": metric_name, "cutoff": cutoff}
    )
    rows = result.fetchall()
    return [
        {
            "time": row[0] if isinstance(row[0], str) else (row[0].isoformat() if row[0] else None),
            "avg": round(row[1], 2) if row[1] else None,
            "min": round(row[2], 2) if row[2] else None,
            "max": round(row[3], 2) if row[3] else None,
        }
        for row in rows
        if row[0] is not None
    ]


async def get_comparison_trend(
    db: AsyncSession,
    line_ids: list[int],
    metric_name: str,
    minutes: int = 60,
) -> list[dict]:
    """多产线对比趋势查询"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    if settings.is_postgres:
        query = text("""
            SELECT
                line_id,
                date_trunc('minute', time) AS bucket,
                AVG(metric_value) AS avg_value
            FROM sensor_data
            WHERE line_id = ANY(:line_ids)
              AND metric_name = :metric_name
              AND time >= :cutoff
            GROUP BY line_id, bucket
            ORDER BY bucket ASC
        """)
    else:
        # SQLite: 用 IN 替代 ANY
        placeholders = ",".join(str(lid) for lid in line_ids)
        query = text(f"""
            SELECT
                line_id,
                strftime('%Y-%m-%d %H:%M:00', time) AS bucket,
                AVG(metric_value) AS avg_value
            FROM sensor_data
            WHERE line_id IN ({placeholders})
              AND metric_name = :metric_name
              AND time >= :cutoff
            GROUP BY line_id, bucket
            ORDER BY bucket ASC
        """)
    result = await db.execute(
        query, {"line_ids": line_ids, "metric_name": metric_name, "cutoff": cutoff}
    )
    rows = result.fetchall()

    # 按产线分组聚合
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        lid = row[0]
        t = row[1] if isinstance(row[1], str) else (row[1].isoformat() if row[1] else None)
        grouped.setdefault(lid, []).append({
            "time": t,
            "avg": round(row[2], 2) if row[2] else None,
        })

    return [
        {"line_id": lid, "metric_name": metric_name, "data_points": points}
        for lid, points in grouped.items()
    ]
