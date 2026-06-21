// frontend/src/AIEngineerPanel.jsx

const placeholderMessages = [
  {
    timestamp: "00:42.500",
    type: "INFO",
    text: "Good pace through Sector 1. Gain of 0.18s on reference."
  },
  {
    timestamp: "01:12.300",
    type: "WARNING",
    text: "Front-left tyre temperatures increasing."
  },
  {
    timestamp: "01:48.900",
    type: "COACH",
    text: "Brake slightly later into Turn 10. Time available on entry."
  },
  {
    timestamp: "02:20.100",
    type: "STRATEGY",
    text: "DRS opportunity ahead. Gap 0.8 seconds."
  }
]

export default function AIEngineerPanel() {
  return (
    <section className="engineer-panel">
      <div className="engineer-header">
        <h2>AI Race Engineer</h2>
        <span className="engineer-status">
          ● STANDBY
        </span>
      </div>

      <div className="engineer-feed">
        {placeholderMessages.map((msg, idx) => (
          <div key={idx} className="engineer-message">
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