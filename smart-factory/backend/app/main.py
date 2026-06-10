"""智能检测工厂产线系统 - FastAPI 主入口"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.alarm_api import router as alarm_router
from app.api.data_api import router as data_router
from app.api.line_api import router as line_router
from app.api.ml_api import router as ml_router
from app.api.report_api import router as report_router
from app.api.stats_api import router as stats_router
from app.api.ws_api import broadcast
from app.core.config import settings
from app.core.database import engine, init_db
from app.core.redis_dep import close_redis, get_redis
from app.models import AlarmRule, ProductionLine, WorkStation
from app.schemas import SensorDataIngestRequest
from app.services.alarm_service import evaluate_alarms
from app.services.data_service import ingest_sensor_data

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动 %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # 初始化数据库表
    await init_db()
    logger.info("数据库表初始化完成")

    # 初始化 Redis
    redis = await get_redis()
    await redis.ping()
    logger.info("Redis 连接成功")

    # 初始化种子数据（产线+工位）
    await seed_data()
    logger.info("种子数据初始化完成")

    yield

    # 清理
    await close_redis()
    await engine.dispose()
    logger.info("%s 已关闭", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(data_router)
app.include_router(alarm_router)
app.include_router(line_router)
app.include_router(stats_router)
app.include_router(report_router)
app.include_router(ml_router)

# 注册 WebSocket 路由（必须最后注册才能拦截到 /ws/live）
from app.api.ws_api import router as ws_router
app.include_router(ws_router)


# ---- 重写 data ingest 端点，整合告警分析和 WebSocket 广播 ----
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis_dep import FakeRedis, get_redis


@app.post("/api/v1/data/ingest", tags=["数据"])
async def ingest_data_full(
    req: SensorDataIngestRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """接收传感器数据 -> 存储 -> 告警分析 -> WebSocket 广播"""
    data_dicts = [item.model_dump(exclude_none=True) for item in req.data]

    # 1. 写入数据库
    records = await ingest_sensor_data(db, data_dicts)

    # 2. 告警分析
    new_alarms = await evaluate_alarms(db, redis, data_dicts)

    # 3. WebSocket 广播传感器数据（将 datetime 转为 ISO 字符串）
    safe_data = []
    for d in data_dicts:
        sd = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in d.items()}
        safe_data.append(sd)
    await broadcast({"type": "sensor_data", "data": safe_data})

    # 4. WebSocket 广播告警事件
    for alarm in new_alarms:
        await broadcast({"type": "alarm_event", "data": alarm})

    return {
        "code": 0,
        "message": "success",
        "data": {
            "saved": len(records),
            "alarms_triggered": len(new_alarms),
        },
    }


async def seed_data() -> None:
    """种子数据：3条产线 + 对应工位 + 默认告警规则"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import async_session

    lines_config = [
        {
            "name": "包装产线 A",
            "code": "LINE-A",
            "stations": ["上料工位", "热封工位", "检测工位", "喷码工位", "装箱工位"],
        },
        {
            "name": "充填包装线 B",
            "code": "LINE-B",
            "stations": ["上料工位", "充填工位", "热封工位", "检测工位"],
        },
        {
            "name": "成型包装线 C",
            "code": "LINE-C",
            "stations": ["上料工位", "成型工位", "热封工位", "冷却工位", "检测工位"],
        },
    ]

    # 默认告警规则：覆盖 4 种指标 × 3 条产线
    # 阈值根据模拟器基准值设定（temperature~150, humidity~45, pressure~0.75, speed~1.2）
    default_rules = [
        # 静态阈值规则（所有产线通用）
        ("温度_上限", "temperature", "static", None, 175.0, None, None, "warning"),
        ("温度_下限", "temperature", "static", 125.0, None, None, None, "critical"),
        ("温度_动态基线", "temperature", "dynamic_baseline", None, None, 60, 2.5, "critical"),
        ("湿度_上限", "humidity", "static", None, 62.0, None, None, "warning"),
        ("湿度_下限", "humidity", "static", 32.0, None, None, None, "warning"),
        ("压力_上限", "pressure", "static", None, 0.92, None, None, "warning"),
        ("压力_下限", "pressure", "static", 0.52, None, None, None, "critical"),
        ("速度_上限", "speed", "static", None, 1.45, None, None, "warning"),
        ("速度_下限", "speed", "static", 0.75, None, None, None, "warning"),
    ]

    async with async_session() as session:
        from sqlalchemy import select

        # 检查是否已有数据
        result = await session.execute(select(ProductionLine).limit(1))
        if result.first():
            return  # 已初始化

        for line_cfg in lines_config:
            line = ProductionLine(name=line_cfg["name"], code=line_cfg["code"])
            session.add(line)
            await session.flush()

            for order, station_name in enumerate(line_cfg["stations"]):
                station = WorkStation(
                    line_id=line.id,
                    name=station_name,
                    code=f"{line_cfg['code']}-S{order+1}",
                    sort_order=order + 1,
                )
                session.add(station)

            # 为每条产线创建默认告警规则
            for name, metric, rtype, low, high, bw, sigma, sev in default_rules:
                rule = AlarmRule(
                    name=f"{line_cfg['code']}_{name}",
                    line_id=line.id,
                    metric_name=metric,
                    rule_type=rtype,
                    lower_limit=low,
                    upper_limit=high,
                    baseline_window=bw,
                    sigma_multiple=sigma,
                    severity=sev,
                    is_active=True,
                )
                session.add(rule)

        await session.commit()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
