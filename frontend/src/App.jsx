import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Research from './pages/Research'
import ClipDetail from './pages/ClipDetail'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/research" element={<Research />} />
        <Route path="/clip/:id" element={<ClipDetail />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
