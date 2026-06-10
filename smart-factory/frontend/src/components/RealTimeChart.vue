<template>
  <div class="chart-container">
    <VChart :option="chartOption" :autoresize="true" style="height: 100%" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

interface TrendPoint {
  time: string
  avg?: number | null
  min?: number | null
  max?: number | null
}

const props = defineProps<{
  title: string
  data: TrendPoint[]
  unit: string
  color?: string
}>()

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  title: {
    text: props.title,
    left: 'center',
    textStyle: { color: '#8ba8c8', fontSize: 13, fontWeight: 'normal' },
    top: 4,
  },
  tooltip: { trigger: 'axis' },
  legend: {
    bottom: 2,
    textStyle: { color: '#6a8aaa', fontSize: 10 },
    data: ['平均值', '最小值', '最大值'],
  },
  grid: { top: 36, bottom: 26, left: 48, right: 16 },
  xAxis: {
    type: 'category',
    data: props.data.map((d) => {
      const t = new Date(d.time)
      return `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}`
    }),
    axisLine: { lineStyle: { color: '#1e3a5f' } },
    axisLabel: { color: '#5a7a9a', fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      color: '#5a7a9a',
      fontSize: 10,
      formatter: `{value} ${props.unit}`,
    },
    splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } },
  },
  series: [
    {
      name: '平均值',
      type: 'line',
      data: props.data.map((d) => d.avg),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: props.color || '#00d4ff', width: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,212,255,0.25)' }, { offset: 1, color: 'rgba(0,212,255,0.01)' }] } },
    },
    {
      name: '最小值',
      type: 'line',
      data: props.data.map((d) => d.min),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: 'rgba(0,220,100,0.5)', width: 1, type: 'dashed' },
    },
    {
      name: '最大值',
      type: 'line',
      data: props.data.map((d) => d.max),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: 'rgba(255,180,0,0.5)', width: 1, type: 'dashed' },
    },
  ],
}))
</script>

<style scoped>
.chart-container { width: 100%; height: 100%; min-height: 200px; }
</style>
