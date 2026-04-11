// Audio playback with waveform

import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'

export default function ClipPlayer({ callId }) {
  const containerRef = useRef(null)
  const wavesurfer = useRef(null)
  const [playClean, setPlayClean] = useState(false)
  const apiUrl = import.meta.env.VITE_API_URL

  const variant = playClean ? 'clean' : 'noisy'

  useEffect(() => {
    if (!containerRef.current) return

    wavesurfer.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#4a9eff',
      progressColor: '#1e6fba',
      cursorColor: '#fff',
      height: 80,
      barWidth: 2,
      barGap: 1,
      responsive: true
    })

    wavesurfer.current.load(`${apiUrl}/clips/${callId}_${variant}.wav`)

    return () => wavesurfer.current?.destroy()
  }, [callId, variant, apiUrl])

  const handlePlayPause = () => {
    wavesurfer.current?.playPause()
  }

  return (
    <div className="clip-player">
      <div className="toggle">
        <button onClick={() => setPlayClean(false)} className={!playClean ? 'active' : ''}>
          Noisy
        </button>
        <button onClick={() => setPlayClean(true)} className={playClean ? 'active' : ''}>
          Clean
        </button>
      </div>
      <div ref={containerRef} className="waveform" />
      <button onClick={handlePlayPause}>Play / Pause</button>
    </div>
  )
}
