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
  const showAiPanel = ref(false)
  // 准备中对话
  const prepMessages = ref([])
  let _panelTimer = null

  function _showPanel() {
    showAiPanel.value = true
    if (_panelTimer) clearTimeout(_panelTimer)
    _panelTimer = setTimeout(() => { showAiPanel.value = false }, 6000)
  }

  // 设置
  const autoInterval = ref(0)
  const gameTools = ref([])
  const activeGameTool = ref(null)
  const gameThinkPrompt = ref('')
  const toolThinkPrompt = ref('')
  const toolObstacleCount = ref(3)

  // 游戏工具结果通信（SnakeGame 等组件通过此字段获取 AI 工具调用结果）
  const lastToolResult = ref(null)
  // 游戏状态上下文（由游戏组件设置，在 think 时传给 AI）
  let gameContext = null

  function setGameContext(ctx) { gameContext = ctx }
  function setToolResult(name, content) { lastToolResult.value = { name, content, ts: Date.now() } }

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
    try { await api.gameStart(threadId) } catch (e) { console.warn(e) }
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
      gameThinkPrompt.value = data.game_think_prompt || ''
      toolThinkPrompt.value = data.tool_think_prompt || ''
      toolObstacleCount.value = data.tool_obstacle_count ?? 3
    } catch (e) { /* ignore */ }
  }

  async function saveSettings(payload) {
    await api.gameUpdateSettings(payload)
    await fetchSettings()
    if (gameMode.value && subMode.value === 'playing') startAutoReply()
  }

  async function triggerThink() {
    if (!gameMode.value || subMode.value !== 'playing' || !threadId || aiThinking.value) return
    aiMessage.value = ''  // 每次思考清空旧消息
    aiThinking.value = true
    try {
      const controller = new AbortController()
      for await (const evt of api.gameThink(threadId, controller.signal, gameContext)) {
        if (evt.type === 'chunk') {
          aiMessage.value += evt.content || ''
          _showPanel()
        } else if (evt.type === 'tool') {
          lastToolResult.value = { name: evt.tool_name, content: evt.content, ts: Date.now() }
        }
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

  async function sendPrepMessage(text) {
    prepMessages.value.push({ role: 'user', content: text })
    try {
      const data = await api.gameChat(text, threadId)
      if (data.response) {
        prepMessages.value.push({ role: 'ai', content: data.response })
      }
    } catch (e) {
      prepMessages.value.push({ role: 'ai', content: '发送失败: ' + e.message })
    }
  }

  async function gameOverReport(summary) {
    stopAutoReply()
    try { await api.gameOver(summary) } catch (e) { /* */ }
    subMode.value = 'preparing'
    aiMessage.value = ''
    gameContext = null
  }

  function onUserMessage() { aiMessage.value = '' }
  function appendAiChunk(content) { aiMessage.value += content || '' }

  async function forceExit(sessionName = '', onDone = null) {
    stopAutoReply()
    // 先立即退出游戏模式（无延迟）
    try { await api.exitGame() } catch (e) { /* */ }
    exitGame()
    if (onDone) onDone()
    // 异步发送退出消息（不阻塞 UI）
    if (sessionName) {
      api.sendMessage(sessionName, '退出游戏').catch(() => {})
    }
  }

  return {
    gameMode, gameType, subMode,
    aiMessage, aiThinking, showAiPanel, prepMessages,
    sendPrepMessage,
    autoInterval, activeGameTool, gameThinkPrompt, toolThinkPrompt, toolObstacleCount, gameTools,
    lastToolResult,
    enterGame, exitGame, startPlaying, endPlaying, gameOverReport,
    checkState, fetchSettings, saveSettings,
    triggerThink, startAutoReply, stopAutoReply,
    onUserMessage, appendAiChunk, forceExit,
    setGameContext, setToolResult,
  }
})
