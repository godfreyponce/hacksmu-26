import { useMemo } from 'react'
import { Activity, TrendingUp, BarChart3 } from 'lucide-react'

export default function CallAnalysisOverview({ calls, stats }) {
  const totalCalls = stats?.total_calls || 0

  const avgDelta = useMemo(() => {
    if (!calls?.length) return 0
    const values = calls
      .map((c) => Number(c.snr_improvement_db))
      .filter((v) => Number.isFinite(v))
    if (!values.length) return 0
    return values.reduce((s, v) => s + v, 0) / values.length
  }, [calls])

  const typeRows = useMemo(() => {
    const byType = stats?.by_call_type || {}
    return Object.entries(byType)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([type, count]) => ({ type, count }))
  }, [stats])

  return (
    <section className="metrics-grid">
      <article className="metric-card">
        <div className="metric-icon">
          <Activity size={20} />
        </div>
        <div className="metric-body">
          <span className="metric-label">Total Calls</span>
          <span className="metric-value">{totalCalls}</span>
        </div>
      </article>

      <article className="metric-card">
        <div className="metric-icon">
          <TrendingUp size={20} />
        </div>
        <div className="metric-body">
          <span className="metric-label">Avg SNR Δ</span>
          <span className="metric-value">{avgDelta >= 0 ? '+' : ''}{avgDelta.toFixed(1)} dB</span>
        </div>
      </article>

      <article className="metric-card metric-card-wide">
        <div className="metric-icon">
          <BarChart3 size={20} />
        </div>
        <div className="metric-body">
          <span className="metric-label">Type Distribution</span>
          <div className="metric-types">
            {typeRows.length === 0 && <span className="metric-type-empty">No data</span>}
            {typeRows.map((row) => (
              <span key={row.type} className="metric-type-tag">
                {row.type} <strong>{row.count}</strong>
              </span>
            ))}
          </div>
        </div>
      </article>
    </section>
  )
}
