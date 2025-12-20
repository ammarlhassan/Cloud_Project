'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Upload, CheckCircle, Circle } from 'lucide-react'
import FileUpload from '@/components/FileUpload'
import LoadingSpinner from '@/components/LoadingSpinner'
import Alert from '@/components/Alert'
import { quizService } from '@/lib/api'

interface Question {
  id: number
  question: string
  options: string[]
  correct_answer: number
  explanation?: string
}

interface Quiz {
  questions: Question[]
}

export default function QuizPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [showResults, setShowResults] = useState(false)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setQuiz(null)
    setError(null)
    setAnswers({})
    setShowResults(false)
  }

  const handleGenerate = async () => {
    if (!file) return

    setLoading(true)
    setError(null)

    try {
      const response = await quizService.generateQuiz(file)
      setQuiz(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate quiz')
    } finally {
      setLoading(false)
    }
  }

  const handleAnswerSelect = (questionId: number, optionIndex: number) => {
    if (showResults) return
    setAnswers(prev => ({ ...prev, [questionId]: optionIndex }))
  }

  const handleSubmit = () => {
    setShowResults(true)
  }

  const calculateScore = () => {
    if (!quiz) return 0
    let correct = 0
    quiz.questions.forEach(q => {
      if (answers[q.id] === q.correct_answer) correct++
    })
    return (correct / quiz.questions.length) * 100
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center space-y-4"
      >
        <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 shadow-lg">
          <BookOpen className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900">Quiz Generator</h1>
        <p className="text-lg text-gray-600">
          Upload a document to automatically generate a quiz to test your knowledge
        </p>
      </motion.div>

      {/* Upload Section */}
      {!quiz && (
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
              onClick={handleGenerate}
              className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 rounded-lg font-medium hover:shadow-lg transition-all flex items-center justify-center space-x-2"
            >
              <Upload className="w-5 h-5" />
              <span>Generate Quiz</span>
            </motion.button>
          )}
        </motion.div>
      )}

      {/* Loading State */}
      {loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-white rounded-2xl shadow-lg p-12"
        >
          <LoadingSpinner size="lg" text="Generating your quiz..." />
        </motion.div>
      )}

      {/* Error State */}
      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Quiz */}
      {quiz && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Score Display */}
          {showResults && (
            <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Quiz Complete!</h2>
              <div className="text-6xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                {calculateScore().toFixed(0)}%
              </div>
              <p className="text-gray-600 mt-2">
                You got {quiz.questions.filter(q => answers[q.id] === q.correct_answer).length} out of {quiz.questions.length} correct
              </p>
            </div>
          )}

          {/* Questions */}
          {quiz.questions.map((question, index) => {
            const isAnswered = answers[question.id] !== undefined
            const isCorrect = answers[question.id] === question.correct_answer

            return (
              <motion.div
                key={question.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-2xl shadow-lg p-8 space-y-4"
              >
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center text-white font-bold">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">{question.question}</h3>
                  </div>
                  {showResults && (
                    <div>
                      {isCorrect ? (
                        <CheckCircle className="w-6 h-6 text-green-500" />
                      ) : (
                        <Circle className="w-6 h-6 text-red-500" />
                      )}
                    </div>
                  )}
                </div>

                <div className="space-y-3 ml-12">
                  {question.options.map((option, optionIndex) => {
                    const isSelected = answers[question.id] === optionIndex
                    const isCorrectAnswer = question.correct_answer === optionIndex
                    
                    let bgColor = 'bg-gray-50 hover:bg-gray-100'
                    if (showResults) {
                      if (isCorrectAnswer) {
                        bgColor = 'bg-green-100 border-green-500'
                      } else if (isSelected && !isCorrectAnswer) {
                        bgColor = 'bg-red-100 border-red-500'
                      }
                    } else if (isSelected) {
                      bgColor = 'bg-blue-100 border-blue-500'
                    }

                    return (
                      <button
                        key={optionIndex}
                        onClick={() => handleAnswerSelect(question.id, optionIndex)}
                        disabled={showResults}
                        className={`w-full text-left p-4 rounded-lg border-2 transition-all ${bgColor} ${
                          showResults ? 'cursor-default' : 'cursor-pointer'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                            isSelected ? 'border-blue-600 bg-blue-600' : 'border-gray-300'
                          }`}>
                            {isSelected && <div className="w-3 h-3 bg-white rounded-full" />}
                          </div>
                          <span className="text-gray-800">{option}</span>
                        </div>
                      </button>
                    )
                  })}
                </div>

                {showResults && question.explanation && (
                  <div className="ml-12 mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-sm text-gray-700">
                      <span className="font-semibold">Explanation:</span> {question.explanation}
                    </p>
                  </div>
                )}
              </motion.div>
            )
          })}

          {/* Submit Button */}
          {!showResults && (
            <button
              onClick={handleSubmit}
              disabled={Object.keys(answers).length !== quiz.questions.length}
              className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-lg font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Submit Quiz
            </button>
          )}

          {/* Retry Button */}
          {showResults && (
            <button
              onClick={() => {
                setQuiz(null)
                setFile(null)
                setAnswers({})
                setShowResults(false)
              }}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 rounded-lg font-medium hover:shadow-lg transition-all"
            >
              Generate New Quiz
            </button>
          )}
        </motion.div>
      )}
    </div>
  )
}
