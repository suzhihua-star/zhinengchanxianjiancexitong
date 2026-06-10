# 智能检测工厂产线系统 - 技术设计与项目规划

## 1. 系统架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                     大屏看板 (Vue 3 + Element Plus)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ 总览态势  │ │ 实时趋势  │ │ 告警列表  │ │  产线拓扑图      │   │
│  │GaugeCard │ │RealTimeChart│ │AlarmList │ │  LineTopology   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│                     AlertPopup (弹窗+声音)                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │ WebSocket / REST API (Vite Proxy)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Nginx (生产) / Vite (开发)                      │
└────────────────────────┬─────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────────┐
│  FastAPI     │  │  模拟数据    │  │  Redis / Fake   │
│  (后端服务)   │  │  生成器      │  │  Redis (缓存)   │
│ main.py      │  │ simulator/  │  │ redis_dep.py    │
└──────┬──────┘  └──────┬──────┘  └─────────────────┘
       │                │
       │   写入/查询     │   HTTP POST /api/v1/data/ingest
       ▼                ▼
┌──────────────────────────────────────┐
│  数据库 (双模式)                       │
│  ┌────────────────────────────────┐  │
│  │ 开发: SQLite (smart_factory.db) │  │
│  │ 生产: TimescaleDB (PostgreSQL)  │  │
│  ├────────┐ ┌────────┐ ┌─────────┤  │
│  │传感器数据│ │告警记录 │ │业务配置  │  │
│  └────────┘ └────────┘ └─────────┘  │
└──────────────────────────────────────┘
```

### 模块说明

| 模块 | 职责 | 技术 | 关键文件 |
|------|------|------|---------|
| **模拟数据生成器** | 模拟 3 条产线传感器数据，高斯噪声+异常注入 | Python asyncio + httpx | `simulator/__init__.py` + `__main__.py` |
| **FastAPI 后端** | 数据接收/存储/分析/告警，提供 REST API + WebSocket | FastAPI + SQLAlchemy | `main.py` (入口) + 6 API + 3 Service |
| **Redis / FakeRedis** | 告警去重（Redis 不可用时自动降级为内存版） | redis-py / FakeRedis | `core/redis_dep.py` |
| **数据库（双模式）** | SQLite 开发/TimescaleDB 生产，通过 `DB_MODE` 切换 | SQLAlchemy ORM | `core/config.py` + `core/database.py` |
| **Vue 3 前端** | 大屏看板、历史查询、告警管理 | Vue 3 + TypeScript + ECharts + Element Plus | `Dashboard.vue` 等 3 页面 + 5 组件 |
| **Nginx** (生产) | 反向代理、静态资源托管 | Nginx | `nginx.conf` |
| **Vite** (开发) | 开发服务器 + API/WebSocket 代理 | Vite 5 | `vite.config.ts` |

## 2. 数据流设计

### 2.1 实时数据流
```
模拟器/PLC → (HTTP POST /api/v1/data/ingest) → FastAPI → {
    1. 写入数据库（SQLite 或 TimescaleDB）
    2. 调用告警分析引擎（alarm_service.evaluate_alarms）
    3. 通过 WebSocket broadcast() 广播到前端
}
→ 前端 WebSocket onmessage → Pinia store 更新 → 组件响应式刷新
```

### 2.2 告警流程
```
传感器数据 → alarm_service.evaluate_alarms {
    ├── 规则1: 静态阈值检测（超过 upper_limit / lower_limit）
    └── 规则2: 动态基线检测（偏离均值超过 N×基准波动）
} → 告警去重（Redis/FakeRedis 检查活跃状态）→ {
    ├── 写入 alarms 表
    └── WebSocket broadcast("alarm_event") → 前端 AlertPopup 弹窗 + useAlarmSound 声音
}
```

### 2.3 历史查询流程
```
前端请求 → REST API → {
    原始数据查询 → data_service.get_history (ORM 筛选)
    聚合统计   → data_service.get_minute_aggregation (SQLite strftime / PG date_trunc)
    统计指标   → stats_service (OEE/良品率)
} → JSON 响应 → 前端 ECharts 渲染 / Element Plus 表格展示
```

## 3. 数据库设计

### 3.1 ORM 模型（SQLAlchemy，同时兼容 SQLite 和 PostgreSQL）

| 模型类 | 表名 | 核心字段 | 说明 |
|--------|------|---------|------|
| `ProductionLine` | `production_lines` | id, name, code, status | 3 条产线种子数据 |
| `WorkStation` | `work_stations` | id, line_id(FK), name, code, sort_order | 每线 4-5 个工位 |
| `SensorData` | `sensor_data` | id, time, line_id, station_id, metric_name, metric_value, unit | **时序主表**，生产环境转为 TimescaleDB hypertable |
| `AlarmRule` | `alarm_rules` | id, name, line_id, metric_name, rule_type, upper_limit, lower_limit, baseline_window, sigma_multiple, severity, is_active | rule_type = static / dynamic_baseline |
| `Alarm` | `alarms` | id, rule_id, line_id, metric_name, actual_value, severity, message, status, triggered_at | status: unconfirmed / confirmed / resolved |

### 3.2 ER 关系
```
production_lines (1) ──── (N) work_stations
production_lines (1) ──── (N) sensor_data
production_lines (1) ──── (N) alarm_rules
alarm_rules     (1) ──── (N) alarms
```

### 3.3 数据库模式切换

| 模式 | 连接串 | ORM 行为 | 特殊处理 |
|------|--------|---------|---------|
| `sqlite` | `sqlite+aiosqlite:///./smart_factory.db` | NullPool, check_same_thread=False | PRAGMA journal_mode=WAL, foreign_keys=ON |
| `postgres` | `postgresql+asyncpg://...` | pool_size=5, 支持 Hypertable | 需手动 `SELECT create_hypertable()` |

