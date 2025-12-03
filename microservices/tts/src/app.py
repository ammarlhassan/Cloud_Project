"""
Text-to-Speech (TTS) Microservice
Converts text to audio using AWS Polly and publishes results to Kafka
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
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
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET = os.environ.get('S3_BUCKET_TTS', 'learning-platform-tts')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'audio.generation.requested'
KAFKA_TOPIC_COMPLETED = 'audio.generation.completed'

# Initialize AWS clients
try:
    polly_client = boto3.client('polly', region_name=AWS_REGION)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    logger.info("AWS clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS clients: {e}")
    polly_client = None
    s3_client = None

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


def convert_text_to_speech(text, voice_id='Joanna', output_format='mp3'):
    """
    Convert text to speech using AWS Polly
    
    Args:
        text: Text to convert
        voice_id: Polly voice ID (default: Joanna)
        output_format: Audio format (mp3, ogg_vorbis, pcm)
    
    Returns:
        tuple: (audio_stream, content_type) or (None, None) on error
    """
    if not polly_client:
        logger.error("Polly client not initialized")
        return None, None
    
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            VoiceId=voice_id,
            Engine='neural'  # Use neural engine for better quality
        )
        
        audio_stream = response.get('AudioStream')
        content_type = response.get('ContentType')
        
        logger.info(f"Successfully generated speech for text length: {len(text)}")
        return audio_stream, content_type
        
    except ClientError as e:
        logger.error(f"Polly synthesis error: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error in text-to-speech conversion: {e}")
        return None, None


def upload_audio_to_s3(audio_stream, file_key):
    """
    Upload audio to S3
    
    Args:
        audio_stream: Audio data stream
        file_key: S3 object key
    
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
            ContentType='audio/mpeg'
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
    health_status = {
        'service': 'tts',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'polly': polly_client is not None,
            's3': s3_client is not None,
            'kafka': kafka_producer is not None
        }
    }
    
    status_code = 200 if all(health_status['components'].values()) else 503
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
        output_format = data.get('format', 'mp3')
        
        # Validate required fields
        if not text:
            return jsonify({'error': 'Missing required field: text'}), 400
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        # Validate text length
        if len(text) > 3000:
            return jsonify({'error': 'Text too long (max 3000 characters)'}), 400
        
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
        audio_stream, content_type = convert_text_to_speech(text, voice_id, output_format)
        
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
        s3_url = upload_audio_to_s3(audio_stream, file_key)
        
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
    """List available Polly voices"""
    try:
        if not polly_client:
            return jsonify({'error': 'Polly client not available'}), 503
        
        response = polly_client.describe_voices()
        voices = response.get('Voices', [])
        
        # Filter and format voice information
        voice_list = [
            {
                'id': voice['Id'],
                'name': voice['Name'],
                'language': voice['LanguageCode'],
                'gender': voice['Gender']
            }
            for voice in voices
        ]
        
        return jsonify({'voices': voice_list}), 200
        
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return jsonify({'error': 'Failed to list voices'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
