# Kafka Integration Patterns

## Overview
This document describes how the Cloud-Based Learning Platform implements four key event-driven architecture patterns using Apache Kafka: Event Sourcing, CQRS, Saga Pattern, and Event Notification.

---

## 1. Event Sourcing

### Definition
Event Sourcing stores the state of a system as a sequence of events rather than as a snapshot of current state. Every state change is captured as an immutable event in Kafka.

### Application in the Learning Platform

#### Use Case: Document Processing History

**Scenario**: Track the complete lifecycle of a document from upload to quiz generation.

**Events Sequence**:
```
1. document.uploaded        → Document added to system
2. document.processed       → Text extraction completed
3. notes.generated          → AI notes created
4. quiz.requested           → User requests quiz
5. quiz.generated           → Quiz created from notes
```

**Implementation**:

```python
# Document Reader Service - Event Sourcing
from kafka import KafkaProducer
import json
from datetime import datetime

class DocumentEventStore:
    """
    Event sourcing implementation for document lifecycle.
    All state changes are stored as events in Kafka.
    """

    def __init__(self, bootstrap_servers):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )

    def publish_event(self, topic, event_data):
        """Publish event to Kafka topic."""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": topic,
            "event_timestamp": datetime.utcnow().isoformat() + 'Z',
            "event_version": "1.0",
            "payload": event_data
        }

        self.producer.send(
            topic,
            value=event,
            key=event_data.get("document_id", "").encode('utf-8')
        )

    def reconstruct_document_state(self, document_id):
        """
        Reconstruct current document state by replaying all events.
        This demonstrates the core principle of event sourcing.
        """
        # Consume events from beginning for this document
        consumer = KafkaConsumer(
            'document.uploaded',
            'document.processed',
            'notes.generated',
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )

        document_state = {
            "document_id": document_id,
            "status": "unknown",
            "events": []
        }

        for message in consumer:
            event = json.loads(message.value.decode('utf-8'))
            if event['payload']['document_id'] == document_id:
                document_state['events'].append(event)

                # Apply event to state
                if event['event_type'] == 'document.uploaded':
                    document_state['status'] = 'uploaded'
                    document_state['file_name'] = event['payload']['file_name']

                elif event['event_type'] == 'document.processed':
                    document_state['status'] = 'processed'
                    document_state['word_count'] = event['payload']['word_count']

                elif event['event_type'] == 'notes.generated':
                    document_state['status'] = 'notes_ready'
                    document_state['notes_id'] = event['payload']['notes_id']

        return document_state


# Usage example
event_store = DocumentEventStore(['kafka-nlb.internal:9092'])

# Publish upload event
event_store.publish_event('document.uploaded', {
    "document_id": "doc_123",
    "user_id": "user_789",
    "file_name": "lecture_notes.pdf",
    "s3_key": "documents/user_789/doc_123.pdf"
})

# Later: Reconstruct state from events
current_state = event_store.reconstruct_document_state("doc_123")
print(f"Document status: {current_state['status']}")
print(f"Event count: {len(current_state['events'])}")
```

### Benefits in Our System
- **Complete Audit Trail**: Every document change is tracked
- **Time Travel**: Can reconstruct document state at any point in time
- **Debugging**: Easy to replay events to understand system behavior
- **Analytics**: Historical data available for reporting

---

## 2. CQRS (Command Query Responsibility Segregation)

### Definition
CQRS separates read operations (queries) from write operations (commands), allowing them to be optimized independently.

### Application in the Learning Platform

#### Use Case: Quiz Service - Separate Write and Read Models

**Write Model** (Commands):
- Generate quiz from document
- Submit quiz answers
- Update quiz scores

**Read Model** (Queries):
- Get quiz questions
- Get quiz results
- List user quiz history

**Implementation**:

