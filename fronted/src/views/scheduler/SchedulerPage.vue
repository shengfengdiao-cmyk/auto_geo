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

    <!-- 任务列表 -->
    <div class="tasks-section">
      <el-table 
        :data="tasks" 
        v-loading="loading" 
        style="width: 100%" 
        :header-cell-style="{ background: '#f9fafb', color: '#606266' }"
      >
        <el-table-column prop="name" label="任务名称" width="220">
          <template #default="{ row }">
            <span class="task-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="功能描述" min-width="300">
          <template #default="{ row }">
            <span class="task-desc">{{ row.description }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="执行频率 (Cron)" width="250">
          <template #default="{ row }">
            <el-tag effect="plain" class="cron-tag" type="info">
              {{ row.cron_expression }}
            </el-tag>
            <span class="cron-desc">{{ getCronDesc(row.cron_expression) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="运行状态" width="120">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              inline-prompt
              active-text="运行"
              inactive-text="暂停"
              style="--el-switch-on-color: #13ce66; --el-switch-off-color: #ff4949"
              @change="handleStatusChange(row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">
              <el-icon class="mr-1"><Edit /></el-icon> 修改频率
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 修改频率对话框 -->
    <el-dialog 
      v-model="showEditDialog" 
      title="修改执行频率" 
      width="500px"
      destroy-on-close
    >
      <el-form label-width="100px" class="edit-form">
        <el-form-item label="任务名称">
          <el-input v-model="currentTask.name" disabled />
        </el-form-item>
        <el-form-item label="Cron表达式">
          <el-input v-model="currentTask.cron_expression" placeholder="例如: */5 * * * *" />
        </el-form-item>
        
        <div class="cron-tips">
          <p class="tips-title">常用配置参考：</p>
          <ul>
            <li @click="quickSetCron('*/1 * * * *')"><code>*/1 * * * *</code> 每 1 分钟执行一次 (测试用)</li>
            <li @click="quickSetCron('*/5 * * * *')"><code>*/5 * * * *</code> 每 5 分钟执行一次</li>
            <li @click="quickSetCron('0 * * * *')"><code>0 * * * *</code> 每小时执行一次</li>
            <li @click="quickSetCron('0 2 * * *')"><code>0 2 * * *</code> 每天凌晨 2:00 执行</li>
            <li @click="quickSetCron('0 9 * * 1-5')"><code>0 9 * * 1-5</code> 工作日早上 9:00 执行</li>
          </ul>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCron" :loading="saving">保存并生效</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Timer, Refresh, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

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

const tasks = ref<Task[]>([])
const loading = ref(false)
const saving = ref(false)
const showEditDialog = ref(false)
const currentTask = ref<any>({})

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
    row.is_active = !row.is_active // 失败则回滚UI状态
    ElMessage.error('状态更新失败')
  }
}

// 打开编辑
const openEdit = (row: Task) => {
  currentTask.value = { ...row }
  showEditDialog.value = true
}

// 快速设置 Cron
const quickSetCron = (cron: string) => {
  currentTask.value.cron_expression = cron
}

// 保存 Cron 修改
const saveCron = async () => {
  saving.value = true
  try {
    await updateTaskApi(currentTask.value)
    ElMessage.success('执行频率已更新，下次执行将按新规则')
    showEditDialog.value = false
    loadTasks() // 刷新列表
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

// 简单的 Cron 描述辅助函数
const getCronDesc = (cron: string) => {
  if (cron.startsWith('*/1 *')) return ' (每分钟)'
  if (cron.startsWith('*/5 *')) return ' (每5分钟)'
  if (cron === '0 * * * *') return ' (每小时)'
  if (cron.includes('0 2 * * *')) return ' (凌晨2点)'
  return ''
}

onMounted(() => {
  loadTasks()
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

/* 任务列表区 */
.tasks-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  
  .task-name {
    font-weight: 600;
    color: #374151;
  }
  
  .task-desc {
    color: #6b7280;
    font-size: 13px;
  }

  .cron-tag {
    font-family: 'Consolas', monospace;
    font-size: 13px;
    letter-spacing: 0.5px;
  }
  
  .cron-desc {
    margin-left: 8px;
    font-size: 12px;
    color: #9ca3af;
  }
  
  .mr-1 {
    margin-right: 4px;
  }
}

/* 弹窗样式 */
.cron-tips {
  margin-top: 20px;
  padding: 15px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;

  .tips-title {
    margin: 0 0 10px 0;
    font-size: 13px;
    font-weight: 600;
    color: #4b5563;
  }

  ul {
    padding-left: 0;
    margin: 0;
    list-style: none;

    li {
      font-size: 12px;
      color: #6b7280;
      margin-bottom: 8px;
      cursor: pointer;
      transition: color 0.2s;

      code {
        background: #e5e7eb;
        padding: 2px 6px;
        border-radius: 4px;
        color: #ef4444;
        margin-right: 8px;
        font-family: monospace;
      }

      &:hover {
        color: #6366f1;
        code {
          background: #e0e7ff;
        }
      }
    }
  }
}
</style>