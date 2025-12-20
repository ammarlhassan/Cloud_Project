"""
Chat Microservice
Manages chat interactions with AI and publishes events to Kafka
"""
import os
import json
import logging
import uuid
import signal
import sys
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import boto3
from botocore.exceptions import ClientError
import redis
import jwt
import time
import requests

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
DB_NAME = os.environ.get('DB_NAME', 'chat_service')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'MySecurePassword123!')

KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_PRODUCE_TOPIC = 'chat.message'
KAFKA_CONSUME_TOPIC = 'document.processed'
KAFKA_CONSUMER_GROUP = 'chat-service-group'

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'chat-service-storage-dev-334413050048')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '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')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

# Global variables
shutdown_event = threading.Event()
kafka_consumer = None
redis_client = None
s3_client = None
openrouter_client = None

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


# S3 Helper Functions
def init_s3_client():
    """Initialize S3 client"""
    global s3_client
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        logger.info(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3: {e}")
        return None


def archive_conversation_to_s3(conversation_id, messages):
    """Archive conversation to S3"""
    if not s3_client:
        return None
    try:
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        s3_key = f"conversations/{timestamp}/{conversation_id}.json"
        data = {
            'conversation_id': conversation_id,
            'messages': messages,
            'archived_at': datetime.utcnow().isoformat()
        }
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        logger.info(f"Conversation archived to S3: {s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"S3 archive error: {e}")
        return None


# Redis Helper Functions
def get_redis_connection():
    """Get Redis connection"""
    global redis_client
    if redis_client:
        try:
            redis_client.ping()
            return redis_client
        except:
            pass
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection error: {e}")
        return None


def cache_document_knowledge(document_id, data):
    """Cache document knowledge in Redis"""
    try:
        r = get_redis_connection()
        if r:
            r.setex(f"document:{document_id}", 7200, json.dumps(data))
    except Exception as e:
        logger.error(f"Redis cache error: {e}")


# Kafka Consumer for document.processed
def create_kafka_consumer():
    """Create Kafka consumer"""
    try:
        consumer = KafkaConsumer(
            KAFKA_CONSUME_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest'
        )
        logger.info(f"Kafka consumer initialized for: {KAFKA_CONSUME_TOPIC}")
        return consumer
    except KafkaError as e:
        logger.error(f"Kafka consumer error: {e}")
        return None


def consume_document_events():
    """Background thread to consume document events"""
    global kafka_consumer
    kafka_consumer = create_kafka_consumer()
    if not kafka_consumer:
        return
    
    try:
        for message in kafka_consumer:
            if shutdown_event.is_set():
                break
            event_data = message.value
            document_id = event_data.get('document_id')
            if document_id:
                cache_document_knowledge(document_id, {
                    'content': event_data.get('content', '')[:5000],
                    'notes': event_data.get('notes', '')[:2000]
                })
                logger.info(f"Document knowledge cached: {document_id}")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        if kafka_consumer:
            kafka_consumer.close()


# Start consumer thread
consumer_thread = threading.Thread(target=consume_document_events, daemon=True)
consumer_thread.start()


# AI Integration
def init_openrouter_client():
    """Initialize OpenRouter client"""
    global openrouter_client
    if OPENROUTER_API_KEY and OPENROUTER_API_KEY != '':
        try:
            # OpenRouter uses REST API, no client initialization needed
            openrouter_client = True
            logger.info("OpenRouter client initialized")
            return openrouter_client
        except Exception as e:
            logger.error(f"OpenRouter init error: {e}")
    return None


# JWT Authentication
def token_required(f):
    """JWT authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            current_user_id = data.get('user_id')
            if not current_user_id:
                return jsonify({'error': 'Invalid token'}), 401
            return f(current_user_id, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    return decorated


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


def generate_ai_response(message, conversation_history=None, document_context=None):
    """
    Generate AI response using OpenRouter API
    """
    if not openrouter_client:
        response = f"I understand you said: '{message}'. "
        if document_context:
            response += "I can see you have a document loaded. "
        return response + "How can I help you?"
    
    try:
        messages = [{"role": "system", "content": "You are a helpful AI learning assistant."}]
        
        if document_context:
            messages[0]["content"] += f"\n\nDocument context: {document_context.get('notes', '')[:1000]}"
        
        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({"role": msg.get('role', 'user'), "content": msg.get('content', '')})
        
        messages.append({"role": "user", "content": message})
        
        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "amazon/nova-2-lite-v1:free",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            return "I apologize, but I'm having trouble generating a response. Please try again."
            
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return "I apologize, but I'm having trouble generating a response. Please try again."


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
        future = kafka_producer.send(KAFKA_PRODUCE_TOPIC, value=message)
        record_metadata = future.get(timeout=10)
        
        logger.info(f"Message published to {KAFKA_PRODUCE_TOPIC}: partition={record_metadata.partition}, offset={record_metadata.offset}")
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
    
    redis_healthy = False
    try:
        r = get_redis_connection()
        if r:
            r.ping()
            redis_healthy = True
    except:
        pass
    
    health_status = {
        'service': 'chat',
        'status': 'healthy' if db_healthy and kafka_producer else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'database': db_healthy,
            'kafka_producer': kafka_producer is not None,
            'kafka_consumer': kafka_consumer is not None,
            'redis': redis_healthy,
            's3': s3_client is not None,
            'openrouter': openrouter_client is not None
        }
    }
    
    status_code = 200 if all(health_status['components'].values()) else 503
    return jsonify(health_status), status_code


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    return jsonify({'status': 'ready'}), 200


@app.route('/api/chat/message', methods=['POST'])
@token_required
def send_message_simple(current_user_id):
    """
    Send message and get AI response (simplified endpoint)
    Request body: {"message": "text", "conversation_id": "optional", "document_id": "optional"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        document_id = data.get('document_id')
        
        if not message:
            return jsonify({'error': 'Missing required field: message'}), 400
        
        if len(message) > 2000:
            return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Insert into database
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Create conversation if needed
            if not conversation_id or conversation_id == str(uuid.uuid4()):
                cursor.execute(
                    """INSERT INTO chat_sessions (session_id, user_id, document_id)
                       VALUES (%s, %s, %s)""",
                    (conversation_id, current_user_id, document_id)
                )
            
            # Get conversation history
            cursor.execute(
                """SELECT role, content FROM chat_messages
                   WHERE session_id = %s ORDER BY created_at ASC""",
                (conversation_id,)
            )
            history = [dict(msg) for msg in cursor.fetchall()]
            
            # Get document context
            doc_context = None
            if document_id:
                r = get_redis_connection()
                if r:
                    cached = r.get(f"document:{document_id}")
                    if cached:
                        doc_context = json.loads(cached)
            
            # Generate IDs
            user_msg_id = str(uuid.uuid4())
            ai_msg_id = str(uuid.uuid4())
            
            # Store user message
            cursor.execute(
                """INSERT INTO chat_messages (message_id, session_id, user_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_msg_id, conversation_id, current_user_id, 'user', message)
            )
            
            # Generate AI response
            ai_response = generate_ai_response(message, history, doc_context)
            
            # Store AI response
            cursor.execute(
                """INSERT INTO chat_messages (message_id, session_id, user_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                (ai_msg_id, conversation_id, current_user_id, 'assistant', ai_response)
            )
            
            # Update timestamp
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                (conversation_id,)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Publish to Kafka
            publish_to_kafka({
                'conversation_id': conversation_id,
                'user_id': current_user_id,
                'document_id': document_id,
                'user_message': message,
                'ai_response': ai_response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return jsonify({
                'conversation_id': conversation_id,
                'user_message': {'message_id': user_msg_id, 'role': 'user', 'content': message},
                'ai_response': {'message_id': ai_msg_id, 'role': 'assistant', 'content': ai_response}
            }), 200
            
        except Exception as e:
            logger.error(f"Database error creating session: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to create session'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in create_session: {e}")
        return jsonify({'error': 'Internal server error'}), 500



@app.route('/api/chat/conversations', methods=['GET'])
@token_required
def list_conversations(current_user_id):
    """List user conversations"""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Get conversations for user
            cursor.execute(
                """
                SELECT c.session_id, c.document_id, c.created_at, c.updated_at,
                       COUNT(m.message_id) as message_count
                FROM chat_sessions c
                LEFT JOIN chat_messages m ON c.session_id = m.session_id
                WHERE c.user_id = %s
                GROUP BY c.session_id
                ORDER BY c.updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (current_user_id, limit, offset)
            )
            
            conversations = [dict(conv) for conv in cursor.fetchall()]
            
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as total FROM chat_sessions WHERE user_id = %s",
                (current_user_id,)
            )
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'conversations': conversations,
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Database error listing conversations: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to list conversations'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in list_conversations: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/chat/conversations/<conversation_id>', methods=['GET'])
@token_required
def get_conversation_history(current_user_id, conversation_id):
    """Get conversation history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit > 100:
            limit = 100
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Verify conversation belongs to user
            cursor.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                (conversation_id, current_user_id)
            )
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': 'Conversation not found'}), 404
            
            # Get messages
            cursor.execute(
                """
                SELECT message_id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (conversation_id, limit, offset)
            )
            
            messages = [dict(msg) for msg in cursor.fetchall()]
            
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as total FROM chat_messages WHERE session_id = %s",
                (conversation_id,)
            )
            total = cursor.fetchone()['total']
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'conversation_id': conversation_id,
                'messages': messages,
                'total': total,
                'limit': limit,
                'offset': offset
            }), 200
            
        except Exception as e:
            logger.error(f"Database error getting conversation: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to get conversation'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_conversation_history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/chat/conversations/<conversation_id>', methods=['DELETE'])
@token_required
def delete_conversation(current_user_id, conversation_id):
    """Delete conversation and archive to S3"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 503
        
        try:
            cursor = conn.cursor()
            
            # Verify conversation belongs to user
            cursor.execute(
                "SELECT session_id FROM chat_sessions WHERE session_id = %s AND user_id = %s",
                (conversation_id, current_user_id)
            )
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'error': 'Conversation not found'}), 404
            
            # Get all messages for archiving
            cursor.execute(
                """
                SELECT message_id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            messages = [dict(msg) for msg in cursor.fetchall()]
            
            # Archive to S3 before deletion
            if s3_client and messages:
                archive_conversation_to_s3(conversation_id, messages)
            
            # Delete messages
            cursor.execute(
                "DELETE FROM chat_messages WHERE session_id = %s",
                (conversation_id,)
            )
            
            # Delete session
            cursor.execute(
                "DELETE FROM chat_sessions WHERE session_id = %s",
                (conversation_id,)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Deleted conversation: {conversation_id}")
            return jsonify({'message': 'Conversation deleted successfully'}), 200
            
        except Exception as e:
            logger.error(f"Database error deleting conversation: {e}")
            if conn:
                conn.close()
            return jsonify({'error': 'Failed to delete conversation'}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in delete_conversation: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


# Graceful shutdown
def graceful_shutdown(signum, frame):
    """Handle graceful shutdown"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_event.set()
    if kafka_producer:
        kafka_producer.close()
    if kafka_consumer:
        kafka_consumer.close()
    if redis_client:
        try:
            redis_client.close()
        except:
            pass
    sys.exit(0)


signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)


# Initialize services on startup
# Database initialization removed - using existing AWS RDS database
init_s3_client()
get_redis_connection()
init_openrouter_client()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=False)
