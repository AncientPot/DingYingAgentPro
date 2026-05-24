<script setup>
import { ref } from 'vue'

defineProps({
  toolName: { type: String, required: true },
  content: { type: String, default: '' },
})

const collapsed = ref(true)
</script>

<template>
  <div class="msg-enter tool-border pl-4 py-2.5 pr-3 my-2 rounded-r-lg bg-amber-tool/5 border-y border-r border-amber-tool/15">
    <div class="flex items-center gap-2 cursor-pointer select-none" @click="collapsed = !collapsed">
      <span class="text-[11px]">{{ collapsed ? '▸' : '▾' }}</span>
      <span class="text-[11px] font-mono text-amber-tool font-medium tracking-wide">TOOL</span>
      <span class="text-xs text-white/50">{{ toolName }}</span>
    </div>
    <div v-if="!collapsed && content" class="mt-2 text-xs text-white/40 font-mono leading-relaxed pl-4 border-l border-amber-tool/20">
      {{ content }}
    </div>
  </div>
</template>
