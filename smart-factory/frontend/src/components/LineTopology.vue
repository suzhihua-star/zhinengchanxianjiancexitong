<template>
  <div class="topology">
    <div class="line-name">产线拓扑 - {{ lineName }}</div>
    <div class="topology-flow">
      <div
        v-for="(station, idx) in stations"
        :key="station.id"
        class="station-node"
        :class="stationStatusClass(station.id)"
      >
        <div class="node-icon">⚙</div>
        <div class="node-name">{{ station.name }}</div>
        <div class="node-code">{{ station.code }}</div>
      </div>
      <div v-if="stations.length === 0" class="empty">暂无工位数据</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const props = defineProps<{
  lineName: string
  stations: Array<{ id: number; name: string; code: string }>
}>()

const store = useAppStore()

function stationStatusClass(stationId: number) {
  const data = store.lineData.filter((d) => d.station_id === stationId)
  if (data.length === 0) return ''
  // 简单判断：如果有指标超出阈值则标红
  // 这里用固定阈值做演示
  const thresholds: Record<string, { max: number; min: number }> = {
    temperature: { max: 170, min: 130 },
    humidity: { max: 60, min: 30 },
    pressure: { max: 0.95, min: 0.55 },
    speed: { max: 1.5, min: 0.7 },
  }
  for (const item of data) {
    const t = thresholds[item.metric_name]
    if (t && (item.metric_value > t.max || item.metric_value < t.min)) {
      return 'danger'
    }
  }
  return 'normal'
}
</script>

<style scoped>
.topology { height: 100%; padding: 12px; }
.line-name { font-size: 13px; color: #8ba8c8; font-weight: 600; margin-bottom: 12px; text-align: center; }
.topology-flow { display: flex; align-items: center; gap: 0; justify-content: center; flex-wrap: wrap; }
.station-node {
  display: flex; flex-direction: column; align-items: center;
  padding: 10px 16px; background: rgba(15, 30, 55, 0.85);
  border: 1px solid rgba(0, 200, 255, 0.2); border-radius: 10px;
  min-width: 80px; transition: all 0.3s;
}
.station-node + .station-node { margin-left: -1px; }
.station-node.normal { border-color: rgba(0, 220, 100, 0.4); }
.station-node.danger { border-color: rgba(255, 50, 50, 0.7); box-shadow: 0 0 12px rgba(255, 50, 50, 0.3); animation: pulse 1s infinite; }
@keyframes pulse { 50% { box-shadow: 0 0 20px rgba(255, 50, 50, 0.5); } }
.node-icon { font-size: 24px; margin-bottom: 4px; }
.node-name { font-size: 12px; color: #c0d0e0; }
.node-code { font-size: 10px; color: #5a7a9a; }
.empty { text-align: center; color: #4a6a8a; font-size: 13px; }
</style>
