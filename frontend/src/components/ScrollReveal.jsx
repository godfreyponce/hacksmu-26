// Sticky canvas, noisy → clean transition

import { useRef } from 'react'
import useScrollReveal from '../hooks/useScrollReveal'

export default function ScrollReveal() {
  const containerRef = useRef(null)
  const progress = useScrollReveal(containerRef)

  return (
    <div ref={containerRef} className="scroll-reveal">
      <canvas
        className="spectrogram-canvas"
        style={{
          // Transition from noisy (0) to clean (1) based on scroll
          filter: `blur(${(1 - progress) * 4}px)`,
          opacity: 0.3 + progress * 0.7
        }}
      />
    </div>
  )
}
