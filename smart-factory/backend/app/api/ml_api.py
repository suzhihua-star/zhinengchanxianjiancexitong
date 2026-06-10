"""ML/AI API 路由 — 预留接口"""
from fastapi import APIRouter, Query

from app.schemas import MLPredictRequest
from app.services.ml_service import detect_anomalies, get_model_status, predict

router = APIRouter(prefix="/api/v1/ml", tags=["ML/AI"])


@router.post("/predict")
async def ml_predict(req: MLPredictRequest):
    """AI 预测接口（预留）"""
    result = await predict(req.line_id, req.metric_name, req.lookback_minutes)
    return {"code": 0, "message": "success", "data": result}


@router.get("/anomaly-detect")
async def ml_anomaly_detect(
    line_id: int = Query(...),
    metric_name: str = Query(...),
    lookback_minutes: int = Query(60, ge=1, le=1440),
):
    """AI 异常检测接口（预留）"""
    result = await detect_anomalies(line_id, metric_name, lookback_minutes)
    return {"code": 0, "message": "success", "data": result}


@router.get("/models")
async def ml_models():
    """已部署模型列表"""
    result = await get_model_status()
    return {"code": 0, "message": "success", "data": result}
