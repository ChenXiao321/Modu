import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import DocumentUploadPage from './features/documents/pages/DocumentUploadPage'
import DocumentListPage from './features/documents/pages/DocumentListPage'
import RequirementViewerPage from './features/documents/pages/RequirementViewerPage'
import DesignDocumentPage from './features/documents/pages/DesignDocumentPage'
import DesignReviewPage from './features/documents/pages/DesignReviewPage'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DocumentUploadPage />} />
        <Route path="/documents" element={<DocumentListPage />} />
        <Route path="/documents/:documentId/requirements" element={<RequirementViewerPage />} />
        <Route path="/documents/:documentId/design" element={<DesignDocumentPage />} />
        <Route path="/documents/:documentId/design-review" element={<DesignReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
