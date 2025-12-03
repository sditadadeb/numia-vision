import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell } from 'recharts'

const isDev = window.location.hostname === 'localhost'
const BACKEND_HOST = isDev ? 'localhost:8000' : 'numia-vision-api.onrender.com'
const WS_URL = isDev ? 'ws://localhost:8000/ws' : `wss://${BACKEND_HOST}/ws`
const API_URL = isDev ? 'http://localhost:8000' : `https://${BACKEND_HOST}`

// ============ STORAGE ============
const STORAGE_KEY = 'numia_vision_sessions'
const loadSessions = () => { try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] } }
const saveSessions = (sessions) => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, 50))) } catch {} }

// ============ UTILS ============
const formatTime = (d) => new Date(d).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
const formatTimeShort = (d) => new Date(d).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
const formatDateTime = (d) => new Date(d).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
const formatDuration = (ms) => {
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  return `${m}m ${s % 60}s`
}

// ============ HOOKS ============
function useWebSocket(url, onMessage) {
  const wsRef = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const onMessageRef = useRef(onMessage)
  useEffect(() => { onMessageRef.current = onMessage }, [onMessage])

  useEffect(() => {
    let reconnectTimeout = null, isUnmounted = false
    const connect = () => {
      if (isUnmounted) return
      const ws = new WebSocket(url)
      wsRef.current = ws
      ws.onopen = () => !isUnmounted && setIsConnected(true)
      ws.onclose = () => { if (!isUnmounted) { setIsConnected(false); reconnectTimeout = setTimeout(connect, 3000) } }
      ws.onerror = () => {}
      ws.onmessage = (e) => { try { onMessageRef.current(JSON.parse(e.data)) } catch {} }
    }
    connect()
    return () => { isUnmounted = true; clearTimeout(reconnectTimeout); wsRef.current?.close() }
  }, [url])

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(data))
  }, [])
  return { isConnected, send }
}

function useCamera() {
  const videoRef = useRef(null), canvasRef = useRef(null), streamRef = useRef(null)
  const [devices, setDevices] = useState([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then(list => {
      const vids = list.filter(d => d.kind === 'videoinput')
      setDevices(vids)
      if (vids.length && !selectedDevice) setSelectedDevice(vids[0].deviceId)
    }).catch(() => {})
  }, [])

  const startCamera = useCallback(async () => {
    try {
      streamRef.current?.getTracks().forEach(t => t.stop())
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: selectedDevice ? { exact: selectedDevice } : undefined, width: { ideal: 1280 }, height: { ideal: 720 } }
      })
      streamRef.current = stream
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); setIsStreaming(true) }
    } catch { alert('No se pudo acceder a la cámara') }
  }, [selectedDevice])

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setIsStreaming(false)
  }, [])

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !isStreaming) return null
    const v = videoRef.current, c = canvasRef.current
    c.width = v.videoWidth; c.height = v.videoHeight
    c.getContext('2d').drawImage(v, 0, 0)
    return c.toDataURL('image/jpeg', 0.7).split(',')[1]
  }, [isStreaming])

  return { videoRef, canvasRef, devices, selectedDevice, setSelectedDevice, isStreaming, startCamera, stopCamera, captureFrame }
}

// ============ COMPONENTS ============

