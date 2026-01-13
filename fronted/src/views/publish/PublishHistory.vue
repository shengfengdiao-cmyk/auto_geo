<template>
  <div class="publish-history-page">
    <h2>发布记录</h2>
    <el-table :data="records" stripe>
      <el-table-column prop="article_title" label="文章标题" />
      <el-table-column prop="platform_name" label="平台">
        <template #default="{ row }">
          <el-tag :color="getPlatformColor(row.platform)">
            {{ row.platform_name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="account_name" label="账号" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="published_at" label="发布时间" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button v-if="row.platform_url" text type="primary" @click="openUrl(row.platform_url)">
            查看文章
          </el-button>
          <el-button v-else-if="row.status === 3" text type="warning" @click="retry(row)">
            重试
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { PLATFORMS } from '@/core/config/platform'

interface PublishRecord {
  id: number
  article_id: number
  article_title: string
  account_id: number
  account_name: string
  platform: string
  platform_name: string
  status: number
  platform_url?: string
  error_msg?: string
  retry_count?: number
  created_at?: string
  published_at?: string
}

const records = ref<PublishRecord[]>([])

onMounted(async () => {
  try {
    const response = await fetch('/api/publish/records?limit=50')
    const data = await response.json()
    if (Array.isArray(data)) {
      records.value = data
    }
  } catch (error) {
    console.error('获取发布记录失败:', error)
    ElMessage.error('获取发布记录失败')
  }
})

const openUrl = (url: string) => {
  window.open(url, '_blank')
}

const retry = async (record: PublishRecord) => {
  try {
    const response = await fetch(`/api/publish/retry/${record.id}`, {
      method: 'POST',
    })
    const result = await response.json()
    if (result.success) {
      ElMessage.success('重试任务已创建')
    } else {
      ElMessage.error(result.message || '重试失败')
    }
  } catch (error) {
    console.error('重试失败:', error)
    ElMessage.error('重试失败')
  }
}

const getPlatformColor = (platform: string) => {
  return PLATFORMS[platform]?.color || '#666'
}

const getStatusType = (status: number) => {
  const types: Record<number, string> = { 0: 'info', 1: 'warning', 2: 'success', 3: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status: number) => {
  const texts: Record<number, string> = { 0: '待发布', 1: '发布中', 2: '成功', 3: '失败' }
  return texts[status] || '未知'
}
</script>

<style scoped lang="scss">
.publish-history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;

  h2 {
    margin: 0;
  }
}
</style>
