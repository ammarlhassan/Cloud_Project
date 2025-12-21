"""
Text-to-Speech (TTS) Microservice
Converts text to audio using gTTS (Google Text-to-Speech) and publishes results to Kafka
Stores audio files in S3
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
from gtts import gTTS
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time
import redis
import threading
import signal
import sys
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Environment configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET = os.environ.get('S3_BUCKET_TTS', 'tts2-service-storage-dev-653040176723')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'audio.generation.requested'
KAFKA_TOPIC_COMPLETED = 'audio.generation.completed'
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
AUDIO_RETENTION_DAYS = int(os.environ.get('AUDIO_RETENTION_DAYS', '7'))

# Supported audio formats and their content types
AUDIO_FORMATS = {
    'mp3': {'content_type': 'audio/mpeg'}
}

# Voice/language mapping for gTTS
VOICE_LANGUAGE_MAP = {
    'Joanna': 'en',      # English (US)
    'Matthew': 'en',     # English (US)
    'Amy': 'en-uk',      # English (UK)
    'Brian': 'en-uk',    # English (UK)
    'Emma': 'en-uk',     # English (UK)
    'Ivy': 'en',         # English (US)
    'default': 'en'      # Default to English
}

# Shutdown flag for graceful termination
shutdown_flag = threading.Event()

# Initialize AWS S3 client (still needed for storage)
try:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    logger.info("AWS S3 client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS S3 client: {e}")
    s3_client = None

logger.info("Using gTTS (Google Text-to-Speech) - No Polly credentials needed!")

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=False,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info("Redis client initialized successfully")
except Exception as e:
    logger.warning(f"Redis not available: {e}. Caching disabled.")
    redis_client = None

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


def ensure_s3_bucket():
    """Ensure S3 bucket exists"""
    if not s3_client:
        return False
    
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"S3 bucket {S3_BUCKET} exists")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            try:
                s3_client.create_bucket(Bucket=S3_BUCKET)
                logger.info(f"Created S3 bucket: {S3_BUCKET}")
                return True
            except ClientError as ce:
                logger.error(f"Failed to create S3 bucket: {ce}")
                return False
        else:
            logger.error(f"Error checking S3 bucket: {e}")
            return False


def convert_text_to_speech(text, voice_id='Joanna', output_format='mp3', language_code=None):
    """
    Convert text to speech using gTTS (Google Text-to-Speech)
    
    Args:
        text: Text to convert
        voice_id: Voice ID mapped to language (default: Joanna -> en)
        output_format: Audio format (only mp3 supported by gTTS)
        language_code: Optional language code override
    
    Returns:
        tuple: (audio_stream, content_type) or (None, None) on error
    """
    # Only MP3 is supported by gTTS
    if output_format.lower() != 'mp3':
        logger.warning(f"gTTS only supports MP3, converting {output_format} request to MP3")
        output_format = 'mp3'
    
    content_type = 'audio/mpeg'
    
    try:
        # Map voice to language
        language = language_code if language_code else VOICE_LANGUAGE_MAP.get(voice_id, 'en')
        
        # Generate speech using gTTS
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Save to BytesIO object
        audio_fp = BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        logger.info(f"Successfully generated speech: format=mp3, language={language}, length={len(text)}")
        return audio_fp, content_type
        
    except Exception as e:
        logger.error(f"gTTS synthesis error: {e}")
        return None, None


def upload_audio_to_s3(audio_stream, file_key, content_type='audio/mpeg'):
    """
    Upload audio to S3
    
    Args:
        audio_stream: Audio data stream
        file_key: S3 object key
        content_type: MIME type of audio
    
    Returns:
        str: S3 URL or None on error
    """
    if not s3_client:
        logger.error("S3 client not initialized")
        return None
    
    try:
        # Read audio stream
        audio_data = audio_stream.read()
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_key,
            Body=audio_data,
            ContentType=content_type
        )
        
        # Generate S3 URL
        s3_url = f"s3://{S3_BUCKET}/{file_key}"
        logger.info(f"Audio uploaded to S3: {s3_url}")
        
        return s3_url
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        return None


def get_audio_from_s3(file_key):
    """
    Retrieve audio file from S3
    
    Args:
        file_key: S3 object key
    
    Returns:
        tuple: (audio_data, content_type) or (None, None) on error
    """
    if not s3_client:
        logger.error("S3 client not initialized")
        return None, None
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_key)
        audio_data = response['Body'].read()
        content_type = response.get('ContentType', 'audio/mpeg')
        
        logger.info(f"Retrieved audio from S3: {file_key}")
        return audio_data, content_type
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"Audio file not found: {file_key}")
        else:
            logger.error(f"S3 retrieval error: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error retrieving from S3: {e}")
        return None, None


def delete_audio_from_s3(file_key):
    """
    Delete audio file from S3
    
    Args:
        file_key: S3 object key
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not s3_client:
        logger.error("S3 client not initialized")
        return False
    
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)
        logger.info(f"Deleted audio from S3: {file_key}")
        return True
        
    except ClientError as e:
        logger.error(f"S3 deletion error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting from S3: {e}")
        return False


