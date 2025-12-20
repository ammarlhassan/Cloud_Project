# Cloud Learning Platform - Frontend

A modern Next.js frontend application for the Cloud-Based Learning Platform with AI-powered microservices.

## Features

- 📄 **Document Reader**: Upload and analyze PDF, DOCX, and text documents
- 💬 **AI Chat Assistant**: Intelligent conversational interface
- 📝 **Quiz Generator**: Automatically generate quizzes from documents
- 🎤 **Speech to Text**: Convert audio to text with high accuracy
- 🔊 **Text to Speech**: Natural-sounding voice synthesis

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.local.example .env.local
```

3. Update `.env.local` with your API Gateway URL:
```env
NEXT_PUBLIC_API_GATEWAY_URL=http://your-api-gateway-url.com
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── chat/              # Chat interface page
│   │   ├── document-reader/   # Document upload & processing
│   │   ├── quiz/              # Quiz generator
│   │   ├── speech-to-text/    # STT interface
│   │   ├── text-to-speech/    # TTS interface
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   └── globals.css        # Global styles
│   ├── components/
│   │   ├── Navbar.tsx         # Navigation component
│   │   ├── LoadingSpinner.tsx # Loading indicator
│   │   ├── Alert.tsx          # Alert/notification component
│   │   └── FileUpload.tsx     # File upload component
│   └── lib/
│       ├── api.ts             # API client & service functions
│       └── utils.ts           # Utility functions
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## API Integration

The frontend connects to your microservices through the API Gateway. Update the `NEXT_PUBLIC_API_GATEWAY_URL` environment variable to point to your deployed API Gateway.

### API Endpoints Expected

- **Document Service**: `POST /document/upload`
- **Chat Service**: `POST /chat`
- **Quiz Service**: `POST /quiz/generate`
- **STT Service**: `POST /stt/transcribe`
- **TTS Service**: `POST /tts/synthesize`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_GATEWAY_URL` | API Gateway base URL | `http://your-lb.amazonaws.com` |

## Features Overview

### Document Reader
- Drag & drop file upload
- Support for PDF, DOCX, and TXT files
- Real-time document processing
- Content extraction and summarization

### Chat Assistant
- Real-time conversational interface
- Message history
- Typing indicators
- Responsive design

### Quiz Generator
- Generate quizzes from uploaded documents
- Multiple choice questions
- Instant feedback
- Score calculation and explanations

### Speech to Text
- Browser-based audio recording
- Audio file upload support
- High-accuracy transcription
- Export transcriptions

### Text to Speech
- Natural voice synthesis
- Audio playback controls
- Download generated audio
- Sample text templates

## Deployment

### Deploy to Vercel (Recommended)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variables
4. Deploy

### Deploy to AWS (S3 + CloudFront)

```bash
npm run build
# Upload the 'out' directory to S3
# Configure CloudFront distribution
```

### Docker Deployment

```bash
docker build -t learning-platform-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_GATEWAY_URL=http://your-api learning-platform-frontend
```

## Customization

### Theming

Update colors in [tailwind.config.ts](tailwind.config.ts):

```typescript
colors: {
  primary: {
    // Your custom colors
  }
}
```

### Add New Pages

1. Create a new directory in `src/app/`
2. Add `page.tsx` with your component
3. Update navigation in [Navbar.tsx](src/components/Navbar.tsx)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is part of the Cloud-Based Learning Platform.

## Support

For issues and questions, please open an issue in the repository.