> 通过 `config.py` 中 `DB_MODE` 环境变量控制，所有 Service 层通过 `settings.is_postgres` 自动适配 SQL 方言。

## 4. API 设计

### 4.1 REST API 端点（共 14 个）

| 方法 | 路径 | 路由文件 | 说明 |
|------|------|---------|------|
| `POST` | `/api/v1/data/ingest` | `main.py` (覆盖) | 接收数据 → 存储 → 告警 → WebSocket 广播 |
| `GET` | `/api/v1/data/latest?line_id=X` | `data_api.py` | 各指标最新值 |
| `GET` | `/api/v1/data/history` | `data_api.py` | 历史数据（line_id/metric_name/start/end） |
| `GET` | `/api/v1/data/trend` | `data_api.py` | 分钟级聚合趋势数据 |
| `GET` | `/api/v1/lines` | `line_api.py` | 产线列表（含工位） |
| `GET` | `/api/v1/lines/{id}/stations` | `line_api.py` | 工位列表 |
| `GET` | `/api/v1/alarms/rules` | `alarm_api.py` | 告警规则列表 |
| `POST` | `/api/v1/alarms/rules` | `alarm_api.py` | 创建规则 |
| `PUT` | `/api/v1/alarms/rules/{id}` | `alarm_api.py` | 更新规则 |
| `DELETE` | `/api/v1/alarms/rules/{id}` | `alarm_api.py` | 删除规则 |
| `GET` | `/api/v1/alarms` | `alarm_api.py` | 告警记录（分页） |
| `PUT` | `/api/v1/alarms/{id}/confirm` | `alarm_api.py` | 确认告警 |
| `PUT` | `/api/v1/alarms/{id}/resolve` | `alarm_api.py` | 关闭告警 |
| `GET` | `/api/v1/stats/oee` | `stats_api.py` | OEE 统计 |
| `GET` | `/api/v1/stats/yield` | `stats_api.py` | 良品率统计 |

### 4.2 WebSocket 端点

| 端点 | 方向 | 消息类型 | 说明 |
|------|------|---------|------|
| `/ws/live` | 服务端→客户端 | `sensor_data` | 每条模拟器数据推送 |
| `/ws/live` | 服务端→客户端 | `alarm_event` | 新告警触发推送 |
| `/ws/live` | 双向 | `ping`/`pong` | 心跳保活（30s 超时） |

**消息格式**：
```json
{
    "type": "sensor_data",
    "data": [{"line_id":1,"station_id":2,"metric":"temperature","value":156.3,"unit":"℃"}]
}
```

## 5. 模拟数据生成器设计

### 5.1 产线配置（硬编码 3 线）

