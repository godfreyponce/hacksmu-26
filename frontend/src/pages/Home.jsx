import { useNavigate } from 'react-router-dom'
import LandingPage from '../components/LandingPage'
import DemoShowcase from '../components/DemoShowcase'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="home-page">
      <LandingPage />
      <DemoShowcase />
      <div className="landing-cta">
        <h3>
          Ready to <em>listen differently?</em>
        </h3>
        <p>Open the full dashboard for cleaned audio, spectrograms, and call classification.</p>
        <button className="btn btn-primary" onClick={() => navigate('/research')}>
          Open dashboard
        </button>
      </div>
    </div>
  )
}
