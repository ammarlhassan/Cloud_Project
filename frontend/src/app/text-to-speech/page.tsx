'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Volume2, Play, Pause, Download } from 'lucide-react'
import LoadingSpinner from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import { ttsService } from '@/lib/api'

export default function TextToSpeechPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)

  const handleGenerate = async () => {
    if (!text.trim()) return

    setLoading(true)
    setError(null)
    setAudioUrl(null)

    try {
      const blob = await ttsService.synthesize(text)
      const url = URL.createObjectURL(blob)
      setAudioUrl(url)
      
      // Create audio element
      const audio = new Audio(url)
      audio.onended = () => setIsPlaying(false)
      setAudioElement(audio)
    } catch (err: any) {
      setError(err.message || 'Failed to generate speech')
    } finally {
      setLoading(false)
    }
  }

  const togglePlayPause = () => {
    if (!audioElement) return

    if (isPlaying) {
      audioElement.pause()
    } else {
      audioElement.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleDownload = () => {
    if (!audioUrl) return

    const a = document.createElement('a')
    a.href = audioUrl
    a.download = 'speech.mp3'
    a.click()
  }

  const sampleTexts = [
    "Welcome to the cloud learning platform. This is an example of text-to-speech conversion.",
    "Artificial intelligence is transforming education by providing personalized learning experiences.",
    "The quick brown fox jumps over the lazy dog. This sentence contains all letters of the alphabet."
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-500 shadow-lg">
          <Volume2 className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900">Text to Speech</h1>
        <p className="text-lg text-gray-600">
          Convert any text into natural-sounding speech with AI-powered voice synthesis
        </p>
      </motion.div>

      {/* Input Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <h2 className="text-2xl font-semibold text-gray-800">Enter Text</h2>
        
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type or paste the text you want to convert to speech..."
          rows={8}
          maxLength={5000}
          disabled={loading}
          className="w-full border border-gray-300 rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none disabled:bg-gray-50"
        />

        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>{text.length} / 5000 characters</span>
        </div>

        {/* Sample Texts */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Try these examples:</p>
          <div className="grid md:grid-cols-3 gap-2">
            {sampleTexts.map((sample, index) => (
              <button
                key={index}
                onClick={() => setText(sample)}
                disabled={loading}
                className="text-left text-xs p-3 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors disabled:opacity-50"
              >
                {sample.substring(0, 60)}...
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={!text.trim() || loading}
          className="w-full bg-gradient-to-r from-indigo-600 to-blue-600 text-white py-3 rounded-lg font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          <Volume2 className="w-5 h-5" />
          <span>Generate Speech</span>
        </button>
      </motion.div>

      {/* Loading State */}
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-2xl shadow-lg p-12"
        >
          <LoadingSpinner size="lg" text="Generating speech..." />
        </motion.div>
      )}

      {/* Error State */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Audio Player */}
      {audioUrl && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
        >
          <h2 className="text-2xl font-semibold text-gray-800">Generated Speech</h2>
          
          <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg p-8">
            <div className="flex items-center justify-center space-x-6">
              <button
                onClick={togglePlayPause}
                className="w-16 h-16 bg-gradient-to-br from-indigo-600 to-blue-600 rounded-full flex items-center justify-center hover:shadow-xl transition-all"
              >
                {isPlaying ? (
                  <Pause className="w-8 h-8 text-white" />
                ) : (
                  <Play className="w-8 h-8 text-white ml-1" />
                )}
              </button>

              <div className="flex-1">
                <div className="text-sm text-gray-600 mb-1">
                  {isPlaying ? 'Playing...' : 'Ready to play'}
                </div>
                <div className="w-full h-2 bg-white rounded-full overflow-hidden">
                  <div className={`h-full bg-gradient-to-r from-indigo-600 to-blue-600 ${isPlaying ? 'animate-pulse' : ''}`} style={{ width: '100%' }} />
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleDownload}
            className="w-full bg-green-600 text-white py-3 rounded-lg font-medium hover:bg-green-700 transition-all flex items-center justify-center space-x-2"
          >
            <Download className="w-5 h-5" />
            <span>Download Audio</span>
          </button>
        </motion.div>
      )}

      {/* Info Box */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-blue-50 border border-blue-200 rounded-xl p-6"
      >
        <h3 className="font-semibold text-blue-900 mb-2">Tips for Best Results:</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Use clear punctuation for natural pauses</li>
          <li>Keep sentences concise and well-structured</li>
          <li>Avoid excessive special characters</li>
          <li>Maximum length: 5000 characters</li>
        </ul>
      </motion.div>
    </div>
  )
}
