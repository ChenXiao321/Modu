import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import DocumentUploadPage from './features/documents/pages/DocumentUploadPage'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DocumentUploadPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
