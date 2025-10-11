import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Mail, Phone, MapPin, Briefcase, GraduationCap, Award, AlertCircle } from 'lucide-react'
import { resumeApi } from '../services/api'

function ResumeDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [resume, setResume] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadResume()
  }, [id])

  const loadResume = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await resumeApi.getResume(id)
      setResume(data)
    } catch (err) {
      setError('Failed to load resume: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading resume...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="ml-2 text-sm text-red-800">{error}</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/')}
          className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Dashboard
        </button>
      </div>
    )
  }

  const processed = resume?.processed_data
  const personal = processed?.personalInformation
  const contact = processed?.contactInformation

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Dashboard
        </button>
      </div>

      {/* Resume Status */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{resume.filename}</h1>
            <p className="mt-1 text-sm text-gray-500">
              Uploaded on {new Date(resume.upload_date).toLocaleString()}
            </p>
          </div>
          <span className={`px-3 py-1 text-sm font-medium rounded-full ${
            resume.status === 'completed' ? 'bg-green-100 text-green-800' :
            resume.status === 'processing' ? 'bg-blue-100 text-blue-800' :
            resume.status === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-yellow-100 text-yellow-800'
          }`}>
            {resume.status}
          </span>
        </div>
      </div>

      {resume.status !== 'completed' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-yellow-800">
            {resume.status === 'processing'
              ? 'This resume is currently being processed. Please check back in a few moments.'
              : resume.status === 'failed'
              ? `Processing failed: ${resume.error || 'Unknown error'}`
              : 'This resume is pending processing.'}
          </p>
        </div>
      )}

      {processed && (
        <>
          {/* Personal Information */}
          {personal && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <div className="flex items-center mb-4">
                <User className="h-6 w-6 text-blue-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Personal Information</h2>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Name</p>
                  <p className="mt-1 text-sm text-gray-900">
                    {personal.firstName} {personal.middleName !== 'N/A' && personal.middleName} {personal.lastName}
                  </p>
                </div>
                {personal.dateOfBirth !== 'N/A' && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Date of Birth</p>
                    <p className="mt-1 text-sm text-gray-900">{personal.dateOfBirth}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Contact Information */}
          {contact && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <div className="flex items-center mb-4">
                <Mail className="h-6 w-6 text-blue-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Contact Information</h2>
              </div>
              <div className="space-y-3">
                <div className="flex items-center">
                  <Mail className="h-4 w-4 text-gray-400 mr-2" />
                  <span className="text-sm text-gray-900">{contact.email}</span>
                </div>
                <div className="flex items-center">
                  <Phone className="h-4 w-4 text-gray-400 mr-2" />
                  <span className="text-sm text-gray-900">{contact.phone}</span>
                </div>
                {contact.address && (
                  <div className="flex items-center">
                    <MapPin className="h-4 w-4 text-gray-400 mr-2" />
                    <span className="text-sm text-gray-900">
                      {contact.address.street}, {contact.address.city}, {contact.address.state} {contact.address.zip}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Summary */}
          {processed.sanitized_summary && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Professional Summary</h2>
              <p className="text-sm text-gray-700 leading-relaxed">{processed.sanitized_summary}</p>
            </div>
          )}

          {/* Work Experience */}
          {processed.workExperience && processed.workExperience.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <div className="flex items-center mb-4">
                <Briefcase className="h-6 w-6 text-blue-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Work Experience</h2>
              </div>
              <div className="space-y-4">
                {processed.workExperience.map((exp, index) => (
                  <div key={index} className="border-l-2 border-blue-600 pl-4">
                    <h3 className="font-medium text-gray-900">{exp.position}</h3>
                    <p className="text-sm text-gray-600">{exp.employer}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {exp.startDate} - {exp.endDate || 'Present'}
                    </p>
                    {exp.responsibilities !== 'N/A' && (
                      <p className="text-sm text-gray-700 mt-2">{exp.responsibilities}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Education */}
          {processed.education && processed.education.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <div className="flex items-center mb-4">
                <GraduationCap className="h-6 w-6 text-blue-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Education</h2>
              </div>
              <div className="space-y-4">
                {processed.education.map((edu, index) => (
                  <div key={index} className="border-l-2 border-blue-600 pl-4">
                    <h3 className="font-medium text-gray-900">{edu.degree}</h3>
                    <p className="text-sm text-gray-600">{edu.institution}</p>
                    {edu.fieldOfStudy !== 'N/A' && (
                      <p className="text-sm text-gray-600">{edu.fieldOfStudy}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">{edu.graduationDate}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Skills */}
          {processed.skills_keywords && processed.skills_keywords.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <div className="flex items-center mb-4">
                <Award className="h-6 w-6 text-blue-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Skills</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {processed.skills_keywords.map((skill, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* AI Generated Roles */}
          {processed.ai_generated_roles && processed.ai_generated_roles.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Suggested Roles</h2>
              <p className="text-sm text-gray-600 mb-4">
                Based on the experience and skills, here are potential roles:
              </p>
              <ul className="grid grid-cols-2 gap-2">
                {processed.ai_generated_roles.map((role, index) => (
                  <li key={index} className="flex items-center text-sm text-gray-700">
                    <span className="h-2 w-2 bg-blue-600 rounded-full mr-2"></span>
                    {role}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ResumeDetail
