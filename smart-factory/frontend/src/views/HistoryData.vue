<template>
  <div class="history-page">
    <header class="page-header">
      <h2>历史数据查询 & 对比分析</h2>
      <router-link to="/" class="back-link">返回大屏</router-link>
    </header>

    <el-tabs v-model="activeTab" class="tabs">
      <!-- Tab 1: 数据查询 -->
      <el-tab-pane label="数据查询" name="query">
        <div class="filter-bar">
          <el-select v-model="lineId" placeholder="选择产线" clearable style="width: 150px">
            <el-option v-for="l in lines" :key="l.id" :label="l.name" :value="l.id" />
          </el-select>
          <el-select v-model="metricName" placeholder="选择指标" clearable style="width: 130px">
            <el-option label="温度" value="temperature" />
            <el-option label="湿度" value="humidity" />
            <el-option label="压力" value="pressure" />
            <el-option label="速度" value="speed" />
          </el-select>
          <el-date-picker v-model="timeRange" type="datetimerange" range-separator="至" start-placeholder="开始" end-placeholder="结束" format="YYYY-MM-DD HH:mm" style="width: 340px" />
          <el-button type="primary" @click="query">查询</el-button>
          <el-button @click="exportCSV" :disabled="rows.length === 0">导出 CSV</el-button>
        </div>
        <el-table :data="rows" border stripe height="calc(100vh - 300px)" v-loading="loading" empty-text="暂无数据，请先查询">
          <el-table-column prop="time" label="时间" width="180">
            <template #default="{ row }">{{ formatTime(row.time) }}</template>
          </el-table-column>
          <el-table-column prop="line_id" label="产线ID" width="80" />
          <el-table-column prop="station_id" label="工位ID" width="80" />
          <el-table-column prop="metric_name" label="指标" width="110" />
          <el-table-column prop="metric_value" label="数值" width="100" />
          <el-table-column prop="unit" label="单位" width="80" />
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 多产线对比 -->
      <el-tab-pane label="多产线对比" name="compare">
        <div class="filter-bar">
          <el-select v-model="compareLineIds" placeholder="选择产线（可多选）" multiple style="width: 280px">
            <el-option v-for="l in lines" :key="l.id" :label="l.name" :value="l.id" />
          </el-select>
          <el-select v-model="compareMetric" placeholder="选择指标" style="width: 130px">
            <el-option label="温度" value="temperature" />
            <el-option label="湿度" value="humidity" />
            <el-option label="压力" value="pressure" />
            <el-option label="速度" value="speed" />
          </el-select>
          <el-select v-model="compareMinutes" style="width: 110px">
            <el-option label="近30分钟" :value="30" />
            <el-option label="近1小时" :value="60" />
            <el-option label="近3小时" :value="180" />
            <el-option label="近6小时" :value="360" />
          </el-select>
          <el-button type="primary" @click="loadComparison" :disabled="compareLineIds.length < 2">开始对比</el-button>
          <el-button @click="downloadReport">下载报表</el-button>
        </div>
        <div v-show="compareSeries.length > 0" ref="compareChartRef" class="compare-chart"></div>
        <el-empty v-show="compareSeries.length === 0" description="请选择至少 2 条产线并开始对比" />
      </el-tab-pane>

      <!-- Tab 3: 不良原因分析 -->
      <el-tab-pane label="缺陷分析" name="defect">
        <div class="filter-bar">
          <el-select v-model="defectLineId" placeholder="全部产线" clearable style="width: 150px">
            <el-option v-for="l in lines" :key="l.id" :label="l.name" :value="l.id" />
          </el-select>
          <el-select v-model="defectHours" style="width: 110px">
            <el-option label="近24小时" :value="24" />
            <el-option label="近7天" :value="168" />
            <el-option label="近30天" :value="720" />
          </el-select>
          <el-button type="primary" @click="loadDefectBreakdown">查询</el-button>
        </div>
        <div v-show="defectChartOption" ref="defectChartRef" class="compare-chart"></div>
        <el-empty v-show="!defectChartOption" description="点击查询加载缺陷分析" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const lines = ref<Array<{ id: number; name: string }>>([])

// ---- Tab 1: 数据查询 ----
const activeTab = ref('query')
const lineId = ref<number | null>(null)
const metricName = ref<string | null>(null)
const timeRange = ref<[Date, Date] | null>(null)
const rows = ref<any[]>([])
const loading = ref(false)

