import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const PIPELINE_STEPS = [
  { label: 'Loading audio', detail: 'Reading WAV file and detecting sample rate' },
  { label: 'Structural separation (HPSS)', detail: 'Exploiting that elephant calls are harmonic (horizontal bands) while noise is broadband' },
  { label: 'Spectral subtraction', detail: 'Removing residual broadband noise from the harmonic component' },
  { label: 'Bandpass filtering', detail: 'Isolating 8–1200 Hz range where elephant vocalizations live' },
  { label: 'Generating spectrograms', detail: 'Creating before & after frequency visualizations' },
  { label: 'Computing in-call energy ratio', detail: 'Proxy metric — no clean reference exists for true SNR' },
]

function formatTime(seconds) {
  if (seconds == null) return '--'
  const m = Math.floor(seconds / 60)
  const s = (seconds % 60).toFixed(1)
  return `${m}:${s.padStart(4, '0')}`
}

export default function DemoUpload() {
  const navigate = useNavigate()
  const apiUrl = import.meta.env.VITE_API_URL
  const fileInputRef = useRef(null)

  const [phase, setPhase] = useState('upload')
  const [dragOver, setDragOver] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [snrExpanded, setSnrExpanded] = useState(false)
  const [specView, setSpecView] = useState('after')

  const resolveAssetUrl = useCallback((path) => {
    if (!path) return ''
    if (path.startsWith('http://') || path.startsWith('https://')) return path
    return `${apiUrl}${path}`
  }, [apiUrl])

  const processFile = useCallback(async (file) => {
    setPhase('processing')
    setCurrentStep(0)
    setError(null)

    const stepTimer = setInterval(() => {
      setCurrentStep((prev) => (prev < PIPELINE_STEPS.length - 2 ? prev + 1 : prev))
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
      for (let i = 0; i < PIPELINE_STEPS.length; i++) {
        await new Promise((r) => setTimeout(r, 250))
        setCurrentStep(i + 1)
      }
      await new Promise((r) => setTimeout(r, 500))
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
    setSpecView('after')
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
            Elephant field recordings from Amboseli are buried in generator, vehicle, and aircraft noise.
            Drop a recording and watch our HPSS pipeline separate calls from noise — pure signal processing, no ML models.
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

          <p className="demo-upload-footer">
            Runs a 6-stage pipeline: Load → Noise Profile → HPSS → Spectral Gate → Spectrogram → Energy-ratio check
          </p>

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
          <h2>Processing on server...</h2>
          <p className="demo-processing-sub">Running 6-stage HPSS pipeline</p>
          <p className="demo-processing-sub" style={{ opacity: 0.6, fontSize: '0.85em' }}>
            Steps shown are illustrative — processing runs server-side.
          </p>

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
    const calls = results.calls || []

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
          {/* Header */}
          <div className="demo-results-header">
            <div>
              <h2>Analysis Complete</h2>
              <p className="demo-results-filename">{results.call_id_csv}</p>
            </div>
            <div className="demo-results-pipeline-tag">
              HPSS → Spectral Gate → Bandpass
            </div>
          </div>

          {/* In-call Energy Ratio (proxy for cleanup — not a true SNR) */}
          <h3 style={{ margin: '1.5rem 0 0.5rem', fontSize: '1rem', opacity: 0.85 }}>
            In-call vs out-of-call energy ratio <span style={{ opacity: 0.6 }}>(proxy for cleanup)</span>
          </h3>
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

          {/* Honest explainer */}
          <button className="snr-explainer-toggle" onClick={() => setSnrExpanded(!snrExpanded)}>
            What does this ratio mean? {snrExpanded ? '\u25B2' : '\u25BC'}
          </button>
          {snrExpanded && (
            <div className="snr-explainer">
              We measure the ratio of RMS energy during labeled call windows vs. the rest of the
              recording, in dB. It's a useful <strong>proxy</strong> for how much the background was
              cleaned up, but it is <strong>not a true SNR</strong> — that would require a clean
              reference recording, which we don't have for field data. A rising ratio can mean
              cleaner background <em>or</em> more aggressive attenuation — inspect the audio and
              spectrogram before drawing conclusions. For this recording, the background floor
              during out-of-call gaps was suppressed by roughly
              <strong> +{improvement?.toFixed(1)} dB</strong> relative to the call windows.
            </div>
          )}

          {/* Spectrogram with toggle */}
          <div className="demo-spec-section">
            <div className="demo-spec-header">
              <h3>Spectrogram</h3>
              <div className="demo-spec-toggle">
                <button className={specView === 'before' ? 'active' : ''} onClick={() => setSpecView('before')}>
                  Before (noisy)
                </button>
                <button className={specView === 'after' ? 'active' : ''} onClick={() => setSpecView('after')}>
                  After (cleaned)
                </button>
              </div>
            </div>
            <img
              className="demo-spec-image"
              src={resolveAssetUrl(specView === 'before' ? results.spectrogram_before_url : results.spectrogram_after_url)}
              alt={`Spectrogram ${specView}`}
            />
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

          {/* Detected Calls Table */}
          {calls.length > 0 && (
            <div className="demo-calls-section">
              <div className="demo-calls-header">
                <h3>Detected Calls</h3>
                <span className="demo-calls-badge">{calls.length} call{calls.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="demo-calls-table-wrap">
                <table className="demo-calls-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Type</th>
                      <th>Start</th>
                      <th>End</th>
                      <th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {calls.map((call, i) => (
                      <tr key={i}>
                        <td className="call-num">{i + 1}</td>
                        <td><span className="call-type-tag">{call.call_type || 'unknown'}</span></td>
                        <td className="call-time">{formatTime(call.start_time)}</td>
                        <td className="call-time">{formatTime(call.end_time)}</td>
                        <td className="call-time">{call.start_time != null && call.end_time != null ? `${(call.end_time - call.start_time).toFixed(1)}s` : '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Extra stats */}
          <div className="demo-extra-stats">
            <span>Duration: {results.duration_seconds?.toFixed(1)}s</span>
            <span>Detection: {results.detection_method === 'auto' ? 'auto (HPSS harmonic energy)' : 'labeled (CSV timestamps)'}</span>
            <span>No ML models — pure DSP</span>
          </div>

          {/* Bottom CTA */}
          <div className="demo-bottom-cta">
            <button className="btn btn-primary" onClick={reset}>Process another recording</button>
            <button className="btn btn-outline" onClick={() => navigate('/research')}>Explore full dataset</button>
          </div>
        </div>
      </div>
    )
  }

  return null
}
