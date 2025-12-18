"""
Quiz Microservice
Generates quizzes from documents using AI and manages quiz submissions
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time
import random
import boto3
from botocore.exceptions import ClientError
import threading
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Environment configuration
DB_HOST = os.environ.get('DB_HOST', 'cloud-project-db.cjyjymrymgig.us-east-1.rds.amazonaws.com')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'quiz_service')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'MySecurePassword123!')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'quiz.requested'
KAFKA_TOPIC_GENERATED = 'quiz.generated'
KAFKA_TOPIC_NOTES_GENERATED = 'notes.generated'

# S3 Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'cse363-quiz-service-dev-334413050048')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

# OpenRouter Configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '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')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'amazon/nova-2-lite-v1:free')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

# Initialize Kafka producer
def create_kafka_producer():
    """Create Kafka producer with retry logic"""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info("Kafka producer initialized successfully")
            return producer
        except KafkaError as e:
            logger.warning(f"Kafka connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to initialize Kafka producer after all retries")
                return None

kafka_producer = create_kafka_producer()

# Initialize S3 client
def create_s3_client():
    """Create S3 client"""
    try:
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            s3_client = boto3.client(
                's3',
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        else:
            # Use IAM role if running in AWS
            s3_client = boto3.client('s3', region_name=AWS_REGION)
        
        logger.info("S3 client initialized successfully")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}")
        return None

s3_client = create_s3_client()

# Initialize OpenRouter client
def create_openrouter_client():
    """Create OpenRouter client instance"""
    if not OPENROUTER_API_KEY:
        logger.warning("OpenRouter API key not configured")
        return None
    
    try:
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://quiz-service.local",
                "X-Title": "Quiz Service"
            }
        )
        logger.info(f"OpenRouter client initialized successfully with model: {OPENROUTER_MODEL}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenRouter client: {e}")
        return None

openrouter_client = create_openrouter_client()


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


# Database initialization removed - using existing AWS RDS database
# Tables are pre-configured in AWS RDS


# Kafka Consumer for quiz.requested and notes.generated
def start_kafka_consumer():
    """Start Kafka consumer in background thread"""
    def consume_messages():
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                consumer = KafkaConsumer(
                    KAFKA_TOPIC_REQUEST,
                    KAFKA_TOPIC_NOTES_GENERATED,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    group_id='quiz-service-group',
                    auto_offset_reset='earliest',
                    enable_auto_commit=True
                )
                
                logger.info("Kafka consumer started successfully")
                
                for message in consumer:
                    try:
                        topic = message.topic
                        data = message.value
                        
                        logger.info(f"Received message from {topic}: {data}")
                        
                        if topic == KAFKA_TOPIC_REQUEST:
                            handle_quiz_requested(data)
                        elif topic == KAFKA_TOPIC_NOTES_GENERATED:
                            handle_notes_generated(data)
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
            except Exception as e:
                logger.warning(f"Kafka consumer attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to start Kafka consumer after all retries")
                    break
    
    consumer_thread = threading.Thread(target=consume_messages, daemon=True)
    consumer_thread.start()
    logger.info("Kafka consumer thread started")


def handle_quiz_requested(data):
    """Handle quiz.requested event"""
    try:
        document_id = data.get('document_id')
        user_id = data.get('user_id')
        logger.info(f"Processing quiz request for document {document_id} by user {user_id}")
        # Additional processing logic can be added here
    except Exception as e:
        logger.error(f"Error handling quiz.requested: {e}")


def handle_notes_generated(data):
    """Handle notes.generated event"""
    try:
        document_id = data.get('document_id')
        notes_content = data.get('notes_content', '')
        logger.info(f"Notes generated for document {document_id}, can use for quiz generation")
        # Can cache or use notes content for better quiz generation
    except Exception as e:
        logger.error(f"Error handling notes.generated: {e}")


# Start Kafka consumer on startup
start_kafka_consumer()


def upload_to_s3(content, key):
    """Upload content to S3 bucket"""
    if not s3_client:
        logger.error("S3 client not initialized")
        return False
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=json.dumps(content),
            ContentType='application/json'
        )
        logger.info(f"Uploaded to S3: {key}")
        return True
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        return False


def download_from_s3(key):
    """Download content from S3 bucket"""
    if not s3_client:
        logger.error("S3 client not initialized")
        return None
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        content = json.loads(response['Body'].read().decode('utf-8'))
        return content
    except ClientError as e:
        logger.error(f"S3 download error: {e}")
        return None


def delete_from_s3(key):
    """Delete content from S3 bucket"""
    if not s3_client:
        logger.error("S3 client not initialized")
        return False
    
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
        logger.info(f"Deleted from S3: {key}")
        return True
    except ClientError as e:
        logger.error(f"S3 delete error: {e}")
        return False


def generate_quiz_questions(document_text, num_questions=5, difficulty='medium'):
    """
    Generate quiz questions from document text using AI
    
    Args:
        document_text: Document text content
        num_questions: Number of questions to generate
        difficulty: Difficulty level (easy, medium, hard)
    
    Returns:
        list: List of question dictionaries
    """
    if not openrouter_client:
        logger.warning("OpenRouter client not initialized, using fallback generation")
        return generate_fallback_questions(num_questions, difficulty)
    
    try:
        # Create prompt for question generation
        prompt = f"""
