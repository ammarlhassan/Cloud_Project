"""
Speech-to-Text (STT) Microservice
Transcribes audio files using AWS Transcribe and publishes results to Kafka
"""
import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import time
import threading

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
S3_BUCKET = os.environ.get('S3_BUCKET_STT', 'stt-service-storage-dev-334413050048')
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
KAFKA_TOPIC_REQUEST = 'audio.transcription.requested'
KAFKA_TOPIC_COMPLETED = 'audio.transcription.completed'

# Audio retention configuration
AUDIO_RETENTION_DAYS = int(os.environ.get('AUDIO_RETENTION_DAYS', '30'))

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


# S3 Storage Functions (No Database)
def save_transcription_to_s3(transcription_id, transcription_data):
    """Save transcription metadata to S3"""
    try:
        s3_key = f"transcriptions/{transcription_id}/metadata.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(transcription_data, default=str),
            ContentType='application/json'
        )
        logger.info(f"Transcription saved to S3: {s3_key}")
        return True
    except Exception as e:
        logger.error(f"Error saving transcription to S3: {e}")
        return False


def get_transcription_from_s3(transcription_id):
    """Get transcription metadata from S3"""
    try:
        s3_key = f"transcriptions/{transcription_id}/metadata.json"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(response['Body'].read())
        return data
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"Transcription not found: {transcription_id}")
        else:
            logger.error(f"Error getting transcription from S3: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading transcription from S3: {e}")
        return None


def list_user_transcriptions_from_s3(user_id, limit=50):
    """List user's transcriptions from S3"""
    try:
        prefix = f"transcriptions/"
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix,
            MaxKeys=1000
        )
        
        transcriptions = []
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('metadata.json'):
                    try:
                        data = get_transcription_from_s3(
                            obj['Key'].split('/')[1]
                        )
                        if data and data.get('user_id') == user_id:
                            transcriptions.append(data)
                    except:
                        continue
        
        # Sort by created_at and limit
        transcriptions.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        return transcriptions[:limit]
        
    except Exception as e:
        logger.error(f"Error listing transcriptions from S3: {e}")
        return []


def save_transcription(transcription_data):
    """Save transcription to S3"""
    transcription_data['created_at'] = datetime.utcnow().isoformat()
    transcription_data['updated_at'] = datetime.utcnow().isoformat()
    return save_transcription_to_s3(
        transcription_data['transcription_id'],
        transcription_data
    )


def update_transcription(transcription_id, update_data):
    """Update transcription record in S3"""
    try:
        # Get existing data
        existing_data = get_transcription_from_s3(transcription_id)
        if not existing_data:
            logger.error(f"Transcription not found for update: {transcription_id}")
            return False
        
        # Update fields
        existing_data.update(update_data)
        existing_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save back to S3
        return save_transcription_to_s3(transcription_id, existing_data)
        
    except Exception as e:
        logger.error(f"Error updating transcription: {e}")
        return False


def get_transcription_by_id(transcription_id):
    """Get transcription by ID from S3"""
    return get_transcription_from_s3(transcription_id)


def get_user_transcriptions(user_id, limit=50, offset=0):
    """Get user's transcription history from S3"""
    transcriptions = list_user_transcriptions_from_s3(user_id, limit + offset)
    return transcriptions[offset:offset + limit]


def delete_old_audio_files():
    """Delete audio files older than retention period"""
    if not s3_client:
        return
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=AUDIO_RETENTION_DAYS)
        
        # List objects in audio folder
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='audio/'
        )
        
        if 'Contents' not in response:
            return
        
        deleted_count = 0
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                s3_client.delete_object(
                    Bucket=S3_BUCKET,
                    Key=obj['Key']
                )
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old audio files")
        
    except Exception as e:
        logger.error(f"Error deleting old audio files: {e}")


