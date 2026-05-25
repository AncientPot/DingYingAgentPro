<script setup>
import { ref, watch } from 'vue'
import { useSessionStore } from '../stores/session'
import { useGameStore } from '../stores/game'

const store = useSessionStore()
const game = useGameStore()
const newName = ref('')

// 侧边栏折叠状态（localStorage 持久化）
const collapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar_collapsed', collapsed.value ? '1' : '0')
}

// 游戏模式进入时自动折叠
watch(() => game.gameMode, (mode) => {
  if (mode && !collapsed.value) {
    collapsed.value = true
    localStorage.setItem('sidebar_collapsed', '1')
  }
})

function handleCreate() {
  if (game.gameMode) return
  store.selectOrCreate(newName.value)
  newName.value = ''
}
</script>

<template>
  <aside
    class="shrink-0 border-r border-white/[0.08] flex flex-col h-full bg-base-850/70 transition-all duration-300 overflow-hidden"
    :class="collapsed ? 'w-0 border-r-0' : 'w-[260px]'"
  >
    <div class="w-[260px] flex flex-col h-full">
      <!-- 标题 -->
      <div class="px-4 py-3 flex items-center justify-between">
        <span class="text-[11px] font-medium tracking-widest text-white/35 uppercase select-none">会话</span>
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-white/25 font-mono">{{ store.sessions.length }}</span>
          <button
            class="w-5 h-5 flex items-center justify-center rounded text-white/20 hover:text-white/50 transition-colors"
            @click="toggleCollapse"
            title="收起侧边栏"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
        </div>
      </div>

      <!-- 会话列表 -->
      <div class="flex-1 overflow-y-auto px-2 space-y-0.5">
        <div
          v-for="s in store.sessions"
          :key="s.name"
          class="group flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all duration-150 text-sm"
          :class="store.activeName === s.name
            ? 'bg-accent/10 text-accent border border-accent/20'
            : 'text-white/55 hover:text-white/80 hover:bg-white/[0.05] border border-transparent'"
          @click="!game.gameMode && (store.activeName = s.name)"
        >
          <span class="text-[10px] shrink-0" :class="store.activeName === s.name ? 'text-accent' : 'text-white/30'">
            {{ store.activeName === s.name ? '◆' : '◇' }}
          </span>
          <span class="truncate flex-1 text-[13px]">{{ s.name }}</span>
          <button
            v-if="!game.gameMode"
            class="shrink-0 w-5 h-5 flex items-center justify-center rounded text-white/25 hover:text-red-400 hover:bg-red-400/10 opacity-0 group-hover:opacity-100 transition-all text-xs"
            @click.stop="store.removeSession(s.name)"
          >
            ×
          </button>
        </div>
        <div v-if="store.sessions.length === 0" class="px-3 py-8 text-center text-white/25 text-xs">
          暂无会话<br>创建一个开始对话
        </div>
      </div>

      <!-- 新建 -->
      <div v-if="!game.gameMode" class="p-2 border-t border-white/[0.07]">
        <div class="flex gap-2">
          <input
            v-model="newName"
            type="text"
            placeholder="新会话名称..."
            class="flex-1 bg-white/[0.06] border border-white/[0.10] rounded-lg px-3 py-1.5 text-xs text-white/70 placeholder-white/20 focus:outline-none focus:border-accent/30 transition-colors font-mono"
            @keydown.enter="handleCreate"
          />
          <button
            :disabled="!newName.trim()"
            class="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            :class="newName.trim()
              ? 'bg-accent/12 text-accent border border-accent/20 hover:bg-accent/20'
              : 'bg-white/[0.05] text-white/20 border border-white/[0.08] cursor-not-allowed'"
            @click="handleCreate"
          >
            +
          </button>
        </div>
      </div>
    </div>
  </aside>

  <!-- 折叠时的展开按钮（独立于侧边栏） -->
  <div
    v-if="collapsed"
    class="shrink-0 w-7 flex flex-col items-center justify-center border-r border-white/[0.06] bg-base-850/70 cursor-pointer hover:bg-white/[0.03] transition-colors group"
    @click="toggleCollapse"
    title="展开侧边栏"
  >
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="text-white/20 group-hover:text-white/50 transition-colors"><polyline points="9 18 15 12 9 6"/></svg>
    <!-- 活跃会话指示点 -->
    <div class="mt-2 flex flex-col gap-1">
      <span
        v-for="s in store.sessions.slice(0, 5)"
        :key="s.name"
        class="w-1 h-1 rounded-full"
        :class="store.activeName === s.name ? 'bg-accent' : 'bg-white/10'"
      ></span>
    </div>
  </div>
</template>
