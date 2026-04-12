import { useRef } from 'react'
import useScrollReveal from '../hooks/useScrollReveal'

export default function ScrollReveal() {
  const containerRef = useRef(null)
  const progress = useScrollReveal(containerRef)
  const stageLabel =
    progress < 0.33
      ? 'Raw recording — ambient machinery masks elephant fundamentals'
      : progress < 0.66
        ? 'After HPSS — harmonic bands isolated from broadband noise'
        : 'After spectral gate + bandpass — elephant-band output'

  return (
    <section ref={containerRef} className="transform-section" id="transform">
      <div className="sticky-container">
        <div className="sticky-inner">
          <div className="transform-canvas-wrap">
            <div className="transform-label">
              <span>Spectrogram · illustrative example · 0-30 seconds</span>
              <strong className={progress > 0.68 ? 'show' : ''}>Harmonic bands emerge from the noise floor</strong>
            </div>

            <div className="transform-canvas-border">
              <div
                className="spectrogram-canvas"
                style={{
                  filter: `blur(${(1 - progress) * 10}px)`,
                  opacity: 0.15 + progress * 0.85
                }}
              />
              <div className={`clean-overlay-text ${progress > 0.72 ? 'show' : ''}`}>
                <div className="cot-inner">
                  <p>Low-frequency harmonic bands isolated · broadband hum suppressed</p>
                  <small>Illustrative example · rumbles live in the 10–200 Hz region</small>
                </div>
              </div>
            </div>

            <div className="progress-bar-wrap">
              <div className="progress-bar" style={{ width: `${progress * 100}%` }} />
            </div>

            <p className="stage-caption">{stageLabel}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
