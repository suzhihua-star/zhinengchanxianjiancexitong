"""Pydantic 请求/响应 Schema"""
import json as _json
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ========== 传感器数据 ==========
class SensorDataPoint(BaseModel):
    line_id: int
    station_id: int | None = None
    metric_name: str
    metric_value: float
    unit: str | None = None
    time: datetime | None = None


class SensorDataIngestRequest(BaseModel):
    data: list[SensorDataPoint]


class SensorDataResponse(BaseModel):
    id: int
    time: datetime
    line_id: int
    station_id: int | None
    metric_name: str
    metric_value: float
    unit: str | None

    class Config:
        from_attributes = True


class LatestDataResponse(BaseModel):
    line_id: int
    station_id: int | None
    metric_name: str
    metric_value: float
    unit: str | None
    time: datetime


# ========== 产线/工位 ==========
class WorkStationResponse(BaseModel):
    id: int
    line_id: int
    name: str
    code: str
    sort_order: int

    class Config:
        from_attributes = True


class ProductionLineResponse(BaseModel):
    id: int
    name: str
    code: str
    status: str
    stations: list[WorkStationResponse] = []

    class Config:
        from_attributes = True


# ========== 告警规则 ==========
class AlarmRuleCreate(BaseModel):
    name: str
    line_id: int
    metric_name: str
    rule_type: str  # static / dynamic_baseline
    upper_limit: float | None = None
    lower_limit: float | None = None
    baseline_window: int = 60
    sigma_multiple: float = 3.0
    severity: str = "warning"
    is_active: bool = True


class AlarmRuleUpdate(BaseModel):
    name: str | None = None
    rule_type: str | None = None
    upper_limit: float | None = None
    lower_limit: float | None = None
    baseline_window: int | None = None
    sigma_multiple: float | None = None
    severity: str | None = None
    is_active: bool | None = None


class AlarmRuleResponse(BaseModel):
    id: int
    name: str
    line_id: int
    metric_name: str
    rule_type: str
    upper_limit: float | None
    lower_limit: float | None
    baseline_window: int
    sigma_multiple: float
    severity: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 告警记录 ==========
class AlarmResponse(BaseModel):
    id: int
    rule_id: int | None
    line_id: int
    station_id: int | None
    metric_name: str
    actual_value: float | None
    expected_range: str | None
    severity: str
    message: str | None
    status: str
    defect_category: str | None = None
    triggered_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class PaginatedAlarms(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AlarmResponse]


# ========== 统计 ==========
class OEEStats(BaseModel):
    line_id: int
    line_name: str
    availability: float = 0.0
    performance: float = 0.0
    quality: float = 0.0
    oee: float = 0.0


class YieldStats(BaseModel):
    line_id: int
    line_name: str
    total_count: int = 0
    good_count: int = 0
    defect_count: int = 0
    yield_rate: float = 0.0


# ========== 不良原因分类统计 ==========
class DefectCategoryItem(BaseModel):
    category: str
    count: int
    percentage: float


class DefectBreakdownResponse(BaseModel):
    line_id: int
    line_name: str
    total_defects: int
    categories: list[DefectCategoryItem]


# ========== 组合告警规则 ==========
class CompositeAlarmRuleCreate(BaseModel):
    name: str
    line_id: int
    rule_ids: list[int]
    logic: str = "AND"  # AND / OR
    composite_severity: str = "critical"
    is_active: bool = True


class CompositeAlarmRuleUpdate(BaseModel):
    name: str | None = None
    rule_ids: list[int] | None = None
    logic: str | None = None
    composite_severity: str | None = None
    is_active: bool | None = None


class CompositeAlarmRuleResponse(BaseModel):
    id: int
    name: str
    line_id: int
    rule_ids: list[int]
    logic: str
    composite_severity: str
    is_active: bool
    created_at: datetime

    @field_validator("rule_ids", mode="before")
    @classmethod
    def parse_rule_ids(cls, v):
        if isinstance(v, str):
            return _json.loads(v)
        return v

    class Config:
        from_attributes = True


# ========== 报表 ==========
class ReportRequest(BaseModel):
    report_type: str  # daily / weekly / monthly
    line_id: int | None = None


class ReportResponse(BaseModel):
    report_id: str
    report_type: str
    line_id: int | None
    generated_at: datetime
    content: dict
    file_url: str | None = None


# ========== 对比趋势 ==========
class ComparisonTrendRequest(BaseModel):
    line_ids: list[int]
    metric_name: str
    minutes: int = 60


# ========== ML 接口预留 ==========
class MLPredictRequest(BaseModel):
    line_id: int
    metric_name: str
    lookback_minutes: int = 60


class MLPredictResponse(BaseModel):
    line_id: int
    metric_name: str
    predicted_at: datetime
    future_values: list[dict] = []
    anomaly_score: float | None = None
    message: str = "ML 模型接口已预留，待后续集成具体模型"


# ========== 通用响应 ==========
class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: object = None