You are an expert educator creating quiz questions from educational content.

Document Content:
{document_text[:4000]}

Generate {num_questions} {difficulty} level quiz questions. Include a mix of:
- Multiple choice questions (4 options each)
- True/False questions
- Short answer questions

For each question, provide:
1. Question text
2. Question type (multiple_choice, true_false, or short_answer)
3. Options (for multiple_choice: array of 4 options, for true_false: ["True", "False"])
4. Correct answer
5. Brief explanation

Return ONLY a valid JSON array with this structure:
[
  {{
    "question_text": "Question here?",
    "question_type": "multiple_choice",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Explanation here"
  }}
]
"""
        
        # Call OpenRouter API with streaming
        response = openrouter_client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educator. Always return valid JSON arrays."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            stream=False  # Use non-streaming for JSON parsing
        )
        
        # Extract response content
        result = response.choices[0].message.content
        
        # Try to extract JSON from markdown code blocks if present
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        # Parse JSON response
        questions_data = json.loads(result.strip())
        
        # Format questions with points
        questions = []
        for q in questions_data:
            question = {
                'question_text': q['question_text'],
                'question_type': q.get('question_type', 'multiple_choice'),
                'options': q.get('options', []),
                'correct_answer': q['correct_answer'],
                'explanation': q.get('explanation', ''),
                'points': 1 if difficulty == 'easy' else 2 if difficulty == 'medium' else 3
            }
            questions.append(question)
        
        return questions[:num_questions]
        
    except Exception as e:
        logger.error(f"AI question generation error: {e}")
        return generate_fallback_questions(num_questions, difficulty)


def generate_fallback_questions(num_questions=5, difficulty='medium'):
    """Generate fallback questions when AI is unavailable"""
    questions = []
    question_types = ['multiple_choice', 'true_false', 'short_answer']
    
    for i in range(num_questions):
        q_type = question_types[i % len(question_types)]
        
        if q_type == 'multiple_choice':
            question = {
                'question_text': f"Question {i + 1}: What is the main concept discussed in the document?",
                'question_type': 'multiple_choice',
                'options': [
                    'Option A: First possible answer',
                    'Option B: Second possible answer',
                    'Option C: Third possible answer',
                    'Option D: Fourth possible answer'
                ],
                'correct_answer': 'Option A: First possible answer',
                'explanation': 'This is the correct answer based on the document content.',
                'points': 1 if difficulty == 'easy' else 2 if difficulty == 'medium' else 3
            }
        elif q_type == 'true_false':
            question = {
                'question_text': f"Question {i + 1}: The document discusses important concepts. True or False?",
                'question_type': 'true_false',
                'options': ['True', 'False'],
                'correct_answer': 'True',
                'explanation': 'This statement is true based on the document content.',
                'points': 1 if difficulty == 'easy' else 2 if difficulty == 'medium' else 3
            }
        else:  # short_answer
            question = {
                'question_text': f"Question {i + 1}: Briefly explain the main topic of the document.",
                'question_type': 'short_answer',
                'options': [],
                'correct_answer': 'The main topic is...',
                'explanation': 'Key points should include...',
                'points': 2 if difficulty == 'easy' else 3 if difficulty == 'medium' else 5
            }
        
        questions.append(question)
    
    return questions


def publish_to_kafka(topic, message):
    """
    Publish message to Kafka topic
    
    Args:
        topic: Kafka topic name
        message: Message dictionary
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not kafka_producer:
        logger.error("Kafka producer not initialized")
        return False
    
    try:
        future = kafka_producer.send(topic, value=message)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message published to {topic}: partition={record_metadata.partition}, offset={record_metadata.offset}")
        return True
        
    except KafkaError as e:
        logger.error(f"Kafka publish error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error publishing to Kafka: {e}")
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db_conn = get_db_connection()
    db_healthy = db_conn is not None
    if db_conn:
        db_conn.close()
    
    health_status = {
        'service': 'quiz',
        'status': 'healthy' if db_healthy and kafka_producer else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'database': db_healthy,
            'kafka': kafka_producer is not None
        }
    }
    
    status_code = 200 if all(health_status['components'].values()) else 503
    return jsonify(health_status), status_code


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    return jsonify({'status': 'ready'}), 200


