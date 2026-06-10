"""报表服务：日报 / 周报 / 月报自动生成"""
import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Alarm, ProductionLine, SensorData

logger = logging.getLogger(__name__)

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


async def generate_report(
    db: AsyncSession,
    report_type: str,
    line_id: int | None = None,
) -> dict:
    """生成报表（支持 daily/weekly/monthly）"""
    now = datetime.now(timezone.utc)

    if report_type == "daily":
        since = now - timedelta(days=1)
        label = "日报"
    elif report_type == "weekly":
        since = now - timedelta(weeks=1)
        label = "周报"
    elif report_type == "monthly":
        since = now - timedelta(days=30)
        label = "月报"
    else:
        raise ValueError(f"不支持的报表类型: {report_type}")

    type_map = {"daily": "日报", "weekly": "周报", "monthly": "月报"}

    # ---- 数据概览 ----
    base_where = [f"time >= '{since.isoformat()}'"]
    if line_id is not None:
        base_where.append(f"line_id = {line_id}")

    where_clause = " AND ".join(base_where)

    # 总数据量
    count_query = text(f"SELECT COUNT(*) FROM sensor_data WHERE {where_clause}")
    result = await db.execute(count_query)
    total_count = result.scalar() or 0

    # 产线概览
    if line_id is None:
        lines_result = await db.execute(select(ProductionLine))
        lines = lines_result.scalars().all()
    else:
        lines_result = await db.execute(select(ProductionLine).where(ProductionLine.id == line_id))
        lines = lines_result.scalars().all()

    line_summaries = []
    for line in lines:
        lw = base_where.copy()
        for i, w in enumerate(lw):
            if w.startswith("line_id ="):
                lw[i] = f"line_id = {line.id}"
            else:
                break

        # 各指标统计
        metric_query = text(f"""
            SELECT metric_name,
                   AVG(metric_value) AS avg_val,
                   MIN(metric_value) AS min_val,
                   MAX(metric_value) AS max_val,
                   COUNT(*) AS cnt
            FROM sensor_data
            WHERE {' AND '.join(lw)}
            GROUP BY metric_name
        """)
        result = await db.execute(metric_query)
        metrics = [
            {"name": row[0], "avg": round(row[1], 2) if row[1] else None,
             "min": round(row[2], 2) if row[2] else None,
             "max": round(row[3], 2) if row[3] else None, "count": row[4]}
            for row in result.fetchall()
        ]

        # 告警统计
        alarm_query = text(f"""
            SELECT severity, COUNT(*) AS cnt
            FROM alarms
            WHERE line_id = {line.id}
              AND triggered_at >= '{since.isoformat()}'
            GROUP BY severity
        """)
        result = await db.execute(alarm_query)
        alarms_by_severity = {row[0]: row[1] for row in result.fetchall()}

        line_summaries.append({
            "line_id": line.id,
            "line_name": line.name,
            "metrics": metrics,
            "alarms": alarms_by_severity,
        })

    report = {
        "report_type": report_type,
        "report_label": type_map.get(report_type, label),
        "generated_at": now.isoformat(),
        "period": {"from": since.isoformat(), "to": now.isoformat()},
        "total_data_points": total_count,
        "line_summaries": line_summaries,
    }

    # 保存 JSON 文件
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_id = f"{report_type}_{now.strftime('%Y%m%d_%H%M%S')}"
    json_path = os.path.join(REPORT_DIR, f"{report_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("报表已生成: %s", report_id)
    return {"report_id": report_id, "content": report, "file_url": f"/reports/{report_id}.json"}


async def generate_csv_report(
    db: AsyncSession,
    report_type: str,
    line_id: int | None = None,
) -> bytes:
    """生成 CSV 格式报表"""
    now = datetime.now(timezone.utc)

    if report_type == "daily":
        since = now - timedelta(days=1)
    elif report_type == "weekly":
        since = now - timedelta(weeks=1)
    elif report_type == "monthly":
        since = now - timedelta(days=30)
    else:
        raise ValueError(f"不支持的报表类型: {report_type}")

    base_where = [f"s.time >= '{since.isoformat()}'"]
    if line_id is not None:
        base_where.append(f"s.line_id = {line_id}")
    where_clause = " AND ".join(base_where)

    query = text(f"""
        SELECT s.time, p.name AS line_name, s.metric_name,
               s.metric_value, s.unit
        FROM sensor_data s
        LEFT JOIN production_lines p ON s.line_id = p.id
        WHERE {where_clause}
        ORDER BY s.time DESC
        LIMIT 10000
    """)
    result = await db.execute(query)
    rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "产线", "指标", "值", "单位"])
    for row in rows:
        writer.writerow(row)

    return output.getvalue().encode("utf-8-sig")
