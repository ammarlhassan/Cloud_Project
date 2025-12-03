"""
API Gateway Service
Provides unified API endpoint with authentication, rate limiting, and routing
"""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Tuple
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import jwt
from werkzeug.exceptions import HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

# Service endpoints
SERVICES = {
    'tts': os.getenv('TTS_SERVICE_URL', 'http://tts-service:5001'),
    'stt': os.getenv('STT_SERVICE_URL', 'http://stt-service:5002'),
    'chat': os.getenv('CHAT_SERVICE_URL', 'http://chat-service:5003'),
    'document': os.getenv('DOCUMENT_SERVICE_URL', 'http://document-service:5004'),
    'quiz': os.getenv('QUIZ_SERVICE_URL', 'http://quiz-service:5005')
}

# Rate limiting storage (in-memory, use Redis in production)
rate_limit_storage: Dict[str, list] = {}
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds

# Request timeout
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))


class AuthenticationError(Exception):
    """Authentication error"""
    pass


class RateLimitError(Exception):
    """Rate limit exceeded error"""
    pass


def generate_token(user_id: str, email: str) -> str:
    """
    Generate JWT token
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Dict:
    """
    Verify JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError('Token has expired')
    except jwt.InvalidTokenError:
        raise AuthenticationError('Invalid token')


def get_client_id(request_obj) -> str:
    """
    Get client identifier for rate limiting
    
    Args:
        request_obj: Flask request object
        
    Returns:
        Client identifier string
    """
    # Try to get user_id from token, fallback to IP
    auth_header = request_obj.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            payload = verify_token(token)
            return f"user:{payload['user_id']}"
        except Exception:
            pass
    
    return f"ip:{request_obj.remote_addr}"


def check_rate_limit(client_id: str) -> Tuple[bool, Dict]:
    """
    Check if client has exceeded rate limit
    
    Args:
        client_id: Client identifier
        
    Returns:
        Tuple of (is_allowed, headers_dict)
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old requests
    if client_id in rate_limit_storage:
        rate_limit_storage[client_id] = [
            req_time for req_time in rate_limit_storage[client_id]
            if req_time > window_start
        ]
    else:
        rate_limit_storage[client_id] = []
    
    # Check limit
    current_requests = len(rate_limit_storage[client_id])
    remaining = max(0, RATE_LIMIT_REQUESTS - current_requests)
    reset_time = int(now + RATE_LIMIT_WINDOW)
    
    headers = {
        'X-RateLimit-Limit': str(RATE_LIMIT_REQUESTS),
        'X-RateLimit-Remaining': str(remaining),
        'X-RateLimit-Reset': str(reset_time)
    }
    
    if current_requests >= RATE_LIMIT_REQUESTS:
        return False, headers
    
    # Add current request
    rate_limit_storage[client_id].append(now)
    return True, headers


def require_auth(f):
    """
    Decorator to require authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'No authorization header',
                'message': 'Authorization header is required'
            }), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Invalid authorization header',
                'message': 'Authorization header must start with Bearer'
            }), 401
        
        try:
            token = auth_header.split(' ')[1]
            payload = verify_token(token)
            request.user = payload
        except AuthenticationError as e:
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 401
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Invalid token'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit(f):
    """
    Decorator to enforce rate limiting
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_id = get_client_id(request)
        allowed, headers = check_rate_limit(client_id)
        
        if not allowed:
            response = jsonify({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds'
            })
            response.status_code = 429
            for key, value in headers.items():
                response.headers[key] = value
            return response
        
        # Call the function
        result = f(*args, **kwargs)
        
        # Add rate limit headers to response
        if isinstance(result, tuple):
            response, status_code = result[0], result[1]
        else:
            response, status_code = result, 200
        
        if isinstance(response, Response):
            for key, value in headers.items():
                response.headers[key] = value
            return response, status_code
        
        return result
    
    return decorated_function


def proxy_request(service: str, path: str, method: str = None) -> Response:
    """
    Proxy request to microservice
    
    Args:
        service: Service name
        path: Request path
        method: HTTP method (default: request.method)
        
    Returns:
        Flask Response object
    """
    if service not in SERVICES:
        return jsonify({
            'error': 'Service not found',
            'message': f'Service {service} is not available'
        }), 404
    
    service_url = SERVICES[service]
    url = f"{service_url}{path}"
    method = method or request.method
    
    # Prepare headers (exclude hop-by-hop headers)
    headers = {
        key: value for key, value in request.headers
        if key.lower() not in ['host', 'connection', 'transfer-encoding']
    }
    
    # Add user info to headers
    if hasattr(request, 'user'):
        headers['X-User-Id'] = request.user.get('user_id', '')
        headers['X-User-Email'] = request.user.get('email', '')
    
    try:
        # Make request to microservice
        logger.info(f"Proxying {method} request to {url}")
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=request.args,
            json=request.get_json(silent=True) if request.is_json else None,
            data=request.data if not request.is_json else None,
            files=request.files if request.files else None,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False
        )
        
        # Create Flask response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [
            (name, value) for name, value in response.headers.items()
            if name.lower() not in excluded_headers
        ]
        
        flask_response = Response(
            response.content,
            status=response.status_code,
            headers=response_headers
        )
        
        return flask_response
        
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout to {service} service")
        return jsonify({
            'error': 'Service timeout',
            'message': f'Request to {service} service timed out'
        }), 504
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to {service} service")
        return jsonify({
            'error': 'Service unavailable',
            'message': f'{service} service is not available'
        }), 503
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}")
        return jsonify({
            'error': 'Proxy error',
            'message': 'An error occurred while processing your request'
        }), 500


@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    if isinstance(error, HTTPException):
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code
    
    logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


# Health check endpoints
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint"""
    # Check if services are reachable
    services_status = {}
    all_ready = True
    
    for service_name, service_url in SERVICES.items():
        try:
            response = requests.get(f"{service_url}/health", timeout=2)
            services_status[service_name] = {
                'status': 'ready' if response.status_code == 200 else 'unhealthy',
                'url': service_url
            }
        except Exception as e:
            services_status[service_name] = {
                'status': 'unreachable',
                'url': service_url,
                'error': str(e)
            }
            all_ready = False
    
    status_code = 200 if all_ready else 503
    return jsonify({
        'status': 'ready' if all_ready else 'not ready',
        'services': services_status
    }), status_code


