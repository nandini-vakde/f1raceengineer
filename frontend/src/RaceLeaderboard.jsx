import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchRaceSimulation } from './api'

const SPEEDS = [1, 2, 4, 8]

function formatLapTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '—'
  const m = Math.floor(seconds / 60)
  const s = (seconds % 60).toFixed(3)
  return m > 0 ? `${m}:${s.padStart(6, '0')}` : s
}

function formatGap(seconds) {
  if (seconds == null || seconds === 0) return 'LEADER'
  return `+${seconds.toFixed(3)}`
}

function formatInterval(seconds) {
  if (seconds == null) return '—'
  return seconds.toFixed(3)
}

function sectorVisibility(lapProgress, leaderEntry) {
  if (!leaderEntry) return { s1: false, s2: false, s3: false, lapTime: false }
  const s1 = leaderEntry.sector1 ?? 0
  const s2 = leaderEntry.sector2 ?? 0
  const s3 = leaderEntry.sector3 ?? 0
  const total = leaderEntry.lapTime ?? s1 + s2 + s3
  if (!total) {
    return {
      s1: lapProgress >= 0.33,
      s2: lapProgress >= 0.66,
      s3: lapProgress >= 1,
      lapTime: lapProgress >= 1,
    }
  }
  const s1End = s1 / total
  const s2End = (s1 + s2) / total
  return {
    s1: lapProgress >= s1End,
    s2: lapProgress >= s2End,
    s3: lapProgress >= 1,
    lapTime: lapProgress >= 1,
  }
}

function compoundClass(compound) {
  if (!compound) return ''
  const key = compound.toUpperCase()
  if (key.includes('SOFT')) return 'tyre-soft'
  if (key.includes('MEDIUM')) return 'tyre-medium'
  if (key.includes('HARD')) return 'tyre-hard'
  if (key.includes('INTER')) return 'tyre-inter'
  if (key.includes('WET')) return 'tyre-wet'
  return ''
}

function LeaderboardRow({ entry, visibility, highlightCode }) {
  const showGap = visibility.lapTime
  return (
    <tr className={entry.code === highlightCode ? 'lb-row lb-row--focus' : 'lb-row'}>
      <td className="lb-pos">{entry.position}</td>
      <td className="lb-driver">
        <span className="lb-code">{entry.code}</span>
        <span className="lb-name">{entry.name}</span>
        {entry.compound && (
          <span
            className={`lb-tyre ${compoundClass(entry.compound)}`}
            title={`${entry.compound}${entry.tyreLife != null ? ` · lap ${entry.tyreLife}` : ''}`}
          />
        )}
      </td>
      <td className="lb-gap">
        {showGap
          ? entry.position === 1
            ? 'LEADER'
            : formatGap(entry.gapToLeader)
          : entry.position === 1
            ? '—'
            : formatInterval(entry.interval)}
      </td>
      <td className="lb-sector">{visibility.s1 ? formatLapTime(entry.sector1) : '—'}</td>
      <td className="lb-sector">{visibility.s2 ? formatLapTime(entry.sector2) : '—'}</td>
      <td className="lb-sector">{visibility.s3 ? formatLapTime(entry.sector3) : '—'}</td>
      <td className="lb-laptime">{visibility.lapTime ? formatLapTime(entry.lapTime) : '—'}</td>
    </tr>
  )
}

