<template>
  <div class="keywords-page">
    <!-- 头部 - 项目选择器 -->
    <header class="page-header">
      <div class="header-left">
        <div class="header-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
          </svg>
        </div>
        <div class="header-text">
          <h1 class="page-title">关键词蒸馏</h1>
          <p class="page-desc">根据领域关键词智能生成用户提问句</p>
        </div>
      </div>
      <div class="header-right">
        <el-select
          v-model="selectedProjectId"
          placeholder="选择项目"
          size="large"
          style="width: 280px"
          @change="handleProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="`${project.name} - ${project.company_name}`"
            :value="project.id"
          >
            <div class="project-option">
              <span class="option-name">{{ project.name }}</span>
              <span class="option-company">{{ project.company_name }}</span>
            </div>
          </el-option>
          <template #empty>
            <div class="project-empty">
              <p>还没有项目</p>
              <el-button type="primary" link @click="goToProjects">去创建</el-button>
            </div>
          </template>
        </el-select>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧 - 蒸馏面板 -->
      <aside class="distill-sidebar">
        <div class="sidebar-header">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
          </div>
          <div>
            <h3 class="sidebar-title">蒸馏面板</h3>
            <span v-if="currentProject" class="sidebar-project">{{ currentProject.name }}</span>
            <span v-else class="sidebar-hint">请先选择项目</span>
          </div>
        </div>

        <!-- 蒸馏输入表单 -->
        <div class="distill-form" :class="{ disabled: !currentProject }">
          <!-- 项目同步状态提示 -->
          <div v-if="currentProject && isProjectSynced" class="sync-notice">
            <svg viewBox="0 0 16 16" fill="currentColor" width="14">
              <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
            </svg>
            <span>已自动从项目「{{ currentProject.name }}」填充信息，可直接修改或开始蒸馏</span>
          </div>

          <!-- 输入区域 -->
          <div class="form-group">
            <label class="form-label">
              <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                <path d="M6.5 2a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1zm3 0a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1z"/>
              </svg>
              领域关键词
            </label>
            <div class="input-wrapper">
              <input
                v-model="distillForm.keyword"
                type="text"
                class="form-input"
                placeholder="如：无人机清洗"
                :disabled="!currentProject"
                @keyup.enter="startDistill"
              >
              <div v-if="isKeywordFromProject" class="auto-fill-tag">
                来自项目
              </div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">
              <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                <path d="M8 1a4 4 0 00-4 4v2H2v2h2v6a2 2 0 002 2h4a2 2 0 002-2V9h2V7h-2V5a4 4 0 00-4-4zm0 2a2 2 0 012 2v2H6V5a2 2 0 012-2z"/>
              </svg>
              公司名称
            </label>
            <div class="input-wrapper">
              <input
                v-model="distillForm.company"
                type="text"
                class="form-input"
                placeholder="如：绿阳环保科技"
                :disabled="!currentProject"
                @keyup.enter="startDistill"
              >
              <div v-if="isCompanyFromProject" class="auto-fill-tag">
                来自项目
              </div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">
              用户自定义前缀（可选）
            </label>
            <div class="input-wrapper">
              <input
                v-model="distillForm.prefixes"
                type="text"
                class="form-input"
                placeholder="如：专业 靠谱 知名"
                :disabled="!currentProject"
                @keyup.enter="startDistill"
              >
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">
              用户自定义后缀（可选）
            </label>
            <div class="input-wrapper">
              <input
                v-model="distillForm.suffixes"
                type="text"
                class="form-input"
                placeholder="如：哪家好 厂家 服务商"
                :disabled="!currentProject"
                @keyup.enter="startDistill"
              >
            </div>
          </div>

          <!-- 示例 -->
          <div v-if="!distilling && results.length === 0" class="example-tip">
            <svg viewBox="0 0 16 16" fill="currentColor" width="16">
              <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
            </svg>
            <span>示例：「无人机清洗」+「绿阳环保」→ 无人机清洗哪家强？无人机清洗推荐？</span>
          </div>

          <!-- 蒸馏按钮 -->
          <button
            class="distill-btn"
            :class="{ loading: distilling, disabled: !canDistill }"
            :disabled="!canDistill"
            @click="startDistill"
          >
            <span v-if="!distilling" class="btn-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </span>
            <span v-else class="btn-spinner"></span>
            <span class="btn-text">{{ distilling ? '蒸馏中...' : '开始蒸馏' }}</span>
          </button>
        </div>

        <!-- 蒸馏结果 -->
        <div v-if="results.length > 0 || distilling" class="distill-results">
          <div class="results-header">
            <h4 class="results-title">
              <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
              </svg>
              蒸馏结果
              <span class="results-count">({{ results.length }})</span>
            </h4>
            <div class="results-actions">
              <button v-if="hasUnsaved" class="action-btn save-all" @click="saveAll">
                <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                  <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
                </svg>
                全部保存
              </button>
              <button class="action-btn clear" @click="clearResults">
                <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                  <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                </svg>
                清空
              </button>
            </div>
          </div>

          <div class="results-list">
            <!-- 骨架屏 -->
            <template v-if="distilling && results.length === 0">
              <div v-for="i in 3" :key="'skeleton-' + i" class="result-skeleton">
                <div class="skeleton-number"></div>
                <div class="skeleton-content">
                  <div class="skeleton-keyword"></div>
                  <div class="skeleton-questions">
                    <div class="skeleton-q"></div>
                    <div class="skeleton-q"></div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 结果列表 -->
            <TransitionGroup name="result">
              <div
                v-for="(result, index) in results"
                :key="result.id"
                class="result-item"
                :class="{ saved: result.saved }"
              >
                <div class="result-number">{{ index + 1 }}</div>
                <div class="result-content">
                  <div class="result-keyword">
                    <span class="keyword-tag">{{ result.keyword }}</span>
                  </div>
                  <div class="result-questions">
                    <div
                      v-for="(q, qIndex) in result.questions"
                      :key="qIndex"
                      class="question-chip"
                    >
                      {{ q }}
                    </div>
                  </div>
                </div>
                <div class="result-action">
                  <button
                    v-if="!result.saved"
                    class="action-btn save"
                    @click="saveResult(result)"
                  >
                    保存
                  </button>
                  <span v-else class="saved-badge">
                    <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                      <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
                    </svg>
                    已保存
                  </span>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </aside>

      <!-- 右侧 - 已保存关键词 -->
      <main class="keywords-main">
        <div class="keywords-header">
          <div class="header-left">
            <h3 class="keywords-title">已保存的关键词</h3>
            <span class="keywords-count">{{ keywords.length }} 个</span>
          </div>
          <div class="view-toggle">
            <button
              :class="{ active: viewMode === 'grid' }"
              @click="viewMode = 'grid'"
            >
              <svg viewBox="0 0 16 16" fill="currentColor" width="16">
                <path d="M1 2.5A1.5 1.5 0 012.5 1h3A1.5 1.5 0 017 2.5v3A1.5 1.5 0 015.5 7h-3A1.5 1.5 0 011 5.5v-3zm8 0A1.5 1.5 0 0110.5 1h3A1.5 1.5 0 0115 2.5v3A1.5 1.5 0 0113.5 7h-3A1.5 1.5 0 019 5.5v-3zm-8 8A1.5 1.5 0 012.5 9h3A1.5 1.5 0 017 10.5v3A1.5 1.5 0 015.5 15h-3A1.5 1.5 0 011 13.5v-3zm8 0A1.5 1.5 0 0110.5 9h3a1.5 1.5 0 011.5 1.5v3a1.5 1.5 0 01-1.5 1.5h-3A1.5 1.5 0 019 13.5v-3z"/>
              </svg>
            </button>
            <button
              :class="{ active: viewMode === 'list' }"
              @click="viewMode = 'list'"
            >
              <svg viewBox="0 0 16 16" fill="currentColor" width="16">
                <path fill-rule="evenodd" d="M2.5 12a.5.5 0 01.5-.5h10a.5.5 0 010 1H3a.5.5 0 01-.5-.5zm0-4a.5.5 0 01.5-.5h10a.5.5 0 010 1H3a.5.5 0 01-.5-.5zm0-4a.5.5 0 01.5-.5h10a.5.5 0 010 1H3a.5.5 0 01-.5-.5z"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- 关键词列表 -->
        <div v-loading="loading" class="keywords-container" :class="viewMode">
          <!-- 空状态 -->
          <div v-if="!loading && keywords.length === 0" class="empty-keywords">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            <p>选择项目后，在左侧蒸馏面板开始蒸馏</p>
          </div>

          <!-- 关键词网格 -->
          <TransitionGroup v-else name="keyword" tag="div" class="keywords-grid">
            <div
              v-for="keyword in keywords"
              :key="keyword.id"
              class="keyword-card"
              @click="viewDetail(keyword)"
            >
              <div class="card-header">
                <h4 class="keyword-text">{{ keyword.keyword }}</h4>
                <div v-if="keyword.difficulty_score" class="difficulty-badge" :class="getDifficultyClass(keyword.difficulty_score)">
                  {{ keyword.difficulty_score }}
                </div>
              </div>
              <div class="card-body">
                <div class="questions-preview">
                  <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                    <path d="M8 1a4 4 0 00-4 4v2H2v2h2v6a2 2 0 002 2h4a2 2 0 002-2V9h2V7h-2V5a4 4 0 00-4-4zm0 2a2 2 0 012 2v2H6V5a2 2 0 012-2z"/>
                  </svg>
                  <span>{{ getQuestionCount(keyword.id) }} 个问题变体</span>
                </div>
                <div class="card-actions">
                  <button class="action-btn view" @click.stop="viewDetail(keyword)">
                    <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                      <path d="M10.5 8a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/>
                      <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8zm8 3.5a3.5 3.5 0 100-7 3.5 3.5 0 000 7z"/>
                    </svg>
                    查看
                  </button>
                  <button class="action-btn delete" @click.stop="deleteKeyword(keyword)">
                    <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                      <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                      <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </main>
    </div>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="showDetail"
      :title="`关键词详情 - ${currentKeyword?.keyword}`"
      width="520px"
      class="detail-dialog"
    >
      <div v-if="currentKeyword" class="detail-content">
        <div class="detail-meta">
          <div class="meta-item">
            <span class="meta-label">关键词</span>
            <el-tag type="warning">{{ currentKeyword.keyword }}</el-tag>
          </div>
          <div class="meta-item">
            <span class="meta-label">难度评分</span>
            <el-tag v-if="currentKeyword.difficulty_score" :type="getDifficultyType(currentKeyword.difficulty_score)">
              {{ currentKeyword.difficulty_score }}
            </el-tag>
            <span v-else class="meta-empty">未评分</span>
          </div>
        </div>

        <el-divider />

        <div class="questions-section">
          <div class="questions-header">
            <h5>问题变体</h5>
            <el-button
              type="primary"
              size="small"
              :loading="generating"
              @click="generateQuestions"
            >
              <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
              </svg>
              生成问题
            </el-button>
          </div>
          <div v-loading="loadingQuestions" class="questions-list">
            <TransitionGroup name="question">
              <div
                v-for="(q, index) in currentQuestions"
                :key="q.id"
                class="question-item"
              >
                <span class="q-number">{{ index + 1 }}</span>
                <span class="q-text">{{ q.question }}</span>
              </div>
            </TransitionGroup>
            <el-empty v-if="currentQuestions.length === 0" description="暂无问题变体，点击上方按钮生成" />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { geoKeywordApi } from '@/services/api'