def store_audio_metadata(task_id, user_id, file_key, voice_id, output_format, text_length):
    """
    Store audio metadata in Redis cache
    
    Args:
        task_id: Unique task identifier
        user_id: User identifier
        file_key: S3 file key
        voice_id: Voice used
        output_format: Audio format
        text_length: Length of original text
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        metadata = {
            'task_id': task_id,
            'user_id': user_id,
            'file_key': file_key,
            'voice_id': voice_id,
            'format': output_format,
            'text_length': text_length,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Store with expiration (7 days default)
        redis_client.setex(
            f"tts:audio:{task_id}",
            AUDIO_RETENTION_DAYS * 86400,
            json.dumps(metadata)
        )
        
        # Also create user index
        redis_client.sadd(f"tts:user:{user_id}", task_id)
        redis_client.expire(f"tts:user:{user_id}", AUDIO_RETENTION_DAYS * 86400)
        
        logger.info(f"Stored metadata for audio: {task_id}")
        return True
        
    except Exception as e:
        logger.error(f"Redis store error: {e}")
        return False


def get_audio_metadata(task_id):
    """
    Retrieve audio metadata from Redis cache
    
    Args:
        task_id: Unique task identifier
    
    Returns:
        dict: Metadata or None if not found
    """
    if not redis_client:
        return None
    
    try:
        data = redis_client.get(f"tts:audio:{task_id}")
        if data:
            return json.loads(data)
        return None
        
    except Exception as e:
        logger.error(f"Redis retrieval error: {e}")
        return None


def delete_audio_metadata(task_id, user_id=None):
    """
    Delete audio metadata from Redis cache
    
    Args:
        task_id: Unique task identifier
        user_id: Optional user identifier to update index
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        redis_client.delete(f"tts:audio:{task_id}")
        
        if user_id:
            redis_client.srem(f"tts:user:{user_id}", task_id)
        
        logger.info(f"Deleted metadata for audio: {task_id}")
        return True
        
    except Exception as e:
        logger.error(f"Redis deletion error: {e}")
        return False


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
    redis_healthy = False
    if redis_client:
        try:
            redis_client.ping()
            redis_healthy = True
        except:
            pass
    
    health_status = {
        'service': 'tts',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'polly': polly_client is not None,
            's3': s3_client is not None,
            'kafka': kafka_producer is not None,
            'redis': redis_healthy
        }
    }
    
    # Redis is optional, so don't fail health check if it's down
    required_components = ['polly', 's3', 'kafka']
    status_code = 200 if all(health_status['components'][c] for c in required_components) else 503
    return jsonify(health_status), status_code


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    return jsonify({'status': 'ready'}), 200


