# Microservices Documentation

## Overview

This project consists of five microservices that work together to provide an AI-powered learning platform with chat, document processing, quiz generation, speech-to-text, and text-to-speech capabilities.

### Architecture

All microservices follow a similar architecture pattern:
- **Framework**: Flask (Python)
- **Message Broker**: Apache Kafka for asynchronous communication
- **Database**: PostgreSQL for persistent storage
- **Cloud Services**: AWS (S3, Transcribe, Polly, Textract)
- **Caching**: Redis (where applicable)
- **API Gateway**: Routes requests to appropriate microservices

### Communication Flow

```
User Request → API Gateway → Microservice → Kafka → Other Microservices
                                ↓
                            PostgreSQL
                                ↓
                            AWS Services
```

---

## 1. Chat Service

### Purpose
Manages chat interactions with AI models, stores conversation history, and publishes chat events to Kafka.

### Key Features
- AI-powered chat using OpenRouter API
- Conversation history management
- Document context integration
- Redis caching for performance
- JWT authentication
- Real-time message publishing to Kafka

### API Endpoints

#### `POST /chat`
Send a message to the AI chatbot.

**Request Body:**
```json
{
  "message": "What is machine learning?",
  "session_id": "optional-session-id",
  "user_id": "user-123",
  "document_context": {
    "document_id": "doc-456",
    "relevant_text": "extracted document text"
  }
}
```

**Response:**
```json
{
  "session_id": "generated-session-id",
  "response": "AI response text",
  "timestamp": "2025-12-05T10:30:00Z"
}
```

#### `GET /chat/history/<session_id>`
Retrieve chat history for a session.

**Response:**
```json
{
  "session_id": "session-123",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-12-05T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2025-12-05T10:30:05Z"
    }
  ]
}
```

#### `GET /chat/sessions`
Get all chat sessions for a user.

**Query Parameters:**
- `user_id`: User identifier

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session-123",
      "created_at": "2025-12-05T10:00:00Z",
      "last_message": "2025-12-05T10:30:00Z",
      "message_count": 10
    }
  ]
}
```

#### `GET /health`
Health check endpoint.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `cloud-project-db.czuu68se8miq.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `chat_service` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers (comma-separated) | `localhost:9092` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_NAME` | S3 bucket for storage | `chat-service-storage-dev-199892543493` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `JWT_SECRET_KEY` | JWT secret key | Change in production |

### Kafka Topics

**Produces:**
- `chat.message`: Published when new chat messages are created

**Consumes:**
- `document.processed`: Receives notifications when documents are processed

### Database Schema

```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    message_id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id),
    role VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Dependencies

- Flask 3.0.0
- kafka-python 2.0.2
- psycopg2-binary 2.9.9
- boto3 1.34.51
- redis 5.0.1
- PyJWT 2.8.0
- langchain 0.1.8

---

## 2. Document Reader Service

### Purpose
Processes uploaded documents, extracts text content, generates AI-powered notes, and publishes results to Kafka.

### Key Features
- Multi-format document support (PDF, DOCX, TXT)
- AWS Textract integration for OCR
- AI-powered note generation using OpenRouter
- S3 document storage
- Text extraction and preprocessing
- Asynchronous processing via Kafka

### API Endpoints

#### `POST /upload`
Upload and process a document.

**Request:** Multipart form data
- `file`: Document file (PDF, DOCX, TXT)
- `user_id`: User identifier (optional)
- `generate_notes`: Boolean (optional, default: true)

**Response:**
```json
{
  "document_id": "doc-uuid",
  "filename": "document.pdf",
  "status": "processing",
  "s3_key": "documents/user-123/doc-uuid.pdf",
  "uploaded_at": "2025-12-05T10:30:00Z"
}
```

#### `GET /document/<document_id>`
Get document details and extracted text.

**Response:**
```json
{
  "document_id": "doc-uuid",
  "filename": "document.pdf",
  "status": "completed",
  "extracted_text": "Full extracted text...",
  "notes": "AI-generated notes...",
  "page_count": 10,
  "processed_at": "2025-12-05T10:35:00Z"
}
```

