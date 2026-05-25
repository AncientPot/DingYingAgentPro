<script setup>
import { ref, nextTick } from 'vue'

const emit = defineEmits(['send'])
const input = ref('')
const textarea = ref(null)

const props = defineProps({
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入消息，Enter 发送，Shift+Enter 换行...' },
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
  <div class="flex items-center gap-2.5 px-3.5 py-2.5 glass border-white/[0.08] rounded-2xl transition-all duration-300 focus-within:border-accent/40 focus-within:shadow-[0_0_30px_rgba(0,229,255,0.06)]">
    <textarea
      ref="textarea"
      v-model="input"
      rows="1"
      :disabled="disabled"
      class="flex-1 bg-transparent text-[13px] text-white/80 placeholder-white/20 resize-none max-h-40 font-mono leading-relaxed outline-none border-0 my-0.5"
      :class="disabled ? 'opacity-40 cursor-not-allowed' : ''"
      :placeholder="placeholder"
      @keydown="handleKeydown"
      @input="autoResize"
    ></textarea>
    <button
      :disabled="disabled || !input.trim()"
      class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200"
      :class="input.trim() && !disabled
        ? 'bg-accent/20 text-accent hover:bg-accent/30 hover:shadow-[0_0_15px_rgba(0,229,255,0.2)] active:scale-90'
        : 'bg-white/[0.05] text-white/15 cursor-not-allowed'"
      @click="handleSend"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"></line>
        <polyline points="5 12 12 5 19 12"></polyline>
      </svg>
    </button>
  </div>
</template>
