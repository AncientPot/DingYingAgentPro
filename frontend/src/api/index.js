const BASE = '/api'

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const r = await fetch(`${BASE}${path}`, opts)
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`)
  return data
}

// Health
export const healthCheck = () => request('GET', '/health')

// Sessions
export const getSessions = () => request('GET', '/sessions')
export const createSession = (name) => request('POST', '/sessions', { name })
export const deleteSession = (name) => request('DELETE', `/sessions/${encodeURIComponent(name)}`)

// Config
export const getConfig = () => request('GET', '/config')
export const updateConfig = (partial) => request('PUT', '/config', partial)

// Tools
export const getTools = () => request('GET', '/tools')
export const toggleTool = (name, enabled) => request('PUT', `/tools/${encodeURIComponent(name)}`, { enabled })
export const testTool = (name) => request('POST', `/tools/${encodeURIComponent(name)}/test`)

// Chat (non-streaming)
export const sendMessage = (sessionName, message) =>
  request('POST', '/chat', { session_name: sessionName, message })

// Chat (streaming SSE) — returns an async generator
export async function* streamMessage(sessionName, message, signal) {
  const r = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_name: sessionName, message }),
    signal,
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: `HTTP ${r.status}` }))
    throw new Error(err.detail || `HTTP ${r.status}`)
  }
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6))
      }
    }
  }
  // flush remaining
  if (buffer.startsWith('data: ')) {
    yield JSON.parse(buffer.slice(6))
  }
}
