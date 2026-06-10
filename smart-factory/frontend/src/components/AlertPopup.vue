<template>
  <Transition name="alert-slide">
    <div v-if="alarm" class="alert-popup" :class="severityClass">
      <div class="alert-icon">⚠</div>
      <div class="alert-body">
        <div class="alert-header">
          <span class="severity-tag">{{ severityLabel }}</span>
          <span class="alert-time">{{ timeStr }}</span>
        </div>
        <div class="alert-msg">{{ alarm.message || `${alarm.metric_name} 异常` }}</div>
        <div class="alert-detail">
          实际值: {{ alarm.actual_value }} | 产线 #{{ alarm.line_id }}
        </div>
      </div>
      <button class="alert-close" @click="$emit('close')">✕</button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import type { AlarmEvent } from '@/stores/app'
import { useAlarmSound } from '@/composables/useAlarm'

const props = defineProps<{ alarm: AlarmEvent | null }>()
defineEmits<{ close: [] }>()

const { play } = useAlarmSound()
const showTimer = ref<ReturnType<typeof setTimeout> | null>(null)

watch(
  () => props.alarm,
  (val) => {
    if (val) {
      play()
      if (showTimer.value) clearTimeout(showTimer.value)
      showTimer.value = setTimeout(() => {/* auto-hide after 8s */ }, 8000)
    }
  },
  { immediate: true }
)

const severityClass = computed(() => `severity-${props.alarm?.severity || 'warning'}`)
const severityLabel = computed(() => {
  const map: Record<string, string> = { warning: '警告', critical: '严重', emergency: '紧急' }
  return map[props.alarm?.severity || 'warning'] || '警告'
})
const timeStr = computed(() => {
  if (!props.alarm?.triggered_at) return ''
  return new Date(props.alarm.triggered_at).toLocaleTimeString('zh-CN')
})
</script>

<style scoped>
.alert-popup {
  position: fixed;
  top: 60px;
  right: 20px;
  width: 360px;
  background: rgba(10, 20, 40, 0.95);
  border: 2px solid;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  backdrop-filter: blur(10px);
  z-index: 9999;
}
.severity-warning { border-color: rgba(255, 180, 0, 0.7); }
.severity-critical { border-color: rgba(255, 100, 50, 0.8); animation: flash-border 0.5s infinite alternate; }
.severity-emergency { border-color: rgba(255, 30, 30, 0.9); animation: flash-border 0.3s infinite alternate; }

@keyframes flash-border {
  from { border-color: rgba(255, 50, 50, 0.4); }
  to { border-color: rgba(255, 50, 50, 1); }
}

.alert-icon { font-size: 28px; flex-shrink: 0; }
.alert-body { flex: 1; }
.alert-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.severity-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 3px; font-weight: 600;
}
.severity-warning .severity-tag { background: rgba(255, 180, 0, 0.3); color: #ffb400; }
.severity-critical .severity-tag { background: rgba(255, 100, 50, 0.3); color: #ff6432; }
.severity-emergency .severity-tag { background: rgba(255, 30, 30, 0.3); color: #ff1e1e; }

.alert-time { font-size: 11px; color: #5a7a9a; }
.alert-msg { font-size: 14px; color: #e0e6ed; font-weight: 500; margin-bottom: 4px; }
.alert-detail { font-size: 12px; color: #6a8aaa; }
.alert-close {
  background: none; border: none; color: #5a7a9a; cursor: pointer; font-size: 16px; padding: 4px;
}
.alert-close:hover { color: #fff; }

.alert-slide-enter-active { transition: all 0.4s ease-out; }
.alert-slide-leave-active { transition: all 0.3s ease-in; }
.alert-slide-enter-from { transform: translateX(400px); opacity: 0; }
.alert-slide-leave-to { transform: translateX(400px); opacity: 0; }
</style>
