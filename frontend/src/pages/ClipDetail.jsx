import { useParams } from 'react-router-dom'
import SpecViewer from '../components/SpecViewer'
import ClipPlayer from '../components/ClipPlayer'

export default function ClipDetail() {
  const { id } = useParams()

  return (
    <div className="clip-detail">
      <h1>Call {id}</h1>
      <SpecViewer callId={id} />
      <ClipPlayer callId={id} />
    </div>
  )
}
