'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  FileText, 
  Download, 
  Trash2, 
  Eye, 
  Clock,
  FileIcon,
  Loader2,
  Search,
  Filter
} from 'lucide-react'
import ProtectedRoute from '@/components/ProtectedRoute'
import LoadingSpinner from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import { documentService } from '@/lib/api'
import { formatFileSize, formatDate } from '@/lib/utils'

interface Document {
  id: string
  filename: string
  file_type: string
  file_size: number
  s3_url: string
  created_at: string
  updated_at: string
  status: string
  notes_generated: boolean
}

export default function MyDocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await documentService.getUserDocuments()
      setDocuments(data.documents || data)
    } catch (err: any) {
      setError(err.message || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document from S3?')) {
      return
    }

    setDeletingId(documentId)
    try {
      await documentService.deleteDocument(documentId)
      setDocuments(docs => docs.filter(d => d.id !== documentId))
    } catch (err: any) {
      setError(err.message || 'Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  const handleDownload = async (doc: Document) => {
    try {
      const blob = await documentService.downloadDocument(doc.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = doc.filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setError(err.message || 'Failed to download document')
    }
  }

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterType === 'all' || doc.file_type === filterType
    return matchesSearch && matchesFilter
  })

  const getFileIcon = (fileType: string) => {
    if (fileType.includes('pdf')) return '📄'
    if (fileType.includes('doc')) return '📝'
    if (fileType.includes('txt')) return '📃'
    return '📄'
  }

  return (
    <ProtectedRoute>
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center space-y-4"
        >
          <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg">
            <FileText className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900">My Documents</h1>
          <p className="text-lg text-gray-600">
            Documents stored in AWS S3 buckets (document-reader-storage)
          </p>
        </motion.div>

        {/* Search and Filter */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-lg p-6"
        >
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="pl-10 pr-8 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none bg-white"
              >
                <option value="all">All Types</option>
                <option value="pdf">PDF</option>
                <option value="docx">DOCX</option>
                <option value="txt">Text</option>
              </select>
            </div>
          </div>
        </motion.div>

        {/* Error Alert */}
        {error && (
          <Alert type="error" message={error} onClose={() => setError(null)} />
        )}

        {/* Documents List */}
        {loading ? (
          <div className="bg-white rounded-2xl shadow-lg p-12">
            <LoadingSpinner size="lg" text="Loading documents from S3..." />
          </div>
        ) : filteredDocuments.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl shadow-lg p-12 text-center"
          >
            <FileIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No documents found</h3>
            <p className="text-gray-600 mb-6">
              {searchTerm || filterType !== 'all' 
                ? 'Try adjusting your search or filter'
                : 'Upload your first document to get started'}
            </p>
            <a
              href="/document-reader"
              className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all"
            >
              <FileText className="w-5 h-5" />
              <span>Upload Document</span>
            </a>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDocuments.map((doc, index) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all"
              >
                {/* File Icon and Type */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="text-4xl">{getFileIcon(doc.file_type)}</div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900 truncate" title={doc.filename}>
                        {doc.filename}
                      </h3>
                      <p className="text-sm text-gray-500 uppercase">{doc.file_type}</p>
                    </div>
                  </div>
                </div>

                {/* File Info */}
                <div className="space-y-2 mb-4 text-sm text-gray-600">
                  <div className="flex items-center justify-between">
                    <span>Size:</span>
                    <span className="font-medium">{formatFileSize(doc.file_size)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Status:</span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      doc.status === 'processed' 
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {doc.status}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1 text-gray-500">
                    <Clock className="w-4 h-4" />
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                </div>

                {/* Notes Badge */}
                {doc.notes_generated && (
                  <div className="mb-4">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                      ✓ Notes Generated
                    </span>
                  </div>
                )}

                {/* S3 Location */}
                <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">S3 Location:</p>
                  <p className="text-xs font-mono text-gray-800 truncate" title={doc.s3_url}>
                    {doc.s3_url || 'document-reader-storage/{env}/...'}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  <a
                    href={`/document-reader/${doc.id}`}
                    className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all text-sm"
                  >
                    <Eye className="w-4 h-4" />
                    <span>View</span>
                  </a>
                  <button
                    onClick={() => handleDownload(doc)}
                    className="flex items-center justify-center p-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-all"
                    title="Download from S3"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="flex items-center justify-center p-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all disabled:opacity-50"
                    title="Delete from S3"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Stats Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-blue-50 border border-blue-200 rounded-xl p-6"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-900">{documents.length}</div>
              <div className="text-sm text-blue-700">Total Documents</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-900">
                {documents.filter(d => d.status === 'processed').length}
              </div>
              <div className="text-sm text-blue-700">Processed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-900">
                {documents.filter(d => d.notes_generated).length}
              </div>
              <div className="text-sm text-blue-700">With Notes</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-900">AWS S3</div>
              <div className="text-sm text-blue-700">Storage</div>
            </div>
          </div>
        </motion.div>
      </div>
    </ProtectedRoute>
  )
}
