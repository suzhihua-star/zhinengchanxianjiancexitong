# 智能检测工厂产线系统 - 通用技术规范 (AGENTS.md)

## 1. 技术栈选型

| 层级 | 技术选型 | 选型理由 |
|------|---------|---------| 
| **后端框架** | Python 3.11+ / FastAPI | 异步高性能、原生 WebSocket 支持、数据科学生态好、适合数据处理场景 |
| **前端框架** | Vue 3 + TypeScript | 轻量、适合大屏看板、生态完善、学习成本低 |
| **UI 组件库** | Element Plus + @element-plus/icons-vue | Vue 3 生态首选、大屏场景组件丰富 |
| **图表库** | ECharts 5 (vue-echarts) | 大屏可视化领域主流、支持实时数据刷新、工业看板效果好 |
| **数据库（开发）** | SQLite + aiosqlite | Docker 不可用时的默认方案，零配置启动 |
| **数据库（生产）** | TimescaleDB (PostgreSQL 16) + asyncpg | 同时支持时序数据和关系型业务数据，内网部署友好，通过 `DB_MODE=postgres` 切换 |
| **缓存（可选）** | Redis + FakeRedis 降级 | Redis 可用时提供告警去重；不可用时自动切换内存 FakeRedis |
| **实时通信** | WebSocket (FastAPI 原生) | 服务端推送传感器数据到前端大屏 |
| **容器化** | Docker + Docker Compose | 一键部署、环境隔离、内网友好 |
| **反向代理** | Nginx | 生产环境静态资源服务 + API 代理 |
| **模拟数据** | Python asyncio + httpx | 独立进程，模拟 3 条产线传感器数据推送 |
| **前后端构建** | Vite 5 | 开发代理 API/WebSocket，生产打包静态资源 |

## 2. 项目结构约定

```
smart-factory/
├── backend/                       # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/                   # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── data_api.py        # 数据查询接口（history/latest/trend）
│   │   │   ├── alarm_api.py       # 告警管理接口（规则CRUD + 确认/关闭）
│   │   │   ├── line_api.py        # 产线与工位查询
│   │   │   ├── stats_api.py       # OEE/良品率统计
│   │   │   └── ws_api.py          # WebSocket 实时推送 + 心跳
│   │   ├── core/                  # 核心配置
│   │   │   ├── config.py          # 双数据库模式 + Redis + 模拟器配置
│   │   │   ├── database.py        # 数据库连接（SQLite/PostgreSQL 自动适配）
│   │   │   └── redis_dep.py       # Redis 连接 + FakeRedis 降级
│   │   ├── models/                # 数据模型 (SQLAlchemy ORM)
│   │   │   └── __init__.py        # 5 张表：production_lines / work_stations / sensor_data / alarm_rules / alarms
│   │   ├── schemas/               # Pydantic 请求/响应模型
│   │   │   └── __init__.py        # 全部 Schema（SensorData/AlarmRule/Alarm/Stats 等）
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── data_service.py    # 数据存储/最新值/历史查询/分钟聚合
│   │   │   ├── alarm_service.py   # 静态阈值 + 动态基线检测 + 告警去重
│   │   │   └── stats_service.py   # OEE + 良品率统计
│   │   ├── simulator/             # 模拟数据生成器
│   │   │   ├── __init__.py        # 3 线模拟逻辑（高斯噪声 + 异常注入）
│   │   │   └── __main__.py        # python -m app.simulator 入口
│   │   ├── __init__.py
│   │   └── main.py                # 应用入口（lifespan / 路由注册 / ingest 整合 / 种子数据）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                      # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── views/                 # 页面视图
│   │   │   ├── Dashboard.vue      # 大屏看板主页（三栏布局）
│   │   │   ├── HistoryData.vue    # 历史数据查询（筛选 + 导出 CSV）
│   │   │   └── AlarmConfig.vue    # 告警规则 CRUD 管理
│   │   ├── components/            # 可复用组件
│   │   │   ├── GaugeCard.vue      # 指标卡片（正常绿/警告黄/异常红+脉冲动画）
│   │   │   ├── RealTimeChart.vue  # ECharts 实时趋势图（mean/min/max 三线）
│   │   │   ├── AlarmList.vue      # 告警实时列表
│   │   │   ├── LineTopology.vue   # 产线工位拓扑图
│   │   │   └── AlertPopup.vue     # 告警弹窗 + Web Audio 声音
│   │   ├── composables/           # 组合式函数
│   │   │   ├── useWebSocket.ts    # WebSocket 自动重连 + 数据分发
│   │   │   └── useAlarm.ts        # Web Audio API 告警音
│   │   ├── stores/                # Pinia 状态管理
│   │   │   └── app.ts             # 实时数据/告警/产线选择状态
│   │   ├── router/
│   │   │   └── index.ts           # 3 路由（/ /history /alarms）
│   │   ├── App.vue
│   │   ├── env.d.ts               # TypeScript 类型声明
│   │   └── main.ts                # 应用入口（Element Plus 注册）
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts             # Vite 配置（@别名 + API/WS 代理）
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── Dockerfile                 # 多阶段构建（node build → nginx）
├── docker-compose.yml             # 5 服务编排（db/redis/backend/simulator/frontend）
├── nginx.conf                     # Nginx 反向代理（API + WebSocket）
└── .gitignore
```

