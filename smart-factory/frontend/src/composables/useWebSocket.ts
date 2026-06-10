import { ref, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import type { SensorDataItem, AlarmEvent } from '@/stores/app'

export function useWebSocket() {
  const store = useAppStore()
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectCount = 0

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/ws/live`

    ws.value = new WebSocket(url)
    ws.value.onopen = () => {
      connected.value = true
      reconnectCount = 0
      console.log('[WS] 已连接')
    }

    ws.value.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'sensor_data' && Array.isArray(msg.data)) {
          store.updateLatestData(msg.data as SensorDataItem[])
        } else if (msg.type === 'alarm_event' && msg.data) {
          store.addAlarm(msg.data as AlarmEvent)
        }
      } catch (e) {
        // ignore parse errors
      }
    }

    ws.value.onclose = () => {
      connected.value = false
      console.log('[WS] 断开，将在 3s 后重连...')
      reconnect()
    }

    ws.value.onerror = () => {
      ws.value?.close()
    }
  }

  function reconnect() {
    if (reconnectTimer) return
    const delay = Math.min(3000 * (reconnectCount + 1), 30000)
    reconnectCount++
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  connect()

  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws.value?.close()
  })

  return { connected }
}
