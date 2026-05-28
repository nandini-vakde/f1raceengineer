const STATIC_OVERVIEW = '/data/overview.json'
const STATIC_SESSIONS = '/data/sessions.json'
const STATIC_REPLAY = '/data/replay.json'

export async function fetchSessions() {
  try {
    const res = await fetch('/api/sessions')
    if (!res.ok) throw new Error('sessions unavailable')
    return res.json()
  } catch {
    const res = await fetch(STATIC_SESSIONS)
    if (!res.ok) throw new Error('Session list not found')
    return res.json()
  }
}

export async function fetchOverview({ sessionId, driver }) {
  const params = new URLSearchParams({ session_id: sessionId })
  if (driver) params.set('driver', driver)

  try {
    const res = await fetch(`/api/overview?${params}`)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `API error ${res.status}`)
    }
    return { data: await res.json(), source: 'live API' }
  } catch (apiErr) {
    const res = await fetch(STATIC_OVERVIEW)
    if (!res.ok) throw apiErr
    const data = await res.json()
    if (data.session?.id && data.session.id !== sessionId) {
      throw new Error(
        'Start the backend to load other sessions: uvicorn api:app --reload --port 8000',
      )
    }
    const resolvedDriver = driver || data.selectedDriver
    return {
      data: filterStaticOverview(data, resolvedDriver),
      source: 'bundled sample (run backend for all sessions)',
    }
  }
}

async function isApiReachable() {
  try {
    const res = await fetch('/api/health')
    return res.ok
  } catch {
    return false
  }
}

export async function fetchTelemetryReplay({ sessionId, driver }) {
  const params = new URLSearchParams({ session_id: sessionId })
  if (driver) params.set('driver', driver)

  const apiUp = await isApiReachable()

  if (apiUp) {
    const res = await fetch(`/api/telemetry/replay?${params}`)
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      const detail = body.detail || `API error ${res.status}`
      throw new Error(
        typeof detail === 'string'
          ? detail
          : 'Failed to load replay. The session may still be caching - try again in a minute.',
      )
    }
    return { data: await res.json(), source: 'Full session (live API)', isDemo: false }
  }

  const res = await fetch(STATIC_REPLAY)
  if (!res.ok) {
    throw new Error(
      'Live replay requires the backend. Run: cd backend && uvicorn api:app --reload --port 8000',
    )
  }
  const data = await res.json()
  if (data.session?.id && data.session.id !== sessionId) {
    throw new Error(
      'This session needs the backend for a full replay. Start uvicorn on port 8000.',
    )
  }
  return {
    data: { ...data, driver: driver || data.driver },
    source: 'Demo only - 3 laps',
    isDemo: true,
  }
}

function filterStaticOverview(data, driverCode) {
  if (!driverCode || driverCode === data.selectedDriver) return data
  const driver = data.drivers?.find((d) => d.code === driverCode)
  if (!driver) return { ...data, selectedDriver: driverCode }

  return {
    ...data,
    selectedDriver: driverCode,
    datasets: {
      ...data.datasets,
      results: {
        ...data.datasets.results,
        description: `Result row for ${driverCode} (sample data).`,
      },
      laps: {
        ...data.datasets.laps,
        description: `Per-lap data for ${driverCode} (sample - same preview rows).`,
      },
      telemetry: {
        ...data.datasets.telemetry,
        description: `Telemetry sample labelled for ${driver.name} (${driverCode}).`,
      },
    },
  }
}
