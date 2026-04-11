import { useNavigate } from 'react-router-dom'

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <section className="landing-shell">
      <nav className="landing-nav">
        <div className="nav-logo">
          <div className="nav-logo-mark">~</div>
          <span>
            Echo<em>Map</em>
          </span>
        </div>
        <div className="nav-links">
          <a href="#transform">How it works</a>
          <a href="#science">The science</a>
          <a href="#partners">ElephantVoices</a>
        </div>
        <button className="btn btn-outline" onClick={() => navigate('/research')}>
          Open dashboard
        </button>
      </nav>

      <div className="hero-wrap">
        <div className="hero-bg" aria-hidden="true" />
        <div className="hero-overlay" />
        <div className="hero-content">
          <p className="hero-eyebrow">ELEPHANTVOICES · FIELD RECORDING ANALYSIS</p>
          <h1>
            <span>Hear what the</span>
            <em>noise was hiding</em>
          </h1>
          <p>212 elephant calls, buried beneath generators and traffic. We found every one.</p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={() => navigate('/research')}>
              Explore the data
            </button>
            <a className="btn btn-outline" href="#science">
              The science
            </a>
          </div>
        </div>
        <a className="scroll-hint" href="#transform" aria-label="Scroll to reveal">
          <span>Scroll to reveal</span>
          <i>↓</i>
        </a>
      </div>

      <div className="features" id="science">
        <p className="features-eyebrow">Built for researchers</p>
        <h2>
          From <em>noisy files</em> to research insights
        </h2>
        <p className="features-sub">
          EchoMap processes every clip through spectral gating, classifies harmonic structure with
          Gemini Vision, and maps behavioral patterns across your dataset.
        </p>
      </div>

      <div className="pipeline-grid" id="partners">
        <article>
          <h3>Spectral noise removal</h3>
          <p>Targets the residual floor after HPSS while preserving ultra-low fundamentals.</p>
        </article>
        <article>
          <h3>Gemini Vision classify</h3>
          <p>Reads spectrogram structure to infer call type, harmonics, and caller count.</p>
        </article>
        <article>
          <h3>Interactive call map</h3>
          <p>Explore behavior patterns with stage toggles, map distribution, and voice query.</p>
        </article>
      </div>

      <div className="landing-cta">
        <h3>
          Ready to <em>listen differently?</em>
        </h3>
        <p>Open the full dashboard for cleaned audio, spectrograms, and call classification.</p>
        <button className="btn btn-primary" onClick={() => navigate('/research')}>
          Open dashboard
        </button>
      </div>
    </section>
  )
}
