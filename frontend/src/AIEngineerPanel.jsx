import { tagFromEvents } from './engineerUtils'

export default function AIEngineerPanel({ messages = [], status = 'STANDBY', error = null }) {
  return (
    <section className="engineer-panel">
      <div className="engineer-header">
        <h2>AI Race Engineer</h2>
        <span className={`engineer-status engineer-status--${status.toLowerCase()}`}>
          ● {status}
        </span>
      </div>

      {error && (
        <p className="engineer-error" role="alert">
          {error}
        </p>
      )}

      <div className="engineer-feed">
        {messages.length === 0 && !error && (
          <p className="engineer-empty muted">
            Start the replay — coaching messages appear when notable telemetry events
            are detected (DRS, braking zones, high speed).
          </p>
        )}

        {messages.map((msg, idx) => (
          <div key={`${msg.timestamp}-${idx}`} className="engineer-message">
            <div className="engineer-meta">
              <span className={`engineer-tag engineer-tag--${msg.type.toLowerCase()}`}>
                {msg.type}
              </span>

              <span className="engineer-time">
                {msg.timestamp}
              </span>
            </div>

            <p>{msg.text}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
