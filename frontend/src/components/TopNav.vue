<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const links = [
  { to: '/chat', label: '对话', icon: '◇' },
  { to: '/tools', label: '工具', icon: '◆' },
  { to: '/settings', label: '设置', icon: '⚙' },
]
</script>

<template>
  <nav class="h-12 px-5 flex items-center justify-between border-b border-white/[0.08] bg-base-900/60 backdrop-blur relative z-20 shrink-0">
    <!-- Logo -->
    <router-link to="/" class="flex items-center gap-3 group select-none">
      <div class="w-7 h-7 rounded-md bg-accent/10 border border-accent/20 flex items-center justify-center text-accent font-mono text-sm font-medium group-hover:glow-accent transition-shadow">
        D
      </div>
      <span class="text-white/85 text-sm font-medium tracking-wide group-hover:text-white transition-colors">
        DingYingAgent
      </span>
    </router-link>

    <!-- 导航链接 -->
    <div class="flex items-center gap-1">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="px-3 py-1.5 rounded-md text-xs tracking-wide transition-all duration-200 flex items-center gap-1.5"
        :class="route.path === link.to
          ? 'text-accent bg-accent/10 border border-accent/20'
          : 'text-white/50 hover:text-white/80 hover:bg-white/[0.06]'"
      >
        <span class="text-[10px]">{{ link.icon }}</span>
        {{ link.label }}
      </router-link>
    </div>
  </nav>
</template>