// ==================== 类型定义 ====================
interface Project {
  id: number
  name: string
  company_name: string
  domain_keyword?: string
  industry?: string
  description?: string
}

interface Keyword {
  id: number
  keyword: string
  difficulty_score?: number
  status: string
}

interface QuestionVariant {
  id: number
  keyword_id: number
  question: string
}

interface DistillResult {
  id: string
  keyword: string
  questions: string[]
  saved: boolean
}

// ==================== 状态 ====================
const router = useRouter()
const projects = ref<Project[]>([])
const keywords = ref<Keyword[]>([])
const keywordQuestions = ref<Record<number, QuestionVariant[]>>({})

const loading = ref(false)
const distilling = ref(false)
const loadingQuestions = ref(false)
const generating = ref(false)

const selectedProjectId = ref<number | null>(null)
const viewMode = ref<'grid' | 'list'>('grid')
const showDetail = ref(false)
const currentKeyword = ref<Keyword | null>(null)

const distillForm = ref({
  keyword: '',
  company: '',
  prefixes: '',
  suffixes: '',
})

const results = ref<DistillResult[]>([])

// ==================== 计算属性 ====================
const currentProject = computed(() => {
  if (!selectedProjectId.value) return null
  return projects.value.find(p => p.id === selectedProjectId.value) || null
})

