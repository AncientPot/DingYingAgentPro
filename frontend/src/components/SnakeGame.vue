<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useGameStore } from '../stores/game'

const game = useGameStore()

// 网格
const GRID = 40
const CELL = 14
const canvasW = GRID * CELL
const canvasH = GRID * CELL

const canvasRef = ref(null)
let ctx = null
let animId = null

// 游戏状态
const snake = ref([{ x: 20, y: 20 }, { x: 19, y: 20 }, { x: 18, y: 20 }])
const direction = ref({ x: 1, y: 0 })
const nextDir = ref({ x: 1, y: 0 })
const obstacles = ref([])
const food = ref(null)
const score = ref(0)
const gameOver = ref(false)
const gameOverReported = ref(false)
const paused = ref(false)

const speed = 150  // ms per tick
let lastTick = 0

// 游戏状态文本（传给 AI）
function gameStateText() {
  const body = snake.value.map(p => `(${p.x},${p.y})`).join(',')
  const obs = obstacles.value.map(p => `(${p.x},${p.y})`).join(',') || '无'
  const fd = food.value ? `(${food.value.x},${food.value.y})` : '无'
  const dirName = direction.value.x === 1 ? '右' : direction.value.x === -1 ? '左' : direction.value.y === -1 ? '上' : '下'
  const overText = gameOver.value ? '\n⚠️ 游戏已结束（蛇撞到了障碍物/墙壁/自身）。请对此做出回应。' : ''
  const targetObs = game.toolObstacleCount || 3
  return `蛇长:${snake.value.length} 方向:${dirName} 蛇身:[${body}] 障碍物:[${obs}](目标维持${targetObs}个) 食物:${fd} 网格:${GRID}x${GRID}${overText}`
}

// 暴露给父组件
defineExpose({ gameStateText })

// 解析 AI 工具调用结果
function handleToolResult(toolName, content) {
  if (toolName !== 'snake_game') return
  if (!content) return
  const parts = String(content).split(',')
  if (parts.length < 2) return
  const x = parseInt(parts[0].split(':').pop() || parts[0])
  const y = parseInt(parts[1])
  if (isNaN(x) || isNaN(y) || x < 0 || x >= GRID || y < 0 || y >= GRID) return
  // 检查不与蛇身重叠
  if (snake.value.some(s => s.x === x && s.y === y)) return
  // 检查不与障碍物重叠
  if (obstacles.value.some(o => o.x === x && o.y === y)) return
  // 检查不与食物重叠
  if (food.value && food.value.x === x && food.value.y === y) return

  if (String(content).startsWith('FOOD:')) {
    food.value = { x, y }
  } else if (String(content).startsWith('OBSTACLE:')) {
    obstacles.value.push({ x, y })
  }
}

// 游戏循环
function gameLoop(ts) {
  if (paused.value || gameOver.value) {
    animId = requestAnimationFrame(gameLoop)
    return
  }
  if (ts - lastTick < speed) {
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

  // 撞墙
  if (newHead.x < 0 || newHead.x >= GRID || newHead.y < 0 || newHead.y >= GRID) {
    triggerGameOver()
    return
  }
  // 撞自己
  if (snake.value.some(s => s.x === newHead.x && s.y === newHead.y)) {
    triggerGameOver()
    return
  }
  // 撞障碍物
  if (obstacles.value.some(o => o.x === newHead.x && o.y === newHead.y)) {
    triggerGameOver()
    return
  }

  snake.value.unshift(newHead)

  // 吃食物
  if (food.value && food.value.x === newHead.x && food.value.y === newHead.y) {
    score.value++
    food.value = null
  } else {
    snake.value.pop()
  }
}

function triggerGameOver() {
  gameOver.value = true
  game.stopAutoReply()
  // 延迟发送总结
  setTimeout(() => {
    if (!gameOverReported.value) {
      gameOverReported.value = true
      const summary = `贪吃蛇游戏结束。得分:${score.value} 长度:${snake.value.length} 障碍物:${obstacles.value.length}个。`
      game.gameOverReport(summary)
    }
  }, 3000)
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

  // 食物
  if (food.value) {
    ctx.fillStyle = '#ffb74d'
    ctx.shadowColor = '#ffb74d'
    ctx.shadowBlur = 6
    ctx.beginPath()
    ctx.arc(food.value.x * CELL + CELL / 2, food.value.y * CELL + CELL / 2, CELL / 2 - 3, 0, Math.PI * 2)
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
  if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)) {
    e.preventDefault()  // 阻止方向键触发页面滚动/UI按钮聚焦
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
  ctx = canvasRef.value?.getContext('2d')
  lastTick = performance.now()
  animId = requestAnimationFrame(gameLoop)
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('keydown', onKey)
})

// 暴露给父组件
const snakeStateText = computed(() => gameStateText())
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

    <!-- 提示 -->
    <p class="text-[10px] text-white/15">方向键 / WASD 控制蛇的移动</p>
  </div>
</template>
