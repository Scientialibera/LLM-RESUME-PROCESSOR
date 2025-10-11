import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, CheckCircle, AlertCircle } from 'lucide-react'
import { resumeApi } from '../services/api'

function UploadResume() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
      setSuccess(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setError(null)
      setSuccess(null)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await resumeApi.uploadResume(file)
      setSuccess(`Resume uploaded successfully! ID: ${response.id}`)
      setFile(null)

      // Reset file input
      document.getElementById('file-input').value = ''

      // Redirect to dashboard after 2 seconds
      setTimeout(() => {
        navigate('/')
      }, 2000)
    } catch (err) {
      setError('Failed to upload resume: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center">
        <Upload className="mx-auto h-12 w-12 text-blue-600" />
        <h2 className="mt-2 text-3xl font-bold text-gray-900">Upload Resume</h2>
        <p className="mt-2 text-sm text-gray-600">
          Upload a resume file to process and extract information
        </p>
      </div>

      <div className="mt-8">
        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-gray-400 transition-colors"
        >
          <input
            id="file-input"
            type="file"
            accept=".txt,.pdf,.doc,.docx"
            onChange={handleFileChange}
            className="hidden"
          />

          <label
            htmlFor="file-input"
            className="cursor-pointer"
          >
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm text-gray-600">
              Drag and drop your resume here, or{' '}
              <span className="text-blue-600 hover:text-blue-700 font-medium">
                browse
              </span>
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Supported formats: TXT, PDF, DOC, DOCX
            </p>
          </label>
        </div>

        {/* Selected File */}
        {file && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-blue-600" />
                <span className="ml-2 text-sm font-medium text-blue-900">
                  {file.name}
                </span>
                <span className="ml-2 text-xs text-blue-600">
                  ({(file.size / 1024).toFixed(2)} KB)
                </span>
              </div>
              <button
                onClick={() => setFile(null)}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="flex">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <p className="ml-2 text-sm text-green-800">{success}</p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <p className="ml-2 text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Upload Button */}
        <div className="mt-6 flex justify-center space-x-4">
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className={`px-6 py-2 rounded-md text-sm font-medium text-white ${
              !file || uploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {uploading ? 'Uploading...' : 'Upload Resume'}
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div className="mt-12 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900">What happens next?</h3>
        <ul className="mt-4 space-y-3 text-sm text-gray-600">
          <li className="flex items-start">
            <span className="flex-shrink-0 h-6 w-6 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 font-medium text-xs">
              1
            </span>
            <span className="ml-3">
              Your resume is uploaded to Azure Cosmos DB for secure storage
            </span>
          </li>
          <li className="flex items-start">
            <span className="flex-shrink-0 h-6 w-6 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 font-medium text-xs">
              2
            </span>
            <span className="ml-3">
              Azure OpenAI extracts structured information from your resume
            </span>
          </li>
          <li className="flex items-start">
            <span className="flex-shrink-0 h-6 w-6 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 font-medium text-xs">
              3
            </span>
            <span className="ml-3">
              AI generates a professional summary and suggests potential roles
            </span>
          </li>
          <li className="flex items-start">
            <span className="flex-shrink-0 h-6 w-6 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 font-medium text-xs">
              4
            </span>
            <span className="ml-3">
              PII is removed for privacy-preserving analysis and storage
            </span>
          </li>
        </ul>
      </div>
    </div>
  )
}

export default UploadResume
