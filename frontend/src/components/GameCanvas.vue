<script setup>
import { ref, onMounted, watch } from 'vue'
import { useGameStore } from '../stores/game'
import GameSettings from './GameSettings.vue'

const game = useGameStore()
const showSettings = ref(false)

onMounted(async () => {
  await game.fetchSettings()
})

// 同步设置面板的值
const localInterval = ref(game.autoInterval)
const localPrompt = ref(game.thinkPrompt)
const localTools = ref([...game.gameTools])

watch(() => game.autoInterval, v => { localInterval.value = v })
watch(() => game.thinkPrompt, v => { localPrompt.value = v })
watch(() => game.gameTools, v => { localTools.value = [...v] })
</script>

<template>
  <div class="game-canvas flex-1 flex flex-col relative overflow-hidden">
    <!-- 背景氛围 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-80 h-80 rounded-full bg-accent/2 blur-3xl"
        :class="{ 'bg-accent/5': game.subMode === 'playing' }"></div>
      <div class="absolute bottom-1/3 right-1/4 w-64 h-64 rounded-full bg-amber-tool/3 blur-3xl"></div>
    </div>

    <!-- 顶部栏 -->
    <div class="relative z-10 flex items-center justify-between px-5 py-3 shrink-0">
      <div class="flex items-center gap-3">
        <span class="relative flex h-2.5 w-2.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full"
            :class="game.subMode === 'playing' ? 'bg-accent/40' : 'bg-white/10'"></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5"
            :class="game.subMode === 'playing' ? 'bg-accent' : 'bg-white/25'"></span>
        </span>
        <span class="text-[11px] font-mono tracking-widest uppercase"
          :class="game.subMode === 'playing' ? 'text-accent/60' : 'text-white/25'">
          {{ game.subMode === 'playing' ? 'GAME · 游戏中' : 'GAME · 准备中' }}
        </span>
      </div>
      <button
        class="w-8 h-8 rounded-lg flex items-center justify-center text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-all"
        :class="{ 'text-accent/60 bg-accent/8': showSettings }"
        @click="showSettings = !showSettings"
        title="游戏设置"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
      </button>
    </div>

    <!-- 设置浮层 -->
    <transition name="settings-fade">
      <GameSettings v-if="showSettings" @close="showSettings = false" />
    </transition>

    <!-- ====== 准备中子模式 ====== -->
    <div v-if="game.subMode === 'preparing' && !showSettings" class="relative z-10 flex-1 flex flex-col items-center justify-center space-y-6 px-8">
      <span class="text-5xl opacity-15 select-none">⚙</span>
      <h2 class="text-xl font-light text-white/60 tracking-wide">准备中</h2>
      <p class="text-xs text-white/20 max-w-sm text-center leading-relaxed">
        游戏尚未开始。你可以调整右侧齿轮中的游戏设置，或通过下方输入栏与 AI 讨论游戏规则。
      </p>
      <div class="flex gap-3 mt-4">
        <button
          class="px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 border"
          :class="'bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 hover:shadow-[0_0_30px_rgba(0,229,255,0.1)] active:scale-[0.98]'"
          @click="game.startPlaying()"
        >
          开始游戏
        </button>
      </div>
    </div>

    <!-- ====== 游戏中子模式 ====== -->
    <div v-if="game.subMode === 'playing' && !showSettings" class="relative z-10 flex-1 flex flex-col items-center justify-center space-y-4 px-8">
      <span class="text-5xl opacity-15 select-none">🎮</span>
      <p class="text-xs text-white/15 font-mono">游戏进行中 · 可通过输入栏与 AI 互动</p>
      <div class="flex gap-3 mt-4">
        <button
          class="px-5 py-2 rounded-xl text-xs font-medium border transition-all duration-200"
          :class="'bg-red-500/5 text-red-400/60 border-red-500/15 hover:bg-red-500/10 active:scale-[0.98]'"
          @click="game.endPlaying()"
        >
          结束游戏
        </button>
      </div>
    </div>

    <!-- AI 面板（游戏中时右上角浮动，准备中时不显示自主回复） -->
    <transition name="ai-panel">
      <div
        v-if="(game.aiMessage || game.aiThinking) && game.subMode === 'playing'"
        class="ai-panel absolute top-14 right-4 w-72 max-h-56 overflow-y-auto z-20 glass rounded-2xl p-4 text-sm leading-relaxed"
      >
        <div class="flex items-center gap-2 mb-2 pb-2 border-b border-white/[0.06]">
          <span class="w-1.5 h-1.5 rounded-full bg-accent"></span>
          <span class="text-[10px] font-mono text-accent/50 tracking-wide">AI</span>
          <span v-if="game.aiThinking" class="loading-dot w-1 h-1 rounded-full bg-accent/60 ml-auto"></span>
        </div>
        <p class="text-white/60 text-xs whitespace-pre-wrap">{{ game.aiMessage }}</p>
        <div v-if="game.aiThinking && !game.aiMessage" class="flex items-center gap-1.5 py-1">
          <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent/50"></span>
          <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent/50"></span>
          <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent/50"></span>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.game-canvas { animation: game-enter 0.5s ease-out both; }
@keyframes game-enter { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
.ai-panel { animation: panel-slide 0.4s ease-out both; }
@keyframes panel-slide { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: translateX(0); } }
.settings-fade-enter-active, .settings-fade-leave-active { transition: opacity 0.2s ease; }
.settings-fade-enter-from, .settings-fade-leave-to { opacity: 0; }
</style>
