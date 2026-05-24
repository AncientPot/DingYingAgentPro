<script setup>
import { ref } from 'vue'
import { useSessionStore } from '../stores/session'

const store = useSessionStore()
const newName = ref('')

function handleCreate() {
  store.selectOrCreate(newName.value)
  newName.value = ''
}
</script>

<template>
  <aside class="w-[260px] shrink-0 border-r border-white/[0.08] flex flex-col h-full bg-base-850/70">
    <!-- 标题 -->
    <div class="px-4 py-3 flex items-center justify-between">
      <span class="text-[11px] font-medium tracking-widest text-white/35 uppercase select-none">会话</span>
      <span class="text-[10px] text-white/25 font-mono">{{ store.sessions.length }}</span>
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
        @click="store.activeName = s.name"
      >
        <span class="text-[10px] shrink-0" :class="store.activeName === s.name ? 'text-accent' : 'text-white/30'">
          {{ store.activeName === s.name ? '◆' : '◇' }}
        </span>
        <span class="truncate flex-1 text-[13px]">{{ s.name }}</span>
        <button
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
    <div class="p-2 border-t border-white/[0.07]">
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
  </aside>
</template>
