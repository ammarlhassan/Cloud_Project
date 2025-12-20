'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { 
  BookOpen, 
  MessageSquare, 
  FileText, 
  Mic, 
  Volume2,
  Sparkles 
} from 'lucide-react'

const features = [
  {
    icon: FileText,
    title: 'Document Reader',
    description: 'Upload and analyze PDF, DOCX, and text documents with AI-powered extraction',
    link: '/document-reader',
    color: 'from-blue-500 to-cyan-500'
  },
  {
    icon: MessageSquare,
    title: 'AI Chat Assistant',
    description: 'Get instant answers and explanations from your learning materials',
    link: '/chat',
    color: 'from-purple-500 to-pink-500'
  },
  {
    icon: BookOpen,
    title: 'Quiz Generator',
    description: 'Automatically generate quizzes from your documents to test your knowledge',
    link: '/quiz',
    color: 'from-green-500 to-emerald-500'
  },
  {
    icon: Mic,
    title: 'Speech to Text',
    description: 'Convert your voice recordings into text with high accuracy',
    link: '/speech-to-text',
    color: 'from-orange-500 to-red-500'
  },
  {
    icon: Volume2,
    title: 'Text to Speech',
    description: 'Listen to your documents and study materials on the go',
    link: '/text-to-speech',
    color: 'from-indigo-500 to-blue-500'
  }
]

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-6 py-12"
      >
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="w-8 h-8 text-yellow-500" />
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Cloud Learning Platform
          </h1>
          <Sparkles className="w-8 h-8 text-yellow-500" />
        </div>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Enhance your learning experience with AI-powered tools for document processing, 
          intelligent chat, quiz generation, and voice capabilities
        </p>
      </motion.div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {features.map((feature, index) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
          >
            <Link href={feature.link}>
              <div className="group relative h-full bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer">
                {/* Gradient Background */}
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
                
                {/* Content */}
                <div className="relative p-8 space-y-4">
                  <div className={`inline-flex p-4 rounded-xl bg-gradient-to-br ${feature.color} shadow-lg`}>
                    <feature.icon className="w-8 h-8 text-white" />
                  </div>
                  
                  <h3 className="text-2xl font-bold text-gray-800 group-hover:text-blue-600 transition-colors">
                    {feature.title}
                  </h3>
                  
                  <p className="text-gray-600 leading-relaxed">
                    {feature.description}
                  </p>
                  
                  <div className="pt-4 flex items-center text-blue-600 font-semibold group-hover:gap-2 transition-all">
                    Try it now
                    <span className="inline-block group-hover:translate-x-2 transition-transform">→</span>
                  </div>
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Stats Section */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-xl p-8 md:p-12"
      >
        <div className="grid md:grid-cols-3 gap-8 text-center text-white">
          <div>
            <div className="text-4xl md:text-5xl font-bold mb-2">5+</div>
            <div className="text-blue-100">AI-Powered Services</div>
          </div>
          <div>
            <div className="text-4xl md:text-5xl font-bold mb-2">100%</div>
            <div className="text-blue-100">Cloud-Native</div>
          </div>
          <div>
            <div className="text-4xl md:text-5xl font-bold mb-2">24/7</div>
            <div className="text-blue-100">Available</div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
