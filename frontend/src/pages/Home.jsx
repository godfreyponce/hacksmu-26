import LandingPage from '../components/LandingPage'
import ScrollReveal from '../components/ScrollReveal'
import DemoShowcase from '../components/DemoShowcase'

export default function Home() {
  return (
    <div className="home-page">
      <LandingPage />
      <ScrollReveal />
      <DemoShowcase />
    </div>
  )
}