// 检查关键词是否来自项目
const isKeywordFromProject = computed(() => {
  return currentProject.value &&
    distillForm.value.keyword === currentProject.value.domain_keyword &&
    currentProject.value.domain_keyword
})

// 检查公司名是否来自项目
const isCompanyFromProject = computed(() => {
  return currentProject.value &&
    distillForm.value.company === currentProject.value.company_name &&
    currentProject.value.company_name
})

// 检查是否有任何信息来自项目
const isProjectSynced = computed(() => {
  return isKeywordFromProject.value || isCompanyFromProject.value
})

const canDistill = computed(() => {
  return currentProject.value &&
    distillForm.value.keyword.trim() &&
    distillForm.value.company.trim()
})

const hasUnsaved = computed(() => {
  return results.value.some(r => !r.saved)
})

const currentQuestions = computed(() => {
  if (!currentKeyword.value) return []
  return keywordQuestions.value[currentKeyword.value.id] || []
})

// ==================== 方法 ====================

// 加载项目列表
const loadProjects = async () => {
  try {
    const result = await geoKeywordApi.getProjects()
    projects.value = result || []
  } catch (error) {
    console.error('加载项目失败:', error)
  }
}

// 加载项目关键词
const loadProjectKeywords = async () => {
  if (!selectedProjectId.value) return

  loading.value = true
  try {
    const result = await geoKeywordApi.getProjectKeywords(selectedProjectId.value)
    keywords.value = result || []
  } catch (error) {
    console.error('加载关键词失败:', error)
  } finally {
    loading.value = false
  }
}

