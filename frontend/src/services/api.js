import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const resumeApi = {
  // Upload a resume
  uploadResume: async (file) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/resumes/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  // Get all resumes
  listResumes: async (status = null, limit = 100) => {
    const params = {}
    if (status) params.status = status
    if (limit) params.limit = limit

    const response = await api.get('/resumes', { params })
    return response.data
  },

  // Get a specific resume
  getResume: async (resumeId) => {
    const response = await api.get(`/resumes/${resumeId}`)
    return response.data
  },

  // Manually trigger processing
  processResume: async (resumeId) => {
    const response = await api.post(`/resumes/${resumeId}/process`)
    return response.data
  },

  // Delete a resume
  deleteResume: async (resumeId) => {
    const response = await api.delete(`/resumes/${resumeId}`)
    return response.data
  },
}

export default api
