import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const PIPELINE_STEPS = [
  { label: 'Loading audio', detail: 'Reading WAV file and detecting sample rate' },
  { label: 'Building noise profile', detail: 'Estimating background noise characteristics' },
  { label: 'Separating harmonics (HPSS)', detail: 'Splitting harmonic elephant calls from percussive noise' },
  { label: 'Applying spectral gate', detail: 'Removing residual noise with bandpass filter' },
  { label: 'Generating spectrograms', detail: 'Creating before & after visualizations' },
  { label: 'Computing SNR', detail: 'Measuring signal-to-noise ratio improvement' },
]

export default function DemoUpload() {
  const navigate = useNavigate()
  const apiUrl = import.meta.env.VITE_API_URL
  const fileInputRef = useRef(null)

  const [phase, setPhase] = useState('upload') // upload | processing | results
  const [dragOver, setDragOver] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [snrExpanded, setSnrExpanded] = useState(false)

  const resolveAssetUrl = useCallback((path) => {
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return `${apiUrl}${path}`
  }, [apiUrl])

  const processFile = useCallback(async (file) => {
    setPhase('processing')
    setCurrentStep(0)
    setError(null)

    // Animate steps while processing happens
    const stepTimer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < PIPELINE_STEPS.length - 2) return prev + 1
        return prev
      })
    }, 1800)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${apiUrl}/process`, { method: 'POST', body: formData })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `Server error ${res.status}`)
      }
      const data = await res.json()

      clearInterval(stepTimer)

      // Finish remaining steps quickly
      for (let i = currentStep; i < PIPELINE_STEPS.length; i++) {
        await new Promise((r) => setTimeout(r, 300))
        setCurrentStep(i)
      }
      setCurrentStep(PIPELINE_STEPS.length)

      await new Promise((r) => setTimeout(r, 600))
      setResults(data)
      setPhase('results')
    } catch (err) {
      clearInterval(stepTimer)
      setError(err.message)
      setPhase('upload')
    }
  }, [apiUrl])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.toLowerCase().endsWith('.wav')) {
      processFile(file)
    } else {
      setError('Please drop a .wav file')
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) processFile(file)
  }

  const reset = () => {
    setPhase('upload')
    setResults(null)
    setError(null)
    setCurrentStep(0)
  }

  // ── Upload Screen ──
  if (phase === 'upload') {
    return (
      <div className="demo-upload-page">
        <nav className="demo-nav">
          <div className="nav-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <div className="nav-logo-mark">~</div>
            <span>Echo<em>Map</em></span>
          </div>
          <span className="demo-nav-title">Live Processing Demo</span>
        </nav>

        <div className="demo-upload-content">
          <h1>Test our pipeline <em>in real time</em></h1>
          <p className="demo-upload-sub">
            Drop an elephant field recording and watch HPSS separate calls from noise — no ML models, pure signal processing.
          </p>

          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="drop-zone-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="drop-zone-main">Drop a <strong>.wav</strong> recording</p>
            <p className="drop-zone-hint">or click to browse</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".wav"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          {error && <p className="demo-error">{error}</p>}
        </div>
      </div>
    )
  }

  // ── Processing Screen ──
  if (phase === 'processing') {
    return (
      <div className="demo-upload-page">
        <nav className="demo-nav">
          <div className="nav-logo">
            <div className="nav-logo-mark">~</div>
            <span>Echo<em>Map</em></span>
          </div>
          <span className="demo-nav-title">Processing...</span>
        </nav>

        <div className="demo-processing">
          <h2>Analyzing recording</h2>
          <p className="demo-processing-sub">Running 6-stage HPSS pipeline</p>

          <div className="pipeline-steps">
            {PIPELINE_STEPS.map((step, i) => {
              const done = i < currentStep
              const active = i === currentStep
              return (
                <div key={i} className={`pipeline-step ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
                  <div className="step-indicator">
                    {done ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : active ? (
                      <div className="step-spinner" />
                    ) : (
                      <div className="step-dot" />
                    )}
                  </div>
                  <div className="step-text">
                    <span className="step-label">{step.label}</span>
                    <span className="step-detail">{step.detail}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // ── Results Screen ──
  if (phase === 'results' && results) {
    const improvement = results.snr_improvement_db
    return (
      <div className="demo-upload-page">
        <nav className="demo-nav">
          <div className="nav-logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <div className="nav-logo-mark">~</div>
            <span>Echo<em>Map</em></span>
          </div>
          <button className="btn btn-outline" onClick={reset}>Try another</button>
        </nav>

        <div className="demo-results">
          <h2>Results</h2>
          <p className="demo-results-filename">{results.call_id_csv}</p>

          {/* SNR Metrics */}
          <div className="snr-metrics">
            <div className="snr-card">
              <span className="snr-label">Before</span>
              <span className="snr-value">{results.snr_before_db?.toFixed(1)} dB</span>
            </div>
            <div className="snr-arrow">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </div>
            <div className="snr-card">
              <span className="snr-label">After</span>
              <span className="snr-value snr-after">{results.snr_after_db?.toFixed(1)} dB</span>
            </div>
            <div className="snr-card snr-improvement-card">
              <span className="snr-label">Improvement</span>
              <span className="snr-value snr-green">+{improvement?.toFixed(1)} dB</span>
            </div>
          </div>

          {/* SNR Explainer */}
          <button className="snr-explainer-toggle" onClick={() => setSnrExpanded(!snrExpanded)}>
            What is SNR? {snrExpanded ? '\u25B2' : '\u25BC'}
          </button>
          {snrExpanded && (
            <div className="snr-explainer">
              <strong>Signal-to-Noise Ratio (SNR)</strong> measures how much louder the elephant call
              is compared to background noise, in decibels (dB). Higher is better. Our HPSS pipeline
              improved this recording by <strong>+{improvement?.toFixed(1)} dB</strong> — meaning the
              elephant call is now {Math.round(Math.pow(10, (improvement || 0) / 20))}x louder
              relative to the noise floor.
            </div>
          )}

          {/* Spectrograms */}
          <div className="demo-spectrograms">
            <div className="demo-spec-col">
              <h3>Before (noisy)</h3>
              <img src={resolveAssetUrl(results.spectrogram_before_url)} alt="Spectrogram before" />
            </div>
            <div className="demo-spec-col">
              <h3>After (cleaned)</h3>
              <img src={resolveAssetUrl(results.spectrogram_after_url)} alt="Spectrogram after" />
            </div>
          </div>

          {/* Audio Players */}
          <div className="demo-audio-players">
            <div className="audio-player-card">
              <label>Original (noisy)</label>
              <audio controls src={resolveAssetUrl(results.audio_original_url)} />
            </div>
            <div className="audio-player-card audio-player-clean">
              <label>Cleaned</label>
              <audio controls src={resolveAssetUrl(results.audio_cleaned_url)} />
            </div>
          </div>

          {/* Extra info */}
          <div className="demo-extra-stats">
            <span>{results.call_count} call{results.call_count !== 1 ? 's' : ''} detected</span>
            <span>Duration: {results.duration_seconds?.toFixed(1)}s</span>
            <span>Detection: {results.detection_method}</span>
          </div>
        </div>
      </div>
    )
  }

  return null
}
