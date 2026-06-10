"""告警分析服务"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Alarm, AlarmRule, CompositeAlarmRule

logger = logging.getLogger(__name__)

# 不良原因分类映射（metric_name → 缺陷类别）
DEFECT_CATEGORY_MAP = {
    "temperature": "温度异常",
    "humidity": "湿度异常",
    "pressure": "压力异常",
    "speed": "速度异常",
    "seal_pressure": "密封压力异常",
    "gas_flow": "气体流量异常",
    "heater_temp": "加热温度异常",
    "rotation_speed": "转速异常",
}


def _classify_defect(metric_name: str) -> str:
    return DEFECT_CATEGORY_MAP.get(metric_name, f"其他异常({metric_name})")


async def evaluate_alarms(
    db: AsyncSession,
    redis,
    data_points: list[dict],
) -> list[dict]:
    """评估所有数据点是否触发告警（含单规则 + 组合规则）"""
    triggered_alarms: list[dict] = []

    # 获取所有活跃告警规则
    result = await db.execute(
        select(AlarmRule).where(AlarmRule.is_active == True)
    )
    rules = result.scalars().all()

    rule_map: dict[tuple[int, str], list[AlarmRule]] = {}
    for rule in rules:
        key = (rule.line_id, rule.metric_name)
        rule_map.setdefault(key, []).append(rule)

    # 收集本轮触发的度量点，用于组合规则判断
    triggered_points: set[tuple[int, str]] = set()

    for point in data_points:
        key = (point["line_id"], point["metric_name"])
        applicable_rules = rule_map.get(key, [])
        for rule in applicable_rules:
            triggered = False
            severity = rule.severity

            if rule.rule_type == "static":
                if rule.upper_limit is not None and point["metric_value"] > rule.upper_limit:
                    triggered = True
                if rule.lower_limit is not None and point["metric_value"] < rule.lower_limit:
                    triggered = True

            elif rule.rule_type == "dynamic_baseline":
                triggered, severity = await _check_dynamic_baseline(db, rule, point)

            if triggered:
                triggered_points.add(key)
                # 检查是否已有活跃告警（去重）
                dedup_key = f"alarm_active:{rule.id}:{point['line_id']}:{point['metric_name']}"
                is_active = await redis.get(dedup_key)
                if is_active:
                    continue

                await redis.set(dedup_key, "1", ex=300)  # 5分钟去重窗口，避免长时间无告警

                alarm = Alarm(
                    rule_id=rule.id,
                    line_id=point["line_id"],
                    station_id=point.get("station_id"),
                    metric_name=point["metric_name"],
                    actual_value=point["metric_value"],
                    expected_range=_format_expected_range(rule),
                    severity=severity,
                    defect_category=_classify_defect(point["metric_name"]),
                    message=f"[{rule.name}] {point['metric_name']}={point['metric_value']}{point.get('unit', '')} 触发告警 (阈值: {_format_expected_range(rule)})",
                    triggered_at=datetime.now(timezone.utc),
                )
                db.add(alarm)
                await db.flush()

                alarm_dict = {
                    "id": alarm.id,
                    "rule_id": alarm.rule_id,
                    "line_id": alarm.line_id,
                    "station_id": alarm.station_id,
                    "metric_name": alarm.metric_name,
                    "actual_value": alarm.actual_value,
                    "expected_range": alarm.expected_range,
                    "severity": alarm.severity,
                    "defect_category": alarm.defect_category,
                    "message": alarm.message,
                    "triggered_at": alarm.triggered_at.isoformat(),
                }
                triggered_alarms.append(alarm_dict)
                logger.warning("告警触发: %s", alarm.message)

    # ---- 组合规则联判 ----
    composite_result = await db.execute(
        select(CompositeAlarmRule).where(CompositeAlarmRule.is_active == True)
    )
    composite_rules = composite_result.scalars().all()

    for cr in composite_rules:
        child_ids = json.loads(cr.rule_ids) if isinstance(cr.rule_ids, str) else cr.rule_ids
        # 查找子规则对应的 (line_id, metric_name)
        child_result = await db.execute(
            select(AlarmRule)
            .where(AlarmRule.id.in_(child_ids))
            .where(AlarmRule.line_id == cr.line_id)
        )
        child_rules = child_result.scalars().all()
        child_keys = {(cr.line_id, r.metric_name) for r in child_rules}

        if _evaluate_composite(child_keys, triggered_points, cr.logic):
            dedup_key = f"composite_alarm_active:{cr.id}"
            is_active = await redis.get(dedup_key)
            if is_active:
                continue
            await redis.set(dedup_key, "1", ex=300)

            alarm = Alarm(
                rule_id=None,
                line_id=cr.line_id,
                metric_name="composite",
                actual_value=None,
                expected_range=f"组合规则: {cr.name}",
                severity=cr.composite_severity,
                defect_category="组合异常",
                message=f"[组合告警:{cr.name}] 多条件({cr.logic})同时触发",
                triggered_at=datetime.now(timezone.utc),
            )
            db.add(alarm)
            await db.flush()

            alarm_dict = {
                "id": alarm.id,
                "rule_id": None,
                "line_id": alarm.line_id,
                "station_id": None,
                "metric_name": "composite",
                "actual_value": None,
                "expected_range": f"组合规则: {cr.name}",
                "severity": cr.composite_severity,
                "defect_category": "组合异常",
                "message": alarm.message,
                "triggered_at": alarm.triggered_at.isoformat(),
            }
            triggered_alarms.append(alarm_dict)
            logger.warning("组合告警触发: %s", alarm.message)

    return triggered_alarms


def _evaluate_composite(
    child_keys: set[tuple[int, str]],
    triggered_points: set[tuple[int, str]],
    logic: str,
) -> bool:
    """判断组合规则是否触发"""
    if not child_keys:
        return False
    if logic.upper() == "AND":
        return child_keys.issubset(triggered_points)
    elif logic.upper() == "OR":
        return bool(child_keys & triggered_points)
    return False


async def _check_dynamic_baseline(db: AsyncSession, rule: AlarmRule, point: dict) -> tuple[bool, str]:
    """动态基线检测（兼容 SQLite 和 PostgreSQL）"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=rule.baseline_window)

    if settings.is_postgres:
        query = text("""
            SELECT AVG(metric_value), STDDEV(metric_value)
            FROM sensor_data
            WHERE line_id = :line_id
              AND metric_name = :metric_name
              AND time >= :cutoff
        """)
    else:
        # SQLite 没有 STDDEV，用 AVG 和 手动计算替代
        query = text("""
            SELECT AVG(metric_value) FROM sensor_data
            WHERE line_id = :line_id
              AND metric_name = :metric_name
              AND time >= :cutoff
        """)
    result = await db.execute(
        query,
        {"line_id": point["line_id"], "metric_name": point["metric_name"], "cutoff": cutoff},
    )
    row = result.fetchone()
    if row is None or row[0] is None:
        return False, rule.severity

    mean = row[0]
    dev = abs(point["metric_value"] - mean)

    # 简便方法：默认用均值的 10% 作为基准波动
    base_fluctuation = max(abs(mean) * 0.1, 0.1)
    threshold = rule.sigma_multiple * base_fluctuation

    if dev > threshold:
        ratio = dev / max(base_fluctuation, 0.01)
        if ratio > 5 * (rule.sigma_multiple or 3):
            severity = "emergency"
        elif ratio > 3 * (rule.sigma_multiple or 3):
            severity = "critical"
        else:
            severity = rule.severity
        return True, severity

    return False, rule.severity