```python
# Quiz Service - CQRS Implementation

# ==================== WRITE SIDE ====================

class QuizCommandService:
    """
    Handles all write operations for quizzes.
    Publishes events to Kafka, writes to PostgreSQL.
    """

    def __init__(self, db_connection, kafka_producer):
        self.db = db_connection
        self.producer = kafka_producer

    def generate_quiz(self, document_id, user_id, parameters):
        """
        Command: Generate new quiz.
        Writes to database and publishes event.
        """
        # 1. Create quiz in database (write model)
        quiz_id = self._create_quiz_record(document_id, user_id, parameters)

        # 2. Generate questions using AI
        questions = self._generate_questions(document_id, parameters)

        # 3. Store questions in database
        self._store_questions(quiz_id, questions)

        # 4. Publish event to Kafka
        self.producer.send('quiz.generated', {
            "quiz_id": quiz_id,
            "user_id": user_id,
            "document_id": document_id,
            "question_count": len(questions)
        })

        return quiz_id

    def submit_quiz_answers(self, quiz_id, user_id, answers):
        """
        Command: Submit quiz answers.
        """
        # 1. Store answers in database
        submission_id = self._store_submission(quiz_id, user_id, answers)

        # 2. Calculate score
        score = self._calculate_score(quiz_id, answers)

        # 3. Update read model (denormalized table for fast queries)
        self._update_quiz_results_view(submission_id, score)

        # 4. Publish event
        self.producer.send('quiz.submitted', {
            "quiz_id": quiz_id,
            "user_id": user_id,
            "score": score,
            "submission_id": submission_id
        })

        return submission_id


# ==================== READ SIDE ====================

class QuizQueryService:
    """
    Handles all read operations for quizzes.
    Reads from optimized read models (denormalized views).
    """

    def __init__(self, db_connection, redis_cache):
        self.db = db_connection
        self.cache = redis_cache

    def get_quiz_questions(self, quiz_id):
        """
        Query: Get quiz questions.
        Uses caching for performance.
        """
        # 1. Check cache
        cached = self.cache.get(f"quiz:{quiz_id}:questions")
        if cached:
            return json.loads(cached)

        # 2. Query from read model (denormalized view)
        questions = self.db.execute("""
            SELECT q.question_id, q.question_text, q.question_type,
                   q.options, q.difficulty
            FROM quiz_questions_view q
            WHERE q.quiz_id = %s
            ORDER BY q.question_order
        """, (quiz_id,))

        # 3. Cache for 1 hour
        self.cache.setex(
            f"quiz:{quiz_id}:questions",
            3600,
            json.dumps(questions)
        )

        return questions

    def get_quiz_results(self, quiz_id, user_id):
        """
        Query: Get quiz results.
        Reads from denormalized results view for fast access.
        """
        # Read from optimized view
        results = self.db.execute("""
            SELECT r.submission_id, r.score, r.total_questions,
                   r.correct_answers, r.submission_timestamp,
                   r.time_taken_seconds
            FROM quiz_results_view r
            WHERE r.quiz_id = %s AND r.user_id = %s
            ORDER BY r.submission_timestamp DESC
        """, (quiz_id, user_id))

        return results

    def list_user_quiz_history(self, user_id, limit=20):
        """
        Query: List user's quiz history.
        Uses materialized view for fast access.
        """
        history = self.db.execute("""
            SELECT h.quiz_id, h.quiz_title, h.score, h.date_taken,
                   h.document_title, h.question_count
            FROM user_quiz_history_view h
            WHERE h.user_id = %s
            ORDER BY h.date_taken DESC
            LIMIT %s
        """, (user_id, limit))

        return history


# ==================== EVENT CONSUMER (Updates Read Model) ====================

class QuizReadModelUpdater:
    """
    Consumes events from Kafka and updates read models.
    Keeps query side synchronized with write side.
    """

    def __init__(self, db_connection, kafka_consumer):
        self.db = db_connection
        self.consumer = kafka_consumer

    def start(self):
        """
        Consume events and update read models.
        """
        for message in self.consumer:
            event = json.loads(message.value.decode('utf-8'))

            if event['event_type'] == 'quiz.generated':
                self._update_quiz_view(event['payload'])

            elif event['event_type'] == 'quiz.submitted':
                self._update_results_view(event['payload'])

    def _update_quiz_view(self, payload):
        """Update denormalized quiz view."""
        self.db.execute("""
            INSERT INTO quiz_questions_view
            (quiz_id, question_id, question_text, ...)
            VALUES (%s, %s, %s, ...)
        """, (payload['quiz_id'], ...))

    def _update_results_view(self, payload):
        """Update denormalized results view."""
        self.db.execute("""
            INSERT INTO quiz_results_view
            (quiz_id, user_id, score, submission_timestamp, ...)
            VALUES (%s, %s, %s, %s, ...)
        """, (payload['quiz_id'], payload['user_id'], payload['score'], ...))


# ==================== DATABASE SCHEMA ====================

# Write Model Tables (normalized)
"""
CREATE TABLE quizzes (
    quiz_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    parameters JSONB
);

CREATE TABLE quiz_questions (
    question_id UUID PRIMARY KEY,
    quiz_id UUID REFERENCES quizzes(quiz_id),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    options JSONB,
    correct_answer TEXT,
    question_order INT
);

CREATE TABLE quiz_submissions (
    submission_id UUID PRIMARY KEY,
    quiz_id UUID REFERENCES quizzes(quiz_id),
    user_id UUID NOT NULL,
    answers JSONB,
    submitted_at TIMESTAMP
);
"""

# Read Model Tables (denormalized for fast queries)
"""
CREATE MATERIALIZED VIEW quiz_results_view AS
SELECT
    s.submission_id,
    s.quiz_id,
    s.user_id,
    s.submitted_at AS submission_timestamp,
    COUNT(q.question_id) AS total_questions,
    SUM(CASE WHEN a.answer = q.correct_answer THEN 1 ELSE 0 END) AS correct_answers,
    (SUM(CASE WHEN a.answer = q.correct_answer THEN 1 ELSE 0 END)::FLOAT /
     COUNT(q.question_id)::FLOAT * 100) AS score
FROM quiz_submissions s
JOIN quiz_questions q ON s.quiz_id = q.quiz_id
LEFT JOIN LATERAL jsonb_each_text(s.answers) a ON TRUE
GROUP BY s.submission_id, s.quiz_id, s.user_id, s.submitted_at;

-- Refresh periodically or on events
REFRESH MATERIALIZED VIEW quiz_results_view;
"""
```