export default function RaceLeaderboard({ sessionId, highlightDriver }) {
  const [simulation, setSimulation] = useState(null)
  const [source, setSource] = useState(null)
  const [isDemo, setIsDemo] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(2)
  const [lapIndex, setLapIndex] = useState(0)
  const [lapProgress, setLapProgress] = useState(0)

  const rafRef = useRef(null)
  const lastFrameRef = useRef(null)
  const lapIndexRef = useRef(0)
  const lapProgressRef = useRef(0)

  const loadSimulation = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    setError(null)
    setPlaying(false)
    setLapIndex(0)
    setLapProgress(0)
    lapIndexRef.current = 0
    lapProgressRef.current = 0
    try {
      const { data, source: src, isDemo: demo } = await fetchRaceSimulation({ sessionId })
      setSimulation(data)
      setSource(src)
      setIsDemo(demo)
      setPlaying(true)
    } catch (err) {
      setSimulation(null)
      setSource(null)
      setIsDemo(false)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadSimulation()
  }, [loadSimulation])

  useEffect(() => {
    lapIndexRef.current = lapIndex
  }, [lapIndex])

  useEffect(() => {
    lapProgressRef.current = lapProgress
  }, [lapProgress])

  const lapsMerged = simulation?.lapsMerged ?? []
  const currentLap = lapsMerged[lapIndex] ?? null
  const leaderEntry = currentLap?.entries?.[0] ?? null
  const lapDuration = (currentLap?.leaderLapTime ?? 90) / speed
  const visibility = sectorVisibility(lapProgress, leaderEntry)

  useEffect(() => {
    if (!playing || !lapsMerged.length || !currentLap) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return undefined
    }

    const tick = (now) => {
      if (lastFrameRef.current != null) {
        const delta = (now - lastFrameRef.current) / 1000
        let progress = lapProgressRef.current + delta / lapDuration
        let idx = lapIndexRef.current

        if (progress >= 1) {
          progress = 0
          idx += 1
          if (idx >= lapsMerged.length) {
            idx = 0
          }
          lapIndexRef.current = idx
          setLapIndex(idx)
        }

        lapProgressRef.current = progress
        setLapProgress(progress)
      }
      lastFrameRef.current = now
      rafRef.current = requestAnimationFrame(tick)
    }

    lastFrameRef.current = null
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [playing, lapsMerged.length, currentLap, lapDuration])

  const handleRestart = () => {
    lapIndexRef.current = 0
    lapProgressRef.current = 0
    setLapIndex(0)
    setLapProgress(0)
    setPlaying(true)
  }

  const handleLapSeek = (e) => {
    const next = Number(e.target.value)
    lapIndexRef.current = next
    lapProgressRef.current = 0
    setLapIndex(next)
    setLapProgress(0)
  }

  if (!sessionId) return null

  return (
    <section className="leaderboard-panel" aria-label="Race leaderboard simulation">
      <div className="replay-header">
        <div>
          <h2>Race leaderboard</h2>
          <p className="replay-subtitle">
            Lap-by-lap simulation with live gaps and sector intervals for all drivers
            {highlightDriver && (
              <>
                {' '}
                · highlighting <strong>{highlightDriver}</strong>
              </>
            )}
            {simulation && (
              <>
                {' '}
                · {simulation.driverCount} drivers · {simulation.totalLaps} laps ·{' '}
                {simulation.trainingRows?.length?.toLocaleString()} training rows
              </>
            )}
          </p>
        </div>
        <div className="replay-header-badges">
          {source && <span className="badge">{source}</span>}
          <span className={`live-badge ${playing ? 'live-badge--on' : ''}`}>
            {playing ? '● LIVE' : 'PAUSED'}
          </span>
        </div>
      </div>

      {isDemo && !loading && (
        <div className="demo-banner" role="status">
          <strong>Demo simulation</strong> — bundled sample laps only. Start the backend for the
          full Monaco race dataset.
        </div>
      )}

      {loading && (
        <div className="status-card loading-card replay-loading">
          <span className="spinner" aria-hidden="true" />
          <p>Building merged lap dataset for all drivers… first load may take a moment.</p>
        </div>
      )}

      {error && !loading && (
        <div className="status-card error-card" role="alert">
          <p>{error}</p>
          <button type="button" onClick={loadSimulation}>
            Retry
          </button>
        </div>
      )}

      {simulation && !loading && currentLap && (
        <>
          <div className="lb-lap-banner">
            <span className="lb-lap-label">Lap</span>
            <span className="lb-lap-value">
              {currentLap.lap} <span className="lb-lap-of">/ {simulation.totalLaps}</span>
            </span>
            <span className="lb-lap-leader">
              Leader: <strong>{currentLap.leaderCode ?? '—'}</strong>
              {currentLap.leaderLapTime != null && (
                <span className="lb-lap-leader-time">
                  {' '}
                  · {formatLapTime(currentLap.leaderLapTime)}
                </span>
              )}
            </span>
            <div className="lb-sector-progress" aria-hidden="true">
              <span className={visibility.s1 ? 'active' : ''}>S1</span>
              <span className={visibility.s2 ? 'active' : ''}>S2</span>
              <span className={visibility.s3 ? 'active' : ''}>S3</span>
            </div>
          </div>

          <div className="lb-table-wrap">
            <table className="lb-table">
              <thead>
                <tr>
                  <th>POS</th>
                  <th>Driver</th>
                  <th>{visibility.lapTime ? 'Gap' : 'Int'}</th>
                  <th>S1</th>
                  <th>S2</th>
                  <th>S3</th>
                  <th>Lap</th>
                </tr>
              </thead>
              <tbody>
                {currentLap.entries.map((entry) => (
                  <LeaderboardRow
                    key={entry.code}
                    entry={entry}
                    visibility={visibility}
                    highlightCode={highlightDriver}
                  />
                ))}
              </tbody>
            </table>
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
              Restart race
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
              max={Math.max(0, lapsMerged.length - 1)}
              step={1}
              value={lapIndex}
              onChange={handleLapSeek}
              aria-label="Lap selector"
            />
            <span className="replay-duration">Lap {currentLap.lap}</span>
          </div>
          <div className="replay-progress" aria-hidden="true">
            <div
              className="replay-progress-fill"
              style={{
                width: `${((lapIndex + lapProgress) / lapsMerged.length) * 100}%`,
              }}
            />
          </div>
        </>
      )}
    </section>
  )
}
