<template>
  <div class="gauge-card" :class="statusClass">
    <div class="label">{{ metricLabel }}</div>
    <div class="value">
      <span class="number">{{ displayValue }}</span>
      <span class="unit">{{ unit }}</span>
    </div>
    <div class="info">{{ stationName || '--' }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  metricLabel: string
  value: number | null
  unit: string
  stationName?: string
  upperLimit?: number | null
  lowerLimit?: number | null
}>()

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '--'
  return props.value.toFixed(2)
})

const statusClass = computed(() => {
  if (props.value === null) return ''
  if (props.upperLimit !== null && props.upperLimit !== undefined && props.value > props.upperLimit) return 'danger'
  if (props.lowerLimit !== null && props.lowerLimit !== undefined && props.value < props.lowerLimit) return 'danger'
  if (props.upperLimit !== null && props.upperLimit !== undefined && props.value > props.upperLimit * 0.85) return 'warning'
  if (props.lowerLimit !== null && props.lowerLimit !== undefined && props.value < props.lowerLimit * 1.15) return 'warning'
  return 'normal'
})
</script>

<style scoped>
.gauge-card {
  background: rgba(15, 30, 55, 0.85);
  border: 1px solid rgba(0, 200, 255, 0.15);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  transition: all 0.3s;
}
.gauge-card.normal { border-color: rgba(0, 220, 100, 0.5); }
.gauge-card.warning { border-color: rgba(255, 180, 0, 0.7); box-shadow: 0 0 12px rgba(255, 180, 0, 0.2); }
.gauge-card.danger { border-color: rgba(255, 50, 50, 0.8); box-shadow: 0 0 16px rgba(255, 50, 50, 0.3); animation: pulse-danger 1s infinite; }

@keyframes pulse-danger {
  0%, 100% { box-shadow: 0 0 8px rgba(255, 50, 50, 0.3); }
  50% { box-shadow: 0 0 20px rgba(255, 50, 50, 0.6); }
}

.label { font-size: 12px; color: #7b93b3; margin-bottom: 4px; }
.number { font-size: 26px; font-weight: 700; color: #e0e6ed; font-family: 'DIN', 'Consolas', monospace; }
.unit { font-size: 13px; color: #5a7a9a; margin-left: 2px; }
.info { font-size: 11px; color: #4a6a8a; margin-top: 2px; }
</style>