### Benefits in Our System
- **Optimized Reads**: Query operations use denormalized views with caching
- **Scalability**: Read and write sides can scale independently
- **Performance**: Complex queries don't impact write operations
- **Flexibility**: Different data models for different use cases

---

## 3. Saga Pattern

### Definition
Saga pattern manages distributed transactions across multiple microservices using a sequence of local transactions coordinated through events.

### Application in the Learning Platform

#### Use Case: Document Upload to Quiz Generation Saga

**Saga Steps**:
```
1. Document Reader: Upload document → Publish document.uploaded
2. Document Reader: Process document → Publish document.processed
3. Document Reader: Generate notes → Publish notes.generated
4. Quiz Service: Listen to notes.generated → Generate quiz
5. Quiz Service: Quiz complete → Publish quiz.generated
```

**Compensation Actions** (if any step fails):
- Delete uploaded document from S3
- Clean up database entries
- Notify user of failure

**Implementation**:

```python
# Document-to-Quiz Saga Implementation

from enum import Enum
from dataclasses import dataclass
from typing import List, Callable

class SagaStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


@dataclass
class SagaStep:
    name: str
    action: Callable
    compensation: Callable
    status: SagaStatus = SagaStatus.PENDING


class DocumentQuizSagaOrchestrator:
    """
    Orchestrates the saga from document upload to quiz generation.
    Manages state transitions and compensations.
    """

    def __init__(self, kafka_producer, kafka_consumer, db):
        self.producer = kafka_producer
        self.consumer = kafka_consumer
        self.db = db

    def execute_saga(self, document_id, user_id, quiz_parameters):
        """
        Execute the complete saga.
        """
        saga_id = str(uuid.uuid4())

        # Initialize saga state
        saga_state = {
            "saga_id": saga_id,
            "document_id": document_id,
            "user_id": user_id,
            "status": SagaStatus.IN_PROGRESS,
            "completed_steps": [],
            "current_step": None
        }

        # Define saga steps
        steps = [
            SagaStep(
                name="upload_document",
                action=lambda: self.upload_document(document_id, user_id),
                compensation=lambda: self.delete_document(document_id)
            ),
            SagaStep(
                name="process_document",
                action=lambda: self.process_document(document_id),
                compensation=lambda: self.delete_processed_data(document_id)
            ),
            SagaStep(
                name="generate_notes",
                action=lambda: self.generate_notes(document_id),
                compensation=lambda: self.delete_notes(document_id)
            ),
            SagaStep(
                name="generate_quiz",
                action=lambda: self.generate_quiz(document_id, quiz_parameters),
                compensation=lambda: self.delete_quiz(document_id)
            )
        ]

        try:
            # Execute each step
            for step in steps:
                saga_state['current_step'] = step.name
                print(f"[Saga {saga_id}] Executing step: {step.name}")

                # Execute step action
                step.action()
                step.status = SagaStatus.COMPLETED
                saga_state['completed_steps'].append(step.name)

                # Wait for event confirmation (event-driven saga)
                self.wait_for_event_confirmation(step.name, document_id)

            # Saga completed successfully
            saga_state['status'] = SagaStatus.COMPLETED
            print(f"[Saga {saga_id}] Completed successfully")

            return saga_state

        except Exception as e:
            # Saga failed - trigger compensation
            print(f"[Saga {saga_id}] Failed at step {saga_state['current_step']}: {e}")
            saga_state['status'] = SagaStatus.COMPENSATING

            # Execute compensations in reverse order
            completed_steps = saga_state['completed_steps']
            for step in reversed(steps):
                if step.name in completed_steps:
                    print(f"[Saga {saga_id}] Compensating: {step.name}")
                    step.compensation()

            saga_state['status'] = SagaStatus.FAILED
            raise SagaFailedException(f"Saga {saga_id} failed", saga_state)

    def upload_document(self, document_id, user_id):
        """Step 1: Upload document to S3."""
        # Upload to S3
        s3_key = f"documents/{user_id}/{document_id}.pdf"
        # ... upload logic ...

        # Publish event
        self.producer.send('document.uploaded', {
            "document_id": document_id,
            "user_id": user_id,
            "s3_key": s3_key
        })

    def process_document(self, document_id):
        """Step 2: Process document (extract text)."""
        # Processing logic
        extracted_text = "..."  # Extract text from PDF

        # Publish event
        self.producer.send('document.processed', {
            "document_id": document_id,
            "extracted_text": extracted_text
        })

    def generate_notes(self, document_id):
        """Step 3: Generate AI notes."""
        # Generate notes using AI
        notes = "..."  # AI-generated notes

        # Publish event
        self.producer.send('notes.generated', {
            "document_id": document_id,
            "notes_content": notes
        })

    def generate_quiz(self, document_id, quiz_parameters):
        """Step 4: Generate quiz from notes."""
        # This is handled by Quiz Service listening to notes.generated
        # We publish quiz.requested event
        self.producer.send('quiz.requested', {
            "document_id": document_id,
            "quiz_parameters": quiz_parameters
        })

    def wait_for_event_confirmation(self, step_name, document_id):
        """
        Wait for event confirmation from Kafka.
        This makes the saga event-driven.
        """
        expected_events = {
            "upload_document": "document.uploaded",
            "process_document": "document.processed",
            "generate_notes": "notes.generated",
            "generate_quiz": "quiz.generated"
        }

        expected_event = expected_events.get(step_name)
        if not expected_event:
            return

        # Poll for event (with timeout)
        timeout = 60  # 60 seconds
        start_time = time.time()

        while time.time() - start_time < timeout:
            for message in self.consumer:
                event = json.loads(message.value.decode('utf-8'))
                if (event['event_type'] == expected_event and
                    event['payload']['document_id'] == document_id):
                    print(f"[Saga] Received confirmation: {expected_event}")
                    return

            time.sleep(1)

        raise TimeoutError(f"Timeout waiting for event: {expected_event}")

    # Compensation actions
    def delete_document(self, document_id):
        """Compensation: Delete document from S3."""
        print(f"[Compensation] Deleting document: {document_id}")
        # Delete from S3
        # Delete from database

    def delete_processed_data(self, document_id):
        """Compensation: Delete processed document data."""
        print(f"[Compensation] Deleting processed data: {document_id}")
        # Clean up processing results

    def delete_notes(self, document_id):
        """Compensation: Delete generated notes."""
        print(f"[Compensation] Deleting notes: {document_id}")
        # Delete notes from S3 and database

    def delete_quiz(self, document_id):
        """Compensation: Delete generated quiz."""
        print(f"[Compensation] Deleting quiz: {document_id}")
        # Delete quiz from database


# Usage
orchestrator = DocumentQuizSagaOrchestrator(producer, consumer, db)

try:
    saga_result = orchestrator.execute_saga(
        document_id="doc_123",
        user_id="user_789",
        quiz_parameters={"question_count": 10}
    )
    print("Saga completed:", saga_result)
except SagaFailedException as e:
    print("Saga failed:", e.saga_state)
```

