import { useState } from 'react'
import { buildApiUrl } from '../lib/api'

const stages = ['hpss', 'gated', 'clean']

export default function SpecViewer({ call }) {
  const [stage, setStage] = useState('clean')

  if (!call) {
    return <div className="spec-viewer">No processed calls yet.</div>
  }

  const imageSrc = buildApiUrl(`/calls/${call.id}/spectrogram/${stage}`)

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
        <p>Type: {call.call_type || 'unknown'}</p>
        <p>Fundamental: {call.fundamental_hz || 'n/a'} Hz</p>
        <p>Harmonics: {(call.harmonics || []).join(', ') || 'n/a'}</p>
      </div>
    </div>
  )
}
