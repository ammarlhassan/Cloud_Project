# Kafka Topics Specification

## Overview
This document defines all Kafka topics, their schemas, configurations, and usage patterns for the Cloud-Based Learning Platform event-driven architecture.

## Topic Naming Convention
Format: `{domain}.{action}.{version}`
- Domain: Service domain (document, quiz, audio, chat)
- Action: Business event (uploaded, processed, requested, completed)
- Version: API version (v1)

## Topics Summary

| Topic Name | Purpose | Producer | Consumer | Partitions | Replication | Retention |
|------------|---------|----------|----------|------------|-------------|-----------|
| `document.uploaded` | Document upload event | Document Reader | Chat, Quiz | 3 | 2 | 7 days |
| `document.processed` | Document processing complete | Document Reader | Chat, Quiz | 3 | 2 | 7 days |
| `notes.generated` | Notes generation complete | Document Reader | Quiz | 3 | 2 | 7 days |
| `quiz.requested` | Quiz generation request | Quiz Service | Quiz Service | 3 | 2 | 3 days |
| `quiz.generated` | Quiz generation complete | Quiz Service | API Gateway | 3 | 2 | 7 days |
| `audio.transcription.requested` | STT request | STT Service | STT Service | 6 | 2 | 3 days |
| `audio.transcription.completed` | STT complete | STT Service | API Gateway, Chat | 6 | 2 | 7 days |
| `audio.generation.requested` | TTS request | TTS Service | TTS Service | 6 | 2 | 3 days |
| `audio.generation.completed` | TTS complete | TTS Service | API Gateway | 6 | 2 | 7 days |
| `chat.message` | Chat interaction | Chat Service | Chat Service, Analytics | 6 | 2 | 30 days |

---

## Topic Configurations

### 1. document.uploaded

**Purpose**: Triggered when a user uploads a document (PDF, DOCX, TXT) to the platform.

**Configuration**:
```properties
topic.name=document.uploaded
partitions=3
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id` to maintain ordering per user.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "document.uploaded",
  "event_timestamp": "2025-11-29T10:30:00Z",
  "event_version": "1.0",
  "payload": {
    "document_id": "doc_123456",
    "user_id": "user_789",
    "file_name": "lecture_notes.pdf",
    "file_size_bytes": 2048576,
    "file_type": "application/pdf",
    "s3_bucket": "document-reader-storage-prod",
    "s3_key": "documents/user_789/doc_123456.pdf",
    "upload_timestamp": "2025-11-29T10:30:00Z",
    "metadata": {
      "course_id": "CSE363",
      "tags": ["cloud", "kafka"]
    }
  }
}
```

**Producer**: Document Reader Service
**Consumer**: Chat Service, Quiz Service
**Consumer Groups**: `chat-service-group`, `quiz-service-group`

---

### 2. document.processed

**Purpose**: Fired when document text extraction and initial processing is complete.

**Configuration**:
```properties
topic.name=document.processed
partitions=3
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `document_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "document.processed",
  "event_timestamp": "2025-11-29T10:35:00Z",
  "event_version": "1.0",
  "payload": {
    "document_id": "doc_123456",
    "user_id": "user_789",
    "extracted_text": "Full extracted text content...",
    "page_count": 45,
    "word_count": 12450,
    "processing_duration_ms": 15000,
    "language": "en",
    "metadata": {
      "headings": ["Introduction", "Kafka Architecture"],
      "has_images": true,
      "has_tables": true
    }
  }
}
```

**Producer**: Document Reader Service
**Consumer**: Chat Service (for context), Quiz Service
**Consumer Groups**: `chat-service-group`, `quiz-service-group`

---

### 3. notes.generated

**Purpose**: Published when AI-generated notes from a document are created.

