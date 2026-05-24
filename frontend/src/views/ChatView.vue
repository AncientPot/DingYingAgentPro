<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
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

watch(() => store.activeName, (name, oldName) => {
  if (name !== oldName) messages.value = []
})

onMounted(async () => {
  await store.fetchSessions()
  if (store.sessions.length > 0) {
    store.activeName = store.sessions[0].name
  } else {
    await store.selectOrCreate('默认')
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

  // 用户消息
  messages.value.push({ type: 'user', content: text })

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
          // 追加到当前 AI 文本段
          if (activeAiIdx >= 0 && activeAiIdx < messages.value.length) {
            messages.value[activeAiIdx].content += evt.content || ''
          }

          // 发现新的工具调用 — 结束当前 AI 段，插入 tool 卡片，再开新 AI 段
          if (evt.tool_calls) {
            for (const tc of evt.tool_calls) {
              if (!tc.name) continue
              // 检查 tool 卡片是否已存在（按 ID 去重）
              const exists = messages.value.find(m => m.type === 'tool' && m.id === tc.id)
              if (exists) continue
              // 结束当前流式 AI 段
              finishAiSegment()
              // 插入 tool 卡片
              messages.value.push({
                type: 'tool',
                name: tc.name,
                id: tc.id,
                args: tc.args || {},
                result: null,
              })
              // 开启新的 AI 文本段（等待后续 chunk 或 tool 结果）
              startAiSegment()
            }
          }
          scrollToBottom()
          break
        }
        case 'tool': {
          // 工具返回结果 — 按 tool_call_id 匹配 tool 卡片
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
            // 后端产生的 tool 事件但前端还没收到对应的 tool_call chunk
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
      <div ref="chatContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-white/25 select-none">
          <div class="w-16 h-16 rounded-2xl glass flex items-center justify-center mb-4">
            <span class="text-2xl font-mono text-accent/50">◇</span>
          </div>
          <p class="text-sm tracking-wide">开始一段对话</p>
          <p class="text-xs mt-1 text-white/15">输入消息，AI 将调用工具来回应你</p>
        </div>

        <!-- 交织渲染：用户消息 / AI 文本段 / 工具调用卡片 -->
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
