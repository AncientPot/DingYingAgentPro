<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useSessionStore } from '../stores/session'
import { useGameStore } from '../stores/game'
import { streamMessage, getSessionMessages } from '../api'
import SessionSidebar from '../components/SessionSidebar.vue'
import ChatMessage from '../components/ChatMessage.vue'
import ToolCallCard from '../components/ToolCallCard.vue'
import ChatInput from '../components/ChatInput.vue'
import GameCanvas from '../components/GameCanvas.vue'

const store = useSessionStore()
const game = useGameStore()
const messages = ref([])
const isStreaming = ref(false)
const abortController = ref(null)
const chatContainer = ref(null)

// 从后端加载会话历史，转换为前端交织格式
async function loadHistory(name) {
  messages.value = []
  if (!name) return
  try {
    const data = await getSessionMessages(name)
    const raw = data.messages || []
    for (const m of raw) {
      if (m.role === 'user') {
        messages.value.push({ type: 'user', content: m.content })
      } else if (m.role === 'assistant') {
        // AI 文本段（先放文本，工具调用在下面单独插入）
        messages.value.push({ type: 'ai', content: m.content || '', streaming: false })
        // 工具调用 → 插入 tool 卡片（历史中无 result）
        const tcs = m.tool_calls || []
        for (const tc of tcs) {
          messages.value.push({
            type: 'tool',
            name: tc.name || '',
            id: tc.id || '',
            args: tc.args || {},
            result: null,
          })
        }
      } else if (m.role === 'tool') {
        // 工具结果 → 匹配已有 tool 卡片填入 result
        const card = messages.value.find(
          t => t.type === 'tool' && t.id === m.tool_call_id && !t.result
        )
        if (card) {
          card.result = m.content
        }
      }
    }
    scrollToBottom()
  } catch (e) {
    console.error('Failed to load history:', e)
  }
}

watch(() => store.activeName, (name) => {
  loadHistory(name)
})

onMounted(async () => {
  await store.fetchSessions()
  if (store.sessions.length > 0) {
    store.activeName = store.sessions[0].name
  } else {
    await store.selectOrCreate('默认')
  }
  // 刷新后检查游戏状态（恢复子模式 + 设置 + 定时器）
  await game.checkState()
  if (game.gameMode && game.subMode === 'playing') {
    game.startAutoReply()
  }
})

