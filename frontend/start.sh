#!/bin/bash

echo "🚀 Starting Cloud Learning Platform Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Creating .env.local from example..."
    cp .env.local.example .env.local
    echo "✅ .env.local created - please update with your API Gateway URL"
    echo ""
fi

echo "✨ Starting development server..."
echo "📍 Frontend will be available at: http://localhost:3000"
echo "🔌 Make sure your backend is running on the configured API Gateway URL"
echo ""

npm run dev
