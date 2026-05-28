import { useCallback, useEffect, useState } from 'react'
import { fetchOverview, fetchSessions } from './api'
import TelemetryReplay from './TelemetryReplay'
import './App.css'

const DATASETS = ['results', 'laps', 'telemetry']
const DEFAULT_SESSION_ID = '2024-monaco-r'

function DataTable({ dataset }) {
  if (!dataset?.columns?.length) {
    return <p className="muted">No columns in this dataset.</p>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {dataset.columns.map((col) => (
              <th key={col.name} title={col.dtype}>
                {col.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataset.previewRows.map((row, i) => (
            <tr key={i}>
              {dataset.columns.map((col) => (
                <td key={col.name}>{formatCell(row[col.name])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatCell(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function SchemaList({ columns }) {
  return (
    <ul className="schema-list">
      {columns.map((col) => (
        <li key={col.name}>
          <span className="schema-name">{col.name}</span>
          <span className="schema-dtype">{col.dtype}</span>
        </li>
      ))}
    </ul>
  )
}

function FilterSelect({ id, label, value, onChange, disabled, children }) {
  return (
    <label className="filter-field" htmlFor={id}>
      <span className="filter-label">{label}</span>
      <select
        id={id}
        className="filter-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {children}
      </select>
    </label>
  )
}

function App() {
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION_ID)
  const [driver, setDriver] = useState('')
  const [drivers, setDrivers] = useState([])

  const [overview, setOverview] = useState(null)
  const [activeDataset, setActiveDataset] = useState('results')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dataSource, setDataSource] = useState(null)

  useEffect(() => {
    fetchSessions()
      .then((data) => {
        const list = data.sessions ?? []
        setSessions(list)
        if (list.length && !list.some((s) => s.id === sessionId)) {
          setSessionId(list[0].id)
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  const loadOverview = useCallback(
    async ({ nextSessionId, nextDriver, keepDriver = true }) => {
      setLoading(true)
      setError(null)
      try {
        const { data, source } = await fetchOverview({
          sessionId: nextSessionId,
          driver: keepDriver ? nextDriver || undefined : undefined,
        })
        setOverview(data)
        setDrivers(data.drivers ?? [])
        setDriver(data.selectedDriver)
        setDataSource(source)
      } catch (err) {
        setError(err.message)
        setOverview(null)
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (!sessionId) return
    loadOverview({ nextSessionId: sessionId, nextDriver: driver, keepDriver: false })
  }, [sessionId, loadOverview])

  const handleSessionChange = (nextSessionId) => {
    setSessionId(nextSessionId)
  }

  const handleDriverChange = (nextDriver) => {
    setDriver(nextDriver)
    loadOverview({
      nextSessionId: sessionId,
      nextDriver,
      keepDriver: true,
    })
  }

  const dataset = overview?.datasets?.[activeDataset]
  const session = overview?.session
  const selectedDriverInfo = drivers.find((d) => d.code === driver)

  return (
    <div className="app">
      <header className="header">
        <div className="header-bar" aria-hidden="true" />
        <div className="header-inner">
          <p className="eyebrow">F1 Race Engineer</p>
          <h1>Data Explorer</h1>
          <p className="subtitle">
            Filter by session and driver, then replay telemetry as if the session
            is happening live.
          </p>
        </div>
      </header>

      <main className="main">
        <section className="filters-card" aria-label="Filters">
          <FilterSelect
            id="session-select"
            label="Session / Race"
            value={sessionId}
            onChange={handleSessionChange}
            disabled={loading && !sessions.length}
          >
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </FilterSelect>

          <FilterSelect
            id="driver-select"
            label="Driver"
            value={driver}
            onChange={handleDriverChange}
            disabled={!drivers.length || loading}
          >
            {drivers.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code} — {d.name}
                {d.team ? ` (${d.team})` : ''}
              </option>
            ))}
          </FilterSelect>

          <div className="filters-meta">
            {dataSource && <span className="badge">{dataSource}</span>}
            <button
              type="button"
              className="btn-secondary"
              disabled={loading}
              onClick={() =>
                loadOverview({
                  nextSessionId: sessionId,
                  nextDriver: driver,
                  keepDriver: true,
                })
              }
            >
              Refresh
            </button>
          </div>
        </section>

        {driver && !loading && (
          <TelemetryReplay
            key={`${sessionId}-${driver}`}
            sessionId={sessionId}
            driver={driver}
            driverInfo={selectedDriverInfo}
          />
        )}

        {loading && (
          <div className="status-card loading-card">
            <span className="spinner" aria-hidden="true" />
            <p>Loading session data… first run may take a minute while FastF1 caches.</p>
          </div>
        )}

        {error && !loading && (
          <div className="status-card error-card" role="alert">
            <p>{error}</p>
            <button
              type="button"
              onClick={() =>
                loadOverview({
                  nextSessionId: sessionId,
                  nextDriver: driver,
                  keepDriver: true,
                })
              }
            >
              Retry
            </button>
          </div>
        )}

        {overview && !loading && (
          <>
            <section