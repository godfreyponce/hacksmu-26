// Main research view

import SpecViewer from './SpecViewer'
import CallMap from './CallMap'
import VoiceBar from './VoiceBar'

export default function Dashboard() {
  return (
    <div className="dashboard">
      <header>
        <h1>Research Dashboard</h1>
        <VoiceBar />
      </header>
      <main>
        <CallMap />
        <SpecViewer />
      </main>
    </div>
  )
}
