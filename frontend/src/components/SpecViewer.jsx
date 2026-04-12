import { useState } from 'react'

const stages = ['hpss', 'gated', 'clean']

export default function SpecViewer({ call }) {
  const [stage, setStage] = useState('clean')
  const apiUrl = import.meta.env.VITE_API_URL

  if (!call) {
    return <div className="spec-viewer">No processed calls yet.</div>
  }

  const imageSrc = `${apiUrl}/calls/${call.id}/spectrogram/${stage}`

  return (
    <div className="spec-viewer">
      <div className="toggle stage-toggle">
        {stages.map((item) => (
          <button key={item} onClick={() => setStage(item)} className={stage === item ? 'active' : ''}>
            {item.toUpperCase()}
          </button>
        ))}
      </div>
      <img src={imageSrc} alt={`Spectrogram ${call.call_id_csv} (${stage})`} />
      <div className="call-metadata">
        <p>Type: {call.call_type || 'unknown'} <span style={{ opacity: 0.6, fontSize: '0.85em' }}>(from CSV label)</span></p>
        {call.snr_improvement_db != null && (
          <p>In-call energy ratio Δ: {Number(call.snr_improvement_db).toFixed(1)} dB</p>
        )}
      </div>
    </div>
  )
}
