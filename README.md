# 智能检测工厂产线监控系统

Smart Factory Monitor — 面向食品/药品包装产线的实时数据采集、智能告警、大屏可视化系统。

---

## 系统架构

```
模拟数据生成器 → HTTP POST /api/v1/data/ingest → FastAPI 后端 → {
    ├── 写入数据库 (SQLite / TimescaleDB)
    ├── 告警引擎 (静态阈值 + 动态基线 + 组合规则)
    └── WebSocket 实时推送 (sensor_data / alarm_event)
}
→ Vue 3 大屏看板 (Pinia store → 组件响应式刷新)
```

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端 | Python + FastAPI | 3.13+ / 0.115+ |
| 数据库 | SQLite (开发) / TimescaleDB PostgreSQL (生产) | — |
| 缓存 | Redis / FakeRedis 自动降级 | 5.0+ |
| 前端 | Vue 3 + TypeScript | 3.5+ |
| UI | Element Plus + ECharts 5 | 2.14+ / 5.6+ |
| 构建 | Vite 5 | 5.4+ |
| 部署 | Docker Compose + Nginx | — |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- （可选）Docker + Docker Compose（生产部署）

### 1. 克隆项目

```bash
cd smart-factory
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 启动后端（SQLite 默认模式，零配置）

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动模拟器（新终端）

```bash
cd backend
python -m app.simulator
```

### 5. 安装并启动前端

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com
npx vite --host 0.0.0.0
```

### 6. 访问

| 服务 | 地址 |
|------|------|
| 大屏看板 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| WebSocket | ws://localhost:8000/ws/live |
| API 文档 | http://localhost:8000/docs |

## Docker 生产部署

```bash
# 设置数据库模式
export DB_MODE=postgres

# 一键启动 5 个服务
docker compose up -d

# 访问
http://<服务器IP>
```

## 项目结构

```
smart-factory/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # 7 个 API 路由 (data/alarm/line/stats/ws/ml/report)
│   │   ├── core/                # 配置/数据库/Redis
│   │   ├── models/              # 6 个 ORM 模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/            # 5 个业务服务
│   │   ├── simulator/           # 模拟数据生成器 (3 线 14 工位 4 指标)
│   │   └── main.py              # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── views/               # 3 页面 (Dashboard/History/Alarms)
│   │   ├── components/          # 5 组件 (GaugeCard/Chart/AlarmList/Topology/Popup)
│   │   ├── composables/         # WebSocket + 告警音
│   │   ├── stores/              # Pinia 状态管理
│   │   └── router/              # Vue Router
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── specs/                       # 设计文档 + 验收报告
│   ├── spec.md                  # 客户需求
│   ├── plan.md                  # 技术方案
│   ├── tasks.md                 # 任务清单
│   └── test-report.md           # 交付测试报告
├── docker-compose.yml           # 5 服务编排
├── nginx.conf                   # 反向代理配置
└── AGENTS.md                    # 工程规范
```

## 核心功能

### 数据采集
- 模拟 3 条产线、14 个工位、4 种传感器指标
- 高斯噪声正常波动 + 3% 异常注入
- 每秒推送实时数据

### 告警引擎
- 静态阈值检测（上限/下限）
- 动态基线检测（均值 ± N×波动）
- 多条件组合规则（AND/OR 联判）
- Redis/FakeRedis 去重窗口
- 三级告警：warning / critical / emergency
- 大屏弹窗 + 声音提示

### 大屏看板
- 2×2 实时趋势图（温度/湿度/压力/速度）
- 指标卡片（GaugeCard 三色 + 脉冲动画）
- 告警实时列表
- 产线工位拓扑示意
- OEE / 良品率统计

### 数据分析
- 历史数据查询与对比
- 分钟级聚合趋势
- 多产线同指标叠加对比
- 日报/周报/月报自动生成（JSON + CSV）

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/data/ingest` | 传感器数据写入 + 告警评估 + WS 广播 |
| GET | `/api/v1/data/latest` | 最新传感器值 |
| GET | `/api/v1/data/history` | 历史数据分页查询 |
| GET | `/api/v1/data/trend` | 分钟聚合趋势 |
| POST | `/api/v1/data/comparison` | 多产线对比趋势 |
| GET | `/api/v1/lines` | 产线列表 |
| GET | `/api/v1/lines/{id}/stations` | 工位列表 |
| CRUD | `/api/v1/alarms/rules` | 告警规则管理 |
| GET | `/api/v1/alarms` | 告警记录分页 |
| PUT | `/api/v1/alarms/{id}/confirm` | 告警确认 |
| PUT | `/api/v1/alarms/{id}/resolve` | 告警关闭 |
| CRUD | `/api/v1/alarms/composite-rules` | 组合规则管理 |
| GET | `/api/v1/alarms/defect-breakdown` | 缺陷分类统计 |
| GET | `/api/v1/stats/oee` | OEE 统计 |
| GET | `/api/v1/stats/yield` | 良品率统计 |
| POST | `/api/v1/reports/generate` | 生成报表 |
| POST | `/api/v1/reports/generate/csv` | CSV 导出 |

完整 API 文档：http://localhost:8000/docs (启动后)

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_MODE` | `sqlite` | 数据库模式：`sqlite` / `postgres` |
| `DB_HOST` | `localhost` | PostgreSQL 主机 |
| `DB_PORT` | `5432` | PostgreSQL 端口 |
| `DB_USER` | `postgres` | 数据库用户 |
| `DB_PASSWORD` | `postgres` | 数据库密码（生产必改） |
| `DB_NAME` | `smart_factory` | 数据库名 |
| `REDIS_HOST` | `localhost` | Redis 主机 |
| `SIMULATOR_INTERVAL_SECONDS` | `1.0` | 模拟器推送间隔 |
| `SIMULATOR_ANOMALY_RATE` | `0.03` | 异常注入概率 |

> 可通过 `.env` 文件或系统环境变量设置。

## 测试

```bash
cd specs
pytest -v

# 输出
# test_data_api.py ............ 13 passed
# test_alarm_api.py .......... 17 passed
# test_stats_api.py ..........  7 passed
# test_misc_api.py ...........  8 passed
# ============ 45 passed in 13s ============
```

## 设计文档

| 文档 | 路径 |
|------|------|
| 客户需求 | `specs/spec.md` |
| 技术方案 | `specs/plan.md` |
| 任务清单 | `specs/tasks.md` |
| 交付测试报告 | `specs/test-report.md` |
| 架构校验报告 | `specs/architecture-review.md` |
| 代码工程报告 | `specs/code-engineering-review.md` |
| 安全审计报告 | `specs/security-audit.md` |
| 工程规范 | `AGENTS.md` |

---

*Smart Factory Monitor v1.0 — 2026-06-10*