#### `POST /process/<document_id>`
Manually trigger document processing.

**Response:**
```json
{
  "message": "Processing started",
  "document_id": "doc-uuid"
}
```

#### `GET /documents`
List all documents for a user.

**Query Parameters:**
- `user_id`: User identifier

**Response:**
```json
{
  "documents": [
    {
      "document_id": "doc-uuid",
      "filename": "document.pdf",
      "status": "completed",
      "uploaded_at": "2025-12-05T10:30:00Z"
    }
  ]
}
```

#### `GET /health`
Health check endpoint.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_DOCUMENTS` | S3 bucket for documents | `document-reader-storage-dev-199892543493` |
| `DB_HOST` | PostgreSQL host | `cloud-project-db.czuu68se8miq.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `document_reader` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `localhost:9092` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |

### Kafka Topics

**Produces:**
- `document.uploaded`: Published when document is uploaded
- `document.processed`: Published when processing is complete
- `notes.generated`: Published when AI notes are generated

### Database Schema

```sql
CREATE TABLE documents (
    document_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    filename VARCHAR(500),
    s3_key VARCHAR(500),
    status VARCHAR(50),
    extracted_text TEXT,
    notes TEXT,
    page_count INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);
```

### Supported Document Formats

- **PDF**: Extracted using PyPDF2 or AWS Textract (for scanned documents)
- **DOCX**: Processed using python-docx
- **TXT**: Direct text reading

### Dependencies

- Flask 3.0.0
- boto3 1.34.10
- PyPDF2 3.0.1
- python-docx 1.1.0
- kafka-python 2.0.2
- psycopg2-binary 2.9.9
- spacy 3.7.2
- langchain 0.1.8

---

## 3. Quiz Service

### Purpose
Generates AI-powered quizzes from documents and manages quiz submissions and scoring.

### Key Features
- AI-powered quiz generation using OpenRouter
- Multiple quiz types (multiple choice, true/false, short answer)
- Automatic grading
- Quiz history and analytics
- Document-based question generation
- Score tracking and statistics

### API Endpoints

#### `POST /quiz/generate`
Generate a quiz from a document.

**Request Body:**
```json
{
  "document_id": "doc-uuid",
  "user_id": "user-123",
  "num_questions": 10,
  "difficulty": "medium",
  "quiz_type": "multiple_choice"
}
```

**Response:**
```json
{
  "quiz_id": "quiz-uuid",
  "document_id": "doc-uuid",
  "questions": [
    {
      "question_id": "q1",
      "question": "What is machine learning?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "type": "multiple_choice"
    }
  ],
  "total_questions": 10,
  "created_at": "2025-12-05T10:30:00Z"
}
```

#### `POST /quiz/submit`
Submit quiz answers for grading.

**Request Body:**
```json
{
  "quiz_id": "quiz-uuid",
  "user_id": "user-123",
  "answers": {
    "q1": "Option A",
    "q2": "True",
    "q3": "Short answer text"
  }
}
```

**Response:**
```json
{
  "submission_id": "sub-uuid",
  "quiz_id": "quiz-uuid",
  "score": 85,
  "total_questions": 10,
  "correct_answers": 9,
  "results": [
    {
      "question_id": "q1",
      "correct": true,
      "user_answer": "Option A",
      "correct_answer": "Option A"
    }
  ],
  "submitted_at": "2025-12-05T10:45:00Z"
}
```

#### `GET /quiz/<quiz_id>`
Get quiz details.

**Response:**
```json
{
  "quiz_id": "quiz-uuid",
  "document_id": "doc-uuid",
  "questions": [...],
  "total_questions": 10,
  "created_at": "2025-12-05T10:30:00Z"
}
```

#### `GET /quiz/history`
Get quiz history for a user.

**Query Parameters:**
- `user_id`: User identifier