// Mini selector de cámara
function CameraSelector({ devices, selected, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const current = devices.find(d => d.deviceId === selected)
  
  return (
    <div style={{ position: 'relative' }}>
      <button 
        onClick={() => !disabled && setOpen(!open)}
        style={{
          background: 'var(--bg-card)', border: '1px solid var(--glass-border)',
          borderRadius: '8px', padding: '8px 12px', cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '13px'
        }}
      >
        📷 {current?.label?.slice(0, 20) || 'Cámara'}
        <span style={{ fontSize: '10px' }}>▼</span>
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: '4px',
          background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)',
          borderRadius: '8px', padding: '4px', zIndex: 100, minWidth: '200px'
        }}>
          {devices.map(d => (
            <div key={d.deviceId} onClick={() => { onChange(d.deviceId); setOpen(false) }}
              style={{
                padding: '8px 12px', cursor: 'pointer', borderRadius: '6px', fontSize: '13px',
                background: d.deviceId === selected ? 'var(--primary-glow)' : 'transparent'
              }}
            >
              {d.label || `Cámara ${devices.indexOf(d) + 1}`}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Stat Card compacto
function StatCard({ icon, label, value, color, subtext, trend, highlight }) {
  return (
    <div style={{
      background: highlight ? 'linear-gradient(135deg, rgba(20,184,166,0.15), rgba(6,182,212,0.1))' : 'var(--glass-bg)',
      border: `1px solid ${highlight ? 'rgba(20,184,166,0.3)' : 'var(--glass-border)'}`,
      borderRadius: '12px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {icon} {label}
        </span>
        {trend && (
          <span style={{ 
            fontSize: '11px', fontWeight: '600',
            color: trend > 0 ? '#22C55E' : trend < 0 ? '#EF4444' : 'var(--text-muted)',
            display: 'flex', alignItems: 'center', gap: '2px'
          }}>
            {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'} {Math.abs(trend)}
          </span>
        )}
      </div>
      <div style={{ fontSize: highlight ? '36px' : '28px', fontWeight: '700', color: color || 'var(--text-primary)' }}>
        {value}
      </div>
      {subtext && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{subtext}</div>}
    </div>
  )
}

// Alerta de aforo
function AforoAlert({ count, threshold, onDismiss }) {
  if (count < threshold) return null
  return (
    <div style={{
      background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.5)',
      borderRadius: '12px', padding: '16px', marginBottom: '20px',
      display: 'flex', alignItems: 'center', gap: '12px', animation: 'pulse 2s infinite'
    }}>
      <span style={{ fontSize: '28px' }}>🚨</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: '600', color: '#EF4444' }}>¡Aforo superado!</div>
        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Hay {count} personas (límite: {threshold})
        </div>
      </div>
      <button onClick={onDismiss} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '18px' }}>✕</button>
    </div>
  )
}

// Gráfico de barras por hora
function HourlyChart({ data }) {
  const hourlyData = useMemo(() => {
    const hours = {}
    data.forEach(d => {
      const h = new Date(d.timestamp).getHours()
      if (!hours[h]) hours[h] = { hour: h, total: 0, count: 0, max: 0 }
      hours[h].total += d.count
      hours[h].count++
      hours[h].max = Math.max(hours[h].max, d.count)
    })
    return Object.values(hours).map(h => ({
      hour: `${h.hour}:00`,
      promedio: Math.round(h.total / h.count * 10) / 10,
      max: h.max
    })).sort((a, b) => parseInt(a.hour) - parseInt(b.hour))
  }, [data])

  if (hourlyData.length < 1) return null

  return (
    <div style={{ height: '200px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={hourlyData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis dataKey="hour" stroke="rgba(255,255,255,0.5)" tick={{ fontSize: 11 }} />
          <YAxis stroke="rgba(255,255,255,0.5)" tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.9)', border: '1px solid rgba(20,184,166,0.5)', borderRadius: '8px' }} />
          <Bar dataKey="promedio" fill="#14B8A6" radius={[4, 4, 0, 0]} name="Promedio" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// Heatmap del día
function DayHeatmap({ data }) {
  const heatData = useMemo(() => {
    const grid = Array(24).fill(0).map(() => ({ count: 0, total: 0 }))
    data.forEach(d => {
      const h = new Date(d.timestamp).getHours()
      grid[h].count++
      grid[h].total += d.count
    })
    const maxAvg = Math.max(...grid.map(g => g.count ? g.total / g.count : 0), 1)
    return grid.map((g, i) => ({
      hour: i,
      avg: g.count ? g.total / g.count : 0,
      level: Math.ceil((g.count ? g.total / g.count : 0) / maxAvg * 5)
    }))
  }, [data])

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: '2px', marginBottom: '8px' }}>
        {heatData.map((h, i) => (
          <div key={i} title={`${i}:00 - Prom: ${h.avg.toFixed(1)}`} style={{
            aspectRatio: '1', borderRadius: '3px',
            background: h.level === 0 ? 'var(--bg-card)' :
              h.level === 1 ? 'rgba(20,184,166,0.2)' :
              h.level === 2 ? 'rgba(20,184,166,0.4)' :
              h.level === 3 ? 'rgba(20,184,166,0.6)' :
              h.level === 4 ? 'rgba(20,184,166,0.8)' : '#14B8A6'
          }} />
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)' }}>
        <span>0:00</span><span>6:00</span><span>12:00</span><span>18:00</span><span>23:00</span>
      </div>
    </div>
  )
}

// Modal de resumen
function SessionSummary({ session, onClose, onDelete, isHistory }) {
  if (!session) return null
  
  const duration = (session.endTime || Date.now()) - session.startTime
  const { maxPersons, avgPersons, totalEntradas, totalSalidas, hourlyData, peakHour, valleyHour } = session.stats || session

  const exportCSV = () => {
    const rows = [['Hora', 'Personas', 'Tipo', 'Mensaje']]
    session.events?.forEach(e => rows.push([formatTime(e.time), '', e.type, e.message]))
    session.stats?.chartData?.forEach(d => rows.push([formatTime(d.timestamp), d.count, 'data', '']))
    const csv = rows.map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `sesion_${formatDateTime(session.startTime).replace(/[/:]/g, '-')}.csv`; a.click()
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }} onClick={onClose}>
      <div style={{ background: 'var(--bg-secondary)', borderRadius: '16px', padding: '24px', maxWidth: '900px', width: '95%', maxHeight: '90vh', overflow: 'auto', border: '1px solid var(--glass-border)' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: 0, fontSize: '20px' }}>📊 Resumen de Sesión</h2>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={exportCSV} style={{ background: 'var(--bg-card)', border: '1px solid var(--glass-border)', color: 'var(--text-secondary)', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px' }}>📥 Exportar CSV</button>
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '24px', cursor: 'pointer' }}>✕</button>
          </div>
        </div>

        {/* Stats principales */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px', marginBottom: '24px' }}>
          <StatCard icon="⏱️" label="Duración" value={formatDuration(duration)} />
          <StatCard icon="📈" label="Máximo" value={maxPersons || 0} color="#14B8A6" />
          <StatCard icon="📊" label="Promedio" value={(avgPersons || 0).toFixed(1)} color="#60A5FA" />
          <StatCard icon="🚶" label="Entradas" value={totalEntradas || 0} color="#22C55E" />
          <StatCard icon="👋" label="Salidas" value={totalSalidas || 0} color="#EF4444" />
          <StatCard icon="🔄" label="Flujo Total" value={(totalEntradas || 0) + (totalSalidas || 0)} />
        </div>

        {/* Hora pico y valle */}
        {(peakHour || valleyHour) && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
            {peakHour && (
              <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>🔥 Hora Pico</div>
                <div style={{ fontSize: '24px', fontWeight: '700' }}>{peakHour.hour}:00</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Máx: {peakHour.max} personas</div>
              </div>
            )}
            {valleyHour && (
              <div style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>🌙 Hora Valle</div>
                <div style={{ fontSize: '24px', fontWeight: '700' }}>{valleyHour.hour}:00</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Mín: {valleyHour.min} personas</div>
              </div>
            )}
          </div>
        )}

        {/* Gráfico por hora */}
        {session.stats?.chartData?.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>📊 Personas por Hora</h3>
            <HourlyChart data={session.stats.chartData} />
          </div>
        )}

        {/* Heatmap */}
        {session.stats?.chartData?.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>🗓️ Intensidad por Hora</h3>
            <DayHeatmap data={session.stats.chartData} />
          </div>
        )}

        {/* Timeline */}
        {session.events?.length > 0 && (
          <div>
            <h3 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>📋 Eventos ({session.events.length})</h3>
            <div style={{ maxHeight: '200px', overflow: 'auto' }}>
              {session.events.slice(0, 50).map(e => (
                <div key={e.id} style={{
                  padding: '10px 12px', marginBottom: '4px', borderRadius: '8px',
                  background: e.type === 'entrada' ? 'rgba(34,197,94,0.1)' : e.type === 'aforo' ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.1)',
                  borderLeft: `3px solid ${e.type === 'entrada' ? '#22C55E' : e.type === 'aforo' ? '#EF4444' : '#EF4444'}`,
                  display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px'
                }}>
                  <span>{e.icon}</span>
                  <span style={{ flex: 1 }}>{e.message}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{formatTime(e.time)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'space-between' }}>
          {isHistory && onDelete && (
            <button onClick={() => { onDelete(session.id); onClose() }} style={{ background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer' }}>🗑️ Eliminar</button>
          )}
          <button onClick={onClose} className="btn btn-primary" style={{ marginLeft: 'auto' }}>Cerrar</button>
        </div>
      </div>
    </div>
  )
}

// Panel de historial
function HistoryPanel({ sessions, onSelect, onRefresh }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderBottom: '1px solid var(--glass-border)' }}>
        <span style={{ fontWeight: '600' }}>📁 Historial ({sessions.length})</span>
        <button onClick={onRefresh} style={{ background: 'var(--bg-card)', border: '1px solid var(--glass-border)', color: 'var(--text-secondary)', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>🔄</button>
      </div>
      <div style={{ maxHeight: '500px', overflow: 'auto' }}>
        {sessions.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No hay sesiones guardadas</div>
        ) : sessions.map(s => (
          <div key={s.id} onClick={() => onSelect(s)} style={{ padding: '14px 16px', borderBottom: '1px solid var(--glass-border)', cursor: 'pointer', transition: 'background 0.2s' }}
            onMouseOver={e => e.currentTarget.style.background = 'var(--bg-card)'} onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontWeight: '500' }}>{formatDateTime(s.startTime)}</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{formatDuration(s.endTime - s.startTime)}</span>
            </div>
            <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: 'var(--text-muted)' }}>
              <span>📈 Máx: {s.maxPersons || s.stats?.maxPersons || 0}</span>
              <span>📊 Prom: {(s.avgPersons || s.stats?.avgPersons || 0).toFixed(1)}</span>
              <span style={{ color: '#22C55E' }}>+{s.totalEntradas || s.stats?.totalEntradas || 0}</span>
              <span style={{ color: '#EF4444' }}>-{s.totalSalidas || s.stats?.totalSalidas || 0}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============ MAIN APP ============
export default function App() {
  const [currentCount, setCurrentCount] = useState(0)
  const [events, setEvents] = useState([])
  const [processedFrame, setProcessedFrame] = useState(null)
  const [chartData, setChartData] = useState([])
  const [sessionSummary, setSessionSummary] = useState(null)
  const [isFromHistory, setIsFromHistory] = useState(false)
  const [savedSessions, setSavedSessions] = useState([])
  const [activeTab, setActiveTab] = useState('live')
  const [aforoLimit, setAforoLimit] = useState(10)
  const [aforoDismissed, setAforoDismissed] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  // Stats calculadas
  const [stats, setStats] = useState({ max: 0, avg: 0, entradas: 0, salidas: 0, trend: 0, lastEntryTime: null, avgTimeBetween: 0 })

  useEffect(() => { setSavedSessions(loadSessions()) }, [])

  const sessionRef = useRef({
    startTime: null, events: [], countHistory: [],
    stats: { maxPersons: 0, totalEntradas: 0, totalSalidas: 0, avgPersons: 0, chartData: [], hourlyData: {}, peakHour: null, valleyHour: null }
  })
  const prevCountRef = useRef(0)
  const lastEventTimeRef = useRef(0)
  const entryTimesRef = useRef([])
  const COOLDOWN_MS = 1500

  const canEmitEvent = () => {
    const now = Date.now()
    if (now - lastEventTimeRef.current > COOLDOWN_MS) { lastEventTimeRef.current = now; return true }
    return false
  }

  const { videoRef, canvasRef, devices, selectedDevice, setSelectedDevice, isStreaming, startCamera, stopCamera, captureFrame } = useCamera()

  const addEvent = (type, icon, message) => {
    const event = { id: Date.now() + Math.random(), type, icon, message, time: new Date().toISOString() }
    setEvents(prev => [event, ...prev].slice(0, 100))
    sessionRef.current.events.unshift(event)
  }

  const { isConnected, send } = useWebSocket(`${WS_URL}/detect`, (data) => {
    if (data.type !== 'detection') return

    const count = data.count || 0
    const prevCount = prevCountRef.current
    const session = sessionRef.current
    const timestamp = data.timestamp || new Date().toISOString()
    const now = Date.now()

    setCurrentCount(count)
    setProcessedFrame(`data:image/jpeg;base64,${data.frame}`)

    // Chart data
    const newPoint = { count, timestamp, time: formatTimeShort(timestamp) }
    setChartData(prev => [...prev.slice(-120), newPoint])
    session.stats.chartData.push(newPoint)
    session.countHistory.push(count)

    // Hourly tracking
    const hour = new Date(timestamp).getHours()
    if (!session.stats.hourlyData[hour]) session.stats.hourlyData[hour] = { counts: [], max: 0, min: Infinity }
    session.stats.hourlyData[hour].counts.push(count)
    session.stats.hourlyData[hour].max = Math.max(session.stats.hourlyData[hour].max, count)
    session.stats.hourlyData[hour].min = Math.min(session.stats.hourlyData[hour].min, count)

    // Update peak/valley
    const hourlyArr = Object.entries(session.stats.hourlyData)
    if (hourlyArr.length) {
      const peak = hourlyArr.reduce((a, b) => b[1].max > a[1].max ? b : a)
      const valley = hourlyArr.reduce((a, b) => b[1].min < a[1].min ? b : a)
      session.stats.peakHour = { hour: parseInt(peak[0]), max: peak[1].max }
      session.stats.valleyHour = { hour: parseInt(valley[0]), min: valley[1].min }
    }

    // Stats
    if (count > session.stats.maxPersons) session.stats.maxPersons = count
    const avg = session.countHistory.reduce((a, b) => a + b, 0) / session.countHistory.length
    session.stats.avgPersons = avg

    // Trend (últimos 10 vs anteriores 10)
    const recent = session.countHistory.slice(-10)
    const previous = session.countHistory.slice(-20, -10)
    const recentAvg = recent.length ? recent.reduce((a, b) => a + b, 0) / recent.length : 0
    const prevAvg = previous.length ? previous.reduce((a, b) => a + b, 0) / previous.length : recentAvg
    const trend = Math.round(recentAvg - prevAvg)

    // Tiempo entre entradas
    let avgTimeBetween = 0
    if (entryTimesRef.current.length > 1) {
      const diffs = []
      for (let i = 1; i < entryTimesRef.current.length; i++) {
        diffs.push(entryTimesRef.current[i] - entryTimesRef.current[i - 1])
      }
      avgTimeBetween = Math.round(diffs.reduce((a, b) => a + b, 0) / diffs.length / 1000)
    }

    setStats({
      max: session.stats.maxPersons, avg, trend,
      entradas: session.stats.totalEntradas, salidas: session.stats.totalSalidas,
      avgTimeBetween, peakHour: session.stats.peakHour, valleyHour: session.stats.valleyHour
    })

    // Eventos
    if (count !== prevCount && canEmitEvent()) {
      const diff = count - prevCount
      if (diff > 0) {
        session.stats.totalEntradas += diff
        entryTimesRef.current.push(now)
        if (entryTimesRef.current.length > 50) entryTimesRef.current.shift()
        addEvent('entrada', '🚶', `+${diff} persona${diff > 1 ? 's' : ''} → Total: ${count}`)
        setStats(s => ({ ...s, entradas: session.stats.totalEntradas }))
        
        // Alerta de aforo
        if (count >= aforoLimit && !aforoDismissed) {
          addEvent('aforo', '🚨', `¡Aforo superado! ${count} personas (límite: ${aforoLimit})`)
        }
      } else {
        const salidas = Math.abs(diff)
        session.stats.totalSalidas += salidas
        addEvent('salida', '👋', `-${salidas} persona${salidas > 1 ? 's' : ''} → Total: ${count}`)
        setStats(s => ({ ...s, salidas: session.stats.totalSalidas }))
      }
    }

    prevCountRef.current = count
  })

  const handleStart = async () => {
    sessionRef.current = {
      startTime: Date.now(), events: [], countHistory: [],
      stats: { maxPersons: 0, totalEntradas: 0, totalSalidas: 0, avgPersons: 0, chartData: [], hourlyData: {}, peakHour: null, valleyHour: null }
    }
    setEvents([]); setChartData([]); setStats({ max: 0, avg: 0, entradas: 0, salidas: 0, trend: 0, avgTimeBetween: 0 })
    prevCountRef.current = 0; lastEventTimeRef.current = 0; entryTimesRef.current = []
    setAforoDismissed(false)
    await startCamera()
  }

  const handleStop = () => {
    stopCamera()
    const session = sessionRef.current
    if (session.startTime) {
      const sessionData = {
        id: Date.now(), startTime: session.startTime, endTime: Date.now(),
        events: [...session.events],
        stats: { ...session.stats },
        maxPersons: session.stats.maxPersons, avgPersons: session.stats.avgPersons,
        totalEntradas: session.stats.totalEntradas, totalSalidas: session.stats.totalSalidas
      }
      const sessions = loadSessions(); sessions.unshift(sessionData); saveSessions(sessions)
      setSavedSessions(loadSessions())
      setIsFromHistory(false); setSessionSummary(sessionData)
    }
  }

  useEffect(() => {
    if (!isStreaming || !isConnected) return
    const interval = setInterval(() => {
      const frame = captureFrame()
      if (frame) send({ type: 'frame', frame })
    }, 400)
    return () => clearInterval(interval)
  }, [isStreaming, isConnected, captureFrame, send])

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <div className="logo-icon">N</div>
          <div className="logo-text">
            <span className="logo-name">Numia Vision</span>
            <span className="logo-sub">Analytics en tiempo real</span>
          </div>
        </div>

        <nav className="nav-tabs">
          <button className={`nav-tab ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>📹 En Vivo</button>
          <button className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            📁 Historial {savedSessions.length > 0 && <span className="badge">{savedSessions.length}</span>}
          </button>
        </nav>

        <div className="header-right">
          <CameraSelector devices={devices} selected={selectedDevice} onChange={setSelectedDevice} disabled={isStreaming} />
          <button onClick={() => setShowSettings(!showSettings)} style={{ background: 'var(--bg-card)', border: '1px solid var(--glass-border)', borderRadius: '8px', padding: '8px 12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>⚙️</button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className={`status-dot ${isConnected ? '' : 'offline'}`}></div>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{isConnected ? 'Conectado' : 'Desconectado'}</span>
          </div>
        </div>
      </header>

      {/* Settings panel */}
      {showSettings && (
        <div style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--glass-border)', padding: '16px 32px', display: 'flex', alignItems: 'center', gap: '24px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>🚨 Alerta de aforo:</span>
          <input type="range" min="1" max="50" value={aforoLimit} onChange={e => setAforoLimit(parseInt(e.target.value))} style={{ width: '150px' }} />
          <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--primary-light)' }}>{aforoLimit} personas</span>
        </div>
      )}

      <main className="main-content">
        {activeTab === 'live' && (
          <>
            {/* Alerta de aforo */}
            {isStreaming && <AforoAlert count={currentCount} threshold={aforoLimit} onDismiss={() => setAforoDismissed(true)} />}

            {/* Stats Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '12px', marginBottom: '20px' }}>
              <StatCard icon="👥" label="Ahora" value={currentCount} highlight trend={stats.trend} />
              <StatCard icon="📈" label="Máximo" value={stats.max} color="#14B8A6" />
              <StatCard icon="📊" label="Promedio" value={stats.avg.toFixed(1)} color="#60A5FA" />
              <StatCard icon="🚶" label="Entradas" value={stats.entradas} color="#22C55E" />
              <StatCard icon="👋" label="Salidas" value={stats.salidas} color="#EF4444" />
              <StatCard icon="⏱️" label="Entre entradas" value={stats.avgTimeBetween ? `${stats.avgTimeBetween}s` : '-'} subtext="promedio" />
              <StatCard icon="🔥" label="Hora pico" value={stats.peakHour ? `${stats.peakHour.hour}:00` : '-'} subtext={stats.peakHour ? `máx ${stats.peakHour.max}` : ''} />
            </div>

            {/* Controls */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              {!isStreaming ? (
                <button className="btn btn-primary" onClick={handleStart} style={{ padding: '12px 24px' }}>▶️ Iniciar Detección</button>
              ) : (
                <button className="btn btn-danger" onClick={handleStop} style={{ padding: '12px 24px' }}>⏹️ Detener y Guardar</button>
              )}
              {isStreaming && (
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                  <span>⏱️ {formatDuration(Date.now() - (sessionRef.current.startTime || Date.now()))}</span>
                </div>
              )}
            </div>

            {/* Gráfico tiempo real */}
            {isStreaming && chartData.length > 1 && (
              <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
                <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px' }}>📈 Personas en Tiempo Real</div>
                <div style={{ height: '150px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData.slice(-60)}>
                      <defs>
                        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#14B8A6" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#14B8A6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="time" stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 10 }} interval="preserveEnd" />
                      <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 10 }} allowDecimals={false} domain={[0, 'auto']} />
                      <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.9)', border: '1px solid #14B8A6', borderRadius: '8px' }} />
                      <Area type="monotone" dataKey="count" stroke="#14B8A6" strokeWidth={2} fill="url(#grad)" name="Personas" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Video + Eventos */}
            <div className="video-section">
              <div className="video-container">
                <video ref={videoRef} style={{ display: 'none' }} playsInline muted />
                <canvas ref={canvasRef} style={{ display: 'none' }} />
                {processedFrame ? (
                  <img src={processedFrame} alt="Detección" className="video-feed" />
                ) : (
                  <div className="empty-state">
                    <div className="empty-state-icon">📹</div>
                    <div className="empty-state-title">Cámara no iniciada</div>
                  </div>
                )}
                <div className="video-overlay">
                  <div className="video-status">
                    <div className={`status-dot ${isStreaming ? '' : 'offline'}`}></div>
                    {isStreaming ? 'EN VIVO' : 'DETENIDO'}
                  </div>
                  {isStreaming && <div className="video-counter"><div className="counter-value">{currentCount}</div><div className="counter-label">Personas</div></div>}
                </div>
              </div>

              <div className="side-panel">
                <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', maxHeight: '500px' }}>
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--glass-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: '600', fontSize: '14px' }}>📋 Eventos ({events.length})</span>
                    <button onClick={() => setEvents([])} style={{ background: 'var(--bg-card)', border: '1px solid var(--glass-border)', color: 'var(--text-muted)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}>🗑️</button>
                  </div>
                  <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
                    {events.length === 0 ? (
                      <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        <div style={{ fontSize: '28px', marginBottom: '8px' }}>👁️</div>
                        <div>Esperando cambios...</div>
                      </div>
                    ) : events.map(e => (
                      <div key={e.id} style={{
                        padding: '8px 10px', marginBottom: '4px', borderRadius: '6px', fontSize: '12px',
                        background: e.type === 'entrada' ? 'rgba(34,197,94,0.1)' : e.type === 'aforo' ? 'rgba(239,68,68,0.2)' : 'rgba(239,68,68,0.1)',
                        borderLeft: `3px solid ${e.type === 'entrada' ? '#22C55E' : '#EF4444'}`,
                        display: 'flex', alignItems: 'center', gap: '8px'
                      }}>
                        <span>{e.icon}</span>
                        <span style={{ flex: 1 }}>{e.message}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>{formatTime(e.time)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Heatmap mini */}
                {isStreaming && chartData.length > 10 && (
                  <div className="card" style={{ padding: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>🗓️ Intensidad por hora</div>
                    <DayHeatmap data={chartData} />
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === 'history' && (
          <HistoryPanel
            sessions={savedSessions}
            onSelect={s => { setIsFromHistory(true); setSessionSummary(s) }}
            onRefresh={() => setSavedSessions(loadSessions())}
          />
        )}
      </main>

      <SessionSummary
        session={sessionSummary}
        onClose={() => setSessionSummary(null)}
        onDelete={id => { saveSessions(loadSessions().filter(s => s.id !== id)); setSavedSessions(loadSessions()) }}
        isHistory={isFromHistory}
      />
    </div>
  )
}
