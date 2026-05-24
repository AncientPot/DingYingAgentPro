import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api'

export const useConfigStore = defineStore('config', () => {
  const items = ref([])
  const loading = ref(false)
  const saving = ref(false)
  const saved = ref(false)
  const error = ref('')

  function getValue(key) {
    const item = items.value.find(i => i.key === key)
    return item ? item.value : ''
  }

  async function fetchConfig() {
    loading.value = true
    try {
      const data = await api.getConfig()
      items.value = data.configs
    } finally {
      loading.value = false
    }
  }

  async function saveConfig(partial) {
    saving.value = true
    saved.value = false
    error.value = ''
    try {
      const data = await api.updateConfig(partial)
      items.value = data.configs
      saved.value = true
      setTimeout(() => { saved.value = false }, 3000)
    } catch (e) {
      error.value = e.message || '保存失败'
      setTimeout(() => { error.value = '' }, 5000)
      throw e
    } finally {
      saving.value = false
    }
  }

  return {
    items,
    loading,
    saving,
    saved,
    error,
    getValue,
    fetchConfig,
    saveConfig,
  }
})
