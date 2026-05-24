<script setup>
import { ref, nextTick, onMounted, watch, onActivated, onDeactivated } from 'vue'
import { useSessionStore } from '../stores/session'
import { streamMessage } from '../api'
import SessionSidebar from '../components/SessionSidebar.vue'
import ChatMessage from '../components/ChatMessage.vue'
import ToolCallCard from '../components/ToolCallCard.vue'
import ChatInput from '../components/ChatInput.vue'

const store = useSessionStore()
const messages = ref([])
const isStreaming = ref(false)
const abortController = ref(null)
const chatContainer = ref(null)
const initialLoad = ref(true)

// 当前会话名变化时切换消息
watch(() => store.activeName, (name, oldName) => {
  if (name !== oldName) {
    messages.value = []
  }
})

onMounted(async () => {
  await store.fetchSessions()
  if (store.sessions.length > 0) {
    store.activeName = store.sessions[0].name
  } else {
    await store.selectOrCreate('默认')
  }
  initialLoad.value = false
})

function scrollToBottom() {
  nextTick(() => {
    const el = chatContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function handleSend(text) {
  if (!store.activeName || isStreaming.value) return

  // 添加用户消息
  messages.value.push({ role: 'user', content: text, toolCalls: [] })

  // 添加 AI 占位消息 —— 关键：push 后再从数组中取引用，确保拿到 Vue 响应式代理
  messages.value.push({ role: 'assistant', content: '', toolCalls: [], streaming: true })
  const aiMsg = messages.value[messages.value.length - 1]
  scrollToBottom()

  // SSE 流式接收
  isStreaming.value = true
  const controller = new AbortController()
  abortController.value = controller

  try {
    for await (const evt of streamMessage(store.activeName, text, controller.signal)) {
      switch (evt.type) {
        case 'chunk': {
          aiMsg.content += evt.content || ''
          if (evt.tool_calls) {
            for (const tc of evt.tool_calls) {
              if (tc.name) {
                const existing = aiMsg.toolCalls.find(t => t.id === tc.id)
                if (!existing) {
                  aiMsg.toolCalls.push({ name: tc.name, args: tc.args || {}, id: tc.id, result: null })
                }
              }
            }
          }
          scrollToBottom()
          break
        }
        case 'tool': {
          const lastTC = aiMsg.toolCalls[aiMsg.toolCalls.length - 1]
          if (lastTC && !lastTC.result) {
            lastTC.result = evt.content
          } else if (evt.tool_name) {
            aiMsg.toolCalls.push({ name: evt.tool_name, args: {}, id: null, result: evt.content })
          }
          scrollToBottom()
          break
        }
        case 'error': {
          aiMsg.content = `错误: ${evt.content}`
          aiMsg.streaming = false
          break
        }
        case 'done': {
          aiMsg.streaming = false
          break
        }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      aiMsg.content = `请求失败: ${e.message}`
    }
    aiMsg.streaming = false
  } finally {
    isStreaming.value = false
    abortController.value = null
    scrollToBottom()
  }
}

function handleStop() {
  if (abortController.value) {
    abortController.value.abort()
    const lastAI = [...messages.value].reverse().find(m => m.role === 'assistant')
    if (lastAI) lastAI.streaming = false
    isStreaming.value = false
  }
}
</script>

<template>
  <div class="flex h-full">
    <SessionSidebar />

    <!-- 聊天区 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 消息列表 -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-white/25 select-none">
          <div class="w-16 h-16 rounded-2xl glass flex items-center justify-center mb-4">
            <span class="text-2xl font-mono text-accent/50">◇</span>
          </div>
          <p class="text-sm tracking-wide">开始一段对话</p>
          <p class="text-xs mt-1 text-white/15">输入消息，AI 将调用工具来回应你</p>
        </div>

        <!-- 消息列表 -->
        <template v-for="(msg, i) in messages" :key="i">
          <ChatMessage
            :role="msg.role"
            :content="msg.content"
            :is-streaming="msg.streaming"
          />
          <ToolCallCard
            v-for="(tc, j) in msg.toolCalls"
            :key="`${i}-tc-${j}`"
            :tool-name="tc.name"
            :content="tc.result || JSON.stringify(tc.args, null, 2)"
          />
        </template>
      </div>

      <!-- 输入栏 -->
      <div class="px-5 py-3 border-t border-white/[0.03] bg-base-900/50">
        <div class="max-w-3xl mx-auto flex items-end gap-3">
          <div class="flex-1">
            <ChatInput :disabled="!store.activeName" @send="handleSend" />
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
