'use client'

import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Mic, Square, Upload } from 'lucide-react'
import LoadingSpinner from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import FileUpload from '@/components/FileUpload'
import { sttService } from '@/lib/api'

export default function SpeechToTextPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [transcription, setTranscription] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setTranscription(null)
    setError(null)
  }

  const handleTranscribe = async (audioFile: File) => {
    setLoading(true)
    setError(null)

    try {
      const response = await sttService.transcribe(audioFile)
      setTranscription(response.text || response.transcription)
    } catch (err: any) {
      setError(err.message || 'Failed to transcribe audio')
    } finally {
      setLoading(false)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const audioFile = new File([blob], 'recording.webm', { type: 'audio/webm' })
        setFile(audioFile)
        handleTranscribe(audioFile)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err: any) {
      setError('Failed to access microphone: ' + err.message)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 shadow-lg">
          <Mic className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900">Speech to Text</h1>
        <p className="text-lg text-gray-600">
          Convert audio recordings to text with high accuracy AI transcription
        </p>
      </motion.div>

      {/* Recording Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <h2 className="text-2xl font-semibold text-gray-800">Record Audio</h2>
        
        <div className="flex justify-center">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading}
            className={`w-32 h-32 rounded-full flex items-center justify-center transition-all ${
              isRecording
                ? 'bg-gradient-to-br from-red-500 to-red-600 animate-pulse'
                : 'bg-gradient-to-br from-orange-500 to-red-500 hover:shadow-xl'
            } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isRecording ? (
              <Square className="w-12 h-12 text-white" />
            ) : (
              <Mic className="w-12 h-12 text-white" />
            )}
          </button>
        </div>

        <p className="text-center text-gray-600">
          {isRecording ? 'Recording... Click to stop' : 'Click to start recording'}
        </p>
      </motion.div>

      {/* Or Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-gradient-to-br from-blue-50 via-white to-purple-50 text-gray-500 font-medium">
            OR UPLOAD AUDIO FILE
          </span>
        </div>
      </div>

      {/* Upload Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <h2 className="text-2xl font-semibold text-gray-800">Upload Audio</h2>
        
        <FileUpload
          onFileSelect={handleFileSelect}
          acceptedTypes=".mp3,.wav,.webm,.m4a,.ogg"
          maxSize={52428800}
          disabled={loading || isRecording}
        />

        {file && !loading && !isRecording && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => handleTranscribe(file)}
            className="w-full bg-gradient-to-r from-orange-600 to-red-600 text-white py-3 rounded-lg font-medium hover:shadow-lg transition-all flex items-center justify-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Transcribe Audio</span>
          </motion.button>
        )}
      </motion.div>

      {/* Loading State */}
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-2xl shadow-lg p-12"
        >
          <LoadingSpinner size="lg" text="Transcribing audio..." />
        </motion.div>
      )}

      {/* Error State */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Transcription Result */}
      {transcription && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
        >
          <h2 className="text-2xl font-semibold text-gray-800">Transcription</h2>
          
          <div className="bg-gray-50 rounded-lg p-6">
            <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{transcription}</p>
          </div>

          <div className="flex space-x-4">
            <button
              onClick={() => navigator.clipboard.writeText(transcription)}
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-all"
            >
              Copy to Clipboard
            </button>
            <button
              onClick={() => {
                const blob = new Blob([transcription], { type: 'text/plain' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'transcription.txt'
                a.click()
              }}
              className="flex-1 bg-green-600 text-white py-3 rounded-lg font-medium hover:bg-green-700 transition-all"
            >
              Download as Text
            </button>
          </div>
        </motion.div>
      )}
    </div>
  )
}
