import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import SpecViewer from '../components/SpecViewer'
import ClipPlayer from '../components/ClipPlayer'
import { fetchJson } from '../lib/api'

export default function ClipDetail() {
  const { id } = useParams()
  const [call, setCall] = useState(null)

  useEffect(() => {
    fetchJson(`/calls/${id}`)
      .then((data) => setCall(data))
      .catch((err) => console.error('Failed to fetch call detail:', err))
  }, [id])

  return (
    <div className="clip-detail">
      <h1>Call {id}</h1>
      <SpecViewer call={call} />
      <ClipPlayer call={call} />
    </div>
  )
}
