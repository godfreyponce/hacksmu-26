import { useEffect, useRef, useState } from 'react'
import { Play, Pause } from 'lucide-react'
import WaveSurfer from 'wavesurfer.js'
import { buildApiUrl } from '../lib/api'

const stages = ['hpss', 'gated', 'clean']
const stageLabels = { hpss: 'Original', gated: 'Gated', clean: 'Cleaned' }

export default function ClipPlayer({ call }) {
  const containerRef = useRef(null)
  const wavesurfer = useRef(null)
  const [stage, setStage] = useState('clean')
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    if (!containerRef.current || !call) return

    wavesurfer.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: 'rgba(126, 200, 160, 0.4)',
      progressColor: '#7ec8a0',
      cursorColor: 'rgba(255,255,255,0.5)',
      height: 64,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      responsive: true,
    })

    wavesurfer.current.on('play', () => setIsPlaying(true))
    wavesurfer.current.on('pause', () => setIsPlaying(false))
    wavesurfer.current.on('finish', () => setIsPlaying(false))

    wavesurfer.current.load(buildApiUrl(`/calls/${call.id}/audio/${stage}`))

    return () => wavesurfer.current?.destroy()
  }, [call, stage])

  const handlePlayPause = () => {
    wavesurfer.current?.playPause()
  }

  if (!call) {
    return (
      <div className="panel panel-empty">
        <p>Select a recording to play audio</p>
      </div>
    )
  }

  return (
    <div className="panel panel-audio">
      <div className="panel-header">
        <h4>Audio Playback</h4>
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
      <div className="panel-waveform" ref={containerRef} />
      <button className="panel-play-btn" onClick={handlePlayPause}>
        {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        <span>{isPlaying ? 'Pause' : 'Play'}</span>
      </button>
    </div>
  )
}
