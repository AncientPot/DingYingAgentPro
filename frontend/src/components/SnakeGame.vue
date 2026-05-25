<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useGameStore } from '../stores/game'

const game = useGameStore()

const GRID = 40
const CELL = 14
const canvasW = GRID * CELL
const canvasH = GRID * CELL

const canvasRef = ref(null)
let ctx = null
let animId = null
let gameOverTimeout = null

// 游戏状态
const snake = ref([])
const direction = ref({ x: 1, y: 0 })
const nextDir = ref({ x: 1, y: 0 })
const obstacles = ref([])
const foods = ref([])
const score = ref(0)
const gameOver = ref(false)
const gameOverReported = ref(false)

const SPEED = 150
let lastTick = 0

const DIR_NAMES = { '1,0': '右', '-1,0': '左', '0,-1': '上', '0,1': '下' }

function initState() {
  snake.value = [{ x: 20, y: 20 }, { x: 19, y: 20 }, { x: 18, y: 20 }]
  direction.value = { x: 1, y: 0 }
  nextDir.value = { x: 1, y: 0 }
  obstacles.value = []
  foods.value = []
  score.value = 0
  gameOver.value = false
  gameOverReported.value = false
}

function isOccupied(x, y) {
  if (snake.value.some(s => s.x === x && s.y === y)) return true
  if (obstacles.value.some(o => o.x === x && o.y === y)) return true
  if (foods.value.some(f => f.x === x && f.y === y)) return true
  return false
}

// 游戏状态文本（传给 AI）
function gameStateText() {
  const body = snake.value.map(p => `(${p.x},${p.y})`).join(',')
  const obs = obstacles.value.map(p => `(${p.x},${p.y})`).join(',') || '无'
  const fdList = foods.value.map(f => `(${f.x},${f.y})`).join(',') || '无'
  const key = `${direction.value.x},${direction.value.y}`
  const dirName = DIR_NAMES[key] || '右'
  const overText = gameOver.value ? '\n⚠️ 游戏已结束（蛇撞到了障碍物/墙壁/自身）。请对此做出回应。' : ''
  return `蛇长:${snake.value.length} 方向:${dirName} 蛇身:[${body}] 障碍物:[${obs}] 食物:[${fdList}] 网格:${GRID}x${GRID}${overText}`
}

defineExpose({ gameStateText })

// 解析 AI 工具调用结果（支持批量：多行结果，每行一个放置项）
function handleToolResult(toolName, content) {
  if (toolName !== 'snake_game' || !content) return
  const lines = String(content).split('\n')
  for (const line of lines) {
    const match = line.trim().match(/^(FOOD|OBSTACLE):(\d+),(\d+)$/)
    if (!match) continue
    const x = parseInt(match[2]), y = parseInt(match[3])
    if (x < 0 || x >= GRID || y < 0 || y >= GRID) continue
    if (isOccupied(x, y)) continue

    if (match[1] === 'FOOD') {
      foods.value.push({ x, y })
    } else {
      obstacles.value.push({ x, y })
    }
  }
}

function startLoop() {
  lastTick = performance.now()
  animId = requestAnimationFrame(gameLoop)
}

function stopLoop() {
  if (animId) { cancelAnimationFrame(animId); animId = null }
}

// 游戏循环
function gameLoop(ts) {
  if (ts - lastTick < SPEED) {
    animId = requestAnimationFrame(gameLoop)
    return
  }
  lastTick = ts
  tick()
  draw()
  animId = requestAnimationFrame(gameLoop)
}

function tick() {
  direction.value = { ...nextDir.value }
  const head = snake.value[0]
  const newHead = { x: head.x + direction.value.x, y: head.y + direction.value.y }

  if (newHead.x < 0 || newHead.x >= GRID || newHead.y < 0 || newHead.y >= GRID) {
    return triggerGameOver()
  }
  if (snake.value.some(s => s.x === newHead.x && s.y === newHead.y)) {
    return triggerGameOver()
  }
  if (obstacles.value.some(o => o.x === newHead.x && o.y === newHead.y)) {
    return triggerGameOver()
  }

  snake.value.unshift(newHead)

  // 吃食物：匹配数组中任意一个
  const eatenIdx = foods.value.findIndex(f => f.x === newHead.x && f.y === newHead.y)
  if (eatenIdx !== -1) {
    score.value++
    foods.value.splice(eatenIdx, 1)
  } else {
    snake.value.pop()
  }
}

function triggerGameOver() {
  gameOver.value = true
  game.stopAutoReply()
  stopLoop()
  gameOverTimeout = setTimeout(() => {
    if (!gameOverReported.value) {
      gameOverReported.value = true
      game.gameOverReport(`贪吃蛇游戏结束。得分:${score.value} 长度:${snake.value.length} 障碍物:${obstacles.value.length}个。`)
    }
  }, 3000)
}

