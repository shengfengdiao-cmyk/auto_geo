<template>
  <div class="scheduler-page">
    <!-- 头部 -->
    <header class="page-header">
      <div class="header-left">
        <div class="header-icon">
          <el-icon><Timer /></el-icon>
        </div>
        <div class="header-text">
          <h1 class="page-title">定时任务调度中心</h1>
          <p class="page-desc">动态管理后台任务频率，无需重启服务即刻生效</p>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="loadTasks" :loading="loading">
          <el-icon class="mr-1"><Refresh /></el-icon> 刷新状态
        </el-button>
      </div>
    </header>

    <!-- 任务卡片列表 -->
    <div class="tasks-section" v-loading="loading">
      <el-card
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        shadow="hover"
      >
        <div class="task-card-content">
          <!-- 任务基本信息 -->
          <div class="task-main">
            <div class="task-header">
              <div class="task-title">
                <el-icon class="task-icon"><component :is="getTaskIcon(task.task_key)" /></el-icon>
                <span class="task-name">{{ task.name }}</span>
              </div>
              <div class="task-status">
                <div :class="['status-indicator', task.is_active ? 'running' : 'stopped']"></div>
                <span :class="['status-text', task.is_active ? 'running' : 'stopped']">
                  {{ task.is_active ? '运行中' : '已停止' }}
                </span>
              </div>
            </div>
            <p class="task-desc">{{ task.description }}</p>
          </div>

          <!-- 执行策略与时间 -->
          <div class="task-schedule">
            <div class="schedule-item">
              <span class="schedule-label">执行策略</span>
              <el-tag :type="getCronTagType(task.cron_expression)" size="small">
                {{ cronToHuman(task.cron_expression) }}
              </el-tag>
            </div>
            <div class="schedule-item" v-if="task.is_active">
              <span class="schedule-label">下次执行</span>
              <span class="schedule-time">{{ getNextRunTime(task.cron_expression) }}</span>
            </div>
          </div>

          <!-- 操作区 -->
          <div class="task-actions">
            <el-switch
              v-model="task.is_active"
              inline-prompt
              active-text=""
              inactive-text=""
              size="large"
              style="--el-switch-on-color: #13ce66; --el-switch-off-color: #d1d5db"
              @change="handleStatusChange(task)"
            />
            <el-button
              type="primary"
              link
              @click="openEdit(task)"
              class="edit-btn"
            >
              <el-icon><Timer /></el-icon> 修改频率
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 修改频率对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="修改执行频率"
      width="600px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <el-form label-width="100px" class="edit-form">
        <el-form-item label="任务名称">
          <el-input v-model="currentTask.name" disabled />
        </el-form-item>

        <!-- 快捷预设卡片 -->
        <div class="preset-section">
          <span class="preset-label">快捷预设</span>
          <div class="preset-cards">
            <div
              v-for="preset in cronPresets"
              :key="preset.id"
              :class="['preset-card', { active: currentTask.cron_expression === preset.cron }]"
              @click="selectPreset(preset.cron)"
            >
              <el-icon class="preset-icon">
                <component :is="preset.icon" />
              </el-icon>
              <div class="preset-info">
                <span class="preset-name">{{ preset.name }}</span>
                <span class="preset-desc">{{ preset.desc }}</span>
              </div>
              <el-icon v-if="currentTask.cron_expression === preset.cron" class="check-icon">
                <Check />
              </el-icon>
            </div>
          </div>
        </div>

        <!-- 高级设置折叠面板 -->
        <el-collapse class="advanced-collapse">
          <el-collapse-item title="高级设置 - 自定义 Cron 表达式" name="advanced">
            <el-form-item label="Cron表达式">
              <el-input
                v-model="currentTask.cron_expression"
                placeholder="例如: */5 * * * *"
                class="cron-input"
              >
                <template #prepend>
                  <el-icon><EditPen /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <div class="cron-examples">
              <span class="example-title">示例说明：</span>
              <ul>
                <li><code>* * * * *</code> - 每分钟执行</li>
                <li><code>*/5 * * * *</code> - 每5分钟执行</li>
                <li><code>0 * * * *</code> - 每小时执行</li>
                <li><code>0 2 * * *</code> - 每天凌晨2点执行</li>
                <li><code>0 9 * * 1-5</code> - 工作日早上9点执行</li>
              </ul>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCron" :loading="saving">
          <el-icon><Check /></el-icon> 保存并生效
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Timer, Refresh, EditPen, Check, DataLine, ChatDotRound, DocumentCopy, Picture, Tools } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import cronstrue from 'cronstrue/i18n' // 稍后可以引入轻量级 cron 解析库

