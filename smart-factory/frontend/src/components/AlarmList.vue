<template>
  <div class="alarm-list">
    <div class="list-header">
      <span class="title">实时告警</span>
      <span class="count">{{ alarms.length }} 条</span>
    </div>
    <div class="list-body">
      <div
        v-for="alarm in alarms"
        :key="alarm.id"
        class="alarm-item"
        :class="`severity-${alarm.severity}`"
      >
        <div class="alarm-left">
          <span class="dot"></span>
          <div>
            <div class="alarm-msg">{{ alarm.message || alarm.metric_name }}</div>
            <div class="alarm-time">{{ formatTime(alarm.triggered_at) }}</div>
          </div>
        </div>
        <el-tag
          :type="alarm.severity === 'emergency' ? 'danger' : alarm.severity === 'critical' ? 'warning' : ''"
          size="small"
          effect="dark"
        >
          {{ severityLabel(alarm.severity) }}
        </el-tag>
      </div>
      <div v-if="alarms.length === 0" class="empty">暂无告警</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AlarmEvent } from '@/stores/app'

defineProps<{ alarms: AlarmEvent[] }>()

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString('zh-CN')
}

function severityLabel(s: string) {
  const m: Record<string, string> = { warning: '警告', critical: '严重', emergency: '紧急' }
  return m[s] || s
}
</script>

<style scoped>
.alarm-list { height: 100%; display: flex; flex-direction: column; }
.list-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-bottom: 1px solid rgba(0, 200, 255, 0.1);
}
.title { font-size: 14px; color: #8ba8c8; font-weight: 600; }
.count { font-size: 12px; color: #ff6464; }
.list-body { flex: 1; overflow-y: auto; padding: 4px 0; }
.alarm-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; border-bottom: 1px solid rgba(30, 58, 95, 0.4);
  transition: background 0.2s;
}
.alarm-item:hover { background: rgba(0, 150, 255, 0.05); }
.alarm-left { display: flex; align-items: center; gap: 8px; }
.dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.severity-warning .dot { background: #ffb400; }
.severity-critical .dot { background: #ff6432; }
.severity-emergency .dot { background: #ff1e1e; animation: blink 0.5s infinite; }

@keyframes blink { 50% { opacity: 0.3; } }

.alarm-msg { font-size: 13px; color: #d0d8e0; }
.alarm-time { font-size: 11px; color: #5a7a9a; margin-top: 2px; }
.empty { text-align: center; padding: 40px; color: #4a6a8a; font-size: 13px; }
</style>
