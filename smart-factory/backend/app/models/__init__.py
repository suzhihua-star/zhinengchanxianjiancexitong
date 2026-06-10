"""数据库 ORM 模型"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ProductionLine(Base):
    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    stations: Mapped[list["WorkStation"]] = relationship(back_populates="line", lazy="selectin")
    alarm_rules: Mapped[list["AlarmRule"]] = relationship(back_populates="line", lazy="selectin")


class WorkStation(Base):
    __tablename__ = "work_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("production_lines.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    line: Mapped["ProductionLine"] = relationship(back_populates="stations")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    line_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlarmRule(Base):
    __tablename__ = "alarm_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("production_lines.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # static / dynamic_baseline
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_window: Mapped[int] = mapped_column(Integer, default=60)
    sigma_multiple: Mapped[float] = mapped_column(Float, default=3.0)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    line: Mapped["ProductionLine"] = relationship(back_populates="alarm_rules")


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alarm_rules.id"), nullable=True)
    line_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unconfirmed")
    defect_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompositeAlarmRule(Base):
    """多条件组合告警规则：多个子规则按 AND/OR 逻辑联判"""
    __tablename__ = "composite_alarm_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("production_lines.id"), nullable=False)
    rule_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: [1, 2, 3]
    logic: Mapped[str] = mapped_column(String(10), nullable=False, default="AND")  # AND / OR
    composite_severity: Mapped[str] = mapped_column(String(20), default="critical")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
