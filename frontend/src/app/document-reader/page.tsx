'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, Upload, CheckCircle } from 'lucide-react'
import FileUpload from '@/components/FileUpload'
import LoadingSpinner from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import { documentService } from '@/lib/api'

export default function DocumentReaderPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    try {
      const response = await documentService.uploadDocument(file)
      setResult(response)
    } catch (err: any) {
      setError(err.message || 'Failed to process document')
    } finally {
      setLoading(false)
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
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg">
          <FileText className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900">Document Reader</h1>
        <p className="text-lg text-gray-600">
          Upload PDF, DOCX, or text documents for AI-powered analysis and extraction
        </p>
      </motion.div>

      {/* Upload Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <h2 className="text-2xl font-semibold text-gray-800">Upload Document</h2>
        
        <FileUpload
          onFileSelect={handleFileSelect}
          acceptedTypes=".pdf,.docx,.txt"
          maxSize={10485760}
          disabled={loading}
        />

        {file && !loading && (
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={handleUpload}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-lg font-medium hover:shadow-lg transition-all flex items-center justify-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Process Document</span>
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
          <LoadingSpinner size="lg" text="Processing your document..." />
        </motion.div>
      )}

      {/* Error State */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Results */}
      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg p-8 space-y-6"
        >
          <div className="flex items-center space-x-3">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <h2 className="text-2xl font-semibold text-gray-800">Document Processed</h2>
          </div>

          {/* Metadata */}
          {result.metadata && (
            <div className="bg-gray-50 rounded-lg p-6 space-y-3">
              <h3 className="font-semibold text-gray-800">Document Information</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Filename:</span>
                  <p className="font-medium text-gray-900">{result.metadata.filename}</p>
                </div>
                <div>
                  <span className="text-gray-600">File Size:</span>
                  <p className="font-medium text-gray-900">{result.metadata.size}</p>
                </div>
                <div>
                  <span className="text-gray-600">Type:</span>
                  <p className="font-medium text-gray-900">{result.metadata.type}</p>
                </div>
                <div>
                  <span className="text-gray-600">Pages:</span>
                  <p className="font-medium text-gray-900">{result.metadata.pages || 'N/A'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Extracted Text */}
          {result.content && (
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-800">Extracted Content</h3>
              <div className="bg-gray-50 rounded-lg p-6 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
                  {result.content}
                </pre>
              </div>
            </div>
          )}

          {/* Summary */}
          {result.summary && (
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-800">AI Summary</h3>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <p className="text-gray-700 leading-relaxed">{result.summary}</p>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}
