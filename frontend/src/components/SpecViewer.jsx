// Noisy / clean spectrogram toggle

import { useState } from 'react'

export default function SpecViewer({ callId }) {
  const [showClean, setShowClean] = useState(false)
  const apiUrl = import.meta.env.VITE_API_URL

  const variant = showClean ? 'clean' : 'noisy'
  const imageSrc = `${apiUrl}/spectrograms/${callId}_${variant}.png`

  return (
    <div className="spec-viewer">
      <div className="toggle">
        <button onClick={() => setShowClean(false)} className={!showClean ? 'active' : ''}>
          Noisy
        </button>
        <button onClick={() => setShowClean(true)} className={showClean ? 'active' : ''}>
          Clean
        </button>
      </div>
      <img src={imageSrc} alt={`Spectrogram ${callId} (${variant})`} />
    </div>
  )
}
