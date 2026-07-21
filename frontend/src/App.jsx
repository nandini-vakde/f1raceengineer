import { useCallback, useEffect, useState } from 'react'
import { fetchOverview, fetchSessions, fetchPersonalities } from './api'
import RaceLeaderboard from './RaceLeaderboard'
import TelemetryReplay from './TelemetryReplay'
import './App.css'
import AIEngineerPanel from './AIEngineerPanel'

const DATASETS = ['results', 'laps', 'raceLaps', 'telemetry']
const DEFAULT_SESSION_ID = '2024-monaco-r'

const SESSION_GROUPS = [
  { label: 'Races', types: ['R'] },
  { label: 'Sprint', types: ['S'] },
  { label: 'Qualifying', types: ['Q'] },
]

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
  const [engineerMessages, setEngineerMessages] = useState([])
  const [engineerStatus, setEngineerStatus] = useState('STANDBY')
  const [engineerError, setEngineerError] = useState(null)

  const [personalities, setPersonalities] = useState([])
  const [selectedPersonality, setSelectedPersonality] = useState(null)

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

    fetchPersonalities()
      .then((list) => {
        setPersonalities(list)
        if (list.length) setSelectedPersonality(list[0].id)
      })
      .catch(() => {})
  }, [])

  const loadOverview = useCallback(
    async ({ nextSessionId, nextDriver, keepDriver = true, silent = false }) => {
      if (!silent) {
        setLoading(true)
        setError(null)
      }
      try {
        const { data, source } = await fetchOverview({
          sessionId: nextSessionId,
          driver: keepDriver ? nextDriver || undefined : undefined,
        })
        setOverview(data)
        setDrivers(data.drivers ?? [])
        setDriver(data.selectedDriver)
        setDataSource(source)
        if (!data.datasets?.[activeDataset]) {
          setActiveDataset('results')
        }
      } catch (err) {
        if (silent) return
        setError(err.message)
        setOverview(null)
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [activeDataset],
  )

  useEffect(() => {
    if (!sessionId) return
    loadOverview({ nextSessionId: sessionId, nextDriver: driver, keepDriver: false })
  }, [sessionId, loadOverview])

  const handleSessionChange = (nextSessionId) => {
    setEngineerMessages([])
    setEngineerError(null)
    setEngineerStatus('STANDBY')
    setSessionId(nextSessionId)
  }

  const handleDriverChange = (nextDriver) => {
    setEngineerMessages([])
    setEngineerError(null)
    setEngineerStatus('STANDBY')
    setDriver(nextDriver)
    const isRace =
      overview?.session?.sessionType === 'R' ||
      sessions.find((s) => s.id === sessionId)?.sessionType === 'R'
    loadOverview({
      nextSessionId: sessionId,
      nextDriver,
      keepDriver: true,
      silent: isRace,
    })
  }

  const handleEngineerMessage = useCallback((msg) => {
    setEngineerMessages((prev) => [...prev, msg])
  }, [])

  const dataset = overview?.datasets?.[activeDataset]
  const session = overview?.session
  const isRaceSession =
    session?.sessionType === 'R' ||
    sessions.find((s) => s.id === sessionId)?.sessionType === 'R'
  const selectedDriverInfo = drivers.find((d) => d.code === driver)

  return (
    <div className="app">
      <header className="header">
        <div className="header-bar" aria-hidden="true" />
        <div className="header-inner">
          <p className="eyebrow">F1 Race Engineer</p>
          <h1>Data Explorer</h1>
          <p className="subtitle">
            {isRaceSession
              ? 'Watch the full-field race leaderboard lap by lap, or pick a driver for telemetry replay.'
              : 'Filter by session and driver, then replay telemetry as if the session is happening live.'}
          </p>
        </div>
      </header>

      <main className="main">
        <section className="filters-card" aria-label="Filters">
          <FilterSelect
            id="session-select"
            label="Race / Session"
            value={sessionId}
            onChange={handleSessionChange}
            disabled={loading && !sessions.length}
          >
            {sessions.length === 0 ? (
              <option value={sessionId}>Loading sessions…</option>
            ) : (
              SESSION_GROUPS.map((group) => {
                const items = sessions.filter((s) => group.types.includes(s.sessionType))
                if (!items.length) return null
                return (
                    <optgroup key={group.label} label={group.label}>
                    {items.map((s) => (
                      <option key={s.session_key ?? s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </optgroup>
                )
              })
            )}
          </FilterSelect>

          <FilterSelect
            id="driver-select"
            label={isRaceSession ? 'Highlight driver' : 'Driver'}
            value={driver}
            onChange={handleDriverChange}
            disabled={!drivers.length || (loading && !overview)}
          >
            {drivers.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code} — {d.name}
                {d.team ? ` ({d.team})` : ''}
              </option>
            ))}
          </FilterSelect>

          <FilterSelect
            id="personality-select"
            label="Engineer voice"
            value={selectedPersonality || ''}
            onChange={(v) => setSelectedPersonality(v)}
            disabled={!personalities.length}
          >
            {personalities.map((p) => (
              <option key={p.id} value={p.id} title={p.description}>
                {p.name}
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

        {overview && !loading && isRaceSession && (
          <RaceLeaderboard
            key={sessionId}
            sessionId={sessionId}
            highlightDriver={driver || undefined}
          />
        )}

        {driver && overview && !loading && (
          <>
            <TelemetryReplay
              key={`${sessionId}-${driver}-${selectedPersonality}`}
              sessionId={sessionId}
              driver={driver}
              driverInfo={selectedDriverInfo}
              selectedPersonality={selectedPersonality}
              onEngineerMessage={handleEngineerMessage}
              onEngineerStatus={setEngineerStatus}
              onEngineerError={setEngineerError}
            />

            <AIEngineerPanel
              messages={engineerMessages}
              status={engineerStatus}
              error={engineerError}
            />
          </>
        )}

        {loading && !overview && (
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
            <section className="session-card">
              <div>
                <h2>Active view</h2>
                <dl className="session-meta">
                  <div>
                    <dt>Event</dt>
                    <dd>{session?.eventName ?? session?.location}</dd>
                  </div>
                  <div>
                    <dt>Session</dt>
                    <dd>
                      {session?.year} · {session?.sessionType} · {session?.name}
                    </dd>
                  </div>
                  <div>
                    <dt>{isRaceSession ? 'Highlight' : 'Driver'}</dt>
                    <dd>
                      {isRaceSession && (
                        <span className="muted-inline">Leaderboard row · </span>
                      )}
                      {selectedDriverInfo
                        ? `${selectedDriverInfo.code} — ${selectedDriverInfo.name}`
                        : driver || '—'}
                    </dd>
                  </div>
                  {session?.date && (
                    <div>
                      <dt>Date</dt>
                      <dd>{session.date}</dd>
                    </div>
                  )}
                </dl>
              </div>
            </section>

            <nav className="tabs" aria-label="Datasets">
              {DATASETS.filter((id) => overview.datasets[id]).map((id) => {
                const ds = overview.datasets[id]
                return (
                  <button
                    key={id}
                    type="button"
                    className={activeDataset === id ? 'tab active' : 'tab'}
                    onClick={() => setActiveDataset(id)}
                    aria-current={activeDataset === id ? 'page' : undefined}
                  >
                    {ds?.title ?? id}
                    <span className="tab-count">{ds?.rowCount ?? 0} rows</span>
                  </button>
                )
              })}
            </nav>

            {dataset && (
              <section className="dataset-panel">
                <div className="dataset-header">
                  <div>
                    <h2>{dataset.title}</h2>
                    <p className="dataset-desc">{dataset.description}</p>
                    <code className="source-tag">{dataset.source}</code>
                  </div>
                  <p className="row-total">
                    Showing {dataset.previewRows.length} of{' '}
                    <strong>{dataset.rowCount}</strong> rows
                  </p>
                </div>

                <div className="panel-grid">
                  <div className="panel-block">
                    <h3>Schema</h3>
                    <SchemaList columns={dataset.columns} />
                  </div>
                  <div className="panel-block panel-wide">
                    <h3>Preview</h3>
                    <DataTable dataset={dataset} />
                  </div>
                </div>
              </section>
            )}
          </>
        )}
      </main>

      <footer className="footer">
        <span>
          {isRaceSession ? 'Race simulation + driver telemetry' : 'Filter by session and driver'}
        </span>
        <span>Data via OpenF1</span>
      </footer>
    </div>
  )
}

export default App
