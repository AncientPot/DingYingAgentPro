<script setup>
import { ref, nextTick } from 'vue'

const emit = defineEmits(['send'])
const input = ref('')
const textarea = ref(null)

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

function handleSend() {
  const msg = input.value.trim()
  if (!msg || props.disabled) return
  emit('send', msg)
  input.value = ''
  nextTick(() => textarea.value?.focus())
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// 自动调整高度
function autoResize() {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}
</script>

<template>
  <div class="flex items-end gap-3 px-4 py-3 glass border-white/[0.10] rounded-2xl transition-all duration-200 focus-within:border-accent/40 focus-within:shadow-[0_0_25px_rgba(0,229,255,0.08)]">
    <textarea
      ref="textarea"
      v-model="input"
      rows="1"
      :disabled="disabled"
      class="flex-1 bg-transparent text-sm text-white/85 placeholder-white/20 resize-none max-h-40 font-mono leading-relaxed glass-input"
      :class="disabled ? 'opacity-40 cursor-not-allowed' : ''"
      placeholder="输入消息，Enter 发送，Shift+Enter 换行..."
      @keydown="handleKeydown"
      @input="autoResize"
    ></textarea>
    <button
      :disabled="disabled || !input.trim()"
      class="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200"
      :class="input.trim() && !disabled
        ? 'bg-accent/20 text-accent hover:bg-accent/30 hover:glow-accent active:scale-95'
        : 'bg-white/[0.06] text-white/20 cursor-not-allowed'"
      @click="handleSend"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"></line>
        <polyline points="5 12 12 5 19 12"></polyline>
      </svg>
    </button>
  </div>
</template>