function scrollToBottom() {
  nextTick(() => {
    const el = chatContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// 当前正在流式输出的 AI 文本段索引（-1 表示无活跃段）
let activeAiIdx = -1

function startAiSegment() {
  messages.value.push({ type: 'ai', content: '', streaming: true })
  activeAiIdx = messages.value.length - 1
  return messages.value[activeAiIdx]
}

function finishAiSegment() {
  if (activeAiIdx >= 0 && activeAiIdx < messages.value.length) {
    messages.value[activeAiIdx].streaming = false
  }
  activeAiIdx = -1
}

async function handleSend(text) {
  if (!store.activeName || isStreaming.value) return

  // 准备中子模式：路由到游戏对话（与正常对话隔离）
  if (game.gameMode && game.subMode === 'preparing') {
    messages.value.push({ type: 'user', content: text })
    game.sendPrepMessage(text)
    scrollToBottom()
    return
  }

  // 游戏中子模式：不允许对话
  if (game.gameMode && game.subMode === 'playing') return

  // 正常模式
  if (game.gameMode) {
    game.onUserMessage(text)
    messages.value.push({ type: 'user', content: text })
  } else {
    messages.value.push({ type: 'user', content: text })
  }

  // 第一个 AI 文本段
  const seg = startAiSegment()
  scrollToBottom()

  isStreaming.value = true
  const controller = new AbortController()
  abortController.value = controller

  try {
    for await (const evt of streamMessage(store.activeName, text, controller.signal)) {
      switch (evt.type) {
        case 'chunk': {
          // 游戏模式：追加到游戏 AI 面板
          if (game.gameMode) {
            game.appendAiChunk(evt.content || '')
          }
          // 正常模式：追加到聊天 AI 段
          if (activeAiIdx >= 0 && activeAiIdx < messages.value.length) {
            messages.value[activeAiIdx].content += evt.content || ''
          }

          // 发现新的工具调用
          if (evt.tool_calls) {
            for (const tc of evt.tool_calls) {
              if (!tc.name) continue
              const exists = messages.value.find(m => m.type === 'tool' && m.id === tc.id)
              if (exists) continue
              finishAiSegment()
              messages.value.push({
                type: 'tool',
                name: tc.name,
                id: tc.id,
                args: tc.args || {},
                result: null,
              })
              startAiSegment()
            }
          }
          scrollToBottom()
          break
        }
        case 'tool': {
          const targetId = evt.tool_call_id
          let card = null
          if (targetId) {
            card = messages.value.find(m => m.type === 'tool' && m.id === targetId && !m.result)
          }
          if (!card) {
            card = messages.value.find(m => m.type === 'tool' && !m.result)
          }
          if (card) {
            card.result = evt.content
          } else if (evt.tool_name) {
            messages.value.push({
              type: 'tool',
              name: evt.tool_name,
              id: targetId || null,
              args: {},
              result: evt.content,
            })
          }
          scrollToBottom()
          break
        }
        case 'error': {
          if (activeAiIdx >= 0 && activeAiIdx < messages.value.length) {
            messages.value[activeAiIdx].content += `\n错误: ${evt.content}`
          }
          finishAiSegment()
          break
        }
        case 'done': {
          finishAiSegment()
          // 检测游戏模式状态变更（进入准备中，不启动自主回复）
          if (evt.game_mode && !game.gameMode) {
            const tid = store.activeSession?.thread_id || ''
            game.enterGame(evt.game_type || 'default', tid)
          } else if (!evt.game_mode && game.gameMode) {
            game.exitGame()
          }
          break
        }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      if (activeAiIdx >= 0 && activeAiIdx < messages.value.length) {
        messages.value[activeAiIdx].content += `\n请求失败: ${e.message}`
      }
    }
    finishAiSegment()
  } finally {
    isStreaming.value = false
    abortController.value = null
    activeAiIdx = -1
    scrollToBottom()
  }
}

function handleStop() {
  if (abortController.value) {
    abortController.value.abort()
    finishAiSegment()
    isStreaming.value = false
  }
}
</script>

<template>
  <div class="flex h-full">
    <SessionSidebar />

    <div class="flex-1 flex flex-col min-w-0">
      <!-- 游戏模式 -->
      <GameCanvas v-if="game.gameMode" :session-name="store.activeName" @exited="loadHistory(store.activeName)" />

      <!-- 正常聊天模式 -->
      <div v-else ref="chatContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-3 chat-area">
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-white/25 select-none">
          <div class="w-16 h-16 rounded-2xl glass flex items-center justify-center mb-4">
            <span class="text-2xl font-mono text-accent/50">◇</span>
          </div>
          <p class="text-sm tracking-wide">开始一段对话</p>
          <p class="text-xs mt-1 text-white/15">输入消息，AI 将调用工具来回应你</p>
        </div>

        <template v-for="(msg, i) in messages" :key="i">
          <ChatMessage
            v-if="msg.type === 'user'"
            :role="'user'"
            :content="msg.content"
          />
          <ChatMessage
            v-else-if="msg.type === 'ai'"
            :role="'assistant'"
            :content="msg.content"
            :is-streaming="msg.streaming"
          />
          <ToolCallCard
            v-else-if="msg.type === 'tool'"
            :tool-name="msg.name"
            :content="msg.result || JSON.stringify(msg.args, null, 2)"
          />
        </template>
      </div>

      <div class="px-5 py-3 border-t border-white/[0.03] bg-base-900/50" :class="{ 'border-accent/10': game.gameMode }">
        <div class="max-w-2xl mx-auto flex items-center gap-3">
          <div class="flex-1">
            <ChatInput
              :disabled="!store.activeName || (game.gameMode && game.subMode === 'playing')"
              :placeholder="game.gameMode && game.subMode === 'playing' ? '游戏中，AI 自主回复中...' : game.gameMode ? '准备中，与 AI 讨论游戏...' : '输入消息，Enter 发送，Shift+Enter 换行...'"
              @send="handleSend"
            />
          </div>
          <button
            v-if="isStreaming"
            class="shrink-0 w-9 h-9 rounded-xl bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all flex items-center justify-center"
            title="停止生成"
            @click="handleStop"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"></rect></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
