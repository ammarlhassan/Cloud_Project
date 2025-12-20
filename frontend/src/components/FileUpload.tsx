'use client'

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File } from 'lucide-react'
import { motion } from 'framer-motion'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  acceptedTypes?: string
  maxSize?: number
  disabled?: boolean
}

export default function FileUpload({
  onFileSelect,
  acceptedTypes = '.pdf,.docx,.txt',
  maxSize = 10485760, // 10MB default
  disabled = false
}: FileUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: acceptedTypes.split(',').reduce((acc, type) => {
      acc[type.trim()] = []
      return acc
    }, {} as Record<string, string[]>),
    maxSize,
    multiple: false,
    disabled
  })

  return (
    <div className="w-full">
      <motion.div
        whileHover={{ scale: disabled ? 1 : 1.01 }}
        whileTap={{ scale: disabled ? 1 : 0.99 }}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          disabled
            ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
            : isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/50'
        }`}
        {...(getRootProps() as any)}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center space-y-4">
          {acceptedFiles.length > 0 ? (
            <>
              <File className="w-12 h-12 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {acceptedFiles[0].name}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </>
          ) : (
            <>
              <Upload className={`w-12 h-12 ${disabled ? 'text-gray-400' : 'text-gray-400'}`} />
              <div>
                <p className={`text-sm font-medium ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
                  {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
                </p>
                <p className={`text-xs mt-1 ${disabled ? 'text-gray-300' : 'text-gray-500'}`}>
                  or click to browse
                </p>
              </div>
              <p className={`text-xs ${disabled ? 'text-gray-300' : 'text-gray-400'}`}>
                Accepted: {acceptedTypes} • Max size: {maxSize / 1024 / 1024}MB
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}