def _format_expected_range(rule: AlarmRule) -> str:
    if rule.rule_type == "static":
        return f"[{rule.lower_limit or '-∞'}, {rule.upper_limit or '+∞'}]"
    return f"动态基线 ±{rule.sigma_multiple}σ"


async def get_alarms(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    line_id: int | None = None,
    status: str | None = None,
) -> tuple[list[Alarm], int]:
    """分页查询告警列表"""
    base_query = select(Alarm)
    count_query = select(func.count(Alarm.id))

    if line_id is not None:
        base_query = base_query.where(Alarm.line_id == line_id)
        count_query = count_query.where(Alarm.line_id == line_id)
    if status:
        base_query = base_query.where(Alarm.status == status)
        count_query = count_query.where(Alarm.status == status)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = base_query.order_by(Alarm.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alarms = result.scalars().all()

    return list(alarms), total


async def update_alarm_status(
    db: AsyncSession, redis, alarm_id: int, new_status: str
) -> Alarm | None:
    """更新告警状态"""
    result = await db.execute(select(Alarm).where(Alarm.id == alarm_id))
    alarm = result.scalar_one_or_none()
    if not alarm:
        return None

    alarm.status = new_status
    if new_status == "resolved":
        alarm.resolved_at = datetime.now(timezone.utc)
        if alarm.rule_id:
            dedup_key = f"alarm_active:{alarm.rule_id}:{alarm.line_id}:{alarm.metric_name}"
            await redis.delete(dedup_key)

    await db.flush()
    return alarm


async def get_defect_breakdown(
    db: AsyncSession, line_id: int | None = None, hours: int = 24
) -> list[dict]:
    """不良原因分类统计：按 defect_category 分组统计"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(
        Alarm.defect_category, func.count(Alarm.id)
    ).where(
        Alarm.triggered_at >= cutoff
    )
    if line_id is not None:
        query = query.where(Alarm.line_id == line_id)
    query = query.group_by(Alarm.defect_category)

    result = await db.execute(query)
    rows = result.all()

    total = sum(r[1] for r in rows if r[0] is not None)
    return [
        {
            "category": r[0] or "未分类",
            "count": r[1],
            "percentage": round(r[1] / max(total, 1) * 100, 1),
        }
        for r in rows
    ]


async def get_composite_rules(db: AsyncSession) -> list[CompositeAlarmRule]:
    result = await db.execute(select(CompositeAlarmRule).order_by(CompositeAlarmRule.id))
    return list(result.scalars().all())


async def create_composite_rule(db: AsyncSession, data: dict) -> CompositeAlarmRule:
    cr = CompositeAlarmRule(
        name=data["name"],
        line_id=data["line_id"],
        rule_ids=json.dumps(data["rule_ids"]),
        logic=data.get("logic", "AND"),
        composite_severity=data.get("composite_severity", "critical"),
        is_active=data.get("is_active", True),
    )
    db.add(cr)
    await db.flush()
    return cr


async def update_composite_rule(db: AsyncSession, rule_id: int, data: dict) -> CompositeAlarmRule | None:
    result = await db.execute(select(CompositeAlarmRule).where(CompositeAlarmRule.id == rule_id))
    cr = result.scalar_one_or_none()
    if not cr:
        return None
    for field in ["name", "logic", "composite_severity"]:
        if field in data and data[field] is not None:
            setattr(cr, field, data[field])
    if "rule_ids" in data and data["rule_ids"] is not None:
        cr.rule_ids = json.dumps(data["rule_ids"])
    if "is_active" in data and data["is_active"] is not None:
        cr.is_active = data["is_active"]
    await db.flush()
    return cr


async def delete_composite_rule(db: AsyncSession, rule_id: int) -> bool:
    result = await db.execute(select(CompositeAlarmRule).where(CompositeAlarmRule.id == rule_id))
    cr = result.scalar_one_or_none()
    if not cr:
        return False
    await db.delete(cr)
    await db.flush()
    return True