// 项目变化处理 - 填充表单并加载关键词
const handleProjectChange = () => {
  const project = projects.value.find(p => p.id === selectedProjectId.value)
  if (project) {
    distillForm.value.keyword = project.domain_keyword || ''
    distillForm.value.company = project.company_name || ''
    distillForm.value.prefixes = ''
    distillForm.value.suffixes = ''
  } else {
    distillForm.value.keyword = ''
    distillForm.value.company = ''
    distillForm.value.prefixes = ''
    distillForm.value.suffixes = ''
  }
  results.value = []
  loadProjectKeywords()
}

// 跳转到项目管理
const goToProjects = () => {
  router.push({ name: 'GeoProjects' })
}

// 开始蒸馏
const startDistill = async () => {
  if (!canDistill.value) {
    ElMessage.warning('请输入关键词和公司名称')
    return
  }

  distilling.value = true
  try {
    const result = await geoKeywordApi.distill({
      project_id: selectedProjectId.value!,
      core_kw: distillForm.value.keyword,
      target_info: distillForm.value.company,
      prefixes: distillForm.value.prefixes,
      suffixes: distillForm.value.suffixes,
      company_name: distillForm.value.company,
      industry: currentProject.value?.industry || '',
      description: currentProject.value?.description || '',
      count: 5,
    })

    if (result.success && result.data?.keywords) {
      const kwList = result.data.keywords
      for (const kw of kwList) {
        const questionsResult = await geoKeywordApi.generateQuestions({
          keyword_id: kw.id,
          count: 3,
        })

        results.value.push({
          id: kw.id.toString(),
          keyword: kw.keyword,
          questions: questionsResult.data?.questions?.map((q: any) => q.question) || [],
          saved: true,
        })
      }

      await loadProjectKeywords()
      ElMessage.success(`蒸馏完成，生成 ${kwList.length} 个关键词`)
    } else {
      ElMessage.error(result.message || '蒸馏失败')
    }
  } catch (error) {
    console.error('蒸馏失败:', error)
    ElMessage.error('蒸馏失败，请稍后重试')
  } finally {
    distilling.value = false
  }
}

