import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface SensorDataItem {
  line_id: number
  station_id: number | null
  metric_name: string
  metric_value: number
  unit: string | null
  time: string | null
}

export interface AlarmEvent {
  id: number
  rule_id: number | null
  line_id: number
  station_id: number | null
  metric_name: string
  actual_value: number | null
  expected_range: string | null
  severity: string
  message: string | null
  triggered_at: string
  status?: string
}

export const useAppStore = defineStore('app', () => {
  // 实时数据
  const latestData = ref<SensorDataItem[]>([])
  // 告警列表（未确认的在前）
  const alarms = ref<AlarmEvent[]>([])
  // 当前选中产线
  const selectedLine = ref<number>(1)

  const lineData = computed(() =>
    latestData.value.filter((d) => d.line_id === selectedLine.value)
  )

  const metricsByLine = computed(() => {
    const map: Record<number, SensorDataItem[]> = {}
    for (const item of latestData.value) {
      if (!map[item.line_id]) map[item.line_id] = []
      map[item.line_id].push(item)
    }
    return map
  })

  const activeAlarms = computed(() =>
    alarms.value.filter((a) => a.status !== 'resolved').slice(0, 10)
  )

  function updateLatestData(data: SensorDataItem[]) {
    for (const item of data) {
      const idx = latestData.value.findIndex(
        (d) =>
          d.line_id === item.line_id &&
          d.station_id === item.station_id &&
          d.metric_name === item.metric_name
      )
      if (idx >= 0) {
        latestData.value[idx] = item
      } else {
        latestData.value.push(item)
      }
    }
  }

  function addAlarm(alarm: AlarmEvent) {
    const exists = alarms.value.find((a) => a.id === alarm.id)
    if (!exists) {
      alarms.value.unshift(alarm)
      // 只保留最近 200 条
      if (alarms.value.length > 200) alarms.value.length = 200
    }
  }

  return {
    latestData,
    alarms,
    selectedLine,
    lineData,
    metricsByLine,
    activeAlarms,
    updateLatestData,
    addAlarm,
  }
})
