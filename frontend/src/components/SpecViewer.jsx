import { useState } from 'react'
import { buildApiUrl } from '../lib/api'

const stages = ['hpss', 'gated', 'clean']
const stageLabels = { hpss: 'Original', gated: 'Gated', clean: 'Cleaned' }

export default function SpecViewer({ call }) {
  const [stage, setStage] = useState('clean')

  if (!call) {
    return (
      <div className="panel panel-empty">
        <p>Select a recording to view spectrogram</p>
      </div>
    )
  }

  const imageSrc = buildApiUrl(`/calls/${call.id}/spectrogram/${stage}`)

  return (
    <div className="panel panel-spec">
      <div className="panel-header">
        <h4>Spectrogram</h4>
        <div className="panel-toggle">
          {stages.map((s) => (
            <button
              key={s}
              onClick={() => setStage(s)}
              className={stage === s ? 'is-active' : ''}
            >
              {stageLabels[s]}
            </button>
          ))}
        </div>
      </div>
      <div className="panel-image">
        <img src={imageSrc} alt={`${call.call_id_csv} ${stage}`} />
      </div>
      <div className="panel-meta">
        <span>Type: <strong>{call.call_type || 'unknown'}</strong></span>
        <span>SNR Δ: <strong className="panel-meta-highlight">+{(call.snr_improvement_db ?? 0).toFixed(1)} dB</strong></span>
      </div>
    </div>
  )
}