// ---- Tab 2: 对比 ----
const compareLineIds = ref<number[]>([])
const compareMetric = ref('temperature')
const compareMinutes = ref(60)
const compareSeries = ref<any[]>([])
const compareChartRef = ref<HTMLDivElement | null>(null)

// ---- Tab 3: 缺陷分析 ----
const defectLineId = ref<number | null>(null)
const defectHours = ref(24)
const defectChartOption = ref<any>(null)
const defectChartRef = ref<HTMLDivElement | null>(null)

async function loadLines() {
  try {
    const resp = await axios.get('/api/v1/lines')
    lines.value = resp.data?.data || []
  } catch (e) { console.error(e) }
}

// ---- 数据查询 ----
async function query() {
  loading.value = true
  try {
    const params: any = { limit: 500 }
    if (lineId.value) params.line_id = lineId.value
    if (metricName.value) params.metric_name = metricName.value
    if (timeRange.value) {
      params.start_time = timeRange.value[0].toISOString()
      params.end_time = timeRange.value[1].toISOString()
    }
    const resp = await axios.get('/api/v1/data/history', { params })
    rows.value = resp.data?.data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}

function exportCSV() {
  const headers = ['时间', '产线ID', '工位ID', '指标', '数值', '单位']
  const csvRows = rows.value.map((r) =>
    [r.time, r.line_id, r.station_id ?? '', r.metric_name, r.metric_value, r.unit ?? ''].join(',')
  )
  const csv = headers.join(',') + '\n' + csvRows.join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `history_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- 多产线对比 ----
async function loadComparison() {
  try {
    const resp = await axios.post('/api/v1/data/comparison', {
      line_ids: compareLineIds.value,
      metric_name: compareMetric.value,
      minutes: compareMinutes.value,
    })
    const data: any[] = resp.data?.data || []
    const allTimes = new Set<string>()
    const lineMap: Record<number, Record<string, number>> = {}
    data.forEach((item) => {
      lineMap[item.line_id] = {}
      item.data_points.forEach((pt: any) => {
        allTimes.add(pt.time)
        lineMap[item.line_id][pt.time] = pt.avg
      })
    })
    const sortedTimes = Array.from(allTimes).sort()
    compareSeries.value = data.map((item) => ({
      name: `产线 ${item.line_id}`,
      type: 'line' as const,
      data: sortedTimes.map((t) => lineMap[item.line_id]?.[t] ?? null),
    }))
    await nextTick()
    renderCompareChart(sortedTimes)
  } catch (e) { console.error(e) }
}

function renderCompareChart(times: string[]) {
  if (!compareChartRef.value) return
  const chart = echarts.init(compareChartRef.value)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: compareSeries.value.map((s) => s.name), textStyle: { color: '#ccc' } },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: times, axisLabel: { color: '#888', rotate: 45 } },
    yAxis: { type: 'value', axisLabel: { color: '#888' } },
    series: compareSeries.value,
  })
}

// ---- 缺陷分析 ----
async function loadDefectBreakdown() {
  try {
    const params: any = { hours: defectHours.value }
    if (defectLineId.value) params.line_id = defectLineId.value
    const resp = await axios.get('/api/v1/alarms/defect-breakdown', { params })
    const data = resp.data?.data || {}
    const cats = data.categories || []
    defectChartOption.value = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', textStyle: { color: '#ccc' } },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        label: { color: '#ccc' },
        data: cats.map((c: any) => ({ name: c.category, value: c.count })),
      }],
    }
    await nextTick()
    renderDefectChart()
  } catch (e) { console.error(e) }
}

function renderDefectChart() {
  if (!defectChartRef.value) return
  const chart = echarts.init(defectChartRef.value)
  chart.setOption(defectChartOption.value)
}

async function downloadReport() {
  try {
    const resp = await axios.post('/api/v1/reports/generate/csv', {
      report_type: 'daily',
      line_id: null,
    }, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `report_daily_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) { console.error(e) }
}

onMounted(loadLines)
</script>

<style scoped>
.history-page { padding: 20px; height: 100vh; background: #0a1628; color: #e0e6ed; overflow: auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 20px; }
.back-link { font-size: 13px; color: #5a7a9a; text-decoration: none; padding: 4px 12px; border: 1px solid rgba(0, 200, 255, 0.2); border-radius: 3px; }
.back-link:hover { color: #00d4ff; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.compare-chart { width: 100%; height: 420px; }
.tabs { margin-top: 8px; }
</style>
