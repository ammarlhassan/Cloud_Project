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
from kafka import KafkaProducer
from kafka.errors import KafkaError
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Environment configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'quiz_db')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'quiz.requested'
KAFKA_TOPIC_GENERATED = 'quiz.generated'

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


def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to initialize database - no connection")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create quizzes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                quiz_id VARCHAR(36) PRIMARY KEY,
                document_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                title VARCHAR(255) NOT NULL,
                difficulty VARCHAR(20) DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                question_id VARCHAR(36) PRIMARY KEY,
                quiz_id VARCHAR(36) NOT NULL,
                question_text TEXT NOT NULL,
                question_type VARCHAR(20) DEFAULT 'multiple_choice',
                options JSONB,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                points INTEGER DEFAULT 1,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
            )
        """)
        
        # Create submissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_submissions (
                submission_id VARCHAR(36) PRIMARY KEY,
                quiz_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                answers JSONB NOT NULL,
                score INTEGER,
                max_score INTEGER,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quizzes_user 
            ON quizzes(user_id, created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quizzes_document 
            ON quizzes(document_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_submissions_quiz 
            ON quiz_submissions(quiz_id, submitted_at DESC)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        if conn:
            conn.close()
        return False


# Initialize database on startup
init_database()


def generate_quiz_questions(document_text, num_questions=5, difficulty='medium'):
    """
    Generate quiz questions from document text (placeholder - integrate with AI)
    
    Args:
        document_text: Document text content
        num_questions: Number of questions to generate
        difficulty: Difficulty level (easy, medium, hard)
    
    Returns:
        list: List of question dictionaries
    """
    # This is a placeholder. In production, integrate with:
    # - Amazon Bedrock
    # - OpenAI API
    # - Anthropic Claude
    # - Custom trained model
    
    # Generate sample questions based on document
    questions = []
    
    for i in range(num_questions):
        question = {
            'question_text': f"Question {i + 1} about the document content: What is the main topic discussed?",
            'question_type': 'multiple_choice',
            'options': [
                'Option A: First possible answer',
                'Option B: Second possible answer',
                'Option C: Third possible answer',
                'Option D: Fourth possible answer'
            ],
            'correct_answer': 'Option A: First possible answer',
            'explanation': 'This is the correct answer because...',
            'points': 1 if difficulty == 'easy' else 2 if difficulty == 'medium' else 3
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


@app.route('/api/v1/quizzes/generate', methods=['POST'])
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


@app.route('/api/v1/quizzes/<quiz_id>', methods=['GET'])
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


@app.route('/api/v1/quizzes/<quiz_id>/submit', methods=['POST'])
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


@app.route('/api/v1/quizzes', methods=['GET'])
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