**Response:**
```json
{
  "quizzes": [
    {
      "quiz_id": "quiz-uuid",
      "document_id": "doc-uuid",
      "score": 85,
      "submitted_at": "2025-12-05T10:45:00Z"
    }
  ]
}
```

#### `GET /health`
Health check endpoint.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `cloud-project-db.czuu68se8miq.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `quiz_service` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `localhost:9092` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_NAME` | S3 bucket | `quiz-service-storage-dev-199892543493` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `OPENROUTER_MODEL` | AI model | `amazon/nova-2-lite-v1:free` |

### Kafka Topics

**Produces:**
- `quiz.generated`: Published when quiz is generated

**Consumes:**
- `quiz.requested`: Listens for quiz generation requests
- `notes.generated`: Receives document notes for context

### Database Schema

```sql
CREATE TABLE quizzes (
    quiz_id VARCHAR(255) PRIMARY KEY,
    document_id VARCHAR(255),
    user_id VARCHAR(255),
    num_questions INTEGER,
    difficulty VARCHAR(50),
    quiz_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quiz_questions (
    question_id VARCHAR(255) PRIMARY KEY,
    quiz_id VARCHAR(255) REFERENCES quizzes(quiz_id),
    question TEXT,
    options JSONB,
    correct_answer TEXT,
    question_type VARCHAR(50)
);

CREATE TABLE quiz_submissions (
    submission_id VARCHAR(255) PRIMARY KEY,
    quiz_id VARCHAR(255) REFERENCES quizzes(quiz_id),
    user_id VARCHAR(255),
    answers JSONB,
    score INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Quiz Types

- **multiple_choice**: 4 options, 1 correct answer
- **true_false**: Boolean questions
- **short_answer**: Free-text responses (graded by AI)

### Dependencies

- Flask 3.0.0
- kafka-python 2.0.2
- psycopg2-binary 2.9.9
- boto3 1.34.0
- openai 1.3.0

---

## 4. Speech-to-Text (STT) Service

### Purpose
Transcribes audio files to text using AWS Transcribe service and publishes results to Kafka.

### Key Features
- Audio file transcription using AWS Transcribe
- Multiple audio format support (MP3, WAV, FLAC, etc.)
- Asynchronous job processing
- S3 storage for audio files
- Transcription history tracking
- Automatic audio retention management

### API Endpoints

#### `POST /transcribe`
Upload audio file for transcription.

**Request:** Multipart form data
- `file`: Audio file
- `user_id`: User identifier (optional)
- `language_code`: Language code (optional, default: 'en-US')

**Response:**
```json
{
  "job_id": "transcription-job-uuid",
  "filename": "audio.mp3",
  "status": "processing",
  "s3_key": "audio/user-123/job-uuid.mp3",
  "submitted_at": "2025-12-05T10:30:00Z"
}
```

#### `GET /transcription/<job_id>`
Get transcription status and results.

**Response:**
```json
{
  "job_id": "transcription-job-uuid",
  "status": "completed",
  "transcript": "Transcribed text content...",
  "confidence": 0.95,
  "duration": 120.5,
  "completed_at": "2025-12-05T10:32:00Z"
}
```

#### `GET /transcriptions`
List all transcriptions for a user.

**Query Parameters:**
- `user_id`: User identifier

**Response:**
```json
{
  "transcriptions": [
    {
      "job_id": "transcription-job-uuid",
      "filename": "audio.mp3",
      "status": "completed",
      "submitted_at": "2025-12-05T10:30:00Z"
    }
  ]
}
```

#### `DELETE /transcription/<job_id>`
Delete a transcription and associated audio file.

**Response:**
```json
{
  "message": "Transcription deleted successfully",
  "job_id": "transcription-job-uuid"
}
```

#### `GET /health`
Health check endpoint.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_STT` | S3 bucket for audio | `stt-service-storage-dev-199892543493` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `localhost:9092` |
| `DB_HOST` | PostgreSQL host | `cloud-project-db.czuu68se8miq.us-east-1.rds.amazonaws.com` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `stt_service` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | Required |
| `AUDIO_RETENTION_DAYS` | Audio retention period | `30` |