@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz():
    """
    Generate quiz from document
    
    Request body:
    {
        "document_id": "doc123",
        "user_id": "user456",
        "title": "Quiz title",
        "num_questions": 5 (optional),
        "difficulty": "medium" (optional: easy, medium, hard)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        document_id = data.get('document_id')
        user_id = data.get('user_id')
        title = data.get('title', 'Generated Quiz')
        num_questions = data.get('num_questions', 5)
        difficulty = data.get('difficulty', 'medium')
        
        # Validate required fields
        if not document_id:
            return jsonify({'error': 'Missing required field: document_id'}), 400
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        # Validate difficulty
        if difficulty not in ['easy', 'medium', 'hard']:
            return jsonify({'error': 'Invalid difficulty level'}), 400
        
        # Validate num_questions
        if num_questions < 1 or num_questions > 20:
            return jsonify({'error': 'num_questions must be between 1 and 20'}), 400
        
        # Generate quiz ID
        quiz_id = str(uuid.uuid4())
        
        # Publish request event to Kafka
        request_event = {
            'quiz_id': quiz_id,
            'document_id': document_id,
            'user_id': user_id,
            'num_questions': num_questions,
            'difficulty': difficulty,
            'status': 'generating',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_REQUEST, request_event)
        
        # In production, fetch document text from document service
        # For now, use placeholder text
        document_text = "This is placeholder document text for quiz generation."
        
        # Generate questions
        questions = generate_quiz_questions(document_text, num_questions, difficulty)
        
        # Store quiz in database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Insert quiz
            cursor.execute(
                """
                INSERT INTO quizzes (quiz_id, document_id, user_id, title, difficulty)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (quiz_id, document_id, user_id, title, difficulty)
            )
            
            # Insert questions
            for question in questions:
                question_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO questions 
                    (question_id, quiz_id, question_text, question_type, options, correct_answer, explanation, points)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        question_id,
                        quiz_id,
                        question['question_text'],
                        question['question_type'],
                        json.dumps(question['options']),
                        question['correct_answer'],
                        question['explanation'],
                        question['points']
                    )
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Upload quiz template to S3
            s3_key = f"quizzes/{quiz_id}/template.json"
            quiz_template = {
                'quiz_id': quiz_id,
                'title': title,
                'difficulty': difficulty,
                'questions': questions,
                'created_at': datetime.utcnow().isoformat()
            }
            upload_to_s3(quiz_template, s3_key)
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to store quiz'}), 500
        
        # Publish generated event to Kafka
        generated_event = {
            'quiz_id': quiz_id,
            'document_id': document_id,
            'user_id': user_id,
            'num_questions': len(questions),
            'difficulty': difficulty,
            'status': 'generated',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_GENERATED, generated_event)
        
        logger.info(f"Quiz generated: {quiz_id}")
        
        return jsonify({
            'quiz_id': quiz_id,
            'title': title,
            'num_questions': len(questions),
            'difficulty': difficulty,
            'status': 'generated'
        }), 201
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_quiz: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/<quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    """Get quiz with questions"""
    try:
        include_answers = request.args.get('include_answers', 'false').lower() == 'true'
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Get quiz
            cursor.execute(
                "SELECT * FROM quizzes WHERE quiz_id = %s",
                (quiz_id,)
            )
            quiz = cursor.fetchone()
            
            if not quiz:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Quiz not found'}), 404
            
            # Get questions
            cursor.execute(
                """
                SELECT question_id, question_text, question_type, options, 
                       correct_answer, explanation, points
                FROM questions
                WHERE quiz_id = %s
                ORDER BY question_id
                """,
                (quiz_id,)
            )
            questions = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format response
            questions_list = []
            for q in questions:
                question_dict = {
                    'question_id': q['question_id'],
                    'question_text': q['question_text'],
                    'question_type': q['question_type'],
                    'options': q['options'],
                    'points': q['points']
                }
                
                # Include answers only if requested
                if include_answers:
                    question_dict['correct_answer'] = q['correct_answer']
                    question_dict['explanation'] = q['explanation']
                
                questions_list.append(question_dict)
            
            response = {
                'quiz_id': quiz['quiz_id'],
                'document_id': quiz['document_id'],
                'title': quiz['title'],
                'difficulty': quiz['difficulty'],
                'created_at': quiz['created_at'].isoformat(),
                'questions': questions_list
            }
            
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to retrieve quiz'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_quiz: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/<quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    """
    Submit quiz answers
    
    Request body:
    {
        "user_id": "user123",
        "answers": {
            "question_id_1": "answer1",
            "question_id_2": "answer2",
            ...
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        user_id = data.get('user_id')
        answers = data.get('answers', {})
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        if not answers:
            return jsonify({'error': 'Missing required field: answers'}), 400
        
        # Get quiz questions with correct answers
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Check if quiz exists
            cursor.execute(
                "SELECT quiz_id FROM quizzes WHERE quiz_id = %s",
                (quiz_id,)
            )
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': 'Quiz not found'}), 404
            
            # Get questions
            cursor.execute(
                "SELECT question_id, correct_answer, points FROM questions WHERE quiz_id = %s",
                (quiz_id,)
            )
            questions = cursor.fetchall()
            
            # Calculate score
            score = 0
            max_score = 0
            results = []
            
            for question in questions:
                question_id = question['question_id']
                correct_answer = question['correct_answer']
                points = question['points']
                
                max_score += points
                
                user_answer = answers.get(question_id, '')
                is_correct = user_answer == correct_answer
                
                if is_correct:
                    score += points
                
                results.append({
                    'question_id': question_id,
                    'is_correct': is_correct,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer
                })
            
            # Store submission
            submission_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO quiz_submissions (submission_id, quiz_id, user_id, answers, score, max_score)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (submission_id, quiz_id, user_id, json.dumps(answers), score, max_score)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Quiz submitted: {quiz_id}, score: {score}/{max_score}")
            
            return jsonify({
                'submission_id': submission_id,
                'quiz_id': quiz_id,
                'score': score,
                'max_score': max_score,
                'percentage': round((score / max_score * 100), 2) if max_score > 0 else 0,
                'results': results
            }), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to submit quiz'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in submit_quiz: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/list', methods=['GET'])
def list_quizzes():
    """List user quizzes"""
    try:
        user_id = request.args.get('user_id')
        document_id = request.args.get('document_id')
        
        if not user_id and not document_id:
            return jsonify({'error': 'Missing required parameter: user_id or document_id'}), 400
        
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute(
                    """
                    SELECT quiz_id, document_id, title, difficulty, created_at
                    FROM quizzes
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
                
                cursor.execute(
                    "SELECT COUNT(*) as total FROM quizzes WHERE user_id = %s",
                    (user_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT quiz_id, user_id, title, difficulty, created_at
                    FROM quizzes
                    WHERE document_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (document_id, limit, offset)
                )
                
                cursor.execute(
                    "SELECT COUNT(*) as total FROM quizzes WHERE document_id = %s",
                    (document_id,)
                )
            
            quizzes = cursor.fetchall()
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'quizzes': [dict(quiz) for quiz in quizzes],
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to list quizzes'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in list_quizzes: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/<quiz_id>/results', methods=['GET'])
def get_quiz_results(quiz_id):
    """Get quiz results and feedback for a specific quiz"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Get quiz info
            cursor.execute(
                "SELECT quiz_id, title, difficulty FROM quizzes WHERE quiz_id = %s",
                (quiz_id,)
            )
            quiz = cursor.fetchone()
            
            if not quiz:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Quiz not found'}), 404
            
            # Get all submissions for this user and quiz
            cursor.execute(
                """
                SELECT submission_id, answers, score, max_score, submitted_at
                FROM quiz_submissions
                WHERE quiz_id = %s AND user_id = %s
                ORDER BY submitted_at DESC
                """,
                (quiz_id, user_id)
            )
            submissions = cursor.fetchall()
            
            if not submissions:
                cursor.close()
                conn.close()
                return jsonify({'error': 'No submissions found'}), 404
            
            # Get questions with correct answers and explanations
            cursor.execute(
                """
                SELECT question_id, question_text, question_type, options, 
                       correct_answer, explanation, points
                FROM questions
                WHERE quiz_id = %s
                ORDER BY question_id
                """,
                (quiz_id,)
            )
            questions = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Format submissions with detailed feedback
            submissions_list = []
            for sub in submissions:
                answers = sub['answers']
                question_results = []
                
                for q in questions:
                    question_id = q['question_id']
                    user_answer = answers.get(question_id, '')
                    is_correct = user_answer == q['correct_answer']
                    
                    question_results.append({
                        'question_id': question_id,
                        'question_text': q['question_text'],
                        'question_type': q['question_type'],
                        'user_answer': user_answer,
                        'correct_answer': q['correct_answer'],
                        'is_correct': is_correct,
                        'explanation': q['explanation'],
                        'points_earned': q['points'] if is_correct else 0,
                        'points_possible': q['points']
                    })
                
                submissions_list.append({
                    'submission_id': sub['submission_id'],
                    'score': sub['score'],
                    'max_score': sub['max_score'],
                    'percentage': round((sub['score'] / sub['max_score'] * 100), 2) if sub['max_score'] > 0 else 0,
                    'submitted_at': sub['submitted_at'].isoformat(),
                    'question_results': question_results
                })
            
            return jsonify({
                'quiz_id': quiz['quiz_id'],
                'title': quiz['title'],
                'difficulty': quiz['difficulty'],
                'submissions': submissions_list,
                'total_attempts': len(submissions),
                'best_score': max([s['score'] for s in submissions]),
                'best_percentage': max([s['score'] / s['max_score'] * 100 for s in submissions]) if submissions else 0
            }), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to get quiz results'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_quiz_results: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/history', methods=['GET'])
def get_quiz_history():
    """Get user's quiz history with scores"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Get quiz history with latest submission info
            cursor.execute(
                """
                SELECT 
                    q.quiz_id,
                    q.document_id,
                    q.title,
                    q.difficulty,
                    q.created_at,
                    COUNT(DISTINCT qs.submission_id) as total_attempts,
                    MAX(qs.score) as best_score,
                    MAX(qs.max_score) as max_score,
                    MAX(qs.submitted_at) as last_attempt
                FROM quizzes q
                LEFT JOIN quiz_submissions qs ON q.quiz_id = qs.quiz_id AND qs.user_id = %s
                WHERE q.user_id = %s
                GROUP BY q.quiz_id, q.document_id, q.title, q.difficulty, q.created_at
                ORDER BY last_attempt DESC NULLS LAST, q.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, user_id, limit, offset)
            )
            history = cursor.fetchall()
            
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as total FROM quizzes WHERE user_id = %s",
                (user_id,)
            )
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            # Format history
            history_list = []
            for item in history:
                history_item = {
                    'quiz_id': item['quiz_id'],
                    'document_id': item['document_id'],
                    'title': item['title'],
                    'difficulty': item['difficulty'],
                    'created_at': item['created_at'].isoformat(),
                    'total_attempts': item['total_attempts'],
                    'best_score': item['best_score'],
                    'max_score': item['max_score'],
                    'best_percentage': round((item['best_score'] / item['max_score'] * 100), 2) if item['max_score'] else None,
                    'last_attempt': item['last_attempt'].isoformat() if item['last_attempt'] else None,
                    'status': 'completed' if item['total_attempts'] > 0 else 'not_started'
                }
                history_list.append(history_item)
            
            return jsonify({
                'history': history_list,
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to get quiz history'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_quiz_history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/quiz/<quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    """Delete quiz and all associated data"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Check if quiz exists and belongs to user
            cursor.execute(
                "SELECT quiz_id, user_id FROM quizzes WHERE quiz_id = %s",
                (quiz_id,)
            )
            quiz = cursor.fetchone()
            
            if not quiz:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Quiz not found'}), 404
            
            if quiz['user_id'] != user_id:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Unauthorized to delete this quiz'}), 403
            
            # Delete from database (cascade will handle questions and submissions)
            cursor.execute("DELETE FROM quizzes WHERE quiz_id = %s", (quiz_id,))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # Delete from S3
            s3_key = f"quizzes/{quiz_id}/template.json"
            delete_from_s3(s3_key)
            
            logger.info(f"Quiz deleted: {quiz_id}")
            
            return jsonify({
                'message': 'Quiz deleted successfully',
                'quiz_id': quiz_id
            }), 200
            
        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to delete quiz'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_quiz: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False)