function restart() {
  if (gameOverTimeout) { clearTimeout(gameOverTimeout); gameOverTimeout = null }
  initState()
  startLoop()
  game.startAutoReply()
}

function draw() {
  if (!ctx) return
  const w = canvasW, h = canvasH
  ctx.clearRect(0, 0, w, h)

  // 背景网格
  ctx.fillStyle = 'rgba(255,255,255,0.02)'
  ctx.fillRect(0, 0, w, h)
  ctx.strokeStyle = 'rgba(255,255,255,0.04)'
  ctx.lineWidth = 0.5
  for (let i = 0; i <= GRID; i++) {
    ctx.beginPath(); ctx.moveTo(i * CELL, 0); ctx.lineTo(i * CELL, h); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(0, i * CELL); ctx.lineTo(w, i * CELL); ctx.stroke()
  }

  // 障碍物
  ctx.fillStyle = 'rgba(255,255,255,0.12)'
  for (const o of obstacles.value) {
    ctx.fillRect(o.x * CELL + 2, o.y * CELL + 2, CELL - 4, CELL - 4)
  }

  // 食物（多个）
  for (const f of foods.value) {
    ctx.fillStyle = '#ffb74d'
    ctx.shadowColor = '#ffb74d'
    ctx.shadowBlur = 6
    ctx.beginPath()
    ctx.arc(f.x * CELL + CELL / 2, f.y * CELL + CELL / 2, CELL / 2 - 3, 0, Math.PI * 2)
    ctx.fill()
    ctx.shadowBlur = 0
  }

  // 蛇身
  for (let i = 0; i < snake.value.length; i++) {
    const s = snake.value[i]
    const alpha = 1 - i / (snake.value.length + 5) * 0.5
    ctx.fillStyle = i === 0
      ? `rgba(0,229,255,${alpha})`
      : `rgba(0,180,220,${alpha})`
    ctx.fillRect(s.x * CELL + 1.5, s.y * CELL + 1.5, CELL - 3, CELL - 3)
  }

  // 游戏结束遮罩
  if (gameOver.value) {
    ctx.fillStyle = 'rgba(0,0,0,0.6)'
    ctx.fillRect(0, 0, w, h)
    ctx.fillStyle = '#ff4444'
    ctx.font = 'bold 20px monospace'
    ctx.textAlign = 'center'
    ctx.fillText('游戏结束', w / 2, h / 2 - 8)
    ctx.fillStyle = 'rgba(255,255,255,0.5)'
    ctx.font = '12px monospace'
    ctx.fillText(`得分: ${score.value}`, w / 2, h / 2 + 16)
    ctx.textAlign = 'start'
  }
}

// 键盘控制
function onKey(e) {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault()
  }
  if (gameOver.value) return
  const k = e.key.toLowerCase()
  if (k === 'arrowup' || k === 'w') {
    if (direction.value.y !== 1) nextDir.value = { x: 0, y: -1 }
  } else if (k === 'arrowdown' || k === 's') {
    if (direction.value.y !== -1) nextDir.value = { x: 0, y: 1 }
  } else if (k === 'arrowleft' || k === 'a') {
    if (direction.value.x !== 1) nextDir.value = { x: -1, y: 0 }
  } else if (k === 'arrowright' || k === 'd') {
    if (direction.value.x !== -1) nextDir.value = { x: 1, y: 0 }
  }
}

// 监听 AI 工具调用结果
watch(() => game.lastToolResult, (result) => {
  if (result) handleToolResult(result.name, result.content)
})

onMounted(() => {
  initState()
  ctx = canvasRef.value?.getContext('2d')
  startLoop()
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  stopLoop()
  if (gameOverTimeout) clearTimeout(gameOverTimeout)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="flex flex-col items-center gap-3 select-none">
    <!-- 状态栏 -->
    <div class="flex items-center gap-4 text-[11px] font-mono">
      <span class="text-white/40">长度 <span class="text-accent/70">{{ snake.length }}</span></span>
      <span class="text-white/40">得分 <span class="text-amber-tool/70">{{ score }}</span></span>
      <span v-if="gameOver" class="text-red-400/70">游戏结束</span>
    </div>

    <!-- 画布 -->
    <canvas
      ref="canvasRef"
      :width="canvasW"
      :height="canvasH"
      class="rounded-xl border border-white/[0.06] bg-base-900/80 cursor-crosshair"
    ></canvas>

    <!-- 操作按钮 -->
    <button v-if="gameOver"
      class="px-4 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 hover:shadow-[0_0_20px_rgba(0,229,255,0.1)] active:scale-[0.98]"
      @click="restart">重新开始</button>
    <p v-else class="text-[10px] text-white/15">方向键 / WASD 控制蛇的移动</p>
  </div>
</template>
