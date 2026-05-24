<script setup>
import { ref, onMounted } from 'vue'
import { useConfigStore } from '../stores/config'

const store = useConfigStore()

// 本地编辑状态
const form = ref({})

onMounted(async () => {
  await store.fetchConfig()
  // 初始化表单
  for (const item of store.items) {
    form.value[item.key] = item.value
  }
})

// 配置项定义
const fields = [
  {
    key: 'model_name',
    label: '模型名称',
    hint: 'DeepSeek 模型标识符',
    type: 'select',
    options: ['deepseek-chat', 'deepseek-reasoner'],
  },
  {
    key: 'temperature',
    label: '温度',
    hint: '控制输出随机性，0 = 确定，2 = 最随机',
    type: 'range',
    min: 0, max: 2, step: 0.1,
  },
  {
    key: 'api_key',
    label: 'API 密钥',
    hint: 'DeepSeek API Key（已脱敏显示）',
    type: 'password',
  },
  {
    key: 'base_url',
    label: 'API 地址',
    hint: '自定义 API 基础 URL，留空使用默认',
    type: 'text',
  },
  {
    key: 'system_prompt',
    label: '系统提示词',
    hint: '定义 AI 助手的行为风格和角色',
    type: 'textarea',
  },
  {
    key: 'max_search_results',
    label: '最大搜索结果',
    hint: '联网搜索返回的最大结果数量',
    type: 'number',
    min: 1, max: 10,
  },
]

function fieldValue(key, defaultVal = '') {
  return form.value[key] ?? defaultVal
}

function setFieldValue(key, val) {
  form.value[key] = val
}

async function handleSave() {
  // 只发送当前页面上可见且被用户修改过的字段
  const visibleKeys = fields.map(f => f.key)
  const payload = {}
  for (const key of visibleKeys) {
    const val = form.value[key]
    if (val === undefined || val === null) continue
    // api_key 脱敏保护：如果值含 '*' 说明是脱敏值，用户未修改，跳过发送
    if (key === 'api_key' && typeof val === 'string' && val.includes('*')) continue
    // 恢复数字类型
    if (key === 'temperature') payload[key] = parseFloat(val)
    else if (key === 'max_search_results') payload[key] = parseInt(val)
    else payload[key] = String(val).trim()
  }
  await store.saveConfig(payload)
}
</script>

<template>
  <div class="h-full overflow-y-auto">
    <div class="max-w-2xl mx-auto py-8 px-6 space-y-6">
      <!-- 标题 -->
      <div class="mb-8">
        <h1 class="text-xl font-semibold text-white/85 tracking-wide">设置</h1>
        <p class="text-xs text-white/25 mt-1">配置 AI 模型参数，修改后即时生效无需重启</p>
      </div>

      <!-- 配置卡片 -->
      <div
        v-for="field in fields"
        :key="field.key"
        class="glass rounded-xl px-5 py-4 transition-all duration-200 hover:border-white/[0.1]"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <label class="text-sm text-white/70 font-medium block">{{ field.label }}</label>
            <p class="text-[11px] text-white/25 mt-0.5">{{ field.hint }}</p>
          </div>
          <div class="shrink-0">
            <!-- select -->
            <select
              v-if="field.type === 'select'"
              :value="fieldValue(field.key)"
              @change="setFieldValue(field.key, $event.target.value)"
              class="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white/70 font-mono focus:outline-none focus:border-accent/30 cursor-pointer"
            >
              <option v-for="opt in field.options" :key="opt" :value="opt" class="bg-base-800">{{ opt }}</option>
            </select>

            <!-- range -->
            <div v-else-if="field.type === 'range'" class="flex items-center gap-3">
              <input
                type="range"
                :min="field.min"
                :max="field.max"
                :step="field.step"
                :value="fieldValue(field.key, 0.7)"
                @input="setFieldValue(field.key, parseFloat($event.target.value))"
                class="w-28 accent-accent h-1 cursor-pointer"
              />
              <span class="text-xs font-mono text-accent w-8 text-right">{{ fieldValue(field.key, 0.7) }}</span>
            </div>

            <!-- number -->
            <input
              v-else-if="field.type === 'number'"
              type="number"
              :min="field.min"
              :max="field.max"
              :value="fieldValue(field.key, 2)"
              @input="setFieldValue(field.key, parseInt($event.target.value))"
              class="w-20 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white/70 font-mono text-right focus:outline-none focus:border-accent/30"
            />

            <!-- password -->
            <input
              v-else-if="field.type === 'password'"
              type="password"
              :value="fieldValue(field.key)"
              @input="setFieldValue(field.key, $event.target.value)"
              class="w-52 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white/70 font-mono focus:outline-none focus:border-accent/30"
              placeholder="留空使用环境变量"
            />

            <!-- text -->
            <input
              v-else-if="field.type === 'text'"
              type="text"
              :value="fieldValue(field.key)"
              @input="setFieldValue(field.key, $event.target.value)"
              class="w-52 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white/70 font-mono focus:outline-none focus:border-accent/30"
              placeholder="留空使用默认"
            />

            <!-- textarea -->
            <textarea
              v-else-if="field.type === 'textarea'"
              :value="fieldValue(field.key)"
              @input="setFieldValue(field.key, $event.target.value)"
              rows="3"
              class="w-72 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white/70 font-mono leading-relaxed resize-none focus:outline-none focus:border-accent/30"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- 保存 -->
      <div class="flex items-center gap-4 pt-2">
        <button
          :disabled="store.saving"
          class="px-6 py-2 rounded-xl text-sm font-medium transition-all duration-200 border"
          :class="store.saving
            ? 'bg-white/[0.03] text-white/20 border-white/[0.05] cursor-wait'
            : 'bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 hover:glow-accent active:scale-[0.98]'"
          @click="handleSave"
        >
          {{ store.saving ? '保存中...' : '保存设置' }}
        </button>
        <transition name="fade">
          <span v-if="store.saved" class="text-xs text-emerald-400/80">已保存，Agent 图已自动重建</span>
        </transition>
        <transition name="fade">
          <span v-if="store.error" class="text-xs text-red-400/80">{{ store.error }}</span>
        </transition>
      </div>
    </div>
  </div>
</template>
