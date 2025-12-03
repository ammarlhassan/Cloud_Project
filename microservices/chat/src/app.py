"""
Chat Microservice
Manages chat interactions with AI and publishes events to Kafka
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
DB_NAME = os.environ.get('DB_NAME', 'chat_db')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC = 'chat.message'

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
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                document_id VARCHAR(36),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON chat_messages(session_id, created_at)
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


def generate_ai_response(message, context=None):
    """
    Generate AI response (placeholder - integrate with actual AI service)
    
    Args:
        message: User message
        context: Optional context from document
    
    Returns:
        str: AI response
    """
    # This is a placeholder. In production, integrate with:
    # - Amazon Bedrock
    # - OpenAI API
    # - Anthropic Claude
    # - Custom trained model
    
    response = f"I understand you said: '{message}'. "
    
    if context:
        response += f"Based on the document context, here's my response... "
    else:
        response += "How can I help you further with your learning?"
    
    return response


def publish_to_kafka(message):
    """
    Publish message to Kafka topic
    
    Args:
        message: Message dictionary
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not kafka_producer:
        logger.error("Kafka producer not initialized")
        return False
    
    try:
        future = kafka_producer.send(KAFKA_TOPIC, value=message)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message published to {KAFKA_TOPIC}: partition={record_metadata.partition}, offset={record_metadata.offset}")
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
        'service': 'chat',
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


@app.route('/api/v1/chat/sessions', methods=['POST'])
def create_session():
    """
    Create new chat session
    
    Request body:
    {
        "user_id": "user123",
        "document_id": "doc456" (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        user_id = data.get('user_id')
        document_id = data.get('document_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Insert into database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_sessions (session_id, user_id, document_id)
                VALUES (%s, %s, %s)
                """,
                (session_id, user_id, document_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Created chat session: {session_id}")
            
            return jsonify({
                'session_id': session_id,
                'user_id': user_id,
                'document_id': document_id,
                'created_at': datetime.utcnow().isoformat()
            }), 201
            
        except Exception as e:
            logger.error(f"Database error creating session: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to create session'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in create_session: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/chat/sessions/<session_id>/messages', methods=['POST'])
def send_message(session_id):
    """
    Send message in chat session
    
    Request body:
    {
        "message": "User message text"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Missing required field: message'}), 400
        
        # Validate message length
        if len(message) > 2000:
            return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
        
        # Get session from database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, document_id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            session = cursor.fetchone()
            
            if not session:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Session not found'}), 404
            
            user_id = session['user_id']
            document_id = session['document_id']
            
            # Generate message IDs
            user_message_id = str(uuid.uuid4())
            ai_message_id = str(uuid.uuid4())
            
            # Store user message
            cursor.execute(
                """
                INSERT INTO chat_messages (message_id, session_id, user_id, role, content)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_message_id, session_id, user_id, 'user', message)
            )
            
            # Generate AI response
            context = None  # In production, fetch document context if document_id exists
            ai_response = generate_ai_response(message, context)
            
            # Store AI response
            cursor.execute(
                """
                INSERT INTO chat_messages (message_id, session_id, user_id, role, content)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ai_message_id, session_id, user_id, 'assistant', ai_response)
            )
            
            # Update session timestamp
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                (session_id,)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Publish to Kafka
            kafka_event = {
                'session_id': session_id,
                'user_id': user_id,
                'document_id': document_id,
                'user_message': message,
                'ai_response': ai_response,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            publish_to_kafka(kafka_event)
            
            logger.info(f"Message sent in session: {session_id}")
            
            return jsonify({
                'user_message': {
                    'message_id': user_message_id,
                    'role': 'user',
                    'content': message
                },
                'ai_response': {
                    'message_id': ai_message_id,
                    'role': 'assistant',
                    'content': ai_response
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Database error sending message: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to send message'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in send_message: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/chat/sessions/<session_id>/messages', methods=['GET'])
def get_messages(session_id):
    """Get all messages in a chat session"""
    try:
        # Get pagination parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate limit
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Check if session exists
            cursor.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': 'Session not found'}), 404
            
            # Get messages
            cursor.execute(
                """
                SELECT message_id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (session_id, limit, offset)
            )
            
            messages = cursor.fetchall()
            
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as total FROM chat_messages WHERE session_id = %s",
                (session_id,)
            )
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'session_id': session_id,
                'messages': [dict(msg) for msg in messages],
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Database error getting messages: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to get messages'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_messages: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/chat/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete chat session and all messages"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Delete messages first (foreign key constraint)
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = %s",
                (session_id,)
            )
            
            # Delete session
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = %s",
                (session_id,)
            )
            
            deleted = cursor.rowcount > 0
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if deleted:
                logger.info(f"Deleted chat session: {session_id}")
                return jsonify({'message': 'Session deleted successfully'}), 200
            else:
                return jsonify({'error': 'Session not found'}), 404
            
        except Exception as e:
            logger.error(f"Database error deleting session: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to delete session'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_session: {e}")
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
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)
