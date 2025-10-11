import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { FileText, Home, Upload } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import UploadResume from './pages/UploadResume'
import ResumeDetail from './pages/ResumeDetail'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <FileText className="h-8 w-8 text-blue-600" />
                  <span className="ml-2 text-xl font-bold text-gray-900">
                    Resume Processor
                  </span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  >
                    <Home className="h-4 w-4 mr-1" />
                    Dashboard
                  </Link>
                  <Link
                    to="/upload"
                    className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  >
                    <Upload className="h-4 w-4 mr-1" />
                    Upload Resume
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<UploadResume />} />
            <Route path="/resumes/:id" element={<ResumeDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