// 保存单个结果
const saveResult = async (result: DistillResult) => {
  result.saved = true
  ElMessage.success('保存成功')
}

// 全部保存
const saveAll = async () => {
  for (const result of results.value) {
    if (!result.saved) {
      await saveResult(result)
    }
  }
}

// 清空结果
const clearResults = () => {
  results.value = []
}

// 获取问题数量
const getQuestionCount = (keywordId: number) => {
  return (keywordQuestions.value[keywordId] || []).length
}

// 获取难度样式类
const getDifficultyClass = (score: number) => {
  if (score >= 80) return 'high'
  if (score >= 60) return 'medium'
  return 'low'
}

// 获取难度标签类型
const getDifficultyType = (score: number) => {
  if (score >= 80) return 'danger'
  if (score >= 60) return 'warning'
  return 'success'
}

// 查看详情
const viewDetail = async (keyword: Keyword) => {
  currentKeyword.value = keyword
  showDetail.value = true
  await loadKeywordQuestions(keyword.id)
}

// 加载关键词问题
const loadKeywordQuestions = async (keywordId: number) => {
  loadingQuestions.value = true
  try {
    const result = await geoKeywordApi.getKeywordQuestions(keywordId)
    keywordQuestions.value[keywordId] = result || []
  } catch (error) {
    console.error('加载问题失败:', error)
  } finally {
    loadingQuestions.value = false
  }
}

// 生成问题
const generateQuestions = async () => {
  if (!currentKeyword.value) return

  generating.value = true
  try {
    const result = await geoKeywordApi.generateQuestions({
      keyword_id: currentKeyword.value.id,
      count: 3,
    })

    if (result.success) {
      await loadKeywordQuestions(currentKeyword.value.id)
      ElMessage.success(result.message || '问题生成成功')
    }
  } catch (error) {
    console.error('生成问题失败:', error)
    ElMessage.error('生成问题失败')
  } finally {
    generating.value = false
  }
}

// 删除关键词
const deleteKeyword = async (keyword: Keyword) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除关键词"${keyword.keyword}"吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )

    await geoKeywordApi.deleteKeyword(keyword.id)
    keywords.value = keywords.value.filter(k => k.id !== keyword.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadProjects()

  // 处理路由参数 - 自动选中项目
  const route = router.currentRoute.value
  const projectIdFromQuery = route.query.projectId
  if (projectIdFromQuery && projects.value.length > 0) {
    const projectId = Number(projectIdFromQuery)
    const project = projects.value.find(p => p.id === projectId)
    if (project) {
      selectedProjectId.value = projectId
      await loadProjectKeywords()
    }
  }
})
</script>

<style scoped lang="scss">
.keywords-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%);
}

// 头部
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: white;
  border-radius: 16px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .header-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;

      svg {
        width: 24px;
        height: 24px;
      }
    }

    .page-title {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
      color: #1a1f36;
    }

    .page-desc {
      margin: 0;
      font-size: 13px;
      color: #9ca3af;
    }
  }

  .project-option {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .option-name {
      font-size: 14px;
      color: #1a1f36;
    }

    .option-company {
      font-size: 12px;
      color: #9ca3af;
    }
  }

  .project-empty {
    text-align: center;
    padding: 10px;

    p {
      margin: 0 0 4px 0;
      font-size: 13px;
      color: #9ca3af;
    }
  }
}

// 主内容区
.main-content {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

// 左侧蒸馏面板
.distill-sidebar {
  width: 380px;
  display: flex;
  flex-direction: column;
  gap: 16px;

  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;

    .header-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;

      svg {
        width: 20px;
        height: 20px;
      }
    }

    .sidebar-title {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #1a1f36;
    }

    .sidebar-project {
      display: block;
      font-size: 12px;
      color: #10b981;
    }

    .sidebar-hint {
      display: block;
      font-size: 12px;
      color: #9ca3af;
    }
  }
}

