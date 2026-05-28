import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchTelemetryReplay } from './api'

const SPEEDS = [1, 2, 4, 8]

function formatRaceTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '00:00.000'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const sec = s.toFixed(3).padStart(6, '0')
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${sec}`
  }
  return `${String(m).padStart(2, '0')}:${sec}`
}

function findPointAtTime(points, t) {
  if (!points?.length) return null
  if (t <= points[0].t) return points[0]
  if (t >= points[points.length - 1].t) return points[points.length - 1]

  let lo = 0
  let hi = points.length - 1
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2)
    if (points[mid].t <= t) lo = mid
    else hi = mid - 1
  }
  return points[lo]
}

function isInPit(points, idx, t) {
  const next = points[idx + 1]
  if (!next) return false
  return next.t - t > 3.5
}

function TrackMap({ points, bounds, current }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !bounds || !points?.length) return

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    canvas.width = w * dpr
    canvas.height = h * dpr
    ctx.scale(dpr, dpr)

    const pad = 16
    const rangeX = bounds.maxX - bounds.minX || 1
    const rangeY = bounds.maxY - bounds.minY || 1
    const scale = Math.min((w - pad * 2) / rangeX, (h - pad * 2) / rangeY)

    const toCanvas = (x, y) => ({
      cx: pad + (x - bounds.minX) * scale,
      cy: h - pad - (y - bounds.minY) * scale,
    })

    ctx.clearRect(0, 0, w, h)
    ctx.fillStyle = '#15151e'
    ctx.fillRect(0, 0, w, h)

    ctx.strokeStyle = 'rgba(255,255,255,0.12)'
    ctx.lineWidth = 2
    ctx.beginPath()
    points.forEach((p, i) => {
      if (p.x == null || p.y == null) return
      const { cx, cy } = toCanvas(p.x, p.y)
      if (i === 0) ctx.moveTo(cx, cy)
      else ctx.lineTo(cx, cy)
    })
    ctx.stroke()

    const trail = []
    const currentIdx = points.findIndex((p) => p === current)
    const start = Math.max(0, currentIdx - 80)
    for (let i = start; i <= currentIdx; i += 1) {
      if (points[i]?.x != null) trail.push(points[i])
    }
    if (trail.length > 1) {
      ctx.strokeStyle = '#e10600'
      ctx.lineWidth = 3
      ctx.beginPath()
      trail.forEach((p, i) => {
        const { cx, cy } = toCanvas(p.x, p.y)
        if (i === 0) ctx.moveTo(cx, cy)
        else ctx.lineTo(cx, cy)
      })
      ctx.stroke()
    }

    if (current?.x != null && current?.y != null) {
      const { cx, cy } = toCanvas(current.x, current.y)
      ctx.fillStyle = '#ffffff'
      ctx.beginPath()
      ctx.arc(cx, cy, 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#e10600'
      ctx.lineWidth = 2
      ctx.stroke()
    }
  }, [points, bounds, current])

  return (
    <canvas
      ref={canvasRef}
      className="replay-track"
      role="img"
      aria-label="Track map with car position"
    />
  )
}

function Metric({ label, value, unit }) {
  return (
    <div className="replay-metric">
      <span className="replay-metric-label">{label}</span>
      <span className="replay-metric-value">
        {value}
        {unit && <span className="replay-metric-unit">{unit}</span>}
      </span>
    </div>
  )
}

export default function TelemetryReplay({ sessionId, driver, driverInfo }) {
  const [replay, setReplay] = useState(null)
  const [replaySource, setReplaySource] = useState(null)
  const [isDemo, setIsDemo] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [playhead, setPlayhead] = useState(0)

  const rafRef = useRef(null)
  const lastFrameRef = useRef(null)
  const playheadRef = useRef(0)

  const loadReplay = useCallback(async () => {
    if (!sessionId || !driver) return
    setLoading(true)
    setError(null)
    setPlaying(false)
    setPlayhead(0)
    playheadRef.current = 0
    try {
      const { data, source, isDemo: demo } = await fetchTelemetryReplay({
        sessionId,
        driver,
      })
      setReplay(data)
      setReplaySource(source)
      setIsDemo(demo)
      playheadRef.current = 0
      setPlayhead(0)
      setPlaying(true)
    } catch (err) {
      setReplay(null)
      setReplaySource(null)
      setIsDemo(false)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [sessionId, driver])

  useEffect(() => {
    loadReplay()
  }, [loadReplay])

  useEffect(() => {
    playheadRef.current = playhead
  }, [playhead])

  useEffect(() => {
    if (!playing || !replay?.points?.length) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return undefined
    }

    const tick = (now) => {
      if (lastFrameRef.current != null) {
        const delta = (now - lastFrameRef.current) / 1000
        let next = playheadRef.current + delta * speed
        if (next >= replay.totalSeconds) {
          next = replay.totalSeconds
          setPlaying(false)
        }
        playheadRef.current = next
        setPlayhead(next)
      }
      lastFrameRef.current = now
      rafRef.current = requestAnimationFrame(tick)
    }

    lastFrameRef.current = null
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [playing, replay, speed])

  const points = replay?.points ?? []
  const current = findPointAtTime(points, playhead)
  const currentIdx = current ? points.indexOf(current) : -1
  const inPit = current && currentIdx >= 0 && isInPit(points, currentIdx, playhead)
  const progress = replay ? (playhead / replay.totalSeconds) * 100 : 0

  const handleSeek = (e) => {
    const value = Number(e.target.value)
    playheadRef.current = value
    setPlayhead(value)
  }

  const handleRestart = () => {
    playheadRef.current = 0
    setPlayhead(0)
    setPlaying(true)
  }

  return (
    <section className="replay-panel" aria-label="Live telemetry replay">
      <div className="replay-header">
        <div>
          <h2>Live telemetry</h2>
          <p className="replay-subtitle">
            Session replay for{' '}
            <strong>{driverInfo?.name ?? driver}</strong>
            {replay && (
              <>
                {' '}
                · {replay.totalLaps} laps · {replay.pointCount.toLocaleString()} samples ·{' '}
                {formatRaceTime(replay.totalSeconds)}
              </>
            )}
          </p>
        </div>
        <div className="replay-header-badges">
          {replaySource && <span className="badge">{replaySource}</span>}
          <span className={`live-badge ${playing ? 'live-badge--on' : ''}`}>
            {playing ? '● LIVE' : 'PAUSED'}
          </span>
        </div>
      </div>

      {isDemo && !loading && (
        <div className="demo-banner" role="status">
          <strong>Demo replay only</strong> — this is a 3-lap / 95s sample bundled for
          offline use. Start the backend for the full race (
          <code>uvicorn api:app --reload --port 8000</code>), then refresh.
        </div>
      )}

      {loading && (
        <div className="status-card loading-card replay-loading">
          <span className="spinner" aria-hidden="true" />
          <p>
            Building full-session telemetry… first load for a session takes about a
            minute; later loads are instant from cache.
          </p>
        </div>
      )}

      {error && !loading && (
        <div className="status-card error-card" role="alert">
          <p>{error}</p>
          <button type="button" onClick={loadReplay}>
            Retry
          </button>
        </div>
      )}

      {replay && !loading && (
        <>
          <div className="replay-layout">
            <TrackMap
              points={points}
              bounds={replay.bounds}
              current={current}
            />
            <div className="replay-dash">
              <div className="replay-clock">
                <span className="replay-clock-label">Session time</span>
                <span className="replay-clock-value">{formatRaceTime(playhead)}</span>
              </div>
              <div className="replay-metrics">
                <Metric
                  label="Speed"
                  value={inPit ? '—' : Math.round(current?.speed ?? 0)}
                  unit="km/h"
                />
                <Metric label="Gear" value={inPit ? 'P' : (current?.gear ?? '—')} />
                <Metric
                  label="Throttle"
                  value={inPit ? '—' : `${Math.round(current?.throttle ?? 0)}`}
                  unit="%"
                />
                <Metric label="Brake" value={current?.brake ? 'ON' : 'OFF'} />
                <Metric
                  label="RPM"
                  value={inPit ? '—' : Math.round(current?.rpm ?? 0).toLocaleString()}
                />
                <Metric
                  label="Lap"
                  value={
                    current?.lap != null && replay?.totalLaps
                      ? `${current.lap} / ${replay.totalLaps}`
                      : '—'
                  }
                />
              </div>
              {inPit && <p className="replay-pit">Pit / stationary — no on-track telemetry</p>}
            </div>
          </div>

          <div className="replay-controls">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setPlaying((p) => !p)}
            >
              {playing ? 'Pause' : 'Play'}
            </button>
            <button type="button" className="btn-ghost" onClick={handleRestart}>
              Restart
            </button>
            <div className="speed-buttons" role="group" aria-label="Playback speed">
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={speed === s ? 'speed-btn active' : 'speed-btn'}
                  onClick={() => setSpeed(s)}
                >
                  {s}×
                </button>
              ))}
            </div>
            <input
              type="range"
              className="replay-scrubber"
              min={0}
              max={replay.totalSeconds}
              step={0.05}
              value={playhead}
              onChange={handleSeek}
              aria-label="Session timeline"
            />
            <span className="replay-duration">{formatRaceTime(replay.totalSeconds)}</span>
          </div>
          <div className="replay-progress" aria-hidden="true">
            <div className="replay-progress-fill" style={{ width: `${progress}%` }} />
            {replay.lapMarkers?.map((m) => (
              <span
                key={m.lap}
                className="lap-tick"
                style={{ left: `${(m.t / replay.totalSeconds) * 100}%` }}
                title={`Lap ${m.lap}`}
              />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