| 产线 | 编码 | 工位数 | 指标 | 基准值 |
|------|------|--------|------|--------|
| 包装产线 A | LINE-A | 5 工位 | temperature/humidity/pressure/speed | 155℃ / 45% / 0.75MPa / 1.2m/s |
| 充填包装线 B | LINE-B | 4 工位 | 同上 | 160℃ / 50% / 0.80MPa / 1.0m/s |
| 成型包装线 C | LINE-C | 5 工位 | 同上 | 148℃ / 42% / 0.72MPa / 1.15m/s |

### 5.2 模拟逻辑
```python
# 每条产线 × 每个工位 × 每个指标 = 60 条数据/秒
#   - 基准值：预设合理范围（如温度 148-160℃）
#   - 正常波动：random.gauss(0, noise) 高斯噪声
#   - 异常注入：random() < 3% 概率，0.15-0.35 比例偏离基准值
#   - 发送频率：1 次/秒（通过 SIMULATOR_INTERVAL_SECONDS 配置）
```

### 5.3 启动方式
```bash
cd smart-factory/backend
python -m app.simulator
# 环境变量可覆盖: SIMULATOR_BACKEND_URL, SIMULATOR_INTERVAL, SIMULATOR_ANOMALY_RATE
```

## 6. 前端大屏设计

### 6.1 页面布局（自适应 1920×1080，三栏响应式）
```
┌─────────────────────────────────────────────────────────┐
│  顶部栏：系统标题 | 时间 | WebSocket状态 | 产线切换 | 导航  │
├───────────────────┬─────────────────────────────────────┤
│   左栏 (22%)       │     中栏 (56%)                      │
│  ┌───────────────┐│  ┌─────────────────────────────────┐│
│  │ 关键指标卡片   ││  │  实时趋势图 (RealTimeChart)       │├──┐
│  │ GaugeCard × N  ││  │  ECharts mean/min/max 三线       ││  │
│  │ 正常绿/警告黄   ││  │  SQLite strftime 分钟聚合         ││  │
│  │ /异常红+脉冲   ││  └─────────────────────────────────┘│  ├ 右栏
│  ├───────────────┤│  ┌─────────────────────────────────┐│  │(22%)
│  │ OEE 统计值     ││  │  产线拓扑示意图 (LineTopology)    ││  │
│  │ 良品率统计值   ││  │  工位节点+异常红闪                 ││  │告警列表
│  └───────────────┘│  └─────────────────────────────────┘│  │AlarmList
└───────────────────┴─────────────────────────────────────┴──┘
```

### 6.2 组件一览

| 组件 | 关键特性 |
|------|---------|
| `GaugeCard.vue` | Props: metricLabel/value/unit/upperLimit/lowerLimit；computed 颜色状态；CSS 脉冲动画 |
| `RealTimeChart.vue` | vue-echarts；三系列（mean/min/max）；平滑面积填充；Props: title/data/unit/color |
| `AlarmList.vue` | Pinia store 绑定；warning/critical/emergency 三级；blink 动画 |
| `LineTopology.vue` | 固定阈值判断异常；flex 流式布局；红色脉冲动画 |
| `AlertPopup.vue` | Vue Transition 滑入；useAlarmSound() Web Audio 800Hz 方波；8s 自动消失；队列播放 |

### 6.3 页面路由

| 路由 | 页面 | 组件依赖 |
|------|------|---------|
| `/` | `Dashboard.vue` | GaugeCard/RealTimeChart/LineTopology/AlarmList/AlertPopup |
| `/history` | `HistoryData.vue` | Element Plus Table/DatePicker/Select；axios GET /api/v1/data/history；CSV 导出 |
| `/alarms` | `AlarmConfig.vue` | Element Plus Table/Dialog/Form；axios CRUD /api/v1/alarms/rules |

### 6.4 状态管理（Pinia store — `stores/app.ts`）

| State | 类型 | 来源 |
|-------|------|------|
| `latestData` | `SensorDataItem[]` | WebSocket `sensor_data` 消息 |
| `alarms` | `AlarmEvent[]` | WebSocket `alarm_event` 消息（最多保留 200 条） |
| `selectedLine` | `number` | 顶部产线选择（默认 1） |

| Getter | 说明 |
|--------|------|
| `lineData` | `latestData` 按 selectedLine 过滤 |
| `activeAlarms` | `alarms` 中未 resolved 的前 10 条 |

## 7. 异常检测算法

