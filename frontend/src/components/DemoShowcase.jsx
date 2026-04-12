import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const stages = ['hpss', 'clean']
const stageLabels = { hpss: 'Original', clean: 'Cleaned' }

function RecordingCard({ call }) {
  const [stage, setStage] = useState('clean')
  const apiUrl = import.meta.env.VITE_API_URL

  return (
    <div className="demo-card">
      <div className="demo-card-header">
        <h3>{call.call_id_csv}</h3>
        <div className="demo-card-stats">
          <span>SNR: <b>{call.snr_before_db?.toFixed(1)}</b> → <b>{call.snr_after_db?.toFixed(1)} dB</b></span>
          <span className="demo-improvement">+{call.snr_improvement_db?.toFixed(1)} dB</span>
          <span>{call.call_count} calls</span>
          <span>{call.duration_seconds?.toFixed(0)}s</span>
        </div>
      </div>

      <div className="demo-toggle">
        {stages.map((s) => (
          <button key={s} className={stage === s ? 'active' : ''} onClick={() => setStage(s)}>
            {stageLabels[s]}
          </button>
        ))}
      </div>

      <img
        className="demo-spectrogram"
        src={`${apiUrl}/calls/${call.id}/spectrogram/${stage}`}
        alt={`${call.call_id_csv} ${stageLabels[stage]}`}
      />

      <div className="demo-audio-row">
        <div>
          <label>Original Recording</label>
          <audio controls src={`${apiUrl}/calls/${call.id}/audio/hpss`} />
        </div>
        <div>
          <label>After Processing</label>
          <audio controls src={`${apiUrl}/calls/${call.id}/audio/clean`} />
        </div>
      </div>
    </div>
  )
}

export default function DemoShowcase() {
  const navigate = useNavigate()
  const apiUrl = import.meta.env.VITE_API_URL
  const [calls, setCalls] = useState([])
  const [stats, setStats] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/calls`).then(r => r.json()),
      fetch(`${apiUrl}/stats`).then(r => r.json()),
    ]).then(([callsData, statsData]) => {
      setCalls(callsData.slice(0, 5))
      setStats(statsData)
    }).catch(err => console.error('Demo load failed:', err))
  }, [apiUrl])

  if (!calls.length) return null

  return (
    <section className="demo-showcase" id="transform">
      <div className="demo-header">
        <p className="demo-eyebrow">Live Results · Top Recordings</p>
        <h2>Hear the <em>difference</em></h2>
        <p className="demo-sub">
          Our top 5 recordings ranked by noise reduction improvement. Toggle between original field audio and processed output.
        </p>
        <button className="btn btn-primary" onClick={() => navigate('/demo')} style={{ marginTop: '8px' }}>
          Try your own recording
        </button>
      </div>

      {stats && (
        <div className="demo-stats-row">
          <div className="demo-stat">
            <span className="demo-stat-value">{calls.length}</span>
            <span className="demo-stat-label">Recordings Shown</span>
          </div>
          <div className="demo-stat">
            <span className="demo-stat-value">{stats.total_calls}</span>
            <span className="demo-stat-label">Calls Detected</span>
          </div>
          <div className="demo-stat">
            <span className="demo-stat-value">+{calls[0]?.snr_improvement_db?.toFixed(1)} dB</span>
            <span className="demo-stat-label">Best Improvement</span>
          </div>
          <div className="demo-stat">
            <span className="demo-stat-value">HPSS</span>
            <span className="demo-stat-label">No ML Models</span>
          </div>
        </div>
      )}

      <div className="demo-cards">
        {calls.map((call) => (
          <RecordingCard key={call.id} call={call} />
        ))}
      </div>
    </section>
  )
}
