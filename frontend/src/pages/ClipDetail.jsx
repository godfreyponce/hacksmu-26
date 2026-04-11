import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import SpecViewer from '../components/SpecViewer'
import ClipPlayer from '../components/ClipPlayer'

export default function ClipDetail() {
  const { id } = useParams()
  const apiUrl = import.meta.env.VITE_API_URL
  const [call, setCall] = useState(null)

  useEffect(() => {
    fetch(`${apiUrl}/calls/${id}`)
      .then((r) => r.json())
      .then((data) => setCall(data))
      .catch((err) => console.error('Failed to fetch call detail:', err))
  }, [apiUrl, id])

  return (
    <div className="clip-detail">
      <h1>Call {id}</h1>
      <SpecViewer call={call} />
      <ClipPlayer call={call} />
    </div>
  )
}