### Kafka Topics

**Produces:**
- `audio.transcription.completed`: Published when transcription completes

**Consumes:**
- `audio.transcription.requested`: Listens for transcription requests

### Database Schema

```sql
CREATE TABLE transcription_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    filename VARCHAR(500),
    s3_key VARCHAR(500),
    aws_job_name VARCHAR(255),
    status VARCHAR(50),
    transcript TEXT,
    confidence DECIMAL(5,4),
    duration DECIMAL(10,2),
    language_code VARCHAR(10),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Supported Audio Formats

- MP3
- MP4
- WAV
- FLAC
- OGG
- AMR
- WebM

### AWS Transcribe Features

- Automatic language detection
- Speaker identification
- Custom vocabulary support
- Confidence scores
- Punctuation and formatting

### Dependencies

- Flask 3.0.0
- boto3 1.34.10
- kafka-python 2.0.2
- psycopg2-binary 2.9.9

---

## 5. Text-to-Speech (TTS) Service

### Purpose
Converts text to audio using AWS Polly service, with caching and Kafka event publishing.

### Key Features
- Text-to-speech using AWS Polly
- Multiple voice and language support
- Audio format options (MP3, OGG, WAV)
- Redis caching for frequently requested audio
- S3 storage for generated audio
- Asynchronous processing via Kafka

### API Endpoints

#### `POST /synthesize`
Convert text to speech.

**Request Body:**
```json
{
  "text": "Hello, this is a test.",
  "voice_id": "Joanna",
  "language_code": "en-US",
  "output_format": "mp3",
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "audio_id": "audio-uuid",
  "s3_url": "https://s3.amazonaws.com/bucket/audio/audio-uuid.mp3",
  "duration": 2.5,
  "cached": false,
  "generated_at": "2025-12-05T10:30:00Z"
}
```

#### `GET /audio/<audio_id>`
Get audio file details and download URL.

**Response:**
```json
{
  "audio_id": "audio-uuid",
  "text": "Hello, this is a test.",
  "voice_id": "Joanna",
  "s3_url": "https://s3.amazonaws.com/bucket/audio/audio-uuid.mp3",
  "format": "mp3",
  "duration": 2.5,
  "generated_at": "2025-12-05T10:30:00Z"
}
```

#### `GET /voices`
List available voices.

**Query Parameters:**
- `language_code`: Filter by language (optional)

**Response:**
```json
{
  "voices": [
    {
      "id": "Joanna",
      "name": "Joanna",
      "language_code": "en-US",
      "gender": "Female"
    }
  ]
}
```

#### `DELETE /audio/<audio_id>`
Delete generated audio.

**Response:**
```json
{
  "message": "Audio deleted successfully",
  "audio_id": "audio-uuid"
}
```

#### `GET /health`
Health check endpoint.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET_TTS` | S3 bucket for audio | `tts-service-storage-dev-199892543493` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `localhost:9092` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database | `0` |
| `AUDIO_RETENTION_DAYS` | Audio retention period | `7` |

### Kafka Topics

**Produces:**
- `audio.generation.completed`: Published when audio generation completes

**Consumes:**
- `audio.generation.requested`: Listens for audio generation requests

### Audio Formats

| Format | Polly Format | Content Type | Use Case |
|--------|--------------|--------------|----------|
| MP3 | mp3 | audio/mpeg | Most compatible, small size |
| OGG | ogg_vorbis | audio/ogg | Open format, good quality |
| WAV | pcm | audio/wav | Highest quality, large size |

### Supported Voices

AWS Polly provides multiple voices for each language:

**English (US):**
- Joanna (Female)
- Matthew (Male)
- Joey (Male)
- Salli (Female)

**English (UK):**
- Amy (Female)
- Brian (Male)
- Emma (Female)

*(Additional languages and voices available)*

### Caching Strategy