// 蒸馏表单
.distill-form {
  padding: 20px;

  // 项目同步通知条
  .sync-notice {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 10px;
    margin-bottom: 16px;
    font-size: 13px;
    color: #059669;

    svg {
      flex-shrink: 0;
      color: #10b981;
    }
  }

  &.disabled {
    opacity: 0.6;
    pointer-events: none;
  }

  .form-group {
    margin-bottom: 16px;

    .form-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 8px;
    }

    .input-wrapper {
      position: relative;

      .form-input {
        width: 100%;
        padding: 12px 90px 12px 14px;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        font-size: 14px;
        background: #ffffff !important;
        color: #111827 !important;
        transition: all 0.2s;

        &::placeholder {
          color: #9ca3af !important;
        }

        &:focus {
          outline: none;
          border-color: #10b981;
          box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }

        &:disabled {
          background: #f9fafb !important;
          color: #6b7280 !important;
          cursor: not-allowed;
        }

        &.synced {
          background: rgba(16, 185, 129, 0.05);
          border-color: #10b981;
          color: #059669;
        }
      }

      // 自动填充标签 - 干净简洁的"来自项目"标签
      .auto-fill-tag {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        padding: 4px 10px;
        background: rgba(16, 185, 129, 0.1);
        border-radius: 6px;
        font-size: 12px;
        color: #059669;
        font-weight: 500;
        pointer-events: none;
      }
    }
  }

  .example-tip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: transparent;
    border-radius: 10px;
    margin-bottom: 16px;
    font-size: 12px;
    color: #9ca3af;

    svg {
      color: #9ca3af;
      flex-shrink: 0;
    }
  }

  .distill-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 24px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 500;
    color: white;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover:not(.disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
    }

    &.disabled {
      background: #e5e7eb;
      cursor: not-allowed;
    }

    &.loading {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      opacity: 0.8;
    }

    .btn-icon svg {
      width: 18px;
      height: 18px;
    }

    .btn-spinner {
      width: 18px;
      height: 18px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }
}

// 蒸馏结果
.distill-results {
  border-radius: 12px;
  overflow: hidden;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;

  .results-title {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-size: 14px;
    font-weight: 500;
    color: #1a1f36;

    svg {
      color: #10b981;
    }

    .results-count {
      font-weight: normal;
      color: #9ca3af;
    }
  }

  .results-actions {
    display: flex;
    gap: 8px;

    .action-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 12px;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s;

      &.save-all {
        background: #4a90e2;
        color: white;

        &:hover {
          background: #357abd;
        }
      }

      &.clear {
        background: #fef2f2;
        color: #ef4444;

        &:hover {
          background: #fee2e2;
        }
      }
    }
  }
}

.results-list {
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 10px;
  border-left: 3px solid transparent;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
  }

  &.saved {
    border-left-color: #10b981;
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.05) 0%, transparent 100%);
  }

  .result-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .result-content {
    flex: 1;
    min-width: 0;

    .result-keyword {
      margin-bottom: 10px;

      .keyword-tag {
        display: inline-flex;
        align-items: center;
        padding: 5px 12px;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.08) 100%);
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        color: #d97706;
      }
    }

    .result-questions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;

      .question-chip {
        padding: 5px 10px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        font-size: 12px;
        color: #6b7280;
      }
    }
  }

  .result-action {
    flex-shrink: 0;

    .action-btn {
      padding: 6px 12px;
      background: #4a90e2;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      color: white;
      cursor: pointer;

      &:hover {
        background: #357abd;
      }
    }

    .saved-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      background: #d1fae5;
      border-radius: 6px;
      font-size: 11px;
      color: #059669;
      font-weight: 500;
    }
  }
}

// 骨架屏
.result-skeleton {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 10px;

  .skeleton-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    flex-shrink: 0;
  }

  .skeleton-content {
    flex: 1;

    .skeleton-keyword {
      width: 80px;
      height: 28px;
      border-radius: 6px;
      background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      margin-bottom: 10px;
    }

    .skeleton-questions {
      display: flex;
      gap: 6px;

      .skeleton-question {
        width: 100px;
        height: 24px;
        border-radius: 6px;
        background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
      }
    }
  }
}

