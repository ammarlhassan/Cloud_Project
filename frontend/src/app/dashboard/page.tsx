'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  FileText, 
  MessageSquare, 
  BookOpen, 
  TrendingUp,
  Clock,
  Award,
  FolderOpen,
  Activity
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import Link from 'next/link'
import { documentService, chatService, quizService } from '@/lib/api'

export default function DashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState({
    documents: 0,
    conversations: 0,
    quizzes: 0,
    score: 0
  })
  const [recentActivity, setRecentActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      // Load user statistics
      const [documents, conversations, quizHistory] = await Promise.all([
        documentService.getUserDocuments().catch(() => []),
        chatService.getConversations().catch(() => []),
        quizService.getUserQuizHistory().catch(() => [])
      ])

      setStats({
        documents: documents.length || 0,
        conversations: conversations.length || 0,
        quizzes: quizHistory.length || 0,
        score: calculateAverageScore(quizHistory)
      })

      // Combine recent activity
      const activity = [
        ...documents.slice(0, 3).map((d: any) => ({ ...d, type: 'document' })),
        ...conversations.slice(0, 3).map((c: any) => ({ ...c, type: 'conversation' })),
        ...quizHistory.slice(0, 3).map((q: any) => ({ ...q, type: 'quiz' }))
      ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

      setRecentActivity(activity.slice(0, 5))
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const calculateAverageScore = (quizzes: any[]) => {
    if (!quizzes || quizzes.length === 0) return 0
    const total = quizzes.reduce((sum, quiz) => sum + (quiz.score || 0), 0)
    return Math.round(total / quizzes.length)
  }

  const statCards = [
    {
      icon: FileText,
      label: 'Documents',
      value: stats.documents,
      color: 'from-blue-500 to-cyan-500',
      link: '/my-documents'
    },
    {
      icon: MessageSquare,
      label: 'Conversations',
      value: stats.conversations,
      color: 'from-purple-500 to-pink-500',
      link: '/chat'
    },
    {
      icon: BookOpen,
      label: 'Quizzes Taken',
      value: stats.quizzes,
      color: 'from-green-500 to-emerald-500',
      link: '/quiz-history'
    },
    {
      icon: Award,
      label: 'Average Score',
      value: `${stats.score}%`,
      color: 'from-orange-500 to-red-500',
      link: '/quiz-history'
    }
  ]

  return (
    <ProtectedRoute>
      <div className="space-y-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-xl p-8 text-white"
        >
          <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.name}! 👋</h1>
          <p className="text-blue-100">Here's an overview of your learning progress</p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Link href={stat.link}>
                <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all cursor-pointer group">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-3 rounded-lg bg-gradient-to-br ${stat.color}`}>
                      <stat.icon className="w-6 h-6 text-white" />
                    </div>
                    <TrendingUp className="w-5 h-5 text-green-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <h3 className="text-gray-600 text-sm font-medium">{stat.label}</h3>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-2xl shadow-lg p-8"
        >
          <div className="flex items-center space-x-3 mb-6">
            <Activity className="w-6 h-6 text-blue-600" />
            <h2 className="text-2xl font-bold text-gray-900">Recent Activity</h2>
          </div>

          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : recentActivity.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FolderOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p>No activity yet. Start by uploading a document!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {recentActivity.map((activity, index) => (
                <div
                  key={index}
                  className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className={`p-2 rounded-lg ${
                    activity.type === 'document' ? 'bg-blue-100' :
                    activity.type === 'conversation' ? 'bg-purple-100' : 'bg-green-100'
                  }`}>
                    {activity.type === 'document' && <FileText className="w-5 h-5 text-blue-600" />}
                    {activity.type === 'conversation' && <MessageSquare className="w-5 h-5 text-purple-600" />}
                    {activity.type === 'quiz' && <BookOpen className="w-5 h-5 text-green-600" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">
                      {activity.type === 'document' && `Document: ${activity.filename || 'Untitled'}`}
                      {activity.type === 'conversation' && `Chat: ${activity.title || 'New conversation'}`}
                      {activity.type === 'quiz' && `Quiz: ${activity.title || 'Untitled quiz'}`}
                    </p>
                    <p className="text-sm text-gray-500 flex items-center space-x-1">
                      <Clock className="w-4 h-4" />
                      <span>{new Date(activity.created_at).toLocaleDateString()}</span>
                    </p>
                  </div>
                  {activity.type === 'quiz' && activity.score && (
                    <div className="text-right">
                      <p className="text-lg font-bold text-green-600">{activity.score}%</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="grid md:grid-cols-3 gap-6"
        >
          <Link href="/document-reader" className="group">
            <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all">
              <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 inline-block mb-4">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Upload Document</h3>
              <p className="text-sm text-gray-600">Start by uploading a new document</p>
            </div>
          </Link>

          <Link href="/chat" className="group">
            <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all">
              <div className="p-3 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 inline-block mb-4">
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Start Chat</h3>
              <p className="text-sm text-gray-600">Ask questions and get instant answers</p>
            </div>
          </Link>

          <Link href="/quiz" className="group">
            <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all">
              <div className="p-3 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 inline-block mb-4">
                <BookOpen className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Take Quiz</h3>
              <p className="text-sm text-gray-600">Test your knowledge with AI-generated quizzes</p>
            </div>
          </Link>
        </motion.div>
      </div>
    </ProtectedRoute>
  )
}
