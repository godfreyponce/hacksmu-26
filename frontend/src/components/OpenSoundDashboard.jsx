import { useState, useEffect, useMemo } from 'react'
import { Waves, Volume2, AlertTriangle, Music } from 'lucide-react'
import RadialOrbitalTimeline from '@/components/ui/radial-orbital-timeline'
import { fetchJson } from '../lib/api'
import { countCategoryMentions } from '../lib/callCategories'

const SOUND_ICONS = {
  rumble: Waves,
  bark: Volume2,
  roar: AlertTriangle,
  trumpet: Music,
}

export default function OpenSoundDashboard({ onCategorySelect }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchJson('/stats')
      .then((data) => {
        setStats(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to load stats:', err)
        setStats({ total_calls: 0, avg_confidence: 0, by_call_type: {} })
        setLoading(false)
      })
  }, [])

  const orbitalData = useMemo(() => {
    const byType = stats?.by_call_type || {}
    const total = stats?.total_calls || 0
    const avgConf = stats?.avg_confidence || 0

    const categories = [
      {
        id: 1,
        category: 'rumble',
        title: 'Rumble',
        content: 'Low-frequency infrasonic calls for long-distance communication.',
        relatedIds: [4],
        trend: 'up',
      },
      {
        id: 2,
        category: 'bark',
        title: 'Bark',
        content: 'Short, sharp vocalizations used in alarm contexts.',
        relatedIds: [3],
        trend: 'stable',
      },
      {
        id: 3,
        category: 'roar',
        title: 'Roar',
        content: 'Powerful broadband calls expressing aggression or distress.',
        relatedIds: [2],
        trend: 'down',
      },
      {
        id: 4,
        category: 'trumpet',
        title: 'Trumpet',
        content: 'High-frequency calls produced through the trunk.',
        relatedIds: [1],
        trend: 'up',
      },
    ]

    return categories.map((cat) => {
      const count = countCategoryMentions(byType, cat.category)
      const pct = total > 0 ? Math.round((count / total) * 100) : 0

      let status = 'low'
      if (count > 50) status = 'high'
      else if (count > 10) status = 'medium'

      return {
        ...cat,
        icon: SOUND_ICONS[cat.category],
        date: 'LIVE',
        status,
        energy: Math.min(100, pct * 2 + 20),
        detections: count,
        confidence: Math.round(avgConf * 100) || 78,
      }
    })
  }, [stats])

  if (loading) {
    return (
      <div className="orbital-loader">
        <div className="orbital-loader-spinner" />
        <span>Loading...</span>
      </div>
    )
  }

  return (
    <div className="orbital-module">
      <div className="orbital-module-header">
        <span className="orbital-module-label">Sound Classification</span>
        <span className="orbital-module-hint">Click a category to filter</span>
      </div>
      <RadialOrbitalTimeline timelineData={orbitalData} onCategorySelect={onCategorySelect} />
    </div>
  )
}
