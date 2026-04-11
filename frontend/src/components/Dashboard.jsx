import { useEffect, useMemo, useState } from 'react'
import SpecViewer from './SpecViewer'
import CallMap from './CallMap'
import VoiceBar from './VoiceBar'
import ClipPlayer from './ClipPlayer'

export default function Dashboard() {
  const apiUrl = import.meta.env.VITE_API_URL
  const [calls, setCalls] = useState([])
  const [stats, setStats] = useState({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    const load = async () => {
      const [callsRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/calls`),
        fetch(`${apiUrl}/stats`)
      ])

      const callsData = await callsRes.json()
      const statsData = await statsRes.json()
      setCalls(callsData)
      setStats(statsData)
      if (callsData.length > 0) {
        setSelectedId(callsData[0].id)
      }
    }

    load().catch((err) => console.error('Dashboard load failed:', err))
  }, [apiUrl])

  const selectedCall = useMemo(() => calls.find((c) => c.id === selectedId) ?? null, [calls, selectedId])

  return (
    <div className="dashboard">
      <header className="dash-header">
        <div>
          <h1>EchoMap Research Dashboard</h1>
          <p>Stage 2/3 denoising, spectrogram analysis, and AI-derived call classification.</p>
        </div>
        <VoiceBar />
      </header>

      <section className="stat-grid">
        <article>
          <h3>Total Calls</h3>
          <p>{stats.total_calls}</p>
        </article>
        <article>
          <h3>Avg Confidence</h3>
          <p>{Number(stats.avg_confidence || 0).toFixed(2)}</p>
        </article>
        <article>
          <h3>Classification Breakdown</h3>
          <ul>
            {Object.entries(stats.by_call_type || {}).map(([type, count]) => (
              <li key={type}>
                <span>{type}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <main className="dash-main">
        <aside className="call-list">
          <h3>Processed Calls</h3>
          {calls.map((call) => (
            <button
              key={call.id}
              className={call.id === selectedId ? 'active' : ''}
              onClick={() => setSelectedId(call.id)}
            >
              {call.call_id_csv} · {call.call_type || 'unknown'}
            </button>
          ))}
        </aside>

        <section className="dash-panels">
          <CallMap calls={calls} selectedId={selectedId} />
          <SpecViewer call={selectedCall} />
          <ClipPlayer call={selectedCall} />
        </section>
      </main>
    </div>
  )
}