### 7.1 静态阈值检测（rule_type=static）
```
IF metric_value > alarm_rules.upper_limit OR metric_value < alarm_rules.lower_limit:
    → 触发告警 [severity: 规则预设]
```

### 7.2 动态基线检测（rule_type=dynamic_baseline）

**SQLite 模式**（无 STDDEV 函数）：
```python
cutoff = NOW() - baseline_window 分钟
mean = AVG(metric_value) WHERE time >= cutoff
base_fluctuation = max(abs(mean) * 0.1, 0.1)  # 均值的 10% 作为基准波动
threshold = sigma_multiple × base_fluctuation
IF |metric_value - mean| > threshold → 触发告警
```

**PostgreSQL 模式**（有 STDDEV 函数）：
```sql
SELECT AVG(metric_value), STDDEV(metric_value) WHERE time >= $cutoff
IF |value - mean| > sigma_multiple × stddev → 触发告警
```

### 7.3 告警去重（Redis / FakeRedis）
```
dedup_key = f"alarm_active:{rule_id}:{line_id}:{metric_name}"
IF redis.get(dedup_key) IS NOT NULL → 跳过（已有活跃告警）
ELSE:
    redis.set(dedup_key, "1", ex=1800)  # 30分钟过期
    → 写入 alarms 表 + WebSocket 广播
```

## 8. 开发与部署方案

### 8.1 开发模式（当前实际运行方案）

| 服务 | 启动命令 | 端口 |
|------|---------|------|
| 后端 API | `uvicorn app.main:app --reload --host 0.0.0.0` | 8000 |
| 模拟器 | `python -m app.simulator` | —（HTTP 推送至 8000） |
| 前端 Dev | `npx vite --host 0.0.0.0` | 5173（代理 API/WS 到 8000） |
| 数据库 | SQLite 文件 `smart_factory.db` | 自动创建 |
| 缓存 | FakeRedis 内存模式 | 自动降级 |

### 8.2 Docker 生产部署

```yaml
# docker compose up -d （需 Docker + 设置 DB_MODE=postgres）
services:
  db:         timescaledb:latest-pg16  (5432)  # TimescaleDB
  redis:      redis:7-alpine           (6379)  # Redis
  backend:    fastapi-app              (8000)  # DB_MODE=postgres
  simulator:  data-simulator           (内部)   # → backend:8000
  frontend:   nginx + vue-dist         (80)    # 静态 + 反向代理
```

## 9. 实际开发阶段完成情况

| 阶段 | 内容 | 状态 | 实际产出 |
|------|------|------|---------|
| **Phase 1** | 后端脚手架 + 数据库 + 模拟器 + WebSocket | **已完成** | 20 个后端文件：config/database/ORM/Schema/6 API/3 Service/WebSocket/模拟器 |
| **Phase 2** | 告警引擎 + 大屏看板 Dashboard | **已完成** | alarm_service（双模式检测+去重）+ 3 页面 + 5 组件 + 2 composables |
| **Phase 3** | 历史数据 + 统计 | **已完成** | HistoryData.vue（筛选+导出）+ stats_service（OEE/良品率） |
| **Phase 4** | 告警规则 CRUD + 配置管理 | **已完成** | AlarmConfig.vue（完整 CRUD）+ 种子数据自初始化 |
| **Phase 5** | Docker + Nginx 部署 | **已完成** | 3 Dockerfile + docker-compose.yml（5服务）+ nginx.conf |

## 10. 关键技术决策与风险

| 决策 | 原因 | 影响 |
|------|------|------|
| **双数据库模式** | 开发环境无 Docker，需 SQLite 零配置启动 | `DB_MODE` 切换 + `is_postgres` 分支适配 SQL 方言 |
| **FakeRedis 降级** | Redis 非开发环境必备 | 告警去重降级为内存字典，重启后活跃状态丢失（可接受） |
| **Vite Proxy** | 开发时前后端分离，避免 CORS | `/api` + `/ws` 代理到 `localhost:8000` |
| **ingest 端点重写** | 需在一个请求内完成存储+分析+广播 | 在 `main.py` 中用 `@app.post()` 覆盖 `data_api.py` 的同名路由 |
| **EChats 增量更新** | 大屏长时间运行性能 | 趋势图每次全量替换数据（60个数据点），非增量 push |

---

*文档版本: v2.0 | 更新日期: 2026-06-10 | 同步实际项目 v1.0*