**Configuration**:
```properties
topic.name=notes.generated
partitions=3
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `document_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "notes.generated",
  "event_timestamp": "2025-11-29T10:40:00Z",
  "event_version": "1.0",
  "payload": {
    "notes_id": "notes_123456",
    "document_id": "doc_123456",
    "user_id": "user_789",
    "notes_content": "Summarized notes content...",
    "summary": "Brief overview of the document...",
    "key_points": [
      "Kafka provides high-throughput message streaming",
      "Zookeeper manages cluster coordination"
    ],
    "s3_bucket": "document-reader-storage-prod",
    "s3_key": "notes/user_789/notes_123456.md",
    "generation_model": "gpt-4",
    "generation_timestamp": "2025-11-29T10:40:00Z"
  }
}
```

**Producer**: Document Reader Service
**Consumer**: Quiz Service
**Consumer Groups**: `quiz-service-group`

---

### 4. quiz.requested

**Purpose**: User or system requests quiz generation from a document.

**Configuration**:
```properties
topic.name=quiz.requested
partitions=3
replication.factor=2
min.insync.replicas=2
retention.ms=259200000  # 3 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "quiz.requested",
  "event_timestamp": "2025-11-29T11:00:00Z",
  "event_version": "1.0",
  "payload": {
    "quiz_request_id": "qreq_123456",
    "user_id": "user_789",
    "document_id": "doc_123456",
    "notes_id": "notes_123456",
    "quiz_parameters": {
      "question_count": 10,
      "question_types": ["multiple_choice", "true_false", "short_answer"],
      "difficulty": "medium",
      "topics": ["Kafka", "Microservices"]
    },
    "request_timestamp": "2025-11-29T11:00:00Z"
  }
}
```

**Producer**: Quiz Service (API endpoint)
**Consumer**: Quiz Service (background processor)
**Consumer Groups**: `quiz-generator-group`

---

### 5. quiz.generated

**Purpose**: Quiz generation completed successfully.

**Configuration**:
```properties
topic.name=quiz.generated
partitions=3
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "quiz.generated",
  "event_timestamp": "2025-11-29T11:05:00Z",
  "event_version": "1.0",
  "payload": {
    "quiz_id": "quiz_123456",
    "quiz_request_id": "qreq_123456",
    "user_id": "user_789",
    "document_id": "doc_123456",
    "question_count": 10,
    "questions": [
      {
        "question_id": "q1",
        "question_text": "What is Apache Kafka?",
        "question_type": "multiple_choice",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "B"
      }
    ],
    "s3_bucket": "quiz-service-storage-prod",
    "s3_key": "quizzes/user_789/quiz_123456.json",
    "generation_timestamp": "2025-11-29T11:05:00Z"
  }
}
```

**Producer**: Quiz Service
**Consumer**: API Gateway (for notifications)
**Consumer Groups**: `notification-service-group`

---

### 6. audio.transcription.requested

**Purpose**: Audio file uploaded for speech-to-text transcription.

**Configuration**:
```properties
topic.name=audio.transcription.requested
partitions=6
replication.factor=2
min.insync.replicas=2
retention.ms=259200000  # 3 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id` (higher partition count for load distribution).

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "audio.transcription.requested",
  "event_timestamp": "2025-11-29T12:00:00Z",
  "event_version": "1.0",
  "payload": {
    "transcription_request_id": "treq_123456",
    "user_id": "user_789",
    "audio_file_id": "audio_987654",
    "s3_bucket": "stt-service-storage-prod",
    "s3_key": "audio/user_789/audio_987654.mp3",
    "file_size_bytes": 5242880,
    "audio_format": "mp3",
    "audio_duration_seconds": 180,
    "language": "en",
    "parameters": {
      "model": "whisper-large-v2",
      "include_timestamps": true,
      "include_confidence": true
    },
    "request_timestamp": "2025-11-29T12:00:00Z"
  }
}
```

**Producer**: STT Service (API endpoint)
**Consumer**: STT Service (background processor)
**Consumer Groups**: `stt-processor-group`

---

### 7. audio.transcription.completed

**Purpose**: Transcription processing completed.

**Configuration**:
```properties
topic.name=audio.transcription.completed
partitions=6
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "audio.transcription.completed",
  "event_timestamp": "2025-11-29T12:03:00Z",
  "event_version": "1.0",
  "payload": {
    "transcription_id": "trans_123456",
    "transcription_request_id": "treq_123456",
    "user_id": "user_789",
    "audio_file_id": "audio_987654",
    "transcribed_text": "Full transcription text...",
    "confidence_score": 0.95,
    "language_detected": "en",
    "processing_duration_ms": 45000,
    "word_count": 450,
    "timestamps": [
      {"word": "Hello", "start": 0.5, "end": 0.8, "confidence": 0.98}
    ],
    "storage": {
      "database_id": "12345",
      "s3_bucket": "stt-service-storage-prod",
      "s3_key": "transcriptions/user_789/trans_123456.json"
    },
    "completion_timestamp": "2025-11-29T12:03:00Z"
  }
}
```

**Producer**: STT Service
**Consumer**: API Gateway (notifications), Chat Service (context)
**Consumer Groups**: `notification-service-group`, `chat-service-group`

---

### 8. audio.generation.requested

**Purpose**: Text-to-speech audio generation requested.

**Configuration**:
```properties
topic.name=audio.generation.requested
partitions=6
replication.factor=2
min.insync.replicas=2
retention.ms=259200000  # 3 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "audio.generation.requested",
  "event_timestamp": "2025-11-29T13:00:00Z",
  "event_version": "1.0",
  "payload": {
    "audio_request_id": "areq_123456",
    "user_id": "user_789",
    "text_content": "Text to be converted to speech...",
    "text_length": 500,
    "parameters": {
      "voice": "en-US-Neural2-F",
      "language": "en-US",
      "audio_format": "mp3",
      "speed": 1.0,
      "pitch": 0
    },
    "request_timestamp": "2025-11-29T13:00:00Z"
  }
}
```

**Producer**: TTS Service (API endpoint)
**Consumer**: TTS Service (background processor)
**Consumer Groups**: `tts-processor-group`

---

### 9. audio.generation.completed

**Purpose**: Text-to-speech generation completed.

**Configuration**:
```properties
topic.name=audio.generation.completed
partitions=6
replication.factor=2
min.insync.replicas=2
retention.ms=604800000  # 7 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `user_id`.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "audio.generation.completed",
  "event_timestamp": "2025-11-29T13:02:00Z",
  "event_version": "1.0",
  "payload": {
    "audio_id": "audio_123456",
    "audio_request_id": "areq_123456",
    "user_id": "user_789",
    "s3_bucket": "tts-service-storage-prod",
    "s3_key": "audio/user_789/audio_123456.mp3",
    "file_size_bytes": 1048576,
    "audio_duration_seconds": 45,
    "audio_format": "mp3",
    "generation_model": "neural2",
    "processing_duration_ms": 2000,
    "completion_timestamp": "2025-11-29T13:02:00Z"
  }
}
```

**Producer**: TTS Service
**Consumer**: API Gateway (notifications)
**Consumer Groups**: `notification-service-group`

---

### 10. chat.message

**Purpose**: Chat messages and AI responses for conversational interactions.

**Configuration**:
```properties
topic.name=chat.message
partitions=6
replication.factor=2
min.insync.replicas=2
retention.ms=2592000000  # 30 days
cleanup.policy=delete
compression.type=snappy
```

**Partitioning Strategy**: Partition by `conversation_id` to maintain message ordering.

**Schema** (JSON):
```json
{
  "event_id": "uuid",
  "event_type": "chat.message",
  "event_timestamp": "2025-11-29T14:00:00Z",
  "event_version": "1.0",
  "payload": {
    "message_id": "msg_123456",
    "conversation_id": "conv_789",
    "user_id": "user_789",
    "sender_type": "user",
    "message_content": "Can you explain Kafka partitioning?",
    "message_timestamp": "2025-11-29T14:00:00Z",
    "context": {
      "document_ids": ["doc_123456"],
      "previous_messages": 5
    },
    "ai_response": {
      "response_id": "resp_123456",
      "response_content": "Kafka partitioning allows...",
      "model": "gpt-4",
      "response_timestamp": "2025-11-29T14:00:05Z",
      "confidence": 0.92
    },
    "metadata": {
      "session_id": "session_456",
      "client_ip": "10.0.10.5"
    }
  }
}
```

**Producer**: Chat Service
**Consumer**: Chat Service (history), Analytics Service (future)
**Consumer Groups**: `chat-history-group`, `analytics-group`

---

## Producer & Consumer Guidelines

### Producer Best Practices

```python
from kafka import KafkaProducer
import json
import uuid
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers=['kafka-nlb.internal:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # Wait for all replicas
    retries=3,
    max_in_flight_requests_per_connection=1,  # Ensure ordering
    compression_type='snappy',
    linger_ms=10,  # Batch for 10ms
    batch_size=16384
)

