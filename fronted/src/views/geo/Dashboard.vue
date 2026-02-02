<template>
  <div class="monitor-page">
    <!-- 1. 核心指标卡片 -->
    <div class="stats-cards">
      <div class="card">
        <div class="card-title">GEO文章总数</div>
        <div class="card-value">{{ stats.total_articles }}</div>
        <div class="card-desc">累计生成</div>
      </div>
      <div class="card">
        <div class="card-title">已发布文章</div>
        <div class="card-value highlight">{{ stats.published_count }}</div>
        <div class="card-desc">发布率 {{ publishRate }}%</div>
      </div>
      <div class="card">
        <div class="card-title">AI收录数</div>
        <div class="card-value success">{{ stats.indexed_count }}</div>
        <div class="card-desc">收录率 {{ stats.index_rate }}%</div>
      </div>
      <div class="card">
        <div class="card-title">活跃项目</div>
        <div class="card-value">{{ overview.total_projects }}</div>
        <div class="card-desc">正在运行中</div>
      </div>
    </div>

    <!-- 2. 图表区域 -->
    <div class="charts-container">
      <!-- 左侧：收录漏斗 -->
      <div class="chart-box">
        <h3 class="chart-title">SEO 转化漏斗</h3>
        <div ref="funnelChartRef" class="chart"></div>
      </div>
      
      <!-- 右侧：平台分布 -->
      <div class="chart-box">
        <h3 class="chart-title">平台收录分布</h3>
        <div ref="pieChartRef" class="chart"></div>
      </div>
    </div>

    <!-- 3. 底部：收录趋势 -->
    <div class="chart-box full-width">
      <h3 class="chart-title">近30天收录趋势</h3>
      <div ref="lineChartRef" class="chart"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
// 假设你有一个封装好的 axios 实例，或者直接用 fetch
import axios from 'axios' 

// ==================== 状态定义 ====================
const stats = ref({
  total_articles: 0,
  published_count: 0,
  indexed_count: 0,
  index_rate: 0,
  platform_distribution: {}
})

const overview = ref({
  total_projects: 0
})

const publishRate = computed(() => {
  if (stats.value.total_articles === 0) return 0
  return ((stats.value.published_count / stats.value.total_articles) * 100).toFixed(1)
})

// 图表 DOM 引用
const funnelChartRef = ref(null)
const pieChartRef = ref(null)
const lineChartRef = ref(null)

// ==================== 数据加载 ====================
// fronted/src/views/geo/Dashboard.vue

const loadData = async () => {
  try {
    // 1. 获取文章统计
    // 🌟 修正点1：确保地址是 8001 且拼写是 article-stats (复数)
    const res1 = await axios.get('http://127.0.0.1:8001/api/reports/article-stats')
    
    // 🌟 修正点2：看你的浏览器截图，后端直接返回了数据对象，没有包裹 {code: 200, data: ...}
    // 所以直接用 res1.data 即可，不需要判断 success
    stats.value = res1.data
    
    // 数据拿到后，初始化图表
    initFunnelChart()
    initPieChart()

    // 2. 获取概览
    const res2 = await axios.get('http://127.0.0.1:8001/api/reports/overview')
    overview.value = res2.data

    // 3. 趋势图
    initLineChart()
    
  } catch (error) {
    console.error("加载报表失败", error)
    // 可以在这里加个 ElMessage.error('数据加载失败')
  }
}

// ==================== 图表初始化 ====================

const initFunnelChart = () => {
  const chart = echarts.init(funnelChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        name: 'SEO转化',
        type: 'funnel',
        left: '10%',
        width: '80%',
        label: { formatter: '{b}: {c}' },
        data: [
          { value: stats.value.total_articles, name: '生成文章' },
          { value: stats.value.published_count, name: '已发布' },
          { value: stats.value.indexed_count, name: '已收录' }
        ]
      }
    ]
  })
}

const initPieChart = () => {
  const chart = echarts.init(pieChartRef.value)
  const data = Object.entries(stats.value.platform_distribution).map(([k, v]) => ({ value: v, name: k }))
  
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center', textStyle: { color: '#fff' } },
    series: [
      {
        name: '发布平台',
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: {
          borderRadius: 10,
          borderColor: '#1e1e1e',
          borderWidth: 2
        },
        data: data.length ? data : [{value: 0, name: '暂无数据'}]
      }
    ]
  })
}

const initLineChart = () => {
  const chart = echarts.init(lineChartRef.value)
  // 模拟最近7天趋势
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: days, axisLabel: { color: '#999' } },
    yAxis: { type: 'value', axisLabel: { color: '#999' }, splitLine: { lineStyle: { color: '#333' } } },
    series: [
      {
        data: [8, 12, 10, 15, 20, 25, stats.value.indexed_count], // 模拟上升趋势
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.2 },
        itemStyle: { color: '#6366f1' }
      }
    ]
  })
}

onMounted(() => {
  nextTick(() => {
    loadData()
  })
  
  // 监听窗口大小变化，重绘图表
  window.addEventListener('resize', () => {
    echarts.dispose(funnelChartRef.value)
    echarts.dispose(pieChartRef.value)
    echarts.dispose(lineChartRef.value)
    initFunnelChart()
    initPieChart()
    initLineChart()
  })
})
</script>

<style scoped lang="scss">
.monitor-page {
  padding: 24px;
  color: #fff;
}

/* 顶部卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;

  .card {
    background: #1e1e1e;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.05);
    
    .card-title { font-size: 14px; color: #888; margin-bottom: 8px; }
    .card-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
    .card-desc { font-size: 12px; color: #666; }
    
    .highlight { color: #409eff; }
    .success { color: #67c23a; }
  }
}

/* 图表容器 */
.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-box {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.05);

  .chart-title {
    font-size: 16px;
    margin-bottom: 20px;
    font-weight: 600;
  }

  .chart {
    height: 300px;
    width: 100%;
  }
  
  &.full-width {
    width: 100%;
  }
}
</style>