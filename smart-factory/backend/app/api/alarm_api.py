"""告警管理 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_dep import get_redis
from app.models import Alarm, AlarmRule
from app.schemas import (
    AlarmRuleCreate,
    AlarmRuleResponse,
    AlarmRuleUpdate,
    AlarmResponse,
    CompositeAlarmRuleCreate,
    CompositeAlarmRuleResponse,
    CompositeAlarmRuleUpdate,
    PaginatedAlarms,
)
from app.services.alarm_service import (
    create_composite_rule,
    delete_composite_rule,
    get_alarms,
    get_composite_rules,
    get_defect_breakdown,
    update_alarm_status,
    update_composite_rule,
)

router = APIRouter(prefix="/api/v1/alarms", tags=["告警"])


@router.get("/rules", response_model=dict)
async def list_rules(db: AsyncSession = Depends(get_db)):
    """告警规则列表"""
    result = await db.execute(select(AlarmRule).order_by(AlarmRule.id))
    rules = result.scalars().all()
    return {
        "code": 0,
        "message": "success",
        "data": [AlarmRuleResponse.model_validate(r).model_dump(mode="json") for r in rules],
    }


@router.post("/rules")
async def create_rule(req: AlarmRuleCreate, db: AsyncSession = Depends(get_db)):
    """创建告警规则"""
    rule = AlarmRule(**req.model_dump())
    db.add(rule)
    await db.flush()
    return {"code": 0, "message": "success", "data": AlarmRuleResponse.model_validate(rule).model_dump(mode="json")}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, req: AlarmRuleUpdate, db: AsyncSession = Depends(get_db)):
    """更新告警规则"""
    result = await db.execute(select(AlarmRule).where(AlarmRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "告警规则不存在")
    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    await db.flush()
    return {"code": 0, "message": "success", "data": AlarmRuleResponse.model_validate(rule).model_dump(mode="json")}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """删除告警规则"""
    result = await db.execute(select(AlarmRule).where(AlarmRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "告警规则不存在")
    await db.delete(rule)
    await db.flush()
    return {"code": 0, "message": "success", "data": None}


@router.get("")
async def list_alarms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    line_id: int | None = Query(None),
    status: str | None = Query(None, description="unconfirmed / confirmed / resolved"),
    db: AsyncSession = Depends(get_db),
):
    """告警记录列表（分页）"""
    alarms, total = await get_alarms(db, page, page_size, line_id, status)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [AlarmResponse.model_validate(a).model_dump(mode="json") for a in alarms],
        },
    }


@router.put("/{alarm_id}/confirm")
async def confirm_alarm(alarm_id: int, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)):
    """确认告警"""
    alarm = await update_alarm_status(db, redis, alarm_id, "confirmed")
    if not alarm:
        raise HTTPException(404, "告警记录不存在")
    return {"code": 0, "message": "success", "data": AlarmResponse.model_validate(alarm).model_dump(mode="json")}


@router.put("/{alarm_id}/resolve")
async def resolve_alarm(alarm_id: int, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)):
    """关闭告警"""
    alarm = await update_alarm_status(db, redis, alarm_id, "resolved")
    if not alarm:
        raise HTTPException(404, "告警记录不存在")
    return {"code": 0, "message": "success", "data": AlarmResponse.model_validate(alarm).model_dump(mode="json")}


# ========== 组合规则 CRUD ==========
@router.get("/composite-rules")
async def list_composite_rules(db: AsyncSession = Depends(get_db)):
    """组合告警规则列表"""
    rules = await get_composite_rules(db)
    items = []
    for r in rules:
        d = CompositeAlarmRuleResponse.model_validate(r).model_dump(mode="json")
        import json
        d["rule_ids"] = json.loads(r.rule_ids) if isinstance(r.rule_ids, str) else r.rule_ids
        items.append(d)
    return {"code": 0, "message": "success", "data": items}


@router.post("/composite-rules")
async def create_composite(req: CompositeAlarmRuleCreate, db: AsyncSession = Depends(get_db)):
    """创建组合告警规则"""
    cr = await create_composite_rule(db, req.model_dump())
    import json
    d = CompositeAlarmRuleResponse.model_validate(cr).model_dump(mode="json")
    d["rule_ids"] = json.loads(cr.rule_ids) if isinstance(cr.rule_ids, str) else cr.rule_ids
    return {"code": 0, "message": "success", "data": d}


@router.put("/composite-rules/{rule_id}")
async def update_composite(rule_id: int, req: CompositeAlarmRuleUpdate, db: AsyncSession = Depends(get_db)):
    """更新组合告警规则"""
    cr = await update_composite_rule(db, rule_id, req.model_dump(exclude_none=True))
    if not cr:
        raise HTTPException(404, "组合规则不存在")
    import json
    d = CompositeAlarmRuleResponse.model_validate(cr).model_dump(mode="json")
    d["rule_ids"] = json.loads(cr.rule_ids) if isinstance(cr.rule_ids, str) else cr.rule_ids
    return {"code": 0, "message": "success", "data": d}


@router.delete("/composite-rules/{rule_id}")
async def remove_composite(rule_id: int, db: AsyncSession = Depends(get_db)):
    """删除组合告警规则"""
    ok = await delete_composite_rule(db, rule_id)
    if not ok:
        raise HTTPException(404, "组合规则不存在")
    return {"code": 0, "message": "success", "data": None}


# ========== 缺陷分析 ==========
@router.get("/defect-breakdown")
async def defect_breakdown(
    line_id: int | None = Query(None),
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    """不良原因分类统计"""
    categories = await get_defect_breakdown(db, line_id, hours)
    total = sum(c["count"] for c in categories)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "line_id": line_id,
            "total_defects": total,
            "hours": hours,
            "categories": categories,
        },
    }