### Saga Choreography vs Orchestration

Our system uses **choreography** (event-driven):
- Each service listens for events and decides what to do
- No central coordinator
- Services publish events when done
- More resilient and decoupled

**Flow**:
```
Document Service → document.uploaded → (consumed by Document Service)
Document Service → document.processed → (consumed by Chat, Quiz)
Document Service → notes.generated → (consumed by Quiz Service)
Quiz Service → quiz.generated → (consumed by API Gateway)
```

### Benefits in Our System
- **Distributed Transaction Management**: Handle multi-step workflows across services
- **Automatic Compensation**: Rollback on failures
- **Resilience**: Each service handles its own logic
- **Loose Coupling**: Services don't directly call each other

---

## 4. Event Notification

### Definition
Services publish events to notify other services of important state changes, without expecting a specific response.

### Application in the Learning Platform

#### Use Case: Multi-Service Notification System

**Scenario**: When a document is processed, multiple services need to be notified.

**Notification Flow**:
```
Document Reader → document.processed event
    ↓
    ├─→ Chat Service (updates knowledge base)
    ├─→ Quiz Service (prepares for quiz generation)
    ├─→ Analytics Service (records metrics)
    └─→ Notification Service (alerts user)
```

**Implementation**:

```python
# Event Notification Pattern Implementation

# ==================== PUBLISHER (Document Reader Service) ====================

class DocumentService:
    """
    Document service publishes events to notify other services.
    """

    def __init__(self, kafka_producer, s3_client):
        self.producer = kafka_producer
        self.s3 = s3_client

    def process_document(self, document_id, user_id):
        """
        Process document and publish notification event.
        """
        # 1. Extract text from document
        extracted_text = self._extract_text(document_id)

        # 2. Store in S3
        s3_key = f"processed/{user_id}/{document_id}.txt"
        self.s3.put_object(
            Bucket='document-reader-storage-prod',
            Key=s3_key,
            Body=extracted_text
        )

        # 3. Publish notification event
        # Multiple services will receive this notification
        self.producer.send('document.processed', {
            "document_id": document_id,
            "user_id": user_id,
            "extracted_text": extracted_text[:1000],  # Preview
            "full_text_s3_key": s3_key,
            "word_count": len(extracted_text.split()),
            "page_count": self._count_pages(document_id),
            "processing_timestamp": datetime.utcnow().isoformat() + 'Z'
        })

        print(f"Published document.processed event for {document_id}")


# ==================== SUBSCRIBERS ====================

# Subscriber 1: Chat Service
class ChatServiceEventListener:
    """
    Chat service listens for document.processed events
    to update its knowledge base.
    """

    def __init__(self, kafka_consumer, vector_db):
        self.consumer = kafka_consumer
        self.vector_db = vector_db

    def start_listening(self):
        """Listen for document.processed events."""
        for message in self.consumer:
            event = json.loads(message.value.decode('utf-8'))

            if event['event_type'] == 'document.processed':
                self.handle_document_processed(event['payload'])

    def handle_document_processed(self, payload):
        """
        Handle document.processed notification.
        Update chat service knowledge base.
        """
        print(f"[Chat Service] Received document.processed: {payload['document_id']}")

        # 1. Download full text from S3
        full_text = self.s3.get_object(
            Bucket='document-reader-storage-prod',
            Key=payload['full_text_s3_key']
        )['Body'].read().decode('utf-8')

        # 2. Create embeddings
        embeddings = self._create_embeddings(full_text)

        # 3. Store in vector database for semantic search
        self.vector_db.insert({
            "document_id": payload['document_id'],
            "user_id": payload['user_id'],
            "embeddings": embeddings,
            "text_chunks": self._chunk_text(full_text)
        })

        print(f"[Chat Service] Updated knowledge base for {payload['document_id']}")


# Subscriber 2: Quiz Service
class QuizServiceEventListener:
    """
    Quiz service listens for notes.generated events
    to prepare quiz generation.
    """

    def __init__(self, kafka_consumer, db):
        self.consumer = kafka_consumer
        self.db = db

    def start_listening(self):
        """Listen for notes.generated events."""
        for message in self.consumer:
            event = json.loads(message.value.decode('utf-8'))

            if event['event_type'] == 'notes.generated':
                self.handle_notes_generated(event['payload'])

    def handle_notes_generated(self, payload):
        """
        Handle notes.generated notification.
        Prepare data for quiz generation.
        """
        print(f"[Quiz Service] Received notes.generated: {payload['document_id']}")

        # Store notes reference for future quiz generation
        self.db.execute("""
            INSERT INTO document_notes_cache
            (document_id, notes_id, notes_content, key_points)
            VALUES (%s, %s, %s, %s)
        """, (
            payload['document_id'],
            payload['notes_id'],
            payload['notes_content'],
            json.dumps(payload['key_points'])
        ))

        print(f"[Quiz Service] Cached notes for quiz generation")


# Subscriber 3: Analytics Service
class AnalyticsServiceEventListener:
    """
    Analytics service listens to all events for metrics tracking.
    """

    def __init__(self, kafka_consumer, metrics_db):
        self.consumer = kafka_consumer
        self.metrics_db = metrics_db

    def start_listening(self):
        """Listen for all events."""
        for message in self.consumer:
            event = json.loads(message.value.decode('utf-8'))
            self.track_event(event)

    def track_event(self, event):
        """Track event for analytics."""
        self.metrics_db.insert({
            "event_type": event['event_type'],
            "event_timestamp": event['event_timestamp'],
            "user_id": event['payload'].get('user_id'),
            "event_data": event['payload']
        })

        print(f"[Analytics] Tracked event: {event['event_type']}")


# Subscriber 4: Notification Service
class NotificationServiceEventListener:
    """
    Notification service sends user notifications for completed events.
    """

    def __init__(self, kafka_consumer, notification_client):
        self.consumer = kafka_consumer
        self.notification_client = notification_client

    def start_listening(self):
        """Listen for completion events."""
        for message in self.consumer:
            event = json.loads(message.value.decode('utf-8'))

            # Notify user on completion events
            if event['event_type'] in ['document.processed', 'quiz.generated',
                                       'audio.transcription.completed']:
                self.send_notification(event)

    def send_notification(self, event):
        """Send notification to user."""
        user_id = event['payload'].get('user_id')

        notification_messages = {
            'document.processed': "Your document has been processed!",
            'quiz.generated': "Your quiz is ready!",
            'audio.transcription.completed': "Your audio has been transcribed!"
        }

        message = notification_messages.get(event['event_type'], "Task completed")

        self.notification_client.send(user_id, message, event['payload'])
        print(f"[Notification] Sent to user {user_id}: {message}")


# ==================== MULTI-CONSUMER SETUP ====================

def start_all_listeners():
    """
    Start all event listeners in separate threads.
    """
    import threading

    # Consumer groups ensure each service gets all events
    chat_consumer = KafkaConsumer(
        'document.processed',
        bootstrap_servers=['kafka-nlb.internal:9092'],
        group_id='chat-service-group',
        auto_offset_reset='latest'
    )

    quiz_consumer = KafkaConsumer(
        'notes.generated',
        bootstrap_servers=['kafka-nlb.internal:9092'],
        group_id='quiz-service-group',
        auto_offset_reset='latest'
    )

    analytics_consumer = KafkaConsumer(
        'document.uploaded', 'document.processed', 'quiz.generated',
        bootstrap_servers=['kafka-nlb.internal:9092'],
        group_id='analytics-service-group',
        auto_offset_reset='latest'
    )

    notification_consumer = KafkaConsumer(
        'document.processed', 'quiz.generated', 'audio.transcription.completed',
        bootstrap_servers=['kafka-nlb.internal:9092'],
        group_id='notification-service-group',
        auto_offset_reset='latest'
    )

    # Start listeners in separate threads
    listeners = [
        ChatServiceEventListener(chat_consumer, vector_db),
        QuizServiceEventListener(quiz_consumer, db),
        AnalyticsServiceEventListener(analytics_consumer, metrics_db),
        NotificationServiceEventListener(notification_consumer, notification_client)
    ]

    for listener in listeners:
        thread = threading.Thread(target=listener.start_listening, daemon=True)
        thread.start()
        print(f"Started listener: {listener.__class__.__name__}")
```

