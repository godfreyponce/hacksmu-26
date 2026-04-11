import { useRef } from 'react'
import useScrollReveal from '../hooks/useScrollReveal'

export default function ScrollReveal() {
  const containerRef = useRef(null)
  const progress = useScrollReveal(containerRef)
  const stageLabel =
    progress < 0.33
      ? 'Raw recording - ambient machinery masks elephant fundamentals'
      : progress < 0.66
        ? 'Stage 2 spectral gate - residual broadband noise is suppressed'
        : 'Stage 3 residual cleanup - harmonic lanes become biologically readable'

  return (
    <section ref={containerRef} className="transform-section" id="transform">
      <div className="sticky-container">
        <div className="sticky-inner">
          <div className="transform-canvas-wrap">
            <div className="transform-label">
              <span>Spectrogram · file_07.wav · 0-30 seconds</span>
              <strong className={progress > 0.68 ? 'show' : ''}>Rumble detected · 94% confidence</strong>
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
                  <p>Fundamental: 14 Hz · Harmonics: 28, 42, 56 Hz</p>
                  <small>Single caller · contact rumble · 8.2 seconds duration</small>
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
