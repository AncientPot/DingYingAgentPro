import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '../api'

export const useGameStore = defineStore('game', () => {
  const gameMode = ref(false)
  const gameType = ref('default')
  const subMode = ref('preparing')  // preparing | playing

  // AI 面板
  const aiMessage = ref('')
  const aiThinking = ref(false)

  // 设置
  const autoInterval = ref(0)
  const gameTools = ref([])
  const activeGameTool = ref(null)
  const thinkPrompt = ref('')

  // 自动回复定时器
  let autoTimer = null
  let threadId = ''

  function enterGame(type = 'default', tid = '') {
    gameMode.value = true
    gameType.value = type
    subMode.value = 'preparing'
    aiMessage.value = ''
    threadId = tid
  }

  function exitGame() {
    stopAutoReply()
    gameMode.value = false
    gameType.value = 'default'
    subMode.value = 'preparing'
    aiMessage.value = ''
  }

  async function startPlaying() {
    try { await api.gameStart() } catch (e) { console.warn(e) }
    subMode.value = 'playing'
    aiMessage.value = ''
    startAutoReply()
  }

  async function endPlaying() {
    stopAutoReply()
    try { await api.gameStop() } catch (e) { console.warn(e) }
    subMode.value = 'preparing'
  }

  async function checkState() {
    try {
      const data = await api.getGameState()
      gameMode.value = data.game_mode
      gameType.value = data.game_type || 'default'
      subMode.value = data.sub_mode || 'preparing'
      if (gameMode.value) {
        // 恢复设置并重启定时器
        await fetchSettings()
        if (subMode.value === 'playing') startAutoReply()
      }
    } catch (e) { /* ignore */ }
  }

  async function fetchSettings() {
    try {
      const data = await api.gameGetSettings()
      autoInterval.value = data.auto_reply_interval
      activeGameTool.value = data.active_game_tool || null
      thinkPrompt.value = data.think_prompt || ''
    } catch (e) { /* ignore */ }
  }

  async function saveSettings(payload) {
    await api.gameUpdateSettings(payload)
    await fetchSettings()
    if (gameMode.value && subMode.value === 'playing') startAutoReply()
  }

  async function triggerThink() {
    if (!gameMode.value || subMode.value !== 'playing' || !threadId || aiThinking.value) return
    aiThinking.value = true
    try {
      const controller = new AbortController()
      for await (const evt of api.gameThink(threadId, controller.signal)) {
        if (evt.type === 'chunk') aiMessage.value += evt.content || ''
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.warn('Think failed:', e)
    } finally { aiThinking.value = false }
  }

  function startAutoReply() {
    stopAutoReply()
    if (autoInterval.value <= 0) return
    autoTimer = setInterval(() => triggerThink(), autoInterval.value * 1000)
  }

  function stopAutoReply() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null }
  }

  function onUserMessage() { aiMessage.value = '' }
  function appendAiChunk(content) { aiMessage.value += content || '' }

  async function forceExit() {
    stopAutoReply()
    try { await api.exitGame() } catch (e) { /* */ }
    exitGame()
  }

  return {
    gameMode, gameType, subMode,
    aiMessage, aiThinking,
    autoInterval, activeGameTool, gameTools, thinkPrompt,
    enterGame, exitGame, startPlaying, endPlaying,
    checkState, fetchSettings, saveSettings,
    triggerThink, startAutoReply, stopAutoReply,
    onUserMessage, appendAiChunk, forceExit,
  }
})
