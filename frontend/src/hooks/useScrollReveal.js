// Scroll progress 0–1

import { useState, useEffect } from 'react'

export default function useScrollReveal(containerRef) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return

      const rect = containerRef.current.getBoundingClientRect()
      const windowHeight = window.innerHeight

      const start = windowHeight
      const end = -rect.height
      const current = rect.top

      const rawProgress = (start - current) / (start - end)
      setProgress(Math.max(0, Math.min(1, rawProgress)))
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()

    return () => window.removeEventListener('scroll', handleScroll)
  }, [containerRef])

  return progress
}