// 右侧关键词主区域
.keywords-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.keywords-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;

  .keywords-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: #1a1f36;
  }

  .keywords-count {
    font-size: 12px;
    color: #9ca3af;
  }

  .view-toggle {
    display: flex;
    background: #f3f4f6;
    border-radius: 8px;
    padding: 2px;

    button {
      padding: 6px 10px;
      background: transparent;
      border: none;
      border-radius: 6px;
      color: #9ca3af;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        color: #6b7280;
      }

      &.active {
        background: white;
        color: #4a90e2;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
      }
    }
  }
}

.keywords-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;

  &.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 16px;
  }

  &.list {
    display: flex;
    flex-direction: column;
    gap: 10px;

    .keyword-card {
      flex-direction: row;
      align-items: center;

      .card-header {
        margin-bottom: 0;
        margin-right: 16px;
      }

      .card-body {
        flex: 1;
        flex-direction: row;
        align-items: center;
        justify-content: space-between;

        .questions-preview {
          margin-bottom: 0;
          margin-right: 16px;
        }
      }
    }
  }
}

// 空状态
.empty-keywords {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #9ca3af;

  svg {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    opacity: 0.5;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

// 关键词卡片
.keyword-card {
  background: #f9fafb;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;

  &:hover {
    border-color: #4a90e2;
    box-shadow: 0 4px 12px rgba(74, 144, 226, 0.1);
    transform: translateY(-2px);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .keyword-text {
      margin: 0;
      font-size: 15px;
      font-weight: 500;
      color: #1a1f36;
    }

    .difficulty-badge {
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;

      &.high {
        background: #fef2f2;
        color: #ef4444;
      }

      &.medium {
        background: #fef3c7;
        color: #d97706;
      }

      &.low {
        background: #d1fae5;
        color: #059669;
      }
    }
  }

  .card-body {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .questions-preview {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #9ca3af;

      svg {
        color: #4a90e2;
      }
    }

    .card-actions {
      display: flex;
      gap: 8px;
      padding-top: 12px;
      border-top: 1px solid #e5e7eb;

      .action-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 8px;
        border: none;
        border-radius: 8px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;

        &.view {
          background: #f3f4f6;
          color: #6b7280;

          &:hover {
            background: #e5e7eb;
            color: #1a1f36;
          }
        }

        &.delete {
          background: #fef2f2;
          color: #ef4444;

          &:hover {
            background: #fee2e2;
          }
        }
      }
    }
  }
}

// 详情对话框
.detail-content {
  .detail-meta {
    display: flex;
    gap: 24px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 8px;

      .meta-label {
        font-size: 13px;
        color: #6b7280;
      }

      .meta-empty {
        font-size: 13px;
        color: #9ca3af;
      }
    }
  }

  .questions-section {
    .questions-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;

      h5 {
        margin: 0;
        font-size: 14px;
        font-weight: 500;
        color: #1a1f36;
      }
    }

    .questions-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 100px;

      .question-item {
        display: flex;
        gap: 12px;
        padding: 12px;
        background: #f9fafb;
        border-radius: 8px;

        .q-number {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: #4a90e2;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 500;
          flex-shrink: 0;
        }

        .q-text {
          flex: 1;
          font-size: 13px;
          color: #374151;
        }
      }
    }
  }
}

// 滚动条
.keywords-container::-webkit-scrollbar,
.results-list::-webkit-scrollbar {
  width: 6px;
}

.keywords-container::-webkit-scrollbar-track,
.results-list::-webkit-scrollbar-track {
  background: transparent;
}

.keywords-container::-webkit-scrollbar-thumb,
.results-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;

  &:hover {
    background: #9ca3af;
  }
}

// 动画
@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.result-enter-active,
.keyword-enter-active {
  transition: all 0.3s ease;
}

.result-enter-from,
.keyword-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.result-enter-to,
.keyword-enter-to {
  opacity: 1;
  transform: translateX(0);
}

.question-enter-active {
  transition: all 0.2s ease;
}

.question-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.question-enter-to {
  opacity: 1;
  transform: translateX(0);
}
</style>