def publish_event(topic, payload, partition_key):
    """Publish event to Kafka topic."""
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": topic,
        "event_timestamp": datetime.utcnow().isoformat() + 'Z',
        "event_version": "1.0",
        "payload": payload
    }

    future = producer.send(
        topic,
        value=event,
        key=partition_key.encode('utf-8')
    )

    # Block for confirmation (or use callback)
    record_metadata = future.get(timeout=10)
    return record_metadata
```

### Consumer Best Practices

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'document.uploaded',
    bootstrap_servers=['kafka-nlb.internal:9092'],
    group_id='chat-service-group',
    auto_offset_reset='earliest',
    enable_auto_commit=False,  # Manual commit for reliability
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    max_poll_records=100,
    session_timeout_ms=30000,
    heartbeat_interval_ms=10000
)

def consume_events():
    """Consume events from Kafka topic."""
    for message in consumer:
        try:
            event = message.value
            process_event(event)

            # Commit offset after successful processing
            consumer.commit()
        except Exception as e:
            print(f"Error processing message: {e}")
            # Optionally: send to DLQ (Dead Letter Queue)
```

---

## Topic Creation Scripts

See [kafka-topic-creation.sh](../scripts/kafka-topic-creation.sh) for automated topic creation.

---

## Monitoring Metrics Per Topic

- **Messages in/out rate**: Messages per second
- **Bytes in/out rate**: Throughput in MB/s
- **Consumer lag**: Messages behind latest offset
- **Request latency**: p95, p99 latencies
- **Error rate**: Failed produce/consume operations
- **Partition distribution**: Even distribution across brokers

---

## Retention & Cleanup Policies

| Topic Type | Retention | Cleanup Policy | Reason |
|------------|-----------|----------------|--------|
| Request events | 3 days | delete | Short-lived, only needed for processing |
| Completion events | 7 days | delete | Moderate retention for debugging |
| Chat messages | 30 days | delete | Longer retention for history |
| Audit logs | 90 days | delete | Compliance and debugging |
