import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '../api'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref([])
  const activeName = ref('')
  const loading = ref(false)

  const activeSession = computed(() =>
    sessions.value.find(s => s.name === activeName.value)
  )

  async function fetchSessions() {
    loading.value = true
    try {
      const data = await api.getSessions()
      sessions.value = data.sessions
    } finally {
      loading.value = false
    }
  }

  async function selectOrCreate(name) {
    if (!name.trim()) return
    try {
      const data = await api.createSession(name.trim())
      activeName.value = data.name
      await fetchSessions()
    } catch (e) {
      console.error('Failed to create session:', e)
    }
  }

  async function removeSession(name) {
    try {
      await api.deleteSession(name)
      if (activeName.value === name) {
        activeName.value = sessions.value.length > 1
          ? sessions.value.find(s => s.name !== name)?.name || ''
          : ''
      }
      await fetchSessions()
    } catch (e) {
      console.error('Failed to delete session:', e)
    }
  }

  return {
    sessions,
    activeName,
    loading,
    activeSession,
    fetchSessions,
    selectOrCreate,
    removeSession,
  }
})
