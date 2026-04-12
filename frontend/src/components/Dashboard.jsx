import { useEffect, useMemo, useState } from 'react'
import SpecViewer from './SpecViewer'
import CallMap from './CallMap'
import VoiceBar from './VoiceBar'
import ClipPlayer from './ClipPlayer'
import GeminiCategories from './GeminiCategories'
import { fetchJson } from '../lib/api'

export default function Dashboard() {
  const [calls, setCalls] = useState([])
  const [stats, setStats] = useState({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
  const [selectedId, setSelectedId] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    const load = async () => {
      const [callsData, statsData] = await Promise.all([
        fetchJson('/calls'),
        fetchJson('/stats')
      ])

      setCalls(callsData)
      setStats(statsData)
      setLoadError('')
      if (callsData.length > 0) {
        setSelectedId(callsData[0].id)
      }
    }

    load().catch((err) => {
      console.error('Dashboard load failed:', err)
      setLoadError(err.message || 'Failed to load dashboard data')
      setCalls([])
      setStats({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
    })
  }, [])

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

      <GeminiCategories stats={stats} selectedCall={selectedCall} />

      {loadError && (
        <p className="demo-error" style={{ margin: '8px 0 0' }}>
          {loadError}
        </p>
      )}

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
