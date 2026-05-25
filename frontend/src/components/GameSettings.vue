<script setup>
import { ref, watch, onMounted } from 'vue'
import { useGameStore } from '../stores/game'
import * as api from '../api'

const emit = defineEmits(['close'])
const game = useGameStore()

const interval = ref(game.autoInterval)
const prompt = ref(game.thinkPrompt)
const selectedTool = ref(game.activeGameTool)
const gameToolList = ref([])
const saving = ref(false)
const saved = ref(false)

watch(() => game.autoInterval, v => { interval.value = v })
watch(() => game.thinkPrompt, v => { prompt.value = v })
watch(() => game.activeGameTool, v => { selectedTool.value = v })

onMounted(async () => {
  try {
    const data = await api.gameGetTools()
    gameToolList.value = data.tools || []
  } catch (e) { /* ignore */ }
})

async function handleSave() {
  saving.value = true; saved.value = false
  try {
    await game.saveSettings({
      auto_reply_interval: Number(interval.value),
      think_prompt: prompt.value,
      active_game_tool: selectedTool.value,
    })
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } finally { saving.value = false }
}
</script>

<template>
  <div class="relative z-20 mx-5 mb-3 glass rounded-2xl p-5 space-y-5">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-medium text-white/70">游戏设置</h3>
      <button class="text-white/20 hover:text-white/50 transition-colors text-sm" @click="emit('close')">✕</button>
    </div>

    <!-- AI 自主回复 -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <label class="text-xs text-white/50">AI 自主回复间隔</label>
        <span class="text-xs font-mono" :class="interval == 0 ? 'text-white/25' : 'text-accent/70'">
          {{ interval == 0 ? '关闭' : interval + ' 秒' }}
        </span>
      </div>
      <input v-model.number="interval" type="range" min="0" max="120" step="5" class="w-full accent-accent h-1 cursor-pointer" />
      <div class="flex justify-between text-[10px] text-white/15 mt-1">
        <span>关闭</span><span>30s</span><span>60s</span><span>120s</span>
      </div>
    </div>

    <!-- AI 思考提示词 -->
    <div>
      <label class="text-xs text-white/50 block mb-2">AI 自主思考提示词</label>
      <textarea
        v-model="prompt" rows="3"
        class="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white/70 font-mono leading-relaxed resize-none focus:outline-none focus:border-accent/30 placeholder-white/15"
        placeholder="输入 AI 在自主思考时使用的提示词..."
      ></textarea>
    </div>

    <!-- 游戏工具选择 -->
    <div>
      <label class="text-xs text-white/50 block mb-3">游戏工具（单选，启动游戏后生效）</label>

      <!-- 无工具可用的空状态 -->
      <div v-if="gameToolList.length === 0" class="text-center py-4">
        <p class="text-xs text-white/15">暂无可用游戏工具</p>
        <p class="text-[10px] text-white/10 mt-1">在 app/tools/game_tools/ 下创建游戏工具</p>
      </div>

      <!-- 工具单选列表 -->
      <div v-else class="space-y-1.5">
        <div
          v-for="tool in gameToolList"
          :key="tool.name"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150"
          :class="selectedTool === tool.name
            ? 'bg-accent/8 border border-accent/15'
            : 'bg-white/[0.02] border border-transparent hover:bg-white/[0.04]'"
          @click="selectedTool = tool.name"
        >
          <!-- 单选圆圈 -->
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

    <!-- 保存 -->
    <div class="flex items-center gap-3 pt-1">
      <button
        :disabled="saving"
        class="px-5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 border"
        :class="saving ? 'bg-white/[0.03] text-white/20 border-white/[0.05]' : 'bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 active:scale-[0.98]'"
        @click="handleSave"
      >{{ saving ? '保存中...' : '保存' }}</button>
      <transition name="fade"><span v-if="saved" class="text-xs text-emerald-400/70">已保存</span></transition>
    </div>
  </div>
</template>
