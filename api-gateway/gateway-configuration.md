# API Gateway Configuration

## Overview

This document describes the API Gateway configuration for the Learner Lab Cloud Platform.

## Service Configuration

### Port Mapping

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| API Gateway | 5000 | 5000 | Main entry point |
| TTS Service | 5001 | - | Text-to-Speech |
| STT Service | 5002 | - | Speech-to-Text |
| Chat Service | 5003 | - | Chat sessions |
| Document Service | 5004 | - | Document processing |
| Quiz Service | 5005 | - | Quiz management |

### Service URLs

```yaml
# Internal service discovery (Docker Compose network)
TTS_SERVICE_URL: http://tts-service:5001
STT_SERVICE_URL: http://stt-service:5002
CHAT_SERVICE_URL: http://chat-service:5003
DOCUMENT_SERVICE_URL: http://document-service:5004
QUIZ_SERVICE_URL: http://quiz-service:5005
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET` | Secret key for JWT signing | `openssl rand -base64 32` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | From Learner Lab |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | From Learner Lab |
| `AWS_SESSION_TOKEN` | AWS session token | From Learner Lab |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Gateway listening port |
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JWT_EXPIRATION_HOURS` | `24` | Token validity |
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window (seconds) |
| `REQUEST_TIMEOUT` | `30` | Upstream request timeout |

## Route Configuration

### Route Mapping

```python
ROUTES = {
    '/api/tts': {
        'service': 'TTS_SERVICE_URL',
        'methods': ['GET', 'POST'],
        'rate_limit': 30,
        'auth_required': True
    },
    '/api/stt': {
        'service': 'STT_SERVICE_URL',
        'methods': ['GET', 'POST'],
        'rate_limit': 20,
        'auth_required': True
    },
    '/api/chat': {
        'service': 'CHAT_SERVICE_URL',
        'methods': ['GET', 'POST', 'PUT', 'DELETE'],
        'rate_limit': 100,
        'auth_required': True
    },
    '/api/documents': {
        'service': 'DOCUMENT_SERVICE_URL',
        'methods': ['GET', 'POST', 'DELETE'],
        'rate_limit': 50,
        'auth_required': True
    },
    '/api/quizzes': {
        'service': 'QUIZ_SERVICE_URL',
        'methods': ['GET', 'POST', 'PUT', 'DELETE'],
        'rate_limit': 100,
        'auth_required': True
    }
}
```

### Public Endpoints (No Auth Required)

```python
PUBLIC_ENDPOINTS = [
    '/health',
    '/ready',
    '/auth/login',
    '/docs',
    '/openapi.yaml'
]
```

## CORS Configuration

```python
CORS_CONFIG = {
    'origins': ['*'],  # Configure for production
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization', 'X-Request-ID'],
    'expose_headers': [
        'X-RateLimit-Limit',
        'X-RateLimit-Remaining',
        'X-RateLimit-Reset'
    ],
    'max_age': 600
}
```

## Request/Response Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     API Gateway Pipeline                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Request ──▶ CORS ──▶ Rate Limit ──▶ Auth ──▶ Route         │
│                                                │              │
│                                                ▼              │
│                                          Microservice        │
│                                                │              │
│                                                ▼              │
│   Response ◀── Headers ◀── Transform ◀── Response            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Health Check Configuration

```python
HEALTH_CHECK = {
    'path': '/health',
    'interval': '30s',
    'timeout': '10s',
    'retries': 3,
    'start_period': '40s'
}
```

## Logging Configuration

```python
LOGGING = {
    'version': 1,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}
```

## Docker Compose Configuration

```yaml
api-gateway:
  build:
    context: .
    dockerfile: docker/dockerfiles/Dockerfile.gateway
  ports:
    - "5000:5000"
  environment:
    JWT_SECRET: ${JWT_SECRET:?required}
    TTS_SERVICE_URL: http://tts-service:5001
    STT_SERVICE_URL: http://stt-service:5002
    CHAT_SERVICE_URL: http://chat-service:5003
    DOCUMENT_SERVICE_URL: http://document-service:5004
    QUIZ_SERVICE_URL: http://quiz-service:5005
    RATE_LIMIT_REQUESTS: 100
    RATE_LIMIT_WINDOW: 60
  depends_on:
    - tts-service
    - stt-service
    - chat-service
    - document-service
    - quiz-service
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Kubernetes Configuration

See `kubernetes/deployments/api-gateway.yaml` for Kubernetes-specific configuration including:
- Readiness and liveness probes
- Resource limits
- Horizontal Pod Autoscaler
- Service and Ingress configuration