# Authentication endpoints
@app.route('/api/v1/auth/login', methods=['POST'])
@rate_limit
def login():
    """
    Login endpoint (simplified - integrate with actual auth service)
    
    Request:
        {
            "email": "user@example.com",
            "password": "password"
        }
    
    Response:
        {
            "token": "jwt-token",
            "user": {
                "id": "user-id",
                "email": "user@example.com"
            }
        }
    """
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'error': 'Invalid request',
            'message': 'Email and password are required'
        }), 400
    
    # TODO: Integrate with actual authentication service
    # For now, generate token for any valid email/password
    user_id = f"user_{hash(data['email']) % 10000}"
    token = generate_token(user_id, data['email'])
    
    return jsonify({
        'token': token,
        'user': {
            'id': user_id,
            'email': data['email']
        }
    }), 200


@app.route('/api/v1/auth/refresh', methods=['POST'])
@require_auth
@rate_limit
def refresh_token():
    """
    Refresh JWT token
    
    Response:
        {
            "token": "new-jwt-token"
        }
    """
    user = request.user
    new_token = generate_token(user['user_id'], user['email'])
    
    return jsonify({
        'token': new_token
    }), 200


@app.route('/api/v1/auth/verify', methods=['GET'])
@require_auth
@rate_limit
def verify():
    """
    Verify JWT token
    
    Response:
        {
            "valid": true,
            "user": {
                "id": "user-id",
                "email": "user@example.com"
            }
        }
    """
    return jsonify({
        'valid': True,
        'user': {
            'id': request.user['user_id'],
            'email': request.user['email']
        }
    }), 200