def kafka_consumer_worker():
    """
    Kafka consumer worker to process audio.transcription.requested events
    Runs in a separate thread
    """
    logger.info("Starting Kafka consumer worker...")
    
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC_REQUEST,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='stt-service-group',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            logger.info(f"Kafka consumer connected, listening to {KAFKA_TOPIC_REQUEST}")
            
            for message in consumer:
                try:
                    event = message.value
                    logger.info(f"Received transcription request: {event}")
                    
                    task_id = event.get('task_id')
                    user_id = event.get('user_id')
                    audio_url = event.get('audio_url')
                    language_code = event.get('language', 'en-US')
                    
                    if not all([task_id, user_id, audio_url]):
                        logger.error(f"Invalid event data: {event}")
                        continue
                    
                    # Save initial transcription record
                    transcription_record = {
                        'transcription_id': task_id,
                        'user_id': user_id,
                        'audio_url': audio_url,
                        'language_code': language_code,
                        'status': 'processing',
                        'file_size': event.get('file_size'),
                        'job_name': f"transcribe-{task_id}"
                    }
                    save_transcription(transcription_record)
                    
                    # Start transcription job
                    job_name = f"transcribe-{task_id}"
                    job = start_transcription_job(job_name, audio_url, language_code)
                    
                    if not job:
                        update_transcription(task_id, {
                            'status': 'failed',
                            'error_message': 'Failed to start transcription job'
                        })
                        
                        failure_event = {
                            'task_id': task_id,
                            'user_id': user_id,
                            'status': 'failed',
                            'error': 'Failed to start transcription',
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
                        continue
                    
                    # Get transcription result (this polls until complete)
                    result = get_transcription_result(job_name)
                    
                    if result and result.get('status') == 'completed':
                        # Update database with results
                        update_transcription(task_id, {
                            'transcript': result['transcript'],
                            'status': 'completed',
                            'completed_at': datetime.utcnow()
                        })
                        
                        # Publish completion event
                        completion_event = {
                            'task_id': task_id,
                            'user_id': user_id,
                            'audio_url': audio_url,
                            'transcript': result['transcript'],
                            'language': language_code,
                            'status': 'completed',
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        publish_to_kafka(KAFKA_TOPIC_COMPLETED, completion_event)
                        logger.info(f"Transcription completed for task: {task_id}")
                    else:
                        error_msg = result.get('error', 'Unknown error') if result else 'No result'
                        
                        update_transcription(task_id, {
                            'status': 'failed',
                            'error_message': error_msg
                        })
                        
                        failure_event = {
                            'task_id': task_id,
                            'user_id': user_id,
                            'status': 'failed',
                            'error': error_msg,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
                        logger.error(f"Transcription failed for task {task_id}: {error_msg}")
                
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    continue
            
        except KafkaError as e:
            logger.warning(f"Kafka consumer error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Kafka consumer failed after all retries")
                return
        except Exception as e:
            logger.error(f"Unexpected error in Kafka consumer: {e}")
            time.sleep(retry_delay)


def audio_cleanup_worker():
    """
    Background worker to periodically clean up old audio files
    Runs every 24 hours
    """
    logger.info("Starting audio cleanup worker...")
    
    while True:
        try:
            logger.info("Running audio file cleanup...")
            delete_old_audio_files()
            
            # Sleep for 24 hours
            time.sleep(24 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Error in audio cleanup worker: {e}")
            time.sleep(60 * 60)  # Retry after 1 hour on error


# Start background workers
consumer_thread = threading.Thread(target=kafka_consumer_worker, daemon=True)
consumer_thread.start()

cleanup_thread = threading.Thread(target=audio_cleanup_worker, daemon=True)
cleanup_thread.start()


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
        max_attempts = 30
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


@app.route('/api/stt/transcribe', methods=['POST'])
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
        
        # Save initial transcription record to database
        transcription_record = {
            'transcription_id': task_id,
            'user_id': user_id,
            'audio_url': s3_url,
            'language_code': language_code,
            'status': 'processing',
            'file_size': len(audio_data),
            'job_name': f"transcribe-{task_id}"
        }
        save_transcription(transcription_record)
        
        # Start transcription job
        job_name = f"transcribe-{task_id}"
        job = start_transcription_job(job_name, s3_url, language_code)
        
        if not job:
            update_transcription(task_id, {
                'status': 'failed',
                'error_message': 'Failed to start transcription'
            })
            
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
            error_msg = result.get('error', 'Transcription failed') if result else 'Unknown error'
            
            update_transcription(task_id, {
                'status': 'failed',
                'error_message': error_msg
            })
            
            failure_event = {
                'task_id': task_id,
                'user_id': user_id,
                'status': 'failed',
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            }
            publish_to_kafka(KAFKA_TOPIC_COMPLETED, failure_event)
            
            return jsonify({'error': error_msg}), 500
        
        # Update transcription record with results
        update_transcription(task_id, {
            'transcript': result['transcript'],
            'status': 'completed',
            'completed_at': datetime.utcnow()
        })
        
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



@app.route('/api/stt/transcription/<transcription_id>', methods=['GET'])
def get_transcription(transcription_id):
    """
    Get transcription result by ID
    
    Query params:
    - user_id: User ID (required for authorization)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        # Fetch transcription from database
        transcription = get_transcription_by_id(transcription_id)
        
        if not transcription:
            return jsonify({'error': 'Transcription not found'}), 404
        
        # Verify user owns this transcription
        if transcription['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Format response
        response_data = {
            'transcription_id': transcription['transcription_id'],
            'transcript': transcription['transcript'],
            'audio_url': transcription['audio_url'],
            'language_code': transcription['language_code'],
            'status': transcription['status'],
            'file_size': transcription['file_size'],
            'created_at': transcription['created_at'].isoformat() if transcription['created_at'] else None,
            'completed_at': transcription['completed_at'].isoformat() if transcription.get('completed_at') else None,
            'error_message': transcription.get('error_message')
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching transcription: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/stt/transcriptions', methods=['GET'])
def list_user_transcriptions():
    """
    List user's transcription history
    
    Query params:
    - user_id: User ID (required)
    - limit: Max results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing required parameter: user_id'}), 400
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Validate limits
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        
        # Fetch transcriptions from database
        transcriptions = get_user_transcriptions(user_id, limit, offset)
        
        # Format response
        response_data = {
            'user_id': user_id,
            'count': len(transcriptions),
            'limit': limit,
            'offset': offset,
            'transcriptions': [
                {
                    'transcription_id': t['transcription_id'],
                    'transcript': t['transcript'][:200] + '...' if t['transcript'] and len(t['transcript']) > 200 else t['transcript'],
                    'language_code': t['language_code'],
                    'status': t['status'],
                    'file_size': t['file_size'],
                    'created_at': t['created_at'].isoformat() if t['created_at'] else None,
                    'completed_at': t['completed_at'].isoformat() if t.get('completed_at') else None
                }
                for t in transcriptions
            ]
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error listing transcriptions: {e}")
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
