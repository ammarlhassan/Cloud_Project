# AI Learner Platform - System Design Document

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Infrastructure Design](#infrastructure-design)
7. [Security Design](#security-design)
8. [Scalability & Performance](#scalability--performance)
9. [Data Models](#data-models)
10. [API Design](#api-design)
11. [Event-Driven Architecture](#event-driven-architecture)
12. [Deployment Architecture](#deployment-architecture)

---

## 1. System Overview

### 1.1 Purpose
The AI Learner Platform is a cloud-native, microservices-based educational platform that provides AI-powered learning tools including text-to-speech conversion, speech-to-text transcription, intelligent chat, document processing, and quiz generation.

### 1.2 Key Objectives
- **Modularity**: Independently deployable microservices
- **Scalability**: Horizontal scaling for individual services
- **Reliability**: Fault isolation and graceful degradation
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new features and services

### 1.3 System Characteristics
- **Distributed System**: Multiple services communicating over network
- **Event-Driven**: Asynchronous communication via Kafka
- **Stateless Services**: Easy horizontal scaling
- **Polyglot Persistence**: Different databases for different services
- **Cloud-Native**: Containerized with Docker, AWS integration

---

## 2. Architecture Patterns

### 2.1 Microservices Architecture

The system follows microservices architecture with these principles:

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│            (Web Apps, Mobile Apps, CLI Tools)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────┴────────────────────────────────────┐
│                      API GATEWAY                                 │
│  - Authentication (JWT)                                          │
│  - Rate Limiting                                                 │
│  - Request Routing                                               │
│  - Load Balancing                                                │
│  - CORS Handling                                                 │
└─┬──────────┬──────────┬──────────┬──────────┬────────────────────┘
  │          │          │          │          │
  │ HTTP     │ HTTP     │ HTTP     │ HTTP     │ HTTP
  │          │          │          │          │
┌─▼────┐  ┌─▼────┐  ┌─▼────┐  ┌─▼────────┐ ┌─▼────┐
│ TTS  │  │ STT  │  │ Chat │  │ Document │ │ Quiz │
│Service│ │Service│ │Service│ │ Service  │ │Service│
└──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘ └──┬───┘
   │         │         │           │          │
   └─────────┴─────────┴───────────┴──────────┘
                       │
                  ┌────▼─────┐
                  │  KAFKA   │  ← Event Bus
                  └────┬─────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐    ┌───▼────┐    ┌───▼────┐
   │ Chat DB │    │ Doc DB │    │Quiz DB │
   │(Postgres)│   │(Postgres)   │(Postgres)
   └─────────┘    └────────┘    └────────┘
                       │
                  ┌────▼─────┐
                  │   AWS    │
                  │ Services │
                  │ S3/Polly │
                  │Transcribe│
                  │ Textract │
                  └──────────┘
```

### 2.2 Design Patterns Used

#### API Gateway Pattern
- **Purpose**: Single entry point for all client requests
- **Benefits**:
  - Centralized authentication and authorization
  - Rate limiting and throttling
  - Request routing and load balancing
  - Protocol translation

#### Service Registry Pattern
- **Implementation**: Docker DNS and container names
- **Benefits**: Dynamic service discovery

#### Circuit Breaker Pattern
- **Implementation**: Request timeouts and retries
- **Benefits**: Prevents cascading failures

#### Event-Driven Pattern
- **Implementation**: Kafka message broker
- **Benefits**: Loose coupling, asynchronous processing

#### Database per Service Pattern
- **Implementation**: Separate PostgreSQL instances
- **Benefits**: Data isolation, independent scaling

---

## 3. Component Design

### 3.1 API Gateway Service

**Port**: 5000
**Responsibilities**:
- JWT token generation and validation
- Rate limiting (100 req/min per user)
- Request routing to microservices
- CORS policy enforcement
- Request/response transformation

**Key Components**:
```python
Authentication Module
├── Token Generation (JWT)
├── Token Verification
└── Token Refresh

Rate Limiter Module
├── In-Memory Storage (Dev)
├── Rate Limit Check
└── Rate Limit Headers

Proxy Module
├── Service Discovery
├── Request Forwarding
├── Response Aggregation
└── Error Handling
```

**Technology**:
- Flask 3.0.0
- PyJWT for authentication
- Flask-CORS for cross-origin requests
- Gunicorn as WSGI server

---

### 3.2 Text-to-Speech (TTS) Service

**Port**: 5001
**Responsibilities**:
- Convert text to natural-sounding speech
- Support multiple voice options and languages
- Store audio files in S3
- Publish audio generation events

**Components**:
```
TTS Controller
├── Text Validation
├── Voice Selection
└── Format Configuration

AWS Polly Integration
├── SynthesizeSpeech API
├── Voice Management
└── Audio Streaming

S3 Storage Manager
├── File Upload
├── URL Generation
└── Lifecycle Management

Kafka Producer
└── audio.generation.requested events
```

**Data Flow**:
1. Receive text and voice preferences
2. Validate input (text length, voice availability)
3. Call AWS Polly SynthesizeSpeech API
4. Upload audio stream to S3
5. Generate presigned URL
6. Publish event to Kafka
7. Return audio URL and metadata

**AWS Services**:
- AWS Polly (Neural TTS engine)
- S3 (Audio file storage)

---

### 3.3 Speech-to-Text (STT) Service

**Port**: 5002
**Responsibilities**:
- Transcribe audio files to text
- Support multiple audio formats
- Provide transcription status polling
- Extract speaker information

**Components**:
```
STT Controller
├── File Upload Handler
├── Format Validation
└── Job Management

AWS Transcribe Integration
├── StartTranscriptionJob
├── GetTranscriptionJob
└── Job Status Polling

S3 Storage Manager
├── Audio Upload
├── Transcript Retrieval
└── File Cleanup

Kafka Producer
└── transcription.requested events
```

**Data Flow**:
1. Receive audio file upload
2. Validate format and size
3. Upload audio to S3
4. Start AWS Transcribe job
5. Poll job status asynchronously
6. Retrieve transcript from S3
7. Return transcript and confidence scores

**AWS Services**:
- AWS Transcribe (Speech recognition)
- S3 (Audio storage)

---

### 3.4 Chat Service

**Port**: 5003
**Responsibilities**:
- Manage chat sessions
- Store conversation history
- Generate AI responses
- Track message metadata

**Components**:
```
Chat Controller
├── Session Management
├── Message Handling
└── History Retrieval

AI Engine (Placeholder)
├── Context Management
├── Response Generation
└── Intent Recognition

Database Layer
├── Session Repository
├── Message Repository
└── Connection Pool

Kafka Producer
└── chat.message.sent events
```

**Database Schema**:
```sql
-- Chat Sessions
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat Messages
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

---

### 3.5 Document Service

**Port**: 5004
**Responsibilities**:
- Upload and store documents
- Extract text from PDF files
- Generate learning notes
- Manage document metadata

**Components**:
```
Document Controller
├── Upload Handler
├── Processing Pipeline
└── Retrieval Manager

Text Extraction Engine
├── PyPDF2 Parser
├── AWS Textract Integration
└── OCR Processing

Notes Generator
├── Text Summarization
├── Key Point Extraction
└── Note Formatting

S3 Storage Manager
├── Document Upload
├── Version Management
└── Access Control

Database Layer
├── Document Repository
├── Notes Repository
└── Transaction Management
```

**Database Schema**:
```sql
-- Documents
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    s3_key VARCHAR(1000) NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Notes
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**AWS Services**:
- S3 (Document storage)
- Textract (OCR and text extraction)

---

### 3.6 Quiz Service

**Port**: 5005
**Responsibilities**:
- Generate quizzes from documents
- Manage question banks
- Grade submissions
- Calculate scores

**Components**:
```
Quiz Controller
├── Quiz Generation
├── Submission Handler
└── Grading Engine

Question Generator
├── Content Analysis
├── Question Creation
├── Answer Generation
└── Difficulty Assessment

Grading Engine
├── Answer Validation
├── Score Calculation
└── Feedback Generation

Database Layer
├── Quiz Repository
├── Question Repository
└── Submission Repository
```

**Database Schema**:
```sql
-- Quizzes
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    document_id INTEGER,
    title VARCHAR(500) NOT NULL,
    total_questions INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Questions
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'multiple_choice',
    options JSONB,
    correct_answer TEXT NOT NULL,
    points INTEGER DEFAULT 1
);

-- Submissions
CREATE TABLE quiz_submissions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(id),
    user_id VARCHAR(255) NOT NULL,
    answers JSONB NOT NULL,
    score FLOAT,
    total_points INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Data Flow

### 4.1 Authentication Flow

```
Client                    API Gateway                Services
  |                            |                         |
  |---POST /auth/login-------->|                         |
  |    {email, password}       |                         |
  |                            |                         |
  |                        [Validate]                    |
  |                        [Generate JWT]                |
  |                            |                         |
  |<----{token, user}----------|                         |
  |                            |                         |
  |---GET /tts/voices--------->|                         |
  |  Header: Bearer <token>    |                         |
  |                            |                         |
  |                        [Verify JWT]                  |
  |                        [Check Rate Limit]            |
  |                            |                         |
  |                            |------Proxy Request----->|
  |                            |                         |
  |                            |<----Response-----------|
  |<----Response---------------|                         |
```

### 4.2 TTS Generation Flow

```
Client       Gateway       TTS Service    AWS Polly      S3      Kafka
  |             |               |              |          |         |
  |---POST----->|               |              |          |         |
  |             |---Proxy------>|              |          |         |
  |             |               |--Synthesize->|          |         |
  |             |               |              |          |         |
  |             |               |<--AudioStream-|         |         |
  |             |               |                         |         |
  |             |               |------Upload------------>|         |
  |             |               |<----S3 URL--------------|         |
  |             |               |                         |         |
  |             |               |---Publish Event----------------->|
  |             |               |                         |         |
  |             |<--Response----|                         |         |
  |<--Response--|               |                         |         |
```

### 4.3 Document Processing Flow

```
Client      Gateway    Doc Service    S3    Textract    DB    Kafka
  |           |            |           |        |        |       |
  |--Upload-->|            |           |        |        |       |
  |           |--Proxy---->|           |        |        |       |
  |           |            |--Upload-->|        |        |       |
  |           |            |           |        |        |       |
  |           |            |---Save Metadata--->|------->|       |
  |           |            |           |        |        |       |
  |<-Response-|<-Response--|           |        |        |       |
  |           |            |           |        |        |       |
  |--Process->|            |           |        |        |       |
  |           |--Proxy---->|           |        |        |       |
  |           |            |--Extract->|------->|        |       |
  |           |            |           |        |        |       |
  |           |            |<----Text--|--------|        |       |
  |           |            |                    |        |       |
  |           |            |----Generate Notes--------->|       |
  |           |            |                    |        |       |
  |           |            |---Publish Event------------------->|
  |           |<-Response--|                    |        |       |
  |<-Response-|            |                    |        |       |
```

---

## 5. Technology Stack

### 5.1 Backend Services
- **Language**: Python 3.11
- **Framework**: Flask 3.0.0
- **WSGI Server**: Gunicorn 21.2.0
- **HTTP Client**: Requests library

### 5.2 Message Broker
- **Kafka**: Confluent Platform 7.5.0
- **Zookeeper**: Included with Kafka
- **Client**: kafka-python

### 5.3 Databases
- **PostgreSQL**: Version 15-alpine
- **Separate Instances**:
  - Chat DB (Port 5432)
  - Document DB (Port 5433)
  - Quiz DB (Port 5434)

### 5.4 Caching
- **Redis**: Version 7-alpine
- **Port**: 6379
- **Use Cases**: Rate limiting, session storage

### 5.5 AWS Services
- **S3**: Object storage
- **Polly**: Text-to-speech
- **Transcribe**: Speech-to-text
- **Textract**: Document text extraction

### 5.6 Authentication
- **JWT**: PyJWT library
- **Algorithm**: HS256
- **Expiration**: 24 hours

### 5.7 Containerization
- **Docker**: Engine 20.10+
- **Docker Compose**: Version 3.8
- **Base Images**: python:3.11-slim, postgres:15-alpine

---

## 6. Infrastructure Design

### 6.1 Container Architecture

Each service runs in isolated containers:

```
Container Network: learner-lab-network (Bridge)

┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │ API Gateway│  │ TTS Service│  │ STT Service│       │
│  │  Port 5000 │  │  Port 5001 │  │  Port 5002 │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │Chat Service│  │ Doc Service│  │Quiz Service│       │
│  │  Port 5003 │  │  Port 5004 │  │  Port 5005 │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │  Kafka     │  │ Zookeeper  │  │   Redis    │       │
│  │  Port 9092 │  │  Port 2181 │  │  Port 6379 │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │  Chat DB   │  │Document DB │  │  Quiz DB   │       │
│  │  Port 5432 │  │  Port 5433 │  │  Port 5434 │       │
│  └────────────┘  └────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Health Checks

Every service implements health check endpoints:

```python
# Standard health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Readiness check (includes dependencies)
@app.route('/ready')
def ready():
    checks = {
        "database": check_db_connection(),
        "kafka": check_kafka_connection(),
        "aws": check_aws_connection()
    }
    return jsonify(checks)
```

**Health Check Configuration**:
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start Period: 40 seconds

### 6.3 Resource Allocation

**Recommended Production Resources**:

| Service | CPU | Memory | Storage |
|---------|-----|--------|---------|
| API Gateway | 1 core | 512 MB | - |
| TTS Service | 1 core | 512 MB | - |
| STT Service | 1 core | 512 MB | - |
| Chat Service | 1 core | 512 MB | - |
| Document Service | 1 core | 512 MB | - |
| Quiz Service | 1 core | 512 MB | - |
| Kafka | 2 cores | 2 GB | 10 GB |
| Zookeeper | 1 core | 512 MB | 5 GB |
| PostgreSQL (each) | 1 core | 1 GB | 20 GB |
| Redis | 1 core | 512 MB | 1 GB |

**Total Requirements**:
- CPU: 12+ cores
- Memory: 10+ GB
- Storage: 60+ GB

---

## 7. Security Design

### 7.1 Authentication Architecture

```
┌─────────────────────────────────────────────────────┐
│              Authentication Flow                     │
└─────────────────────────────────────────────────────┘

1. User Login
   Client --> API Gateway: POST /auth/login
   Credentials: {email, password}

2. Token Generation
   API Gateway: Validate credentials
   API Gateway: Generate JWT with payload:
   {
     user_id: "123",
     email: "user@example.com",
     exp: timestamp + 24h,
     iat: timestamp
   }

3. Token Storage
   Client: Store token (localStorage/cookie)

4. Authenticated Request
   Client --> API Gateway: GET /resource
   Header: Authorization: Bearer <token>

5. Token Verification
   API Gateway: Extract token
   API Gateway: Verify signature with JWT_SECRET
   API Gateway: Check expiration
   API Gateway: Extract user context

6. Request Forwarding
   API Gateway --> Service: Forward with user context
   Header: X-User-ID, X-User-Email
```

### 7.2 Security Layers

#### Layer 1: Network Security
- **Docker Network Isolation**: Services communicate over internal bridge network
- **Port Exposure**: Only API Gateway exposed to external network
- **Service Discovery**: Internal DNS resolution

#### Layer 2: API Gateway Security
- **JWT Validation**: All requests verified before routing
- **Rate Limiting**: Prevent DoS attacks (100 req/min)
- **CORS Policy**: Restrict cross-origin requests
- **Request Validation**: Input sanitization

#### Layer 3: Service Security
- **AWS IAM**: Principle of least privilege
- **Environment Variables**: Sensitive data not hardcoded
- **Database Credentials**: Per-service isolation
- **S3 Bucket Policies**: Private by default

#### Layer 4: Data Security
- **Encryption in Transit**: HTTPS for external, HTTP internal
- **Encryption at Rest**: S3 server-side encryption
- **Database Encryption**: PostgreSQL SSL connections
- **Secrets Management**: AWS Secrets Manager (production)

### 7.3 Rate Limiting Design

```python
# In-memory rate limiter (development)
rate_limit_storage = {
    'user_123': [
        timestamp1,
        timestamp2,
        ...
    ]
}

# Algorithm: Sliding Window
def check_rate_limit(user_id):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old requests
    requests = [t for t in rate_limit_storage.get(user_id, [])
                if t > window_start]

    if len(requests) >= RATE_LIMIT_REQUESTS:
        return False  # Rate limit exceeded

    requests.append(now)
    rate_limit_storage[user_id] = requests
    return True
```

**Production Implementation**:
- Use Redis for distributed rate limiting
- Implement token bucket algorithm
- Per-user and per-IP limits

---

## 8. Scalability & Performance

### 8.1 Horizontal Scaling Strategy

```
Load Balancer (AWS ALB/ELB)
    |
    ├─── API Gateway Instance 1
    ├─── API Gateway Instance 2
    └─── API Gateway Instance 3
            |
            ├─── TTS Service (1-N replicas)
            ├─── STT Service (1-N replicas)
            ├─── Chat Service (1-N replicas)
            ├─── Document Service (1-N replicas)
            └─── Quiz Service (1-N replicas)
```

**Scaling Metrics**:
- CPU utilization > 70%
- Memory utilization > 80%
- Request latency > 2 seconds
- Request queue depth > 100

### 8.2 Database Scaling

**Vertical Scaling**:
- Increase CPU and memory
- Use larger instance types

**Horizontal Scaling (Future)**:
- Read replicas for read-heavy workloads
- Sharding for write-heavy workloads
- Connection pooling (PgBouncer)

**Current Schema**:
```
Primary DB (Write)
    |
    ├─── Read Replica 1
    ├─── Read Replica 2
    └─── Read Replica 3
```

### 8.3 Caching Strategy

**Redis Cache Layers**:

1. **API Gateway Cache**
   - User sessions
   - Rate limit counters
   - JWT blacklist (for logout)

2. **Service-Level Cache**
   - Frequently accessed data
   - AWS Polly voice list
   - Document metadata

3. **Database Query Cache**
   - Popular quiz questions
   - Common chat responses

**Cache Invalidation**:
- TTL-based expiration
- Event-based invalidation via Kafka
- Manual cache flush endpoints

### 8.4 Performance Optimizations

**Request Processing**:
- Connection pooling (PostgreSQL)
- Persistent HTTP connections (Keep-Alive)
- Request timeout limits
- Async processing for long operations

**Database Optimizations**:
- Indexed columns (user_id, created_at)
- JSONB for flexible schema
- Prepared statements
- Query optimization

**AWS Optimizations**:
- S3 presigned URLs (reduce latency)
- CloudFront CDN for static assets
- Multi-part upload for large files
- Intelligent-Tiering storage class

---

## 9. Data Models

### 9.1 Chat Service Models

```python
class ChatSession:
    id: int (PK)
    user_id: str (indexed)
    title: str
    created_at: datetime
    updated_at: datetime

class ChatMessage:
    id: int (PK)
    session_id: int (FK -> ChatSession)
    role: str (user/assistant)
    content: text
    timestamp: datetime
    metadata: jsonb
```

### 9.2 Document Service Models

```python
class Document:
    id: int (PK)
    user_id: str (indexed)
    title: str
    filename: str
    s3_key: str (unique)
    file_type: str
    file_size: int
    status: str (uploaded/processing/completed/failed)
    created_at: datetime
    processed_at: datetime

class Note:
    id: int (PK)
    document_id: int (FK -> Document)
    content: text
    created_at: datetime
    updated_at: datetime
```

### 9.3 Quiz Service Models

```python
class Quiz:
    id: int (PK)
    user_id: str (indexed)
    document_id: int (nullable)
    title: str
    total_questions: int
    created_at: datetime

class Question:
    id: int (PK)
    quiz_id: int (FK -> Quiz)
    question_text: text
    question_type: str (multiple_choice/true_false/short_answer)
    options: jsonb [{id, text}]
    correct_answer: str
    points: int

class QuizSubmission:
    id: int (PK)
    quiz_id: int (FK -> Quiz)
    user_id: str (indexed)
    answers: jsonb {question_id: answer}
    score: float
    total_points: int
    submitted_at: datetime
```

### 9.4 Event Models (Kafka)

```python
# Audio Generation Event
{
    "event_type": "audio.generation.requested",
    "timestamp": "2024-12-04T10:30:00Z",
    "user_id": "user_123",
    "request_id": "req_abc",
    "text": "Hello world",
    "voice_id": "Joanna",
    "s3_url": "s3://bucket/audio.mp3"
}

# Transcription Event
{
    "event_type": "transcription.completed",
    "timestamp": "2024-12-04T10:35:00Z",
    "user_id": "user_123",
    "job_id": "job_xyz",
    "transcript": "Transcribed text...",
    "confidence": 0.95
}

# Document Processing Event
{
    "event_type": "document.processed",
    "timestamp": "2024-12-04T10:40:00Z",
    "user_id": "user_123",
    "document_id": 456,
    "pages_processed": 10,
    "text_length": 5000
}
```

---

## 10. API Design

### 10.1 RESTful Principles

All APIs follow REST conventions:
- **GET**: Retrieve resources
- **POST**: Create resources
- **PUT/PATCH**: Update resources
- **DELETE**: Remove resources

### 10.2 API Versioning

Base URL: `/api/v1/`

Future versions: `/api/v2/`, `/api/v3/`

### 10.3 Response Format

**Success Response (2xx)**:
```json
{
  "id": "resource_id",
  "status": "success",
  "data": {
    // Resource data
  },
  "timestamp": "2024-12-04T10:30:00Z"
}
```

**Error Response (4xx/5xx)**:
```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "field": "validation error"
  },
  "request_id": "req_123",
  "timestamp": "2024-12-04T10:30:00Z"
}
```

### 10.4 Pagination

For list endpoints:
```
GET /api/v1/documents?page=1&limit=20

Response:
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### 10.5 Error Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | Service down |

---

## 11. Event-Driven Architecture

### 11.1 Kafka Topics

```
Topics Structure:

audio.generation.requested
├── Partition 0
├── Partition 1
└── Partition 2

transcription.requested
├── Partition 0
└── Partition 1

document.uploaded
├── Partition 0
└── Partition 1

document.processed
├── Partition 0
└── Partition 1

chat.message.sent
├── Partition 0
├── Partition 1
└── Partition 2

quiz.generated
├── Partition 0
└── Partition 1

quiz.submitted
├── Partition 0
└── Partition 1
```

### 11.2 Producer Pattern

```python
class KafkaProducer:
    def __init__(self, bootstrap_servers):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def publish_event(self, topic, event):
        future = self.producer.send(topic, event)
        future.get(timeout=10)  # Block until sent
```

### 11.3 Consumer Pattern (Future)

```python
class EventConsumer:
    def __init__(self, bootstrap_servers, topics):
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id='service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

    def process_events(self):
        for message in self.consumer:
            self.handle_event(message.topic, message.value)
```

### 11.4 Event Schema

All events follow this structure:
```json
{
  "event_id": "evt_unique_id",
  "event_type": "domain.action.status",
  "timestamp": "ISO8601",
  "user_id": "user_id",
  "service": "service_name",
  "version": "1.0",
  "payload": {
    // Event-specific data
  }
}
```

---

## 12. Deployment Architecture

### 12.1 Development Environment

```
Developer Laptop
├── Docker Desktop
├── Docker Compose
└── Local Services
    ├── All microservices
    ├── Kafka + Zookeeper
    ├── PostgreSQL instances
    └── Redis
```

### 12.2 AWS Learner Lab Environment

```
AWS Account
├── EC2 Instance (t3.large)
│   ├── Docker Engine
│   ├── Docker Compose
│   └── All Services
├── S3 Buckets
│   ├── learner-lab-audio
│   └── learner-lab-documents
├── IAM Roles
│   ├── EC2 Instance Role
│   └── Service Permissions
└── Security Groups
    ├── Port 5000 (API Gateway)
    └── Internal ports
```

### 12.3 Production Architecture (Future)

```
AWS Production Environment

┌──────────────────────────────────────────────────┐
│                  Route 53 (DNS)                  │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────┴─────────────────────────────┐
│          CloudFront CDN (Static Assets)          │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────┴─────────────────────────────┐
│         Application Load Balancer (ALB)          │
└────────┬────────────────────────┬─────────────────┘
         │                        │
    ┌────▼─────┐           ┌─────▼────┐
    │   AZ-1   │           │   AZ-2   │
    ├──────────┤           ├──────────┤
    │ ECS Tasks│           │ ECS Tasks│
    │ API GW   │           │ API GW   │
    │ Services │           │ Services │
    └────┬─────┘           └─────┬────┘
         │                       │
    ┌────┴───────────────────────┴────┐
    │        Amazon MSK (Kafka)       │
    └────────────────┬─────────────────┘
                     │
    ┌────────────────┴─────────────────┐
    │      RDS PostgreSQL (Multi-AZ)   │
    └──────────────────────────────────┘
                     │
    ┌────────────────┴─────────────────┐
    │      ElastiCache Redis Cluster   │
    └──────────────────────────────────┘
                     │
    ┌────────────────┴─────────────────┐
    │    S3 + CloudWatch + Secrets     │
    └──────────────────────────────────┘
```

### 12.4 Container Orchestration

**Current**: Docker Compose
**Future**:
- **AWS ECS**: Fargate for serverless containers
- **Kubernetes**: For complex orchestration needs

**ECS Task Definition Example**:
```json
{
  "family": "api-gateway",
  "cpu": "512",
  "memory": "1024",
  "networkMode": "awsvpc",
  "containerDefinitions": [{
    "name": "api-gateway",
    "image": "account.dkr.ecr.region.amazonaws.com/api-gateway:latest",
    "portMappings": [{
      "containerPort": 5000,
      "protocol": "tcp"
    }],
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3
    }
  }]
}
```

### 12.5 CI/CD Pipeline

```
┌──────────────┐
│   GitHub     │
│  Repository  │
└──────┬───────┘
       │ push
┌──────▼───────┐
│  GitHub      │
│  Actions     │
├──────────────┤
│ - Lint       │
│ - Test       │
│ - Build      │
└──────┬───────┘
       │
┌──────▼───────┐
│   AWS ECR    │
│ (Container   │
│  Registry)   │
└──────┬───────┘
       │
┌──────▼───────┐
│   AWS ECS    │
│  (Deploy)    │
└──────────────┘
```

---

## Appendix

### A. Environment Variables Reference

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token
AWS_REGION=us-east-1

# S3 Buckets
S3_BUCKET_NAME=learner-lab-audio
S3_DOCUMENTS_BUCKET=learner-lab-documents

# JWT Configuration
JWT_SECRET=your-super-secret-key
JWT_EXPIRATION_HOURS=24

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Database Configuration (per service)
DB_HOST=chat-db
DB_PORT=5432
DB_NAME=chat_db
DB_USER=chat_user
DB_PASSWORD=chat_password

# Service URLs (for API Gateway)
TTS_SERVICE_URL=http://tts-service:5001
STT_SERVICE_URL=http://stt-service:5002
CHAT_SERVICE_URL=http://chat-service:5003
DOCUMENT_SERVICE_URL=http://document-service:5004
QUIZ_SERVICE_URL=http://quiz-service:5005

# Logging
LOG_LEVEL=INFO
DEBUG=False

# Performance
REQUEST_TIMEOUT=30
MAX_FILE_SIZE=10485760
```

### B. Port Allocation

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| API Gateway | 5000 | 5000 | HTTP |
| TTS Service | 5001 | 5001 | HTTP |
| STT Service | 5002 | 5002 | HTTP |
| Chat Service | 5003 | 5003 | HTTP |
| Document Service | 5004 | 5004 | HTTP |
| Quiz Service | 5005 | 5005 | HTTP |
| Kafka | 9092 | 9092 | TCP |
| Kafka (external) | 9093 | 9093 | TCP |
| Zookeeper | 2181 | 2181 | TCP |
| Chat DB | 5432 | 5432 | TCP |
| Document DB | 5432 | 5433 | TCP |
| Quiz DB | 5432 | 5434 | TCP |
| Redis | 6379 | 6379 | TCP |

### C. Docker Image Sizes

| Service | Base Image | Final Size | Build Time |
|---------|------------|------------|------------|
| API Gateway | python:3.11-slim | ~200 MB | ~2 min |
| TTS Service | python:3.11-slim | ~250 MB | ~2 min |
| STT Service | python:3.11-slim | ~250 MB | ~2 min |
| Chat Service | python:3.11-slim | ~220 MB | ~2 min |
| Document Service | python:3.11-slim | ~280 MB | ~3 min |
| Quiz Service | python:3.11-slim | ~220 MB | ~2 min |

### D. Monitoring Metrics

**System Metrics**:
- CPU utilization per service
- Memory utilization per service
- Disk I/O
- Network throughput

**Application Metrics**:
- Request rate (req/sec)
- Request latency (p50, p95, p99)
- Error rate (5xx errors)
- Success rate

**Business Metrics**:
- Active users
- API calls per service
- Document processing time
- Quiz completion rate

### E. Glossary

- **API Gateway**: Entry point for all client requests
- **JWT**: JSON Web Token for authentication
- **Kafka**: Distributed event streaming platform
- **Microservice**: Independently deployable service
- **S3**: Amazon Simple Storage Service
- **PostgreSQL**: Relational database system
- **Docker**: Container platform
- **REST**: Representational State Transfer
- **CORS**: Cross-Origin Resource Sharing
- **Rate Limiting**: Throttling request frequency

---

**Document Version**: 1.0
**Last Updated**: December 4, 2024
**Author**: System Architecture Team
**Status**: Production Ready