# TTS Service routes
@app.route('/api/v1/tts/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
@rate_limit
def tts_proxy(path):
    """Proxy requests to TTS service"""
    return proxy_request('tts', f'/api/v1/tts/{path}')


# STT Service routes
@app.route('/api/v1/stt/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
@rate_limit
def stt_proxy(path):
    """Proxy requests to STT service"""
    return proxy_request('stt', f'/api/v1/stt/{path}')


# Chat Service routes
@app.route('/api/v1/chat/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
@rate_limit
def chat_proxy(path):
    """Proxy requests to Chat service"""
    return proxy_request('chat', f'/api/v1/chat/{path}')


# Document Service routes
@app.route('/api/v1/documents', methods=['GET', 'POST'])
@require_auth
@rate_limit
def documents_list():
    """Proxy requests to Document service"""
    return proxy_request('document', '/api/v1/documents')


@app.route('/api/v1/documents/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
@rate_limit
def documents_proxy(path):
    """Proxy requests to Document service"""
    return proxy_request('document', f'/api/v1/documents/{path}')


# Quiz Service routes
@app.route('/api/v1/quizzes', methods=['GET', 'POST'])
@require_auth
@rate_limit
def quizzes_list():
    """Proxy requests to Quiz service"""
    return proxy_request('quiz', '/api/v1/quizzes')


@app.route('/api/v1/quizzes/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_auth
@rate_limit
def quizzes_proxy(path):
    """Proxy requests to Quiz service"""
    return proxy_request('quiz', f'/api/v1/quizzes/{path}')


# API documentation endpoint
@app.route('/api/v1/docs', methods=['GET'])
def api_docs():
    """
    API documentation endpoint
    
    Response:
        {
            "version": "1.0",
            "services": {...}
        }
    """
    return jsonify({
        'version': '1.0',
        'services': {
            'auth': {
                'endpoints': [
                    {'path': '/api/v1/auth/login', 'method': 'POST', 'description': 'User login'},
                    {'path': '/api/v1/auth/refresh', 'method': 'POST', 'description': 'Refresh token'},
                    {'path': '/api/v1/auth/verify', 'method': 'GET', 'description': 'Verify token'}
                ]
            },
            'tts': {
                'base_path': '/api/v1/tts',
                'description': 'Text-to-Speech service',
                'endpoints': [
                    {'path': '/api/v1/tts/synthesize', 'method': 'POST', 'description': 'Convert text to speech'},
                    {'path': '/api/v1/tts/voices', 'method': 'GET', 'description': 'List available voices'}
                ]
            },
            'stt': {
                'base_path': '/api/v1/stt',
                'description': 'Speech-to-Text service',
                'endpoints': [
                    {'path': '/api/v1/stt/transcribe', 'method': 'POST', 'description': 'Transcribe audio file'},
                    {'path': '/api/v1/stt/status/<task_id>', 'method': 'GET', 'description': 'Get transcription status'}
                ]
            },
            'chat': {
                'base_path': '/api/v1/chat',
                'description': 'Chat service',
                'endpoints': [
                    {'path': '/api/v1/chat/sessions', 'method': 'POST', 'description': 'Create chat session'},
                    {'path': '/api/v1/chat/sessions/<id>/messages', 'method': 'POST', 'description': 'Send message'},
                    {'path': '/api/v1/chat/sessions/<id>/messages', 'method': 'GET', 'description': 'Get messages'}
                ]
            },
            'document': {
                'base_path': '/api/v1/documents',
                'description': 'Document processing service',
                'endpoints': [
                    {'path': '/api/v1/documents/upload', 'method': 'POST', 'description': 'Upload document'},
                    {'path': '/api/v1/documents/<id>/process', 'method': 'POST', 'description': 'Process document'},
                    {'path': '/api/v1/documents/<id>/notes', 'method': 'GET', 'description': 'Get document notes'}
                ]
            },
            'quiz': {
                'base_path': '/api/v1/quizzes',
                'description': 'Quiz service',
                'endpoints': [
                    {'path': '/api/v1/quizzes/generate', 'method': 'POST', 'description': 'Generate quiz'},
                    {'path': '/api/v1/quizzes/<id>', 'method': 'GET', 'description': 'Get quiz'},
                    {'path': '/api/v1/quizzes/<id>/submit', 'method': 'POST', 'description': 'Submit quiz'}
                ]
            }
        }
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting API Gateway on port {port}")
    logger.info(f"Connected services: {list(SERVICES.keys())}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
