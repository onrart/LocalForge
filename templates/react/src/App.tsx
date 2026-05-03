import { Routes, Route } from 'react-router-dom'

function Home() {
  return (
    <div>
      <h1>{project_name}</h1>
      <p>Uygulama başarıyla çalışıyor.</p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  )
}
