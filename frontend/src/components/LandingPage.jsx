import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatedHero } from '@/components/ui/animated-hero'

const fadeIn = (progress, start, peak) => Math.max(0, Math.min(1, (progress - start) / (peak - start)))
const fadeOut = (progress, peak, end) => Math.max(0, Math.min(1, 1 - (progress - peak) / (end - peak)))
const clamp = (value, min, max) => Math.max(min, Math.min(max, value))
const WHEEL_SCRUB_SPEED = 0.00045
const TOUCH_SCRUB_SPEED = 0.0007
const KEY_SCRUB_STEP = 0.025

export default function LandingPage() {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const metadataReadyRef = useRef(false)
  const progressRef = useRef(0)
  const touchStartRef = useRef(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return undefined

    const onLoadedMetadata = () => {
      metadataReadyRef.current = true
      video.currentTime = progressRef.current * (video.duration || 0)
    }

    video.muted = true
    video.playsInline = true
    video.preload = 'auto'
    video.addEventListener('loadedmetadata', onLoadedMetadata)

    return () => {
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
    }
  }, [])

  useEffect(() => {
    progressRef.current = progress
  }, [progress])

  useEffect(() => {
    const video = videoRef.current
    if (!video || !metadataReadyRef.current || !video.duration) return
    video.currentTime = progress * video.duration
  }, [progress])

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    const previousOverscroll = document.body.style.overscrollBehavior

    if (progress < 1) {
      document.body.style.overflow = 'hidden'
      document.body.style.overscrollBehavior = 'none'
    } else {
      document.body.style.overflow = previousOverflow || 'auto'
      document.body.style.overscrollBehavior = previousOverscroll || 'auto'
    }

    return () => {
      document.body.style.overflow = previousOverflow
      document.body.style.overscrollBehavior = previousOverscroll
    }
  }, [progress])

  useEffect(() => {
    const stepProgress = (delta) => {
      setProgress((prev) => {
        const next = clamp(prev + delta, 0, 1)
        progressRef.current = next
        return next
      })
    }

    const onWheel = (event) => {
      const atTop = window.scrollY <= 2
      const current = progressRef.current

      if (current < 1) {
        event.preventDefault()
        stepProgress(event.deltaY * WHEEL_SCRUB_SPEED)
        return
      }

      if (atTop && event.deltaY < 0) {
        event.preventDefault()
        stepProgress(event.deltaY * WHEEL_SCRUB_SPEED)
      }
    }

    const onTouchStart = (event) => {
      if (event.touches.length > 0) {
        touchStartRef.current = event.touches[0].clientY
      }
    }

    const onTouchMove = (event) => {
      if (touchStartRef.current == null || event.touches.length === 0) return

      const currentY = event.touches[0].clientY
      const deltaY = touchStartRef.current - currentY
      touchStartRef.current = currentY

      const atTop = window.scrollY <= 2
      const current = progressRef.current

      if (current < 1) {
        event.preventDefault()
        stepProgress(deltaY * TOUCH_SCRUB_SPEED)
        return
      }

      if (atTop && deltaY < 0) {
        event.preventDefault()
        stepProgress(deltaY * TOUCH_SCRUB_SPEED)
      }
    }

    const onKeyDown = (event) => {
      const atTop = window.scrollY <= 2
      const current = progressRef.current

      if (['ArrowDown', 'PageDown', ' ', 'Spacebar'].includes(event.key)) {
        if (current >= 1) return
        event.preventDefault()
        stepProgress(KEY_SCRUB_STEP)
      }

      if (['ArrowUp', 'PageUp'].includes(event.key)) {
        if (current >= 1 && !atTop) return
        event.preventDefault()
        stepProgress(-KEY_SCRUB_STEP)
      }
    }

    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: false })
    window.addEventListener('keydown', onKeyDown)

    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  const overlayAOpacity =
    progress < 0.15 ? fadeIn(progress, 0, 0.15) : progress < 0.3 ? fadeOut(progress, 0.15, 0.3) : 0

  const overlayBOpacity =
    progress < 0.45 ? fadeIn(progress, 0.3, 0.45) : progress < 0.65 ? fadeOut(progress, 0.45, 0.65) : 0

  const overlayCOpacity = progress < 0.8 ? fadeIn(progress, 0.65, 0.8) : 1
  const endHeroOpacity = fadeIn(progress, 0.86, 0.98)

  const overlayBaseStyle = {
    position: 'absolute',
    bottom: '11%',
    left: '50%',
    transform: 'translateX(-50%)',
    textAlign: 'center',
    width: 'min(92vw, 900px)',
    transition: 'opacity 120ms linear',
    pointerEvents: 'none',
    textShadow: '0 4px 24px rgba(0,0,0,0.6)'
  }

  const eyebrowStyle = {
    fontFamily: 'DM Sans, Avenir Next, sans-serif',
    fontSize: '12px',
    letterSpacing: '0.18em',
    color: 'rgba(126,200,160,0.92)',
    textTransform: 'uppercase'
  }

  const headingStyle = {
    fontFamily: 'Cormorant Garamond, Georgia, serif',
    fontSize: 'clamp(38px, 5vw, 64px)',
    fontWeight: 500,
    color: '#edf6ea',
    letterSpacing: '-0.02em',
    lineHeight: 1,
    marginTop: '8px'
  }

  const subtextStyle = {
    fontFamily: 'DM Sans, Avenir Next, sans-serif',
    fontSize: '15px',
    color: 'rgba(237,246,234,0.78)',
    marginTop: '10px'
  }

  return (
    <section className="landing-shell">
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          background: '#07110c',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              border: '1px solid rgba(255,255,255,0.12)',
              display: 'grid',
              placeItems: 'center',
              color: '#7ec8a0',
              fontSize: '1.7rem',
              background: 'rgba(255,255,255,0.02)'
            }}
          >
            ~
          </div>
          <div style={{ fontFamily: 'DM Sans, Avenir Next, sans-serif', fontSize: '24px', letterSpacing: '-0.02em' }}>
            Echo
            <em style={{ color: '#7ec8a0', fontFamily: 'Cormorant Garamond, Georgia, serif', fontStyle: 'italic' }}>
              Map
            </em>
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '30px',
            color: 'rgba(232,237,229,0.78)',
            fontFamily: 'DM Sans, Avenir Next, sans-serif',
            fontSize: '14px',
            fontWeight: 700
          }}
        >
          <a href="#transform" style={{ textDecoration: 'none' }}>How it works</a>
          <a href="#science" style={{ textDecoration: 'none' }}>The science</a>
          <a href="#partners" style={{ textDecoration: 'none' }}>ElephantVoices</a>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/demo')}
            style={{ fontFamily: 'DM Sans, Avenir Next, sans-serif', fontSize: '14px', padding: '12px 26px' }}
          >
            Live Demo
          </button>
          <button
            className="btn btn-outline"
            onClick={() => navigate('/research')}
            style={{ fontFamily: 'DM Sans, Avenir Next, sans-serif', fontSize: '14px', padding: '12px 22px' }}
          >
            Open dashboard
          </button>
        </div>
      </div>

      <div id="transform" style={{ height: '100vh', position: 'relative' }}>
        <div style={{ position: 'relative', height: '100vh', overflow: 'hidden' }}>
          <video
            ref={videoRef}
            src="/Address_Me.mp4"
            muted
            playsInline
            preload="auto"
            controls={false}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />

          <div
            style={{
              position: 'absolute',
              inset: 0,
              pointerEvents: 'none',
              background: 'radial-gradient(ellipse at center, transparent 30%, rgba(9,11,8,0.6) 100%)'
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '35%',
              pointerEvents: 'none',
              background: 'linear-gradient(transparent, rgba(9,11,8,0.85))'
            }}
          />

          <div style={{ ...overlayBaseStyle, opacity: overlayAOpacity }}>
            <p style={eyebrowStyle}>FIELD RECORDINGS · AMBOSELI ECOSYSTEM</p>
            <p style={headingStyle}>44 recordings</p>
            <p style={subtextStyle}>Raw audio, buried in mechanical noise</p>
          </div>

          <div style={{ ...overlayBaseStyle, opacity: overlayBOpacity }}>
            <p style={eyebrowStyle}>HPSS · SPECTRAL GATING · RESIDUAL CLEANUP</p>
            <p style={headingStyle}>3-stage denoising</p>
            <p style={subtextStyle}>Separating elephant harmonics from generator hum</p>
          </div>

          <div style={{ ...overlayBaseStyle, opacity: overlayCOpacity }}>
            <p style={eyebrowStyle}>212 CALLS CLASSIFIED · 4 TYPES IDENTIFIED</p>
            <p style={headingStyle}>Every call found</p>
            <p style={subtextStyle}>Rumble · Roar · Trumpet · Contact</p>
          </div>

          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'grid',
              placeItems: 'center',
              pointerEvents: endHeroOpacity > 0.98 ? 'auto' : 'none',
              opacity: endHeroOpacity,
              transition: 'opacity 220ms linear',
              textAlign: 'center',
              padding: '0 24px'
            }}
          >
            <div
              style={{
                width: 'min(92vw, 980px)',
                background: 'rgba(8,12,9,0.52)',
                border: '1px solid rgba(126,200,160,0.22)',
                borderRadius: '16px',
                padding: '34px 20px',
                backdropFilter: 'blur(6px)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.45)'
              }}
            >
              <h1
                style={{
                  fontFamily: 'Cormorant Garamond, Georgia, serif',
                  fontSize: 'clamp(56px, 7vw, 108px)',
                  fontWeight: 500,
                  lineHeight: 0.9,
                  letterSpacing: '-0.02em',
                  color: '#f1f7ee',
                  textShadow: '0 6px 34px rgba(0,0,0,0.65)'
                }}
              >
                <span style={{ display: 'block' }}>Hear what the</span>
                <em style={{ display: 'block', color: '#7ec8a0', fontStyle: 'italic' }}>noise was hiding</em>
              </h1>
              <p
                style={{
                  fontFamily: 'DM Sans, Avenir Next, sans-serif',
                  fontSize: '17px',
                  color: 'rgba(228,237,224,0.84)',
                  marginTop: '16px'
                }}
              >
                212 elephant calls, buried beneath generators and traffic. We found every one.
              </p>
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '22px', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={() => navigate('/demo')}>
                  Try it yourself
                </button>
                <button className="btn btn-outline" onClick={() => navigate('/research')}>
                  Explore the data
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: '20vh', background: 'linear-gradient(rgba(9,11,8,0), #090b08)' }} />

      <div className="features" id="science">
        <p className="features-eyebrow">Built for researchers</p>
        <h2>
          From <em>noisy files</em> to research insights
        </h2>
        <p className="features-sub">
          EchoMap processes every clip through HPSS + per-file spectral subtraction + an 8–1200 Hz
          bandpass, producing cleaned audio, before/after spectrograms, and per-recording metrics
          you can actually inspect.
        </p>
      </div>

      <div className="pipeline-grid" id="partners">
        <article>
          <h3>HPSS structural separation</h3>
          <p>Exploits that rumbles are harmonic horizontal bands while mechanical noise is broadband — no ML model, fully deterministic.</p>
        </article>
        <article>
          <h3>Per-file spectral subtraction</h3>
          <p>Builds a noise fingerprint from each recording's own silent gaps, preserving ultra-low fundamentals down to 8 Hz.</p>
        </article>
        <article>
          <h3>Natural-language query</h3>
          <p>Ask questions in English over the processed-recordings metrics JSON (Gemini-backed chat, no vision classifier).</p>
        </article>
      </div>

      <div style={{
        borderTop: '1px solid rgba(126, 200, 160, 0.15)',
        background: 'linear-gradient(180deg, rgba(13,15,11,0) 0%, rgba(126,200,160,0.03) 100%)'
      }}>
        <AnimatedHero
          onExplore={() => navigate('/demo')}
          onDashboard={() => navigate('/research')}
        />
      </div>
    </section>
  )
}