// 假设后端地址，如果配置了代理可以直接写 /api/...
const API_BASE = 'http://127.0.0.1:8001/api/scheduler'

interface Task {
  id: number
  name: string
  task_key: string
  cron_expression: string
  is_active: boolean
  description: string
}

interface CronPreset {
  id: string
  name: string
  desc: string
  cron: string
  icon: any
}

const tasks = ref<Task[]>([])
const loading = ref(false)
const saving = ref(false)
const showEditDialog = ref(false)
const currentTask = ref<any>({})

// Cron 快捷预设
const cronPresets: CronPreset[] = [
  {
    id: 'test',
    name: '测试模式',
    desc: '每分钟执行，用于快速测试',
    cron: '*/1 * * * *',
    icon: Tools
  },
  {
    id: 'stable',
    name: '生产稳健',
    desc: '每小时执行，平衡性能',
    cron: '0 * * * *',
    icon: DocumentCopy
  },
  {
    id: 'daily',
    name: '每日执行',
    desc: '凌晨2点执行，避开高峰',
    cron: '0 2 * * *',
    icon: DataLine
  },
  {
    id: 'workday',
    name: '工作日',
    desc: '工作日9点执行',
    cron: '0 9 * * 1-5',
    icon: ChatDotRound
  },
  {
    id: 'fast',
    name: '极速抓取',
    desc: '每5分钟执行，高频模式',
    cron: '*/5 * * * *',
    icon: Picture
  }
]

// 获取任务图标
const getTaskIcon = (taskKey: string) => {
  const iconMap: Record<string, any> = {
    '收录查询': DataLine,
    '关键词监控': ChatDotRound,
    '其他': Timer
  }
  return iconMap[taskKey] || Timer
}

// Cron 表达式转自然语言
const cronToHuman = (cron: string): string => {
  const map: Record<string, string> = {
    '*/1 * * * *': '每分钟执行',
    '*/5 * * * *': '每5分钟执行',
    '0 * * * *': '每小时执行',
    '0 2 * * *': '每天凌晨 02:00',
    '0 9 * * 1-5': '工作日 09:00',
    '*/10 * * * *': '每10分钟执行',
    '*/30 * * * *': '每30分钟执行',
    '0 */2 * * *': '每2小时执行',
    '0 */4 * * *': '每4小时执行',
    '0 */6 * * *': '每6小时执行',
    '0 0 * * *': '每天 00:00'
  }
  return map[cron] || '自定义频率'
}

// 获取 Cron 标签类型
const getCronTagType = (cron: string): string => {
  if (cron.startsWith('*/1')) return 'warning'
  if (cron.startsWith('*/5') || cron.startsWith('*/10')) return 'primary'
  if (cron.includes('0 9 * * 1-5')) return 'success'
  return 'info'
}

// 计算下次执行时间
const getNextRunTime = (cron: string): string => {
  try {
    // 简单解析，实际可引入 cron-parser 库
    const now = new Date()
    const parts = cron.split(' ')

    if (parts[0].startsWith('*/')) {
      const interval = parseInt(parts[0].substring(2))
      const nextMin = Math.ceil(now.getMinutes() / interval) * interval
      const nextTime = new Date(now)
      nextTime.setMinutes(nextMin)
      if (nextTime <= now) {
        nextTime.setMinutes(nextMin + interval)
      }
      return formatTime(nextTime)
    }

    if (parts[1] === '0' && parts[2] === '*') {
      const nextHour = new Date(now)
      nextHour.setHours(now.getHours() + 1, 0, 0, 0)
      return formatTime(nextHour)
    }

    if (parts[1] === '2' && parts[2] === '*') {
      const tomorrow = new Date(now)
      tomorrow.setDate(tomorrow.getDate() + 1)
      tomorrow.setHours(2, 0, 0, 0)
      return formatTime(tomorrow)
    }

    return '计算中...'
  } catch {
    return '未知'
  }
}

// 格式化时间
const formatTime = (date: Date): string => {
  const now = new Date()
  const diff = date.getTime() - now.getTime()

  if (diff < 60000) return '即将执行'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟后`

  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours}小时后`

  const days = Math.floor(hours / 24)
  return `${days}天后 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/jobs`)
    tasks.value = res.data
  } catch (error) {
    ElMessage.error('无法连接到调度中心')
  } finally {
    loading.value = false
  }
}

// 切换开关状态
const handleStatusChange = async (row: Task) => {
  try {
    await updateTaskApi(row)
    ElMessage.success(row.is_active ? `任务 [${row.name}] 已启动` : `任务 [${row.name}] 已暂停`)
  } catch (error) {
    row.is_active = !row.is_active
    ElMessage.error('状态更新失败')
  }
}

