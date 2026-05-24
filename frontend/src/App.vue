<script setup>
import TopNav from './components/TopNav.vue'
</script>

<template>
  <div class="h-full flex flex-col bg-base-900 bg-grid relative overflow-hidden">
    <!-- 扫描线叠加 -->
    <div class="absolute inset-0 pointer-events-none z-0 bg-scanline"></div>
    <!-- 顶部光晕 -->
    <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px] bg-gradient-to-r from-transparent via-accent/30 to-transparent"></div>

    <TopNav />
    <main class="flex-1 overflow-hidden relative z-10">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>

    <!-- 状态栏 -->
    <footer class="h-7 px-4 flex items-center justify-between text-[11px] text-white/35 border-t border-white/[0.06] bg-base-900/80 backdrop-blur relative z-10 select-none">
      <div class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500/70 animate-pulse"></span>
        <span>在线</span>
      </div>
      <div class="flex items-center gap-4">
        <span>模型: deepseek-chat</span>
        <span>DingYingAgent Pro v0.1</span>
      </div>
    </footer>
  </div>
</template>
