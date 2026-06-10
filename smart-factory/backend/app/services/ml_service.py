"""ML/AI 模型接口预留服务

本模块定义了 AI 异常检测的接口规范，为未来集成具体模型（如 LSTM、Isolation Forest、
AutoEncoder 等）做好准备。当前返回占位响应，不会阻塞系统运行。

使用方式：
    1. 将训练好的模型放在 backend/ml_models/ 目录下
    2. 在此文件中实现具体的 predict 和 train 逻辑
    3. 模型文件通过 mlflow / pickle / ONNX 等格式加载
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MLModelInterface:
    """ML 模型接口抽象类 — 未来模型需实现此接口"""

    async def predict(self, line_id: int, metric_name: str, lookback_minutes: int = 60) -> dict:
        """时序预测：给出未来 N 分钟内的预测值序列"""
        raise NotImplementedError

    async def detect_anomalies(self, line_id: int, metric_name: str, lookback_minutes: int = 60) -> dict:
        """异常检测：返回异常分数及是否异常的判断"""
        raise NotImplementedError

    async def train(self, line_id: int, metric_name: str) -> dict:
        """模型训练/重训练"""
        raise NotImplementedError


async def predict(
    line_id: int,
    metric_name: str,
    lookback_minutes: int = 60,
) -> dict:
    """ML 预测接口（占位实现）

    Returns:
        dict: 包含占位预测值、预测时间和状态说明
    """
    logger.info(
        "[ML] 收到预测请求 line_id=%s metric=%s lookback=%dmin — 模型未部署，返回占位",
        line_id, metric_name, lookback_minutes,
    )
    now = datetime.now(timezone.utc)

    # 占位：返回最近均值作为"预测"基线
    return {
        "line_id": line_id,
        "metric_name": metric_name,
        "predicted_at": now.isoformat(),
        "future_values": [
            {"time": f"+{i}min", "predicted_value": None, "confidence_interval": None}
            for i in range(5, 35, 5)
        ],
        "anomaly_score": None,
        "message": "ML 模型接口已预留，请部署具体模型文件后启用预测功能",
    }


async def detect_anomalies(
    line_id: int,
    metric_name: str,
    lookback_minutes: int = 60,
) -> dict:
    """AI 异常检测接口（占位实现）"""
    logger.info(
        "[ML] 收到异常检测请求 line_id=%s metric=%s — 模型未部署，返回占位",
        line_id, metric_name,
    )
    return {
        "line_id": line_id,
        "metric_name": metric_name,
        "lookback_minutes": lookback_minutes,
        "anomaly_score": None,
        "is_anomaly": False,
        "message": "AI 异常检测模型未部署，当前使用静态阈值 + 动态基线方案",
    }


async def get_model_status() -> dict:
    """查询已部署模型状态"""
    return {
        "models_deployed": [],
        "framework": "预留接口",
        "deployment_path": "backend/ml_models/",
        "message": "ML 模型目录已预留，当前系统使用规则引擎进行异常检测",
    }
