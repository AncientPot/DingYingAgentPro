<script setup>
import { ref, watch, onMounted } from 'vue'
import { useGameStore } from '../stores/game'
import * as api from '../api'

const emit = defineEmits(['close'])
const game = useGameStore()

const interval = ref(game.autoInterval)
const selectedTool = ref(game.activeGameTool)
const thinkPrompt = ref(game.gameThinkPrompt)
const toolThinkPrompt = ref(game.toolThinkPrompt)
const gameToolList = ref([])
const saving = ref(false)
const saved = ref(false)

watch(() => game.autoInterval, v => { interval.value = v })
watch(() => game.activeGameTool, v => { selectedTool.value = v })
watch(() => game.gameThinkPrompt, v => { thinkPrompt.value = v })
watch(() => game.toolThinkPrompt, v => { toolThinkPrompt.value = v })

onMounted(async () => { try { gameToolList.value = (await api.gameGetTools()).tools || [] } catch (e) { /* */ } })

async function handleSave() {
  saving.value = true; saved.value = false
  try {
    await game.saveSettings({
      auto_reply_interval: Number(interval.value),
      game_think_prompt: thinkPrompt.value,
      tool_think_prompt: toolThinkPrompt.value,
      active_game_tool: selectedTool.value,
    })
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } finally { saving.value = false }
}
</script>

<template>
  <div class="glass rounded-2xl p-6 space-y-6 h-full flex flex-col">
    <h3 class="text-sm font-medium text-white/70 shrink-0">游戏设置</h3>

    <div class="flex-1 overflow-y-auto space-y-6 pr-1">
      <!-- 游戏工具选择 -->
      <div>
        <label class="text-xs text-white/50 block mb-3">游戏工具（单选，启动后生效）</label>
        <div v-if="gameToolList.length === 0" class="text-center py-6">
          <p class="text-xs text-white/15">暂无可用游戏工具</p>
        </div>
        <div v-else class="space-y-1.5">
          <div v-for="tool in gameToolList" :key="tool.name"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150"
            :class="selectedTool === tool.name ? 'bg-accent/8 border border-accent/15' : 'bg-white/[0.02] border border-transparent hover:bg-white/[0.04]'"
            @click="selectedTool = tool.name">
            <div class="shrink-0 w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors"
              :class="selectedTool === tool.name ? 'border-accent' : 'border-white/[0.15]'">
              <div v-if="selectedTool === tool.name" class="w-2 h-2 rounded-full bg-accent"></div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs text-white/65 font-mono">{{ tool.display || tool.name }}</div>
              <div class="text-[10px] text-white/25 leading-relaxed mt-0.5">{{ tool.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 选中工具的专属设置 -->
      <div v-if="selectedTool === 'snake_game'" class="space-y-4">
        <div>
          <label class="text-xs text-white/50 block mb-2">AI 自主回复间隔</label>
          <div class="flex items-center justify-between mb-1">
            <input v-model.number="interval" type="range" min="0" max="120" step="5" class="flex-1 accent-accent h-1 cursor-pointer" />
            <span class="text-xs font-mono ml-3 w-12 text-right" :class="interval == 0 ? 'text-white/25' : 'text-accent/70'">{{ interval == 0 ? '关闭' : interval + ' 秒' }}</span>
          </div>
          <div class="flex justify-between text-[10px] text-white/15"><span>关闭</span><span>30s</span><span>60s</span><span>120s</span></div>
        </div>
        <div>
          <label class="text-xs text-white/50 block mb-2">贪吃蛇 AI 提示词</label>
          <textarea v-model="toolThinkPrompt" rows="3"
            class="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white/70 font-mono leading-relaxed resize-none focus:outline-none focus:border-accent/30"
            placeholder="贪吃蛇游戏专属 AI 提示词..."></textarea>
        </div>
      </div>

      <!-- 未选工具提示 -->
      <div v-if="!selectedTool" class="text-center py-4">
        <p class="text-xs text-white/15">请先选择游戏工具</p>
      </div>

    </div>

    <!-- 保存 -->
    <div class="flex items-center gap-3 pt-2 border-t border-white/[0.04] shrink-0">
      <button :disabled="saving" class="px-5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border"
        :class="saving ? 'bg-white/[0.03] text-white/20 border-white/[0.05]' : 'bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 active:scale-[0.98]'"
        @click="handleSave">{{ saving ? '保存中...' : '保存' }}</button>
      <transition name="fade"><span v-if="saved" class="text-xs text-emerald-400/70">已保存</span></transition>
    </div>
  </div>
</template>
