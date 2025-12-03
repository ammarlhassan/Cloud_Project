"""
Speech-to-Text (STT) Microservice
Transcribes audio files using AWS Transcribe and publishes results to Kafka
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
S3_BUCKET = os.environ.get('S3_BUCKET_STT', 'learning-platform-stt')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'audio.transcription.requested'
KAFKA_TOPIC_COMPLETED = 'audio.transcription.completed'

# Initialize AWS clients
try:
    transcribe_client = boto3.client('transcribe', region_name=AWS_REGION)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    logger.info("AWS clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize AWS clients: {e}")
    transcribe_client = None
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


def upload_audio_to_s3(audio_data, file_key):
    """
    Upload audio file to S3
    
    Args:
        audio_data: Audio file binary data
        file_key: S3 object key
    
    Returns:
        str: S3 URL or None on error
    """
    if not s3_client:
        logger.error("S3 client not initialized")
        return None
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=file_key,
            Body=audio_data,
            ContentType='audio/mpeg'
        )
        
        s3_url = f"s3://{S3_BUCKET}/{file_key}"
        logger.info(f"Audio uploaded to S3: {s3_url}")
        
        return s3_url
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        return None


def start_transcription_job(job_name, s3_uri, language_code='en-US'):
    """
    Start AWS Transcribe job
    
    Args:
        job_name: Unique job name
        s3_uri: S3 URI of audio file
        language_code: Language code (default: en-US)
    
    Returns:
        dict: Job details or None on error
    """
    if not transcribe_client:
        logger.error("Transcribe client not initialized")
        return None
    
    try:
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat='mp3',
            LanguageCode=language_code,
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 5
            }
        )
        
        logger.info(f"Transcription job started: {job_name}")
        return response.get('TranscriptionJob')
        
    except ClientError as e:
        logger.error(f"Transcribe job start error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error starting transcription: {e}")
        return None


def get_transcription_result(job_name):
    """
    Get transcription job result
    
    Args:
        job_name: Job name
    
    Returns:
        dict: Transcription result or None
    """
    if not transcribe_client:
        return None
    
    try:
        # Poll for job completion
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            job = response.get('TranscriptionJob', {})
            status = job.get('TranscriptionJobStatus')
            
            if status == 'COMPLETED':
                transcript_uri = job.get('Transcript', {}).get('TranscriptFileUri')
                
                # Download transcript file
                import urllib.request
                with urllib.request.urlopen(transcript_uri) as response:
                    transcript_data = json.loads(response.read().decode('utf-8'))
                
                return {
                    'status': 'completed',
                    'transcript': transcript_data.get('results', {}).get('transcripts', [{}])[0].get('transcript', ''),
                    'full_result': transcript_data
                }
            
            elif status == 'FAILED':
                return {
                    'status': 'failed',
                    'error': job.get('FailureReason', 'Unknown error')
                }
            
            # Wait before polling again
            time.sleep(5)
            attempt += 1
        
        return {
            'status': 'timeout',
            'error': 'Transcription job timed out'
        }
        
    except Exception as e:
        logger.error(f"Error getting transcription result: {e}")
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
        'service': 'stt',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'transcribe': transcribe_client is not None,
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


@app.route('/api/v1/stt/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio file
    
    Request: multipart/form-data with 'audio' file
    Form data:
    - audio: Audio file (required)
    - user_id: User ID (required)
    - language: Language code (optional, default: en-US)
    """
    try:
        # Validate request
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id')
        language_code = request.form.get('language', 'en-US')
        
        if not user_id:
            return jsonify({'error': 'Missing required field: user_id'}), 400
        
        if audio_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Validate file size (max 100MB)
        audio_data = audio_file.read()
        if len(audio_data) > 100 * 1024 * 1024:
            return jsonify({'error': 'File too large (max 100MB)'}), 400
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Publish request event to Kafka
        request_event = {
            'task_id': task_id,
            'user_id': user_id,
            'file_size': len(audio_data),
            'language': language_code,
            'status': 'processing',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_REQUEST, request_event)
        
        # Ensure S3 bucket exists
        ensure_s3_bucket()
        
        # Upload audio to S3
        file_key = f"audio/{user_id}/{task_id}.mp3"
        s3_url = upload_audio_to_s3(audio_data, file_key)
        
        if not s3_url:
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': 'S3 upload failed',
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': 'Failed to upload audio'}), 500
        
        # Start transcription job
        job_name = f"transcribe-{task_id}"
        job = start_transcription_job(job_name, s3_url, language_code)
        
        if not job:
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': 'Failed to start transcription',
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': 'Failed to start transcription'}), 500
        
        # Get transcription result (blocking)
        result = get_transcription_result(job_name)
        
        if not result or result.get('status') != 'completed':
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': result.get('error', 'Transcription failed'),
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': result.get('error', 'Transcription failed')}), 500
        
        # Publish completion event to Kafka
        completion_event = {
            'task_id': task_id,
            'user_id': user_id,
            'audio_url': s3_url,
            'transcript': result['transcript'],
            'language': language_code,
            'status': 'completed',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        publish_to_kafka(KAFKA_TOPIC_COMPLETED, completion_event)
        
        # Return response
        return jsonify({
            'task_id': task_id,
            'transcript': result['transcript'],
            'audio_url': s3_url,
            'status': 'completed',
            'language': language_code
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in transcribe_audio: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/stt/status/<task_id>', methods=['GET'])
def get_transcription_status(task_id):
    """Get transcription job status"""
    try:
        if not transcribe_client:
            return jsonify({'error': 'Transcribe client not available'}), 503
        
        job_name = f"transcribe-{task_id}"
        response = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )
        
        job = response.get('TranscriptionJob', {})
        status = job.get('TranscriptionJobStatus')
        
        return jsonify({
            'task_id': task_id,
            'status': status.lower(),
            'creation_time': job.get('CreationTime').isoformat() if job.get('CreationTime') else None
        }), 200
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'BadRequestException':
            return jsonify({'error': 'Job not found'}), 404
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': 'Failed to get status'}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
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
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
