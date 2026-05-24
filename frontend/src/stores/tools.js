import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api'

export const useToolsStore = defineStore('tools', () => {
  const tools = ref([])
  const loading = ref(false)

  async function fetchTools() {
    loading.value = true
    try {
      const data = await api.getTools()
      tools.value = data.tools
    } finally {
      loading.value = false
    }
  }

  async function toggle(name, enabled) {
    try {
      const data = await api.toggleTool(name, enabled)
      const idx = tools.value.findIndex(t => t.name === name)
      if (idx >= 0) tools.value[idx] = data
    } catch (e) {
      console.error('Failed to toggle tool:', e)
    }
  }

  return { tools, loading, fetchTools, toggle }
})
