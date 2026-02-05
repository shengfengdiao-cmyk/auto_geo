<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">🚀</span>
          <span class="logo-text">AutoGeo</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="route in visibleRoutes"
          :key="route.name"
          :to="route.path"
          class="nav-item"
          :class="{ active: isActive(route.path) }"
        >
          <el-icon>
            <component :is="route.meta?.icon" />
          </el-icon>
          <span>{{ route.meta?.title }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="status-info">
          <div class="status-dot online"></div>
          <span>后端服务正常</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 顶部栏 -->
      <header class="header">
        <div class="header-left">
          <h1 class="page-title">{{ currentPageTitle }}</h1>
        </div>
        <div class="header-right">
          <el-button text @click="minimizeWindow">
            <el-icon><Minus /></el-icon>
          </el-button>
          <el-button text @click="maximizeWindow">
            <el-icon><FullScreen /></el-icon>
          </el-button>
          <el-button text @click="closeWindow">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Minus, FullScreen, Close } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 获取可见的路由（隐藏 meta.hidden 的路由）
const visibleRoutes = computed(() => {
  return router.getRoutes().filter(r => r.path.startsWith('/') && !r.meta?.hidden)
})

// 当前页面标题
const currentPageTitle = computed(() => {
  return route.meta?.title || 'AutoGeo'
})

// 判断路由是否激活
const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}

// 窗口控制
const minimizeWindow = () => {
  window.electronAPI?.minimizeWindow()
}

const maximizeWindow = () => {
  window.electronAPI?.maximizeWindow()
}

const closeWindow = () => {
  window.electronAPI?.closeWindow()
}
</script>

<style scoped lang="scss">
.main-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

// 侧边栏
.sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;

  .sidebar-header {
    padding: 20px;
    border-bottom: 1px solid var(--border);

    .logo {
      display: flex;
      align-items: center;
      gap: 12px;

      .logo-icon {
        font-size: 28px;
      }

      .logo-text {
        font-size: 20px;
        font-weight: 600;
        background: linear-gradient(135deg, #4a90e2, #67b26f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
    }
  }

  .sidebar-nav {
    flex: 1;
    padding: 16px 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;
    overflow-x: hidden;

    /* 自定义滚动条样式 - 窄条、半透明、悬停显示 */
    &::-webkit-scrollbar {
      width: 4px;
    }

    &::-webkit-scrollbar-track {
      background: transparent;
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 4px;
      transition: background 0.2s;
    }

    &::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.4);
    }

    /* Firefox 滚动条样式 */
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.2) transparent;

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 8px;
      color: var(--text-secondary);
      text-decoration: none;
      transition: all 0.2s;

      &:hover {
        background: rgba(74, 144, 226, 0.1);
        color: var(--text-primary);
      }

      &.active {
        background: rgba(74, 144, 226, 0.2);
        color: #4a90e2;
        border-left: 3px solid #4a90e2;
      }

      .el-icon {
        font-size: 20px;
      }
    }
  }

  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid var(--border);

    .status-info {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-secondary);

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;

        &.online {
          background: #4caf50;
          box-shadow: 0 0 8px #4caf50;
        }

        &.offline {
          background: #f44336;
        }
      }
    }
  }
}

// 主内容区
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 60px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  .header-left {
    .page-title {
      margin: 0;
      font-size: 18px;
      font-weight: 500;
    }
  }

  .header-right {
    display: flex;
    gap: 8px;

    .el-button {
      color: var(--text-secondary);

      &:hover {
        color: var(--text-primary);
      }
    }
  }
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

// 动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
