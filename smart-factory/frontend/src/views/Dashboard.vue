<template>
  <div class="dashboard">
    <!-- 顶部栏 -->
    <header class="top-bar">
      <div class="title-area">
        <h1 class="sys-title">智能检测工厂产线监控系统</h1>
        <span class="sys-time">{{ currentTime }}</span>
      </div>
      <div class="status-area">
        <span class="ws-status" :class="{ connected: wsConnected }">
          {{ wsConnected ? '已连接' : '重连中...' }}
        </span>
        <div class="line-indicators">
          <span
            v-for="line in lines"
            :key="line.id"
            class="line-tag"
            :class="{ active: selectedLine === line.id }"
            @click="selectLine(line.id)"
          >
            {{ line.code }}
          </span>
        </div>
        <div class="nav-links">
          <router-link to="/history" class="nav-link">历史数据</router-link>
          <router-link to="/alarms" class="nav-link">告警配置</router-link>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 左栏: 指标卡片 + 仪表 -->
      <aside class="left-panel">
        <div class="panel-title">实时指标</div>
        <div class="metrics-grid">
          <GaugeCard
            v-for="(item, idx) in displayMetrics"
            :key="idx"
            :metric-label="metricLabelMap[item.metric_name] || item.metric_name"
            :value="item.metric_value"
            :unit="item.unit || ''"
            :station-name="stationName(item.station_id)"
            :upper-limit="thresholds[item.metric_name]?.max"
            :lower-limit="thresholds[item.metric_name]?.min"
          />
        </div>
        <div class="stats-section">
          <div class="stat-item">
            <span class="stat-label">OEE</span>
            <span class="stat-value" style="color: #00d4ff">{{ oeeValue }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">良品率</span>
            <span class="stat-value" style="color: #00dc64">{{ yieldValue }}</span>
          </div>
        </div>
      </aside>

      <!-- 中栏: 趋势图 2x2 + 拓扑图 -->
      <section class="center-panel">
        <div class="chart-grid">
          <div v-for="m in metricOptions" :key="m.key" class="chart-cell">
            <RealTimeChart
              v-if="trendData[m.key] && trendData[m.key].length > 0"
              :title="metricLabelMap[m.key]"
              :data="trendData[m.key]"
              :unit="metricUnitMap[m.key] || ''"
              :color="metricColorMap[m.key] || '#00d4ff'"
            />
            <div v-else class="loading-placeholder">{{ m.label }} — 等待数据...</div>
          </div>
        </div>
        <div class="topology-area">
          <LineTopology
            :line-name="currentLine?.name || '--'"
            :stations="currentStations"
          />
        </div>
      </section>

      <!-- 右栏: 告警列表 -->
      <aside class="right-panel">
        <AlarmList :alarms="store.activeAlarms" />
      </aside>
    </main>

    <!-- 告警弹窗 -->
    <AlertPopup :alarm="latestAlarm" @close="dismissAlarm" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'
import { useAppStore } from '@/stores/app'
import { useWebSocket } from '@/composables/useWebSocket'
import GaugeCard from '@/components/GaugeCard.vue'
import RealTimeChart from '@/components/RealTimeChart.vue'
import LineTopology from '@/components/LineTopology.vue'
import AlarmList from '@/components/AlarmList.vue'
import AlertPopup from '@/components/AlertPopup.vue'
import type { AlarmEvent } from '@/stores/app'

const store = useAppStore()
const { connected: wsConnected } = useWebSocket()

const selectedLine = ref(1)
const currentTime = ref('')
let clockTimer: ReturnType<typeof setInterval> | null = null

const metricOptions = [
  { key: 'temperature', label: '温度' },
  { key: 'humidity', label: '湿度' },
  { key: 'pressure', label: '压力' },
  { key: 'speed', label: '速度' },
]

const metricUnitMap: Record<string, string> = {
  temperature: '℃',
  humidity: '%RH',
  pressure: 'MPa',
  speed: 'm/s',
}

const metricColorMap: Record<string, string> = {
  temperature: '#ff6432',
  humidity: '#00d4ff',
  pressure: '#ffb800',
  speed: '#00dc64',
}

const latestAlarm = ref<AlarmEvent | null>(null)
let alarmQueue: AlarmEvent[] = []

// 产线列表（从 API 获取）
const lines = ref<Array<{ id: number; name: string; code: string; stations: any[] }>>([])

// 趋势数据
const trendData = ref<Record<string, any[]>>({
  temperature: [],
  humidity: [],
  pressure: [],
  speed: [],
})

const thresholds: Record<string, { max: number; min: number }> = {
  temperature: { max: 170, min: 130 },
  humidity: { max: 60, min: 30 },
  pressure: { max: 0.95, min: 0.55 },
  speed: { max: 1.5, min: 0.7 },
}

const metricLabelMap: Record<string, string> = {
  temperature: '温度',
  humidity: '湿度',
  pressure: '压力',
  speed: '速度',
}

const stationNameMap = ref<Record<number, string>>({})

function stationName(stationId: number | null): string {
  if (!stationId) return ''
  return stationNameMap.value[stationId] || `工位#${stationId}`
}

const displayMetrics = computed(() => store.lineData)

const currentLine = computed(() => lines.value.find((l) => l.id === selectedLine.value))
const currentStations = computed(() => currentLine.value?.stations || [])

const oeeValue = computed(() => {
  const cnt = displayMetrics.value.filter((d) => d.metric_value > 0).length
  const total = displayMetrics.value.length || 1
  return `${((cnt / total) * 100).toFixed(0)}%`
})

const yieldValue = computed(() => {
  const bad = store.activeAlarms.filter((a) => a.line_id === selectedLine.value).length
  return `${Math.max(85, 100 - bad * 3)}.0%`
})

function selectLine(id: number) {
  selectedLine.value = id
  store.selectedLine = id
  loadTrendData(id)
}

function dismissAlarm() {
  latestAlarm.value = null
  if (alarmQueue.length > 0) {
    const next = alarmQueue.shift()!
    latestAlarm.value = next
  }
}

// 监听新告警
watch(
  () => store.alarms.length,
  () => {
    if (store.alarms.length > 0) {
      const last = store.alarms[0]
      if (!last.status || last.status === 'unconfirmed') {
        if (!latestAlarm.value) {
          latestAlarm.value = last
        } else {
          alarmQueue.push(last)
        }
      }
    }
  }
)

// 趋势数据加载
async function loadTrendData(lineId: number) {
  try {
    for (const metric of ['temperature', 'humidity', 'pressure', 'speed']) {
      const resp = await axios.get('/api/v1/data/trend', {
        params: { line_id: lineId, metric_name: metric, minutes: 60 },
      })
      const result = resp.data?.data
      if (result && Array.isArray(result)) {
        trendData.value[metric] = result
      }
    }
  } catch (e) {
    console.error('加载趋势数据失败:', e)
  }
}

// 趋势数据定时刷新
let trendTimer: ReturnType<typeof setInterval> | null = null

async function loadLines() {
  try {
    const resp = await axios.get('/api/v1/lines')
    const data = resp.data?.data
    if (Array.isArray(data)) {
      lines.value = data
      for (const line of data) {
        if (line.stations) {
          for (const station of line.stations) {
            stationNameMap.value[station.id] = station.name
          }
        }
      }
    }
  } catch (e) {
    console.error('加载产线数据失败:', e)
  }
}

onMounted(() => {
  loadLines()
  loadTrendData(selectedLine.value)

  // 时钟
  currentTime.value = new Date().toLocaleString('zh-CN')
  clockTimer = setInterval(() => {
    currentTime.value = new Date().toLocaleString('zh-CN')
  }, 1000)

  // 趋势数据刷新
  trendTimer = setInterval(() => loadTrendData(selectedLine.value), 5000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (trendTimer) clearInterval(trendTimer)
})
</script>

<style scoped>
.dashboard { width: 100vw; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

/* 顶部栏 */
.top-bar {
  height: 50px; flex-shrink: 0;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 20px;
  background: linear-gradient(180deg, rgba(0, 150, 255, 0.1), rgba(0, 0, 0, 0));
  border-bottom: 1px solid rgba(0, 200, 255, 0.1);
}
.title-area { display: flex; align-items: baseline; gap: 16px; }
.sys-title { font-size: 18px; color: #e0e6ed; font-weight: 600; }
.sys-time { font-size: 13px; color: #5a7a9a; }
.status-area { display: flex; align-items: center; gap: 16px; }
.ws-status { font-size: 12px; padding: 2px 10px; border-radius: 10px; background: rgba(255, 50, 50, 0.2); color: #ff6432; }
.ws-status.connected { background: rgba(0, 200, 100, 0.2); color: #00dc64; }
.line-indicators { display: flex; gap: 8px; }
.line-tag {
  font-size: 12px; padding: 3px 12px; border-radius: 3px;
  background: rgba(0, 150, 255, 0.1); color: #7b93b3; cursor: pointer;
  border: 1px solid rgba(0, 150, 255, 0.2); transition: all 0.2s;
}
.line-tag.active { background: rgba(0, 150, 255, 0.3); color: #00d4ff; border-color: #00d4ff; }
.line-tag:hover { background: rgba(0, 150, 255, 0.2); }
.nav-links { display: flex; gap: 12px; margin-left: 12px; }
.nav-link { font-size: 12px; color: #5a7a9a; text-decoration: none; padding: 3px 8px; border-radius: 3px; transition: all 0.2s; }
.nav-link:hover { color: #00d4ff; background: rgba(0, 150, 255, 0.1); }

/* 主内容 */
.main-content { flex: 1; display: flex; gap: 0; overflow: hidden; }
.left-panel { width: 22%; flex-shrink: 0; border-right: 1px solid rgba(0, 200, 255, 0.1); padding: 12px; display: flex; flex-direction: column; }
.center-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.right-panel { width: 22%; flex-shrink: 0; border-left: 1px solid rgba(0, 200, 255, 0.1); }

.panel-title { font-size: 13px; color: #8ba8c8; font-weight: 600; margin-bottom: 8px; }
.metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; flex: 1; align-content: start; }

.stats-section { display: flex; gap: 12px; padding: 12px 0; border-top: 1px solid rgba(0, 200, 255, 0.1); margin-top: 8px; }
.stat-item { flex: 1; text-align: center; }
.stat-label { font-size: 12px; color: #5a7a9a; }
.stat-value { font-size: 28px; font-weight: 700; font-family: 'DIN', 'Consolas', monospace; }

.chart-grid { flex: 1; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 6px; padding: 4px 4px 0; min-height: 0; }
.chart-cell { min-height: 0; overflow: hidden; border-radius: 4px; background: rgba(0, 150, 255, 0.04); padding: 2px; }
.topology-area { height: 120px; flex-shrink: 0; border-top: 1px solid rgba(0, 200, 255, 0.1); }

.loading-placeholder {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: #5a7a9a; font-size: 14px;
}
</style>
