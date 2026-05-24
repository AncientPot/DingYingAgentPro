<script setup>
import { ref, onMounted } from 'vue'
import { useToolsStore } from '../stores/tools'
import * as api from '../api'

const store = useToolsStore()

onMounted(() => store.fetchTools())

const testing = ref({})   // { toolName: 'testing' | 'ok' | 'fail' }
const testResults = ref({}) // { toolName: resultObject }

const iconMap = {
  calculator: '⚡',
  netease_cloud_music: '♫',
  tavily_search: '◎',
}

async function handleTest(name) {
  testing.value[name] = 'testing'
  testResults.value[name] = null
  try {
    const data = await api.testTool(name)
    testing.value[name] = data.ok ? 'ok' : 'fail'
    testResults.value[name] = data
  } catch (e) {
    testing.value[name] = 'fail'
    testResults.value[name] = { ok: false, message: `请求失败: ${e.message}`, details: '' }
  }
  // 3 秒后自动清除结果
  setTimeout(() => {
    if (testing.value[name] !== 'testing') {
      delete testing.value[name]
      delete testResults.value[name]
    }
  }, 5000)
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="max-w-4xl mx-auto py-8 px-6 space-y-6">
      <!-- 标题 -->
      <div class="mb-8">
        <h1 class="text-xl font-semibold text-white/85 tracking-wide">工具管理</h1>
        <p class="text-xs text-white/35 mt-1">
          在 <code class="text-accent/60 font-mono">app/tools/</code> 目录下新增 .py 文件即可添加工具，删除文件即移除
        </p>
      </div>

      <!-- 工具卡片网格 -->
      <div v-if="store.loading" class="text-center text-white/25 text-sm py-12">加载中...</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="tool in store.tools"
          :key="tool.name"
          class="glass rounded-xl px-5 py-4 transition-all duration-200 hover:border-white/[0.1]"
          :class="tool.enabled ? '' : 'opacity-50'"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2.5 mb-1">
                <span class="text-lg">{{ iconMap[tool.name] || '◆' }}</span>
                <h3 class="text-sm font-medium text-white/75 font-mono">{{ tool.display_name }}</h3>
              </div>
              <p class="text-[11px] text-white/30 leading-relaxed line-clamp-3 ml-8">{{ tool.description }}</p>

              <!-- 测试结果 -->
              <div
                v-if="testResults[tool.name]"
                class="mt-2 ml-8 text-[11px] leading-relaxed px-2.5 py-1.5 rounded-lg"
                :class="testResults[tool.name].ok
                  ? 'bg-emerald-500/8 border border-emerald-500/20 text-emerald-400/80'
                  : 'bg-red-500/8 border border-red-500/20 text-red-400/80'"
              >
                {{ testResults[tool.name].message }}
              </div>
            </div>

            <div class="flex items-center gap-3">
              <!-- 测试按钮 -->
              <button
                class="shrink-0 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200 border"
                :class="testing[tool.name] === 'testing'
                  ? 'bg-accent/5 text-accent/40 border-accent/15 cursor-wait'
                  : testing[tool.name] === 'ok'
                    ? 'bg-emerald-500/10 text-emerald-400/70 border-emerald-500/20'
                    : testing[tool.name] === 'fail'
                      ? 'bg-red-500/10 text-red-400/70 border-red-500/20'
                      : 'bg-white/[0.04] text-white/35 border-white/[0.08] hover:bg-white/[0.08] hover:text-white/60'"
                :disabled="testing[tool.name] === 'testing'"
                @click="handleTest(tool.name)"
              >
                {{ testing[tool.name] === 'testing' ? '检测中...' : testing[tool.name] === 'ok' ? '通过' : testing[tool.name] === 'fail' ? '失败' : '测试' }}
              </button>

              <!-- Toggle -->
              <div
                class="shrink-0 toggle-track"
                :class="{ active: tool.enabled }"
                @click="store.toggle(tool.name, !tool.enabled)"
              >
                <div class="toggle-thumb"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!store.loading && store.tools.length === 0" class="text-center py-16">
        <div class="w-12 h-12 rounded-xl glass flex items-center justify-center mb-3 mx-auto">
          <span class="text-lg text-white/20">+</span>
        </div>
        <p class="text-sm text-white/20">暂无可用工具</p>
        <p class="text-xs text-white/12 mt-1">在 app/tools/ 下添加 Python 文件来创建工具</p>
      </div>
    </div>
  </div>
</template>
