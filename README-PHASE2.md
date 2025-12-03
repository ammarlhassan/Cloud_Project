# AI Learner Platform - Phase 2

A cloud-native microservices platform for AI-powered learning, built with Flask, Kafka, PostgreSQL, and AWS services.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [AWS Setup](#aws-setup)
- [Quick Start](#quick-start)
- [Services](#services)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## 🎯 Overview

The AI Learner Platform is a microservices-based system that provides:

- **Text-to-Speech (TTS)**: Convert text to natural-sounding speech using AWS Polly
- **Speech-to-Text (STT)**: Transcribe audio files using AWS Transcribe
- **AI Chat**: Intelligent chat sessions with conversation history
- **Document Processing**: Upload, process, and extract text from documents
- **Quiz Generation**: Create and grade quizzes from learning materials

### Key Features

- ✅ Event-driven architecture with Apache Kafka
- ✅ RESTful API with JWT authentication
- ✅ Rate limiting and request throttling
- ✅ PostgreSQL databases for persistent storage
- ✅ AWS integration (S3, Polly, Transcribe, Textract)
- ✅ Docker containerization with health checks
- ✅ Production-ready error handling and logging

## 🏗️ Architecture

```
┌─────────────┐
│  API Gateway │ (Port 5000)
│  JWT Auth    │
│  Rate Limit  │
└──────┬──────┘
       │
       ├───────────┬───────────┬───────────┬────────────┐
       │           │           │           │            │
   ┌───▼──┐    ┌──▼──┐    ┌──▼──┐    ┌───▼───┐    ┌──▼──┐
   │ TTS  │    │ STT │    │Chat │    │  Doc  │    │Quiz │
   │:5001 │    │:5002│    │:5003│    │ :5004 │    │:5005│
   └───┬──┘    └──┬──┘    └──┬──┘    └───┬───┘    └──┬──┘
       │          │          │            │           │
       └──────────┴──────────┴────────────┴───────────┘
                          │
                     ┌────▼────┐
                     │  Kafka  │
                     │  :9092  │
                     └─────────┘
```

### Technology Stack

- **Language**: Python 3.11
- **Framework**: Flask 3.0.0
- **Message Broker**: Apache Kafka 2.0.2
- **Databases**: PostgreSQL 15 (separate DBs for Chat, Document, Quiz)
- **AWS Services**: S3, Polly, Transcribe, Textract
- **Container**: Docker with multi-stage builds
- **Web Server**: Gunicorn 21.2.0

## 📦 Prerequisites

### Required

- Docker Engine 20.10+ and Docker Compose 2.0+
- AWS Academy Learner Lab account with active session
- 8GB+ RAM for running all services
- 10GB+ disk space

### For Development

- Python 3.11+
- Git
- Text editor (VS Code recommended)

## ☁️ AWS Setup

### 1. Start AWS Academy Learner Lab

1. Log into AWS Academy and start your Learner Lab session
2. Click "AWS Details" to view credentials
3. Copy the AWS CLI credentials

### 2. Create S3 Buckets

```bash
# Set your AWS credentials first
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_SESSION_TOKEN="your_token"
export AWS_REGION="us-east-1"

# Create S3 buckets
aws s3 mb s3://learner-lab-audio --region us-east-1
aws s3 mb s3://learner-lab-documents --region us-east-1

# Verify buckets
aws s3 ls
```

### 3. Configure IAM Permissions

Ensure your Learner Lab role has permissions for:
- `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`
- `polly:SynthesizeSpeech`, `polly:DescribeVoices`
- `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`
- `textract:DetectDocumentText`

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd Cloud_Project
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your AWS credentials
nano .env
```

Update the following in `.env`:
```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_SESSION_TOKEN=your_session_token_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=learner-lab-audio
JWT_SECRET=your-super-secret-jwt-key
```

### 3. Build and Start Services

```bash
# Build all services
docker-compose -f docker-compose.learner-lab.yml build

# Start all services
docker-compose -f docker-compose.learner-lab.yml up -d

# Check service health
docker-compose -f docker-compose.learner-lab.yml ps
```

### 4. Verify Deployment

```bash
# Check API Gateway
curl http://localhost:5000/health

# Check all services
curl http://localhost:5000/ready

# View logs
docker-compose -f docker-compose.learner-lab.yml logs -f api-gateway
```

### 5. Get JWT Token

```bash
# Login to get JWT token
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }'

# Response includes token
# {"token": "eyJ...", "user": {...}}
```

### 6. Test Services

```bash
# Set your token
TOKEN="your_jwt_token_here"

# Test TTS
curl -X POST http://localhost:5000/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test.",
    "voice_id": "Joanna"
  }'

# Test Chat
curl -X POST http://localhost:5000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session"}'
```

## 🔧 Services

### API Gateway (Port 5000)

**Entry point for all client requests**

Features:
- JWT authentication
- Rate limiting (100 req/min per user)
- Request routing to microservices
- CORS support

Endpoints:
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/verify` - Verify JWT token
- `GET /api/v1/docs` - API documentation

### TTS Service (Port 5001)

**Convert text to speech using AWS Polly**

Features:
- Neural voice synthesis
- Multiple voice options
- S3 audio storage
- Kafka event publishing

Endpoints:
- `POST /api/v1/tts/synthesize` - Convert text to speech
- `GET /api/v1/tts/voices` - List available voices

Example:
```bash
curl -X POST http://localhost:5000/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to the AI Learner Platform",
    "voice_id": "Joanna",
    "output_format": "mp3"
  }'
```

### STT Service (Port 5002)

**Transcribe audio files using AWS Transcribe**

Features:
- Audio file upload
- Job status polling
- Speaker identification
- Kafka event publishing

Endpoints:
- `POST /api/v1/stt/transcribe` - Upload and transcribe audio
- `GET /api/v1/stt/status/<task_id>` - Get transcription status

Example:
```bash
curl -X POST http://localhost:5000/api/v1/stt/transcribe \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3" \
  -F "language=en-US"
```

### Chat Service (Port 5003)

**AI-powered chat with session management**

Features:
- Session management
- Message history
- AI response generation (placeholder)
- PostgreSQL storage

Endpoints:
- `POST /api/v1/chat/sessions` - Create chat session
- `POST /api/v1/chat/sessions/<id>/messages` - Send message
- `GET /api/v1/chat/sessions/<id>/messages` - Get message history
- `DELETE /api/v1/chat/sessions/<id>` - Delete session

Database:
- `chat_sessions`: Session metadata
- `chat_messages`: Message history with timestamps

### Document Service (Port 5004)

**Process and extract text from documents**

Features:
- PDF/TXT upload to S3
- Text extraction (PyPDF2 + AWS Textract)
- Notes generation
- PostgreSQL storage

Endpoints:
- `POST /api/v1/documents/upload` - Upload document
- `POST /api/v1/documents/<id>/process` - Process document
- `GET /api/v1/documents/<id>` - Get document details
- `GET /api/v1/documents/<id>/notes` - Get generated notes
- `GET /api/v1/documents` - List all documents

Database:
- `documents`: Document metadata and S3 paths
- `notes`: Generated notes with timestamps

### Quiz Service (Port 5005)

**Generate and grade quizzes**

Features:
- Quiz generation from documents
- Multiple-choice questions
- Automatic grading
- Score calculation

Endpoints:
- `POST /api/v1/quizzes/generate` - Generate quiz
- `GET /api/v1/quizzes/<id>` - Get quiz
- `POST /api/v1/quizzes/<id>/submit` - Submit answers
- `GET /api/v1/quizzes` - List all quizzes

Database:
- `quizzes`: Quiz metadata
- `questions`: Question bank with JSONB options
- `quiz_submissions`: User submissions and scores

## 📚 API Documentation

### Authentication

All API requests (except `/auth/login`) require a JWT token:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Rate Limits

- 100 requests per 60 seconds per user
- Headers returned:
  - `X-RateLimit-Limit`: Maximum requests
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

### Response Formats

Success (200):
```json
{
  "id": "123",
  "status": "success",
  "data": {...}
}
```

Error (4xx/5xx):
```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

## 💻 Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies for a service
cd microservices/tts/src
pip install -r requirements.txt

# Run service locally
export AWS_ACCESS_KEY_ID="your_key"
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
python app.py
```

### Project Structure

```
Cloud_Project/
├── api-gateway/
│   └── src/
│       ├── app.py
│       └── requirements.txt
├── microservices/
│   ├── tts/src/
│   ├── stt/src/
│   ├── chat/src/
│   ├── document-reader/src/
│   └── quiz/src/
├── docker/
│   └── dockerfiles/
│       ├── Dockerfile.gateway
│       ├── Dockerfile.tts
│       ├── Dockerfile.stt
│       ├── Dockerfile.chat
│       ├── Dockerfile.document
│       └── Dockerfile.quiz
├── kafka/
│   ├── scripts/
│   └── topics/
├── docker-compose.learner-lab.yml
├── .env.example
└── README.md
```

### Adding New Endpoints

1. Add route to service's `app.py`
2. Update API Gateway proxy routes if needed
3. Document in this README
4. Test with curl or Postman

### Database Migrations

Each service initializes its database on startup. To modify schemas:

1. Update table creation code in service's `app.py`
2. Rebuild service: `docker-compose build <service-name>`
3. Restart service: `docker-compose up -d <service-name>`

## 🧪 Testing

### Manual Testing

```bash
# Test health endpoints
curl http://localhost:5000/health
curl http://localhost:5001/health
curl http://localhost:5002/health

# Test authentication
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test"}'

# Test with token
TOKEN="your_token"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/v1/tts/voices
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.learner-lab.yml logs -f

# Specific service
docker-compose -f docker-compose.learner-lab.yml logs -f tts-service

# Last 100 lines
docker-compose -f docker-compose.learner-lab.yml logs --tail=100
```

### Kafka Topic Inspection

```bash
# Enter Kafka container
docker exec -it kafka bash

# List topics
kafka-topics --bootstrap-server localhost:9092 --list

# Consume messages from topic
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic audio.generation.requested --from-beginning
```

## 🔍 Troubleshooting

### Services Not Starting

```bash
# Check service status
docker-compose -f docker-compose.learner-lab.yml ps

# Check logs
docker-compose -f docker-compose.learner-lab.yml logs

# Restart services
docker-compose -f docker-compose.learner-lab.yml restart

# Rebuild from scratch
docker-compose -f docker-compose.learner-lab.yml down -v
docker-compose -f docker-compose.learner-lab.yml build --no-cache
docker-compose -f docker-compose.learner-lab.yml up -d
```

### AWS Credentials Issues

```bash
# Verify credentials are set
docker-compose -f docker-compose.learner-lab.yml exec tts-service \
  env | grep AWS

# Test AWS connectivity
docker-compose -f docker-compose.learner-lab.yml exec tts-service \
  python -c "import boto3; print(boto3.client('s3').list_buckets())"
```

### Database Connection Issues

```bash
# Check database health
docker-compose -f docker-compose.learner-lab.yml exec chat-db \
  pg_isready -U chat_user

# Connect to database
docker-compose -f docker-compose.learner-lab.yml exec chat-db \
  psql -U chat_user -d chat_db

# Inside psql:
# \dt - list tables
# \d table_name - describe table
```

### Kafka Issues

```bash
# Check Kafka health
docker-compose -f docker-compose.learner-lab.yml logs kafka

# Verify Zookeeper
docker-compose -f docker-compose.learner-lab.yml logs zookeeper

# Restart Kafka
docker-compose -f docker-compose.learner-lab.yml restart zookeeper kafka
```

### Port Conflicts

If ports are already in use:

```bash
# Check what's using a port
lsof -i :5000

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.learner-lab.yml
```

### Common Errors

**"JWT token expired"**
- Login again to get a new token
- Token expires after 24 hours

**"Rate limit exceeded"**
- Wait 60 seconds
- Or increase `RATE_LIMIT_REQUESTS` in docker-compose

**"Service unavailable"**
- Check if microservice is running
- Check service logs for errors

**"S3 bucket not found"**
- Create bucket: `aws s3 mb s3://learner-lab-audio`
- Verify bucket exists: `aws s3 ls`

## 🚀 Production Deployment

### EC2 Deployment

1. **Launch EC2 Instance**
   - Instance type: t3.large or larger
   - OS: Amazon Linux 2 or Ubuntu 22.04
   - Security group: Allow ports 5000-5005, 9092, 5432-5434

2. **Install Docker**
   ```bash
   # Amazon Linux 2
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
     -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Deploy Application**
   ```bash
   git clone <your-repo>
   cd Cloud_Project
   cp .env.example .env
   # Edit .env with production credentials
   docker-compose -f docker-compose.learner-lab.yml up -d
   ```

4. **Configure Security**
   - Change `JWT_SECRET` in `.env`
   - Use AWS Secrets Manager for credentials
   - Enable HTTPS with Let's Encrypt
   - Configure CloudWatch logging

### Environment Variables for Production

```env
# Production settings
DEBUG=False
LOG_LEVEL=INFO

# Strong JWT secret
JWT_SECRET=use-secrets-manager-value

# AWS credentials from IAM role (preferred)
# Or use AWS Secrets Manager

# Kafka (use private IP for EC2)
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://<ec2-private-ip>:9092

# Rate limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60
```

### Monitoring

- Use CloudWatch for logs and metrics
- Set up health check alarms
- Monitor disk space and memory usage
- Track API response times

### Backup Strategy

```bash
# Backup PostgreSQL databases
docker-compose -f docker-compose.learner-lab.yml exec chat-db \
  pg_dump -U chat_user chat_db > chat_db_backup.sql

# Backup all databases
for db in chat-db document-db quiz-db; do
  docker-compose -f docker-compose.learner-lab.yml exec $db \
    pg_dumpall -U postgres > ${db}_backup.sql
done
```

## 📝 License

This project is created for educational purposes as part of CSE363 Cloud Computing course.

## 👥 Contributors

- Your Name - Phase 2 Implementation

## 📞 Support

For issues and questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review service logs
3. Contact course instructor

---

**Last Updated**: December 2024
**Version**: 2.0.0
