<script setup>
defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  isStreaming: { type: Boolean, default: false },
})

function renderContent(text) {
  if (!text) return ''
  // 将 **粗体** 转为 HTML
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-medium">$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <div class="msg-enter flex gap-3" :class="role === 'user' ? 'justify-end' : 'justify-start'">
    <!-- AI 头像 -->
    <div v-if="role === 'assistant'" class="shrink-0 w-8 h-8 rounded-lg bg-accent/8 border border-accent/15 flex items-center justify-center text-accent text-xs font-mono">
      AI
    </div>

    <!-- 消息气泡 -->
    <div
      class="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed"
      :class="role === 'user'
        ? 'bg-white/[0.10] border border-white/[0.10] text-white/90 rounded-br-md'
        : 'bg-white/[0.03] text-white/80 rounded-bl-md'"
    >
      <!-- content -->
      <div
        v-if="content"
        class="break-words"
        :class="{ 'typing-cursor': isStreaming }"
        v-html="renderContent(content)"
      ></div>

      <!-- 流式加载中的空状态 -->
      <div v-if="!content && isStreaming" class="flex items-center gap-1.5 py-1">
        <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent"></span>
        <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent"></span>
        <span class="loading-dot w-1.5 h-1.5 rounded-full bg-accent"></span>
      </div>
    </div>

    <!-- 用户头像 -->
    <div v-if="role === 'user'" class="shrink-0 w-8 h-8 rounded-lg bg-white/[0.10] border border-white/[0.10] flex items-center justify-center text-white/60 text-xs font-mono">
      U
    </div>
  </div>
</template>
