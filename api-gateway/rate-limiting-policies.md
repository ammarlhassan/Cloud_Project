# Rate Limiting Policies

## Overview

The API Gateway implements rate limiting to protect backend services from abuse and ensure fair usage across all users.

## Configuration

Rate limits are configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_REQUESTS` | 100 | Maximum requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Time window in seconds |

## Implementation

### Algorithm: Token Bucket

The gateway uses a **token bucket** algorithm with Redis for distributed rate limiting:

```
┌─────────────────────────────────────────────────────────────┐
│                    Token Bucket Algorithm                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Bucket Capacity: 100 tokens (RATE_LIMIT_REQUESTS)        │
│   Refill Rate: 100 tokens per 60 seconds                   │
│                                                             │
│   ┌─────────────────────────────────────────────┐          │
│   │  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  │          │
│   │  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  │ Tokens   │
│   │  ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ●  │          │
│   └─────────────────────────────────────────────┘          │
│                         │                                   │
│                         ▼                                   │
│              Each request consumes 1 token                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Rate Limit Keys

Requests are limited by **IP address** by default:

```python
# Key format in Redis
rate_limit_key = f"rate_limit:{client_ip}"

# For authenticated users (optional enhancement)
rate_limit_key = f"rate_limit:user:{user_id}"
```

## Response Headers

Every response includes rate limit headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests allowed | `100` |
| `X-RateLimit-Remaining` | Requests remaining in window | `95` |
| `X-RateLimit-Reset` | Unix timestamp when window resets | `1701792000` |

## Rate Limit Exceeded Response

When rate limit is exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701792060
Retry-After: 45

{
    "error": "rate_limit_exceeded",
    "message": "Too many requests. Please retry after 45 seconds.",
    "retry_after": 45
}
```

## Per-Endpoint Limits

Different endpoints may have different limits:

| Endpoint Category | Requests/Min | Reason |
|-------------------|--------------|--------|
| `/health` | Unlimited | Health checks shouldn't be limited |
| `/auth/login` | 10 | Prevent brute force attacks |
| `/api/tts/*` | 30 | AWS Polly costs |
| `/api/stt/*` | 20 | AWS Transcribe costs |
| `/api/documents/*` | 50 | S3 + Textract costs |
| `/api/chat/*` | 100 | Standard limit |
| `/api/quizzes/*` | 100 | Standard limit |

## Code Implementation

```python
from functools import wraps
from flask import request, jsonify
import time
import redis

redis_client = redis.Redis(host='redis', port=6379, db=0)

def rate_limit(max_requests=100, window_seconds=60):
    """Rate limiting decorator using Redis"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            key = f"rate_limit:{client_ip}"
            
            # Get current count
            current = redis_client.get(key)
            
            if current is None:
                # First request - set counter with expiry
                redis_client.setex(key, window_seconds, 1)
                remaining = max_requests - 1
            elif int(current) >= max_requests:
                # Rate limit exceeded
                ttl = redis_client.ttl(key)
                response = jsonify({
                    'error': 'rate_limit_exceeded',
                    'message': f'Too many requests. Please retry after {ttl} seconds.',
                    'retry_after': ttl
                })
                response.status_code = 429
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(time.time()) + ttl)
                response.headers['Retry-After'] = str(ttl)
                return response
            else:
                # Increment counter
                redis_client.incr(key)
                remaining = max_requests - int(current) - 1
            
            # Execute the function
            response = f(*args, **kwargs)
            
            # Add rate limit headers
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = str(max(0, remaining))
                ttl = redis_client.ttl(key) or window_seconds
                response.headers['X-RateLimit-Reset'] = str(int(time.time()) + ttl)
            
            return response
        return decorated_function
    return decorator

# Usage
@app.route('/api/tts/synthesize', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def synthesize():
    # ... handler code
    pass
```

## Distributed Rate Limiting

For multi-instance deployments, Redis provides distributed rate limiting:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Gateway 1  │     │  Gateway 2  │     │  Gateway 3  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │  (shared)   │
                    └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        rate_limit:   rate_limit:   rate_limit:
        192.168.1.1   192.168.1.2   192.168.1.3
```

## Best Practices

1. **Graceful Degradation**: Return cached responses when possible during rate limiting
2. **Monitoring**: Track rate limit hits in metrics (Prometheus/CloudWatch)
3. **Whitelisting**: Allow internal services to bypass rate limits
4. **Documentation**: Clearly document limits in API docs and error messages
5. **Retry Headers**: Always include `Retry-After` header in 429 responses

## Environment Configuration

```bash
# .env
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# For production (stricter limits)
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_WINDOW=60
```
