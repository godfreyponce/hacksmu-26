import { useState, useEffect, useRef } from 'react'
import { Zap, TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function RadialOrbitalTimeline({ timelineData, onCategorySelect }) {
  const [expandedId, setExpandedId] = useState(null)
  const [rotationAngle, setRotationAngle] = useState(0)
  const [autoRotate, setAutoRotate] = useState(true)
  const containerRef = useRef(null)

  const handleBackgroundClick = (e) => {
    if (e.target === containerRef.current || e.target.classList.contains('orb-stage')) {
      setExpandedId(null)
      setAutoRotate(true)
      onCategorySelect?.(null)
    }
  }

  const selectNode = (id) => {
    if (expandedId === id) {
      setExpandedId(null)
      setAutoRotate(true)
      onCategorySelect?.(null)
    } else {
      const item = timelineData.find((d) => d.id === id)
      setExpandedId(id)
      setAutoRotate(false)
      onCategorySelect?.(item?.category || null)
      centerOnNode(id)
    }
  }

  useEffect(() => {
    if (!autoRotate) return
    const timer = setInterval(() => {
      setRotationAngle((prev) => (prev + 0.15) % 360)
    }, 40)
    return () => clearInterval(timer)
  }, [autoRotate])

  const centerOnNode = (id) => {
    const idx = timelineData.findIndex((d) => d.id === id)
    const target = (idx / timelineData.length) * 360
    setRotationAngle(270 - target)
  }

  const getPosition = (index, total) => {
    const angle = ((index / total) * 360 + rotationAngle) % 360
    const rad = (angle * Math.PI) / 180
    const radius = 140
    return {
      x: radius * Math.cos(rad),
      y: radius * Math.sin(rad),
      z: Math.round(50 + 30 * Math.cos(rad)),
      opacity: 0.5 + 0.5 * ((1 + Math.sin(rad)) / 2),
    }
  }

  const getColor = (cat) => {
    const colors = { rumble: '#7ec8a0', bark: '#f59e0b', roar: '#ef4444', trumpet: '#3b82f6' }
    return colors[cat] || '#7ec8a0'
  }

  const TrendIcon = ({ trend }) => {
    if (trend === 'up') return <TrendingUp size={11} className="orb-trend-up" />
    if (trend === 'down') return <TrendingDown size={11} className="orb-trend-down" />
    return <Minus size={11} className="orb-trend-flat" />
  }

  return (
    <div className="orb-container" ref={containerRef} onClick={handleBackgroundClick}>
      <div className="orb-stage">
        {/* Center core */}
        <div className="orb-core">
          <div className="orb-core-pulse" />
          <div className="orb-core-inner">~</div>
        </div>

        {/* Orbital rings */}
        <div className="orb-ring orb-ring-1" />
        <div className="orb-ring orb-ring-2" />

        {/* Nodes */}
        {timelineData.map((item, idx) => {
          const pos = getPosition(idx, timelineData.length)
          const isActive = expandedId === item.id
          const color = getColor(item.category)
          const Icon = item.icon

          return (
            <div
              key={item.id}
              className={`orb-node ${isActive ? 'is-active' : ''}`}
              style={{
                transform: `translate(${pos.x}px, ${pos.y}px)`,
                zIndex: isActive ? 100 : pos.z,
                opacity: isActive ? 1 : pos.opacity,
              }}
              onClick={(e) => { e.stopPropagation(); selectNode(item.id) }}
            >
              <div
                className="orb-node-circle"
                style={{
                  borderColor: color,
                  backgroundColor: isActive ? color : 'transparent',
                  boxShadow: isActive ? `0 0 16px ${color}66` : 'none',
                }}
              >
                <Icon size={18} style={{ color: isActive ? '#0a0a0a' : color }} />
              </div>
              <span className="orb-node-label" style={{ color: isActive ? color : 'rgba(255,255,255,0.6)' }}>
                {item.title}
              </span>

              {isActive && (
                <div className="orb-tooltip" onClick={(e) => e.stopPropagation()}>
                  <div className="orb-tooltip-header">
                    <span
                      className="orb-tooltip-status"
                      style={{
                        backgroundColor: item.status === 'high' ? '#22c55e' : item.status === 'medium' ? '#f59e0b' : '#64748b',
                      }}
                    >
                      {item.status === 'high' ? 'HIGH' : item.status === 'medium' ? 'MED' : 'LOW'}
                    </span>
                    <TrendIcon trend={item.trend} />
                  </div>
                  <h4 className="orb-tooltip-title">{item.title}</h4>
                  <p className="orb-tooltip-desc">{item.content}</p>
                  <div className="orb-tooltip-stats">
                    <div>
                      <span>Detections</span>
                      <strong style={{ color }}>{item.detections}</strong>
                    </div>
                    <div>
                      <span>Confidence</span>
                      <strong>{item.confidence}%</strong>
                    </div>
                  </div>
                  <div className="orb-tooltip-bar">
                    <div className="orb-tooltip-bar-label">
                      <Zap size={10} />
                      <span>Density</span>
                      <span>{item.energy}%</span>
                    </div>
                    <div className="orb-tooltip-bar-track">
                      <div className="orb-tooltip-bar-fill" style={{ width: `${item.energy}%`, backgroundColor: color }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