// 打开编辑
const openEdit = (row: Task) => {
  currentTask.value = { ...row }
  showEditDialog.value = true
}

// 选择预设
const selectPreset = (cron: string) => {
  currentTask.value.cron_expression = cron
}

// 保存 Cron 修改
const saveCron = async () => {
  saving.value = true
  try {
    await updateTaskApi(currentTask.value)
    ElMessage.success('执行频率已更新，下次执行将按新规则')
    showEditDialog.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error('更新失败，请检查Cron格式')
  } finally {
    saving.value = false
  }
}

// 统一更新接口
const updateTaskApi = async (task: Task) => {
  const payload = {
    cron_expression: task.cron_expression,
    is_active: task.is_active
  }
  await axios.put(`${API_BASE}/jobs/${task.id}`, payload)
}

onMounted(() => {
  loadTasks()
  // 启动定时刷新倒计时
  setInterval(() => {
    tasks.value.forEach(task => {
      task.next_run = getNextRunTime(task.cron_expression)
    })
  }, 30000)
})
</script>

<style scoped lang="scss">
.scheduler-page {
  padding: 24px;
  background: #f3f4f6;
  min-height: 100vh;
}

/* 头部样式 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  margin-bottom: 24px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 24px;
    }

    .page-title {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
      color: #1f2937;
    }

    .page-desc {
      margin: 0;
      font-size: 13px;
      color: #6b7280;
    }
  }
}

/* 任务卡片列表区 */
.tasks-section {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.task-card {
  border-radius: 12px;
  border: none;

  :deep(.el-card__body) {
    padding: 20px;
  }

  &.is-hover:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
    transition: all 0.3s ease;
  }
}

.task-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.task-main {
  .task-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .task-title {
    display: flex;
    align-items: center;
    gap: 10px;

    .task-icon {
      font-size: 18px;
      color: #6366f1;
    }

    .task-name {
      font-weight: 600;
      color: #1f2937;
      font-size: 16px;
    }
  }

  .task-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;

    .status-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;

      &.running {
        background: #4caf50;
        box-shadow: 0 0 8px rgba(76, 175, 80, 0.4);
        animation: pulse 2s infinite;
      }

      &.stopped {
        background: #9ca3af;
      }
    }

    .status-text {
      &.running {
        color: #4caf50;
      }

      &.stopped {
        color: #9ca3af;
      }
    }
  }

  .task-desc {
    color: #6b7280;
    font-size: 13px;
    line-height: 1.5;
    margin: 0;
  }
}

.task-schedule {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;

  .schedule-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;

    .schedule-label {
      color: #6b7280;
    }

    .schedule-time {
      color: #6366f1;
      font-weight: 500;
    }
  }
}

.task-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
  margin-top: auto;

  .edit-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
  }
}

/* 弹窗样式 */
.edit-form {
  .mr-1 {
    margin-right: 4px;
  }
}

.preset-section {
  margin: 20px 0;

  .preset-label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 12px;
  }

  .preset-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

.preset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;

  &:hover {
    border-color: #6366f1;
    background: #f9fafb;
  }

  &.active {
    border-color: #6366f1;
    background: #eef2ff;
  }

  .preset-icon {
    font-size: 24px;
    color: #6366f1;
  }

  .preset-info {
    display: flex;
    flex-direction: column;
    flex: 1;

    .preset-name {
      font-weight: 600;
      font-size: 14px;
      color: #1f2937;
    }

    .preset-desc {
      font-size: 12px;
      color: #6b7280;
    }
  }

  .check-icon {
    position: absolute;
    top: 8px;
    right: 8px;
    font-size: 16px;
    color: #6366f1;
  }
}

.advanced-collapse {
  margin-top: 20px;

  :deep(.el-collapse-item__header) {
    font-weight: 500;
    color: #6b7280;
  }

  :deep(.el-collapse-item__content) {
    padding-top: 16px;
  }
}

.cron-input {
  :deep(.el-input-group__prepend) {
    background: #f3f4f6;
    border-color: #d1d5db;
  }
}

.cron-examples {
  margin-top: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;

  .example-title {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 8px;
  }

  ul {
    margin: 0;
    padding-left: 0;
    list-style: none;

    li {
      font-size: 12px;
      color: #6b7280;
      margin-bottom: 6px;
      font-family: 'Consolas', monospace;

      code {
        background: #e5e7eb;
        padding: 2px 6px;
        border-radius: 4px;
        color: #6366f1;
      }
    }
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 8px rgba(76, 175, 80, 0.4);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 12px rgba(76, 175, 80, 0.6);
  }
}
</style>
