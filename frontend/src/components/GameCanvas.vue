<script setup>
import { ref, onMounted, watch } from 'vue'
import { useGameStore } from '../stores/game'
import GameSettings from './GameSettings.vue'
import SnakeGame from './SnakeGame.vue'

const props = defineProps({ sessionName: { type: String, default: '' } })
defineEmits(['exited'])

const game = useGameStore()
const snakeRef = ref(null)
const showSettings = ref(false)

onMounted(async () => { await game.fetchSettings() })

// 定时更新游戏上下文
let ctxTimer = null
watch(() => game.subMode, (mode) => {
  if (mode === 'playing' && game.activeGameTool === 'snake_game') {
    ctxTimer = setInterval(() => {
      if (snakeRef.value?.gameStateText) game.setGameContext(snakeRef.value.gameStateText())
    }, 500)
  } else {
    if (ctxTimer) { clearInterval(ctxTimer); ctxTimer = null }
  }
})
</script>

<template>
  <div class="game-canvas flex-1 flex flex-col relative overflow-hidden">
    <!-- 背景 -->
    <div class="absolute inset-0 pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-80 h-80 rounded-full bg-accent/2 blur-3xl"
        :class="{ 'bg-accent/5': game.subMode === 'playing' }"></div>
      <div class="absolute bottom-1/3 right-1/4 w-64 h-64 rounded-full bg-amber-tool/3 blur-3xl"></div>
    </div>

    <!-- 顶部状态栏 -->
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
    </div>

    <!-- ====== 准备中子模式：设置面板 + 操作按钮 ====== -->
    <div v-if="game.subMode === 'preparing'" class="relative z-10 flex-1 flex flex-col overflow-hidden">
      <div class="flex-1 overflow-y-auto px-4">
        <GameSettings />
      </div>
      <div class="shrink-0 flex justify-center gap-4 py-4 border-t border-white/[0.04]">
        <button class="px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 border bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 hover:shadow-[0_0_30px_rgba(0,229,255,0.1)] active:scale-[0.98]"
          @click="game.startPlaying()">开始游戏</button>
        <button class="px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border bg-white/[0.03] text-white/30 border-white/[0.08] hover:bg-white/[0.06] hover:text-white/50 active:scale-[0.98]"
          @click="game.forceExit(props.sessionName, () => $emit('exited'))">退出游戏模式</button>
      </div>
    </div>

    <!-- ====== 游戏中子模式 ====== -->
    <div v-if="game.subMode === 'playing' && !showSettings" class="relative z-10 flex-1 flex flex-col items-center justify-center px-8">
      <SnakeGame v-if="game.activeGameTool === 'snake_game'" ref="snakeRef" />
      <div v-else class="space-y-4 text-center">
        <span class="text-5xl opacity-15 select-none">🎮</span>
        <p class="text-xs text-white/15 font-mono">游戏进行中</p>
      </div>
      <div class="flex gap-3 mt-4">
        <button class="px-5 py-2 rounded-xl text-xs font-medium border transition-all duration-200 bg-red-500/5 text-red-400/60 border-red-500/15 hover:bg-red-500/10 active:scale-[0.98]"
          @click="game.endPlaying()">结束游戏</button>
      </div>
    </div>

    <!-- AI 面板 + 加载指示器 -->
    <transition name="ai-fade">
      <div v-if="game.showAiPanel && game.subMode === 'playing' && (game.aiMessage || game.aiThinking)"
        class="ai-panel absolute top-3 left-1/2 -translate-x-1/2 w-[85%] max-w-lg max-h-32 overflow-y-auto z-20 px-5 py-2.5 text-center">
        <p v-if="game.aiMessage" class="text-white/55 text-xs leading-relaxed whitespace-pre-wrap">{{ game.aiMessage }}</p>
        <div v-else class="flex items-center justify-center gap-1.5 py-1">
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
.ai-panel { text-shadow: 0 0 20px rgba(0,0,0,0.5); }
.ai-fade-enter-active { animation: ai-in 0.5s ease-out; }
.ai-fade-leave-active { animation: ai-out 1.5s ease-in; }
@keyframes ai-in { from { opacity: 0; transform: translate(-50%, 8px); } to { opacity: 1; transform: translate(-50%, 0); } }
@keyframes ai-out { from { opacity: 1; } to { opacity: 0; } }
.settings-fade-enter-active, .settings-fade-leave-active { transition: opacity 0.2s ease; }
.settings-fade-enter-from, .settings-fade-leave-to { opacity: 0; }
</style>
