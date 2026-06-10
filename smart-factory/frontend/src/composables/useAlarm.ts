import { ref } from 'vue'

export function useAlarmSound() {
  const audioCtx = ref<AudioContext | null>(null)
  const playing = ref(false)

  function play() {
    if (playing.value) return
    try {
      if (!audioCtx.value) {
        audioCtx.value = new AudioContext()
      }
      const ctx = audioCtx.value

      // 告警音：800Hz 方波，持续 0.3s，重复 3 次
      for (let i = 0; i < 3; i++) {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = 'square'
        osc.frequency.value = 800
        gain.gain.value = 0.15
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(ctx.currentTime + i * 0.4)
        osc.stop(ctx.currentTime + i * 0.4 + 0.3)
      }
      playing.value = true
      setTimeout(() => {
        playing.value = false
      }, 1500)
    } catch (e) {
      // 浏览器可能禁止自动播放音频
      console.warn('告警音播放失败:', e)
    }
  }

  return { play }
}