### Benefits in Our System
- **Loose Coupling**: Services don't need to know about each other
- **Scalability**: Add new subscribers without changing publishers
- **Asynchronous**: Publishers don't wait for subscribers
- **Resilience**: Subscriber failures don't affect publishers

---

## Pattern Comparison Matrix

| Pattern | When to Use | Complexity | Consistency | Example in Our System |
|---------|-------------|------------|-------------|----------------------|
| **Event Sourcing** | Need complete audit trail, time travel | High | Eventual | Document lifecycle tracking |
| **CQRS** | Different read/write requirements | Medium | Eventual | Quiz queries vs commands |
| **Saga** | Multi-service transactions | High | Eventual | Document → Quiz workflow |
| **Event Notification** | Broadcast state changes | Low | Eventual | document.processed → multiple services |

---

## Best Practices for Our Implementation

1. **Idempotency**: Ensure event handlers can process the same event multiple times safely
2. **Event Versioning**: Include event_version field for schema evolution
3. **Error Handling**: Use Dead Letter Queues (DLQ) for failed events
4. **Monitoring**: Track event processing lag and error rates
5. **Ordering**: Use partition keys to maintain order when needed
6. **Retries**: Implement exponential backoff for transient failures

---

## Monitoring and Observability

### Key Metrics to Track

```python
# Metrics to monitor for each pattern

# Event Sourcing
- Event replay duration
- Event store size
- Time to reconstruct state

# CQRS
- Read/write latency
- Read model lag (time behind write model)
- Cache hit rate

# Saga
- Saga completion rate
- Average saga duration
- Compensation execution count

# Event Notification
- Event delivery latency
- Consumer lag per subscriber
- Failed event count
```

---

This completes the Kafka integration patterns documentation for the Cloud-Based Learning Platform.
