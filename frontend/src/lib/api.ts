import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:5000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token to all requests
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || error.response?.data?.error || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

// Auth Service (matches your API Gateway endpoints)
export const authService = {
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/api/v1/auth/login', { email, password })
    return response.data
  },

  register: async (name: string, email: string, password: string) => {
    // For now, use login endpoint (register not yet implemented in backend)
    const response = await apiClient.post('/api/v1/auth/login', { email, password, name })
    return response.data
  },

  verify: async () => {
    const response = await apiClient.get('/api/v1/auth/verify')
    return response.data
  },

  refreshToken: async () => {
    const response = await apiClient.post('/api/v1/auth/refresh')
    return response.data
  },
}

// Document Service
export const documentService = {
  uploadDocument: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/api/v1/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  processDocument: async (documentId: string) => {
    const response = await apiClient.post(`/api/v1/documents/${documentId}/process`)
    return response.data
  },

  getUserDocuments: async () => {
    const response = await apiClient.get('/api/v1/documents')
    return response.data
  },

  getDocument: async (documentId: string) => {
    const response = await apiClient.get(`/api/v1/documents/${documentId}`)
    return response.data
  },

  deleteDocument: async (documentId: string) => {
    const response = await apiClient.delete(`/api/v1/documents/${documentId}`)
    return response.data
  },

  downloadDocument: async (documentId: string) => {
    const response = await apiClient.get(`/api/v1/documents/${documentId}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  getNotes: async (documentId: string) => {
    const response = await apiClient.get(`/api/v1/documents/${documentId}/notes`)
    return response.data
  },

  regenerateNotes: async (documentId: string) => {
    const response = await apiClient.post(`/api/v1/documents/${documentId}/regenerate-notes`)
    return response.data
  },
}

// Chat Service
export const chatService = {
  createSession: async () => {
    const response = await apiClient.post('/api/v1/chat/sessions')
    return response.data
  },

  sendMessage: async (sessionId: string, message: string) => {
    const response = await apiClient.post(`/api/v1/chat/sessions/${sessionId}/messages`, {
      message,
    })
    return response.data
  },

  getMessages: async (sessionId: string) => {
    const response = await apiClient.get(`/api/v1/chat/sessions/${sessionId}/messages`)
    return response.data
  },

  getSessions: async () => {
    const response = await apiClient.get('/api/v1/chat/sessions')
    return response.data
  },

  deleteSession: async (sessionId: string) => {
    const response = await apiClient.delete(`/api/v1/chat/sessions/${sessionId}`)
    return response.data
  },

  // Backward compatibility
  getConversations: async () => {
    const response = await apiClient.get('/api/v1/chat/sessions')
    return response.data
  },
}

// Quiz Service
export const quizService = {
  generateQuiz: async (file: File, numQuestions: number = 5) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('num_questions', numQuestions.toString())

    const response = await apiClient.post('/api/v1/quizzes/generate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getQuiz: async (quizId: string) => {
    const response = await apiClient.get(`/api/v1/quizzes/${quizId}`)
    return response.data
  },

  submitAnswers: async (quizId: string, answers: Record<number, number>) => {
    const response = await apiClient.post(`/api/v1/quizzes/${quizId}/submit`, { answers })
    return response.data
  },

  getUserQuizHistory: async () => {
    const response = await apiClient.get('/api/v1/quizzes')
    return response.data
  },

  getQuizResults: async (quizId: string) => {
    const response = await apiClient.get(`/api/v1/quizzes/${quizId}/results`)
    return response.data
  },

  deleteQuiz: async (quizId: string) => {
    const response = await apiClient.delete(`/api/v1/quizzes/${quizId}`)
    return response.data
  },
}

// Speech-to-Text Service
export const sttService = {
  transcribe: async (audioFile: File) => {
    const formData = new FormData()
    formData.append('audio', audioFile)

    const response = await apiClient.post('/api/v1/stt/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getTranscription: async (taskId: string) => {
    const response = await apiClient.get(`/api/v1/stt/status/${taskId}`)
    return response.data
  },

  getUserTranscriptions: async () => {
    const response = await apiClient.get('/api/v1/stt/transcriptions')
    return response.data
  },
}

// Text-to-Speech Service
export const ttsService = {
  synthesize: async (text: string, voice?: string) => {
    const response = await apiClient.post(
      '/api/v1/tts/synthesize',
      { text, voice },
      {
        responseType: 'blob',
      }
    )
    return response.data
  },

  getVoices: async () => {
    const response = await apiClient.get('/api/v1/tts/voices')
    return response.data
  },

  getAudio: async (audioId: string) => {
    const response = await apiClient.get(`/api/v1/tts/audio/${audioId}`, {
      responseType: 'blob',
    })
    return response.data
  },

  deleteAudio: async (audioId: string) => {
    const response = await apiClient.delete(`/api/v1/tts/audio/${audioId}`)
    return response.data
  },
}

export default apiClient
