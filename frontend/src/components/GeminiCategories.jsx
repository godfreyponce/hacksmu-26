import { useMemo } from 'react'

const CATEGORY_COLORS = {
  rumble: '#7ec8a0',
  roar: '#f59e0b',
  trumpet: '#3b82f6',
  contact: '#a855f7',
  unknown: 'rgba(232, 237, 229, 0.4)'
}

const CATEGORY_ICONS = {
  rumble: '~',
  roar: '!',
  trumpet: '^',
  contact: '*',
  unknown: '?'
}

export default function GeminiCategories({ stats, selectedCall }) {
  const byType = stats?.by_call_type || {}
  const total = stats?.total_calls || 0
  const avgConfidence = stats?.avg_confidence || 0

  const categories = useMemo(() => {
    const ordered = ['rumble', 'roar', 'trumpet', 'contact', 'unknown']
    return ordered.map((type) => ({
      type,
      count: byType[type] || 0,
      pct: total > 0 ? ((byType[type] || 0) / total) * 100 : 0,
      color: CATEGORY_COLORS[type],
      icon: CATEGORY_ICONS[type]
    }))
  }, [byType, total])

  const dominant = useMemo(() => {
    if (total === 0) return null
    return categories.reduce((max, cat) => (cat.count > max.count ? cat : max), categories[0])
  }, [categories, total])

  return (
    <div className="gemini-categories">
      <div className="gemini-header">
        <div className="gemini-title">
          <span className="gemini-eyebrow">Gemini Vision Classification</span>
          <h2>Call Categories</h2>
        </div>
        {dominant && (
          <div className="gemini-dominant">
            <span className="dominant-label">Dominant</span>
            <span className="dominant-type" style={{ color: dominant.color }}>
              {dominant.type}
            </span>
          </div>
        )}
      </div>

      <div className="gemini-bars">
        {categories.map((cat) => (
          <div key={cat.type} className="category-row">
            <div className="category-label">
              <span className="category-icon" style={{ color: cat.color }}>
                {cat.icon}
              </span>
              <span className="category-name">{cat.type}</span>
              <span className="category-count">{cat.count}</span>
            </div>
            <div className="category-bar-track">
              <div
                className="category-bar-fill"
                style={{
                  width: `${cat.pct}%`,
                  background: cat.color
                }}
              />
            </div>
            <span className="category-pct">{cat.pct.toFixed(0)}%</span>
          </div>
        ))}
      </div>

      <div className="gemini-stats-row">
        <div className="gemini-stat-card">
          <span className="stat-value">{total}</span>
          <span className="stat-label">Total Calls</span>
        </div>
        <div className="gemini-stat-card">
          <span className="stat-value">{(avgConfidence * 100).toFixed(0)}%</span>
          <span className="stat-label">Avg Confidence</span>
        </div>
        <div className="gemini-stat-card">
          <span className="stat-value">{Object.keys(byType).length}</span>
          <span className="stat-label">Types Found</span>
        </div>
      </div>

      {selectedCall && (
        <div className="gemini-selected">
          <div className="selected-header">
            <span className="selected-eyebrow">Selected Call</span>
            <span className="selected-id">{selectedCall.call_id_csv}</span>
          </div>
          <div className="selected-details">
            <div className="detail-item">
              <span className="detail-label">Type</span>
              <span
                className="detail-value type-badge"
                style={{ color: CATEGORY_COLORS[selectedCall.call_type] || CATEGORY_COLORS.unknown }}
              >
                {selectedCall.call_type || 'unknown'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Confidence</span>
              <span className="detail-value">
                {((selectedCall.confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Fundamental</span>
              <span className="detail-value">
                {selectedCall.fundamental_hz ? `${selectedCall.fundamental_hz} Hz` : '—'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">SNR Gain</span>
              <span className="detail-value snr-gain">
                +{(selectedCall.snr_improvement_db || 0).toFixed(1)} dB
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
