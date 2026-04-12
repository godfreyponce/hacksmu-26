import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SpecViewer from './SpecViewer'
import ClipPlayer from './ClipPlayer'
import OpenSoundDashboard from './OpenSoundDashboard'
import CallAnalysisOverview from './CallAnalysisOverview'
import { fetchJson } from '../lib/api'
import { matchesCategory } from '../lib/callCategories'

function callMatchesSelectedCategory(call, selectedCategory) {
  if (!selectedCategory) return true

  if (matchesCategory(call?.call_type, selectedCategory)) {
    return true
  }

  const nestedCalls = call?.calls || []
  return nestedCalls.some((entry) => matchesCategory(entry?.call_type, selectedCategory))
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [calls, setCalls] = useState([])
  const [stats, setStats] = useState({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
  const [selectedId, setSelectedId] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    const load = async () => {
      const [callsData, statsData] = await Promise.all([
        fetchJson('/calls'),
        fetchJson('/stats')
      ])

      setCalls(callsData)
      setStats(statsData)
      setLoadError('')
      if (callsData.length > 0) {
        setSelectedId(callsData[0].id)
      }
    }

    load().catch((err) => {
      console.error('Dashboard load failed:', err)
      setLoadError(err.message || 'Failed to load dashboard data')
      setCalls([])
      setStats({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
    })
  }, [])

  const filteredCalls = useMemo(() => {
    if (!selectedCategory) return calls
    return calls.filter((call) => callMatchesSelectedCategory(call, selectedCategory))
  }, [calls, selectedCategory])

  useEffect(() => {
    if (!filteredCalls.length) {
      setSelectedId(null)
      return
    }
    const hasSelectedInFiltered = filteredCalls.some((call) => call.id === selectedId)
    if (!hasSelectedInFiltered) {
      setSelectedId(filteredCalls[0].id)
    }
  }, [filteredCalls, selectedId])

  const selectedCall = useMemo(() => filteredCalls.find((call) => call.id === selectedId) ?? null, [filteredCalls, selectedId])

  return (
    <div className="dash-page">
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', cursor: 'pointer' }} onClick={() => navigate('/')}>
          <img
            src="/logo-full.svg"
            alt="EchoMap"
            style={{ height: '54px', width: 'auto', display: 'block' }}
          />
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
          <a href="/#transform" style={{ textDecoration: 'none' }}>How it works</a>
          <a href="/#science" style={{ textDecoration: 'none' }}>The science</a>
          <a href="/#partners" style={{ textDecoration: 'none' }}>ElephantVoices</a>
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
            onClick={() => navigate('/')}
            style={{ fontFamily: 'DM Sans, Avenir Next, sans-serif', fontSize: '14px', padding: '12px 22px' }}
          >
            Back To Home
          </button>
        </div>
      </div>

      {/* Page header */}
      <header className="dash-hero">
        <p className="dash-hero-eyebrow">Research Dashboard</p>
        <h1>Call <em>Analysis</em></h1>
        <p className="dash-hero-sub">
          Real-time classification of processed elephant vocalizations with spectral analysis.
        </p>
      </header>

      {loadError && (
        <div className="dash-error">
          <p>{loadError}</p>
        </div>
      )}

      {/* Metrics overview */}
      <CallAnalysisOverview calls={calls} stats={stats} />

      {/* Main content grid */}
      <div className="dash-content">
        {/* Left panel: call list */}
        <aside className="dash-sidebar">
          <div className="dash-sidebar-header">
            <h3>Recordings</h3>
            {selectedCategory && (
              <span className="dash-filter-badge">{selectedCategory}</span>
            )}
          </div>
          <div className="dash-call-list">
            {filteredCalls.map((call) => (
              <button
                key={call.id}
                className={`dash-call-item ${call.id === selectedId ? 'is-active' : ''}`}
                onClick={() => setSelectedId(call.id)}
              >
                <span className="dash-call-name">{call.call_id_csv}</span>
                <span className="dash-call-type">{call.call_type || 'unknown'}</span>
              </button>
            ))}
            {!filteredCalls.length && (
              <p className="dash-empty-msg">No calls match "{selectedCategory}"</p>
            )}
          </div>
        </aside>

        {/* Center: Orbital visualization */}
        <div className="dash-orbital-container">
          <OpenSoundDashboard onCategorySelect={setSelectedCategory} />
        </div>

        {/* Right panel: Analysis */}
        <div className="dash-analysis">
          <SpecViewer call={selectedCall} />
          <ClipPlayer call={selectedCall} />
        </div>
      </div>
    </div>
  )
}