> **文件总数**：约 35 个源文件（不含 `__pycache__` 和 `node_modules`）

## 3. 代码规范

### 3.1 Python (后端)
- 使用 **black** 格式化，行宽 100
- 使用 **isort** 排序导入
- 类型注解：所有函数参数和返回值必须有类型注解
- 异步优先：IO 操作用 async/await
- 命名规范：snake_case（变量/函数）、PascalCase（类）、UPPER_CASE（常量）
- 日志：使用 `logging` 模块，统一格式 `[时间] [级别] [模块] 消息`

### 3.2 TypeScript/Vue3 (前端)
- 使用 ESLint + Prettier，遵循 Vue 3 官方风格指南
- 组合式 API (`<script setup lang="ts">`) 优先
- 命名规范：camelCase（变量/函数）、PascalCase（组件文件）
- 组件文件使用 `.vue` 单文件组件，必须包含 `<script setup lang="ts">`
- Props 和 Emits 必须有 TypeScript 类型定义

### 3.3 数据库
- 表名使用 `snake_case` 复数形式
- 字段名使用 `snake_case`
- 所有表包含 `id` (主键)、`created_at`、`updated_at` 字段
- 开发模式使用 SQLite（WAL 模式 + 外键约束）
- 生产模式使用 TimescaleDB hypertable

## 4. 数据库命名规范

| 实体 | 表名 | 生产模式特性 |
|------|------|-------------|
| 产线 | `production_lines` | 标准表 |
| 工位 | `work_stations` | 外键关联 production_lines |
| 传感器数据 | `sensor_data` | 生产环境转换为 TimescaleDB hypertable |
| 告警记录 | `alarms` | 标准表，按 triggered_at 索引 |
| 告警规则 | `alarm_rules` | 标准表，rule_type=static/dynamic_baseline |

## 5. API 设计规范

- RESTful 风格，JSON 格式
- URL 前缀：`/api/v1/`
- WebSocket 端点：`/ws/live`
- 分页：`?page=1&page_size=20`
- 时间筛选：`?start_time=ISO8601&end_time=ISO8601`
- 响应格式统一：
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## 6. 开发环境

### 6.1 环境要求
- Python 3.11+（使用 `venv` 或 conda 环境）
- Node.js 20+（使用 `npm` 包管理）

### 6.2 本地开发启动

```bash
# 1. 安装后端依赖
cd smart-factory/backend
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings redis httpx python-dotenv

# 2. 启动后端（SQLite 模式，无需 Docker）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动模拟器（新终端）
cd smart-factory/backend
python -m app.simulator

# 4. 安装前端依赖并启动
cd smart-factory/frontend
npm install --registry=https://registry.npmmirror.com
npm install element-plus @element-plus/icons-vue --registry=https://registry.npmmirror.com
npx vite --host 0.0.0.0
```

### 6.3 Docker 部署（生产环境，需 PostgreSQL + Redis）

```bash
cd smart-factory
# 先设置环境变量切换数据库模式
export DB_MODE=postgres
docker compose up -d
```

## 7. 访问地址

| 环境 | 前端 | 后端 API | WebSocket |
|------|------|---------|-----------|
| 本地开发 | `http://localhost:5173` | `http://localhost:8000` | `ws://localhost:8000/ws/live` |
| Docker 部署 | `http://<服务器IP>` | `http://<服务器IP>/api/` | `ws://<服务器IP>/ws/live` |

> 开发模式下 Vite 自动代理 `/api` → `localhost:8000`，前端无需关心跨域。

## 8. 数据库双模式说明

| 模式 | 数据库 | 适用场景 | 切换方式 |
|------|--------|---------|---------|
| `sqlite`（默认） | SQLite 文件 | 本地开发、无 Docker 环境 | 无需配置 |
| `postgres` | TimescaleDB | 生产部署、大规模数据 | 设置环境变量 `DB_MODE=postgres` |

> SQLite 模式下会自动启用 WAL 模式和外键约束，Redis 不可用时自动降级为内存 FakeRedis。

## 9. Vite 配置约定

- `@` 路径别名 → `src/`
- `/api` 代理 → `http://localhost:8000`
- `/ws` WebSocket 代理 → `ws://localhost:8000`
- 开发端口：5173
- 构建输出：`dist/`

## 10. Git 提交规范

采用 Conventional Commits：
- `feat:` 新功能
- `fix:` 修复
- `refactor:` 重构
- `docs:` 文档
- `style:` 格式
- `test:` 测试
- `chore:` 构建/工具