- Redis caches generated audio for frequently requested text
- Cache key: SHA256 hash of (text + voice_id + format)
- Cache TTL: Configurable (default: 24 hours)
- Reduces AWS Polly costs for repeated requests

### Dependencies

- Flask 3.0.0
- boto3 1.34.10
- kafka-python 2.0.2
- redis 5.0.1

---

## Common Patterns

### Error Handling

All services follow consistent error response format:

```json
{
  "error": "Error message description",
  "code": "ERROR_CODE",
  "timestamp": "2025-12-05T10:30:00Z"
}
```

### Health Checks

All services expose `/health` endpoint:

```json
{
  "status": "healthy",
  "service": "service-name",
  "timestamp": "2025-12-05T10:30:00Z",
  "dependencies": {
    "database": "connected",
    "kafka": "connected",
    "aws": "connected"
  }
}
```

### Graceful Shutdown

All services handle SIGTERM/SIGINT signals:
1. Stop accepting new requests
2. Complete ongoing requests
3. Close database connections
4. Flush Kafka producers
5. Close Redis connections

---

## Deployment

### Docker

Each microservice has a Dockerfile in `/docker/dockerfiles/`:

```bash
# Build image
docker build -f docker/dockerfiles/Dockerfile.chat -t chat-service .

# Run container
docker run -p 5000:5000 \
  -e DB_HOST=postgres \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  chat-service
```

### Kubernetes

Deployment manifests are in `/kubernetes/deployments/`:

```bash
# Deploy service
kubectl apply -f kubernetes/deployments/chat-service.yaml

# Check status
kubectl get pods -n cloud-project
```

### Docker Compose

For local development:

```bash
docker-compose -f docker-compose.learner-lab.yml up
```

---

## Development

### Running Locally

1. **Install dependencies:**
   ```bash
   cd microservices/chat/src
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DB_HOST=localhost
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   export AWS_REGION=us-east-1
   ```

3. **Run the service:**
   ```bash
   python app.py
   ```

### Testing

Each service runs on a different port:
- Chat Service: 5000
- Document Reader: 5001
- Quiz Service: 5002
- STT Service: 5003
- TTS Service: 5004

---

## Monitoring & Logging

### Logging Format

All services use structured logging:

```
2025-12-05 10:30:00 - service-name - INFO - Message description
```

### Metrics

Key metrics to monitor:
- Request rate and latency
- Error rates
- Kafka lag
- Database connection pool
- AWS API call counts
- Cache hit rates (Redis)

---

## Security

### Authentication

- JWT tokens for API authentication
- Token validation in API Gateway
- User identification in all requests

### Data Protection

- Sensitive data encrypted at rest (S3, RDS)
- TLS for data in transit
- Secrets managed via environment variables
- IAM roles for AWS service access

---

## Troubleshooting

### Common Issues

**Kafka Connection Failed:**
- Check `KAFKA_BOOTSTRAP_SERVERS` configuration
- Verify Kafka cluster is running
- Check network connectivity

**Database Connection Error:**
- Verify PostgreSQL is running
- Check credentials and host
- Ensure database exists

**AWS Service Error:**
- Verify IAM permissions
- Check AWS credentials
- Validate region configuration

**Redis Connection Failed:**
- Check Redis host and port
- Verify Redis is running
- Services continue without caching if Redis unavailable

---

## API Gateway Integration

All services are accessed through the API Gateway which:
- Routes requests to appropriate microservices
- Handles authentication
- Provides rate limiting
- Logs all requests
- Implements circuit breakers

Gateway configuration in `/api-gateway/src/app.py`

---

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Advanced caching strategies
- [ ] Metrics and tracing (Prometheus, Jaeger)
- [ ] API versioning
- [ ] Rate limiting per user
- [ ] Multi-tenancy support
- [ ] Advanced search capabilities
- [ ] Batch processing endpoints

---

## Support & Contributing

For issues or questions:
1. Check existing documentation
2. Review logs for error details
3. Verify configuration and dependencies
4. Contact the development team

---

## License

[Your License Here]

---

*Last Updated: December 5, 2025*
