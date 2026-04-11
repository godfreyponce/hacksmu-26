import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'

const stages = ['hpss', 'gated', 'clean']

export default function ClipPlayer({ call }) {
  const containerRef = useRef(null)
  const wavesurfer = useRef(null)
  const [stage, setStage] = useState('clean')
  const apiUrl = import.meta.env.VITE_API_URL

  useEffect(() => {
    if (!containerRef.current || !call) return

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

    wavesurfer.current.load(`${apiUrl}/calls/${call.id}/audio/${stage}`)

    return () => wavesurfer.current?.destroy()
  }, [call, stage, apiUrl])

  const handlePlayPause = () => {
    wavesurfer.current?.playPause()
  }

  if (!call) {
    return <div className="clip-player">No audio available.</div>
  }

  return (
    <div className="clip-player">
      <div className="toggle stage-toggle">
        {stages.map((item) => (
          <button key={item} onClick={() => setStage(item)} className={stage === item ? 'active' : ''}>
            {item.toUpperCase()}
          </button>
        ))}
      </div>
      <div ref={containerRef} className="waveform" />
      <button onClick={handlePlayPause}>Play / Pause</button>
    </div>
  )
}