@app.route('/api/v1/tts/synthesize', methods=['POST'])
def synthesize_speech():
    """
    Synthesize speech from text
    
    Request body:
    {
        "text": "Text to convert",
        "user_id": "user123",
        "voice_id": "Joanna" (optional),
        "format": "mp3" (optional)
    }
    """
    try:
        # Validate request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        text = data.get('text')
        user_id = data.get('user_id')
        voice_id = data.get('voice_id', 'Joanna')
        output_format = data.get('format', 'mp3').lower()
        language_code = data.get('language_code')
        
        # Validate required fields
        if not text:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        # Validate text length
        if len(text) > 3000:
            return jsonify({'error': 'Text too long (max 3000 characters)'}), 400
        
        # Validate format
        if output_format not in AUDIO_FORMATS:
            return jsonify({
                'error': f'Unsupported format. Supported: {list(AUDIO_FORMATS.keys())}'
            }), 400
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Publish request event to Kafka
        request_event = {
            'task_id': task_id,
            'user_id': user_id,
            'text_length': len(text),
            'voice_id': voice_id,
            'format': output_format,
            'status': 'processing',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_REQUEST, request_event)
        
        # Convert text to speech
        audio_stream, content_type = convert_text_to_speech(text, voice_id, output_format, language_code)
        
        if not audio_stream:
            # Publish failure event
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': 'Speech synthesis failed',
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': 'Speech synthesis failed'}), 500
        
        # Ensure S3 bucket exists
        ensure_s3_bucket()
        
        # Upload to S3
        file_key = f"audio/{user_id}/{task_id}.{output_format}"
        s3_url = upload_audio_to_s3(audio_stream, file_key, content_type)
        
        if not s3_url:
            # Publish failure event
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': 'S3 upload failed',
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': 'Failed to upload audio'}), 500
        
        # Publish completion event to Kafka
        completion_event = {
            'task_id': task_id,
            'user_id': user_id,
            'audio_url': s3_url,
            'voice_id': voice_id,
            'format': output_format,
            'text_length': len(text),
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_COMPLETED, completion_event)
        
        # Store metadata in Redis
        store_audio_metadata(task_id, user_id, file_key, voice_id, output_format, len(text))
        
        # Return response
        return jsonify({
            'task_id': task_id,
            'audio_url': s3_url,
            'status': 'completed',
            'voice_id': voice_id,
            'format': output_format
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in synthesize_speech: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/tts/voices', methods=['GET'])
def list_voices():
    """List available gTTS voices (language mappings)"""
    try:
        # Return available voice/language mappings for gTTS
        voice_list = [
            {
                'id': 'Joanna',
                'name': 'Joanna',
                'language': 'en',
                'gender': 'Female',
                'description': 'English (US)'
            },
            {
                'id': 'Matthew',
                'name': 'Matthew',
                'language': 'en',
                'gender': 'Male',
                'description': 'English (US)'
            },
            {
                'id': 'Amy',
                'name': 'Amy',
                'language': 'en-uk',
                'gender': 'Female',
                'description': 'English (UK)'
            },
            {
                'id': 'Brian',
                'name': 'Brian',
                'language': 'en-uk',
                'gender': 'Male',
                'description': 'English (UK)'
            },
            {
                'id': 'Emma',
                'name': 'Emma',
                'language': 'en-uk',
                'gender': 'Female',
                'description': 'English (UK)'
            },
            {
                'id': 'Ivy',
                'name': 'Ivy',
                'language': 'en',
                'gender': 'Female',
                'description': 'English (US)'
            }
        ]
        
        return jsonify({
            'voices': voice_list,
            'engine': 'gTTS (Google Text-to-Speech)',
            'note': 'Voice IDs map to language codes for gTTS'
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return jsonify({'error': 'Failed to list voices'}), 500


@app.route('/api/tts/audio/<task_id>', methods=['GET'])
def get_audio(task_id):
    """
    Retrieve generated audio file with S3 fallback
    """
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        # Try to get metadata from cache first
        metadata = get_audio_metadata(task_id)
        
        if metadata:
            # Happy path: metadata exists in Redis
            if metadata.get('user_id') != user_id:
                return jsonify({'error': 'Unauthorized access'}), 403
            
            file_key = metadata.get('file_key')
            audio_format = metadata.get('format', 'mp3')
            
        else:
            # Fallback: Try to find file in S3 directly
            logger.warning(f"Metadata not found for {task_id}, attempting S3 fallback")
            
            # Try all possible formats
            file_key = None
            audio_format = None
            
            for fmt in AUDIO_FORMATS.keys():
                potential_key = f"audio/{user_id}/{task_id}.{fmt}"
                
                # Check if file exists in S3
                try:
                    s3_client.head_object(Bucket=S3_BUCKET, Key=potential_key)
                    file_key = potential_key
                    audio_format = fmt
                    logger.info(f"Found audio in S3 via fallback: {file_key}")
                    break
                except ClientError:
                    continue
            
            if not file_key:
                return jsonify({'error': 'Audio not found or expired'}), 404
        
        # Retrieve audio from S3
        audio_data, content_type = get_audio_from_s3(file_key)
        
        if not audio_data:
            return jsonify({'error': 'Audio file not found in storage'}), 404
        
        # Return audio file
        return send_file(
            BytesIO(audio_data),
            mimetype=content_type,
            as_attachment=True,
            download_name=f"{task_id}.{audio_format}"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving audio: {e}")
        return jsonify({'error': 'Failed to retrieve audio'}), 500


@app.route('/api/tts/audio/<task_id>', methods=['DELETE'])
def delete_audio(task_id):
    """
    Delete generated audio file with S3 fallback
    
    Path parameters:
        task_id: The task ID returned from synthesize endpoint
    
    Request body:
    {
        "user_id": "user123"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        # Try to get metadata from cache first
        metadata = get_audio_metadata(task_id)
        
        if metadata:
            # Happy path: metadata exists in Redis
            if metadata.get('user_id') != user_id:
                return jsonify({'error': 'Unauthorized access'}), 403
            
            file_key = metadata.get('file_key')
            
        else:
            # Fallback: Try to find file in S3 directly
            logger.warning(f"Metadata not found for {task_id}, attempting S3 fallback for deletion")
            
            # Try all possible formats
            file_key = None
            
            for fmt in AUDIO_FORMATS.keys():
                potential_key = f"audio/{user_id}/{task_id}.{fmt}"
                
                # Check if file exists in S3
                try:
                    s3_client.head_object(Bucket=S3_BUCKET, Key=potential_key)
                    file_key = potential_key
                    logger.info(f"Found audio in S3 via fallback for deletion: {file_key}")
                    break
                except ClientError:
                    continue
            
            if not file_key:
                # Truly not found anywhere
                return jsonify({'error': 'Audio not found or already deleted'}), 404
        
        # Delete from S3
        s3_deleted = delete_audio_from_s3(file_key)
        
        # Delete metadata from cache (if it exists)
        cache_deleted = delete_audio_metadata(task_id, user_id)
        
        if s3_deleted or cache_deleted:
            deletion_event = {
                'task_id': task_id,
                'user_id': user_id,
                'file_key': file_key,
                'action': 'deleted',
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka('audio.generation.deleted', deletion_event)
            logger.info(f"Deleted audio: {task_id} for user: {user_id}")
            return jsonify({
                'message': 'Audio deleted successfully',
                'task_id': task_id
            }), 200
        else:
            return jsonify({'error': 'Failed to delete audio'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting audio: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


def consume_kafka_events():
    """
    Kafka consumer thread to listen for audio generation requests
    This enables asynchronous processing of TTS requests
    """
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC_REQUEST,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='tts-service-group',
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        
        logger.info(f"Kafka consumer started, listening to {KAFKA_TOPIC_REQUEST}")
        
        for message in consumer:
            if shutdown_flag.is_set():
                break
            
            try:
                event = message.value
                logger.info(f"Received Kafka event: {event.get('task_id')}")
                
                # Process async TTS requests here if needed
                # For now, we handle requests synchronously via REST API
                # This consumer is ready for future async processing
                
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")
        
        consumer.close()
        logger.info("Kafka consumer stopped")
        
    except Exception as e:
        logger.error(f"Kafka consumer error: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag.set()
    
    # Close Kafka producer
    if kafka_producer:
        try:
            kafka_producer.flush()
            kafka_producer.close()
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")
    
    # Close Redis connection
    if redis_client:
        try:
            redis_client.close()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    # Start Kafka consumer in background thread
    consumer_thread = threading.Thread(target=consume_kafka_events, daemon=True)
    consumer_thread.start()
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
