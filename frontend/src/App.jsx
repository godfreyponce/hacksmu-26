import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Research from './pages/Research'
import ClipDetail from './pages/ClipDetail'
import Demo from './pages/Demo'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/research" element={<Research />} />
        <Route path="/clip/:id" element={<ClipDetail />} />
        <Route path="/demo" element={<Demo />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
