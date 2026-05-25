import { useCallback, useEffect, useState } from 'react'
import './App.css'

const DATASETS = ['results', 'laps', 'telemetry']

async function fetchOverview() {
  const res = await fetch('/api/overview')
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
  }
  return res.json()
}

async function fetchStaticFallback() {
  const res = await fetch('/data/overview.json')
  if (!res.ok) throw new Error('Static sample data not found')
  return res.json()
}

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

function App() {
  const [overview, setOverview] = useState(null)
  const [activeDataset, setActiveDataset] = useState('results')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dataSource, setDataSource] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchOverview()
      setOverview(data)
      setDataSource('live API')
    } catch {
      try {
        const data = await fetchStaticFallback()
        setOverview(data)
        setDataSource('bundled sample (run backend for live data)')
      } catch (fallbackErr) {
        setError(
          fallbackErr.message ||
            'Could not load data. Start the API with: uvicorn api:app --reload --port 8000',
        )
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const dataset = overview?.datasets?.[activeDataset]
  const session = overview?.session

  return (
    <div className="app">
      <header className="header">
        <div className="header-bar" aria-hidden="true" />
        <div className="header-inner">
          <p className="eyebrow">F1 Race Engineer</p>
          <h1>Data Explorer</h1>
          <p className="subtitle">
            Preview the FastF1 datasets powering this project — race results,
            lap times, and telemetry.
          </p>
        </div>
      </header>

      <main className="main">
        {loading && (
          <div className="status-card loading-card">
            <span className="spinner" aria-hidden="true" />
            <p>Loading session data… first run may take a minute while FastF1 caches.</p>
          </div>
        )}

        {error && !loading && (
          <div className="status-card error-card" role="alert">
            <p>{error}</p>
            <button type="button" onClick={loadData}>
              Retry
            </button>
          </div>
        )}

        {overview && !loading && (
          <>
            <section className="session-card">
              <div>
                <h2>Session</h2>
                {session && (
                  <dl className="session-meta">
                    <div>
                      <dt>Event</dt>
                      <dd>{session.eventName ?? session.location}</dd>
                    </div>
                    <div>
                      <dt>Year</dt>
                      <dd>{session.year}</dd>
                    </div>
                    <div>
                      <dt>Type</dt>
                      <dd>{session.sessionType}</dd>
                    </div>
                    <div>
                      <dt>Name</dt>
                      <dd>{session.name}</dd>
                    </div>
                  </dl>
                )}
              </div>
              <div className="session-side">
                <span className="badge">{dataSource}</span>
                <button type="button" className="btn-secondary" onClick={loadData}>
                  Refresh
                </button>
              </div>
            </section>

            <nav className="tabs" aria-label="Datasets">
              {DATASETS.map((id) => {
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
        <span>Theme: F1 red / white / black</span>
        <span>Data via FastF1</span>
      </footer>
    </div>
  )
}

export default App
