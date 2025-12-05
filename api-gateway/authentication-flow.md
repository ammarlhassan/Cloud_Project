# Authentication Flow Diagrams

## Overview

The API Gateway uses **JWT (JSON Web Token)** authentication for securing API endpoints.

## Authentication Flow

### 1. Login Flow

```
┌──────────┐          ┌─────────────┐          ┌──────────────┐
│  Client  │          │ API Gateway │          │   Database   │
└────┬─────┘          └──────┬──────┘          └──────┬───────┘
     │                       │                        │
     │  POST /auth/login     │                        │
     │  {username, password} │                        │
     │──────────────────────>│                        │
     │                       │                        │
     │                       │  Validate credentials  │
     │                       │───────────────────────>│
     │                       │                        │
     │                       │  User data (if valid)  │
     │                       │<───────────────────────│
     │                       │                        │
     │                       │  Generate JWT token    │
     │                       │  (sign with secret)    │
     │                       │                        │
     │  {token, expires_in}  │                        │
     │<──────────────────────│                        │
     │                       │                        │
     │  Store token locally  │                        │
     │                       │                        │
```

### 2. Authenticated Request Flow

```
┌──────────┐          ┌─────────────┐          ┌─────────────┐
│  Client  │          │ API Gateway │          │ Microservice│
└────┬─────┘          └──────┬──────┘          └──────┬──────┘
     │                       │                        │
     │  GET /api/chat/sessions                        │
     │  Authorization: Bearer <token>                 │
     │──────────────────────>│                        │
     │                       │                        │
     │                       │  Validate JWT          │
     │                       │  - Check signature     │
     │                       │  - Check expiration    │
     │                       │  - Extract user_id     │
     │                       │                        │
     │                       │  Forward request       │
     │                       │  X-User-ID: <user_id>  │
     │                       │───────────────────────>│
     │                       │                        │
     │                       │  Response              │
     │                       │<───────────────────────│
     │                       │                        │
     │  Response             │                        │
     │<──────────────────────│                        │
     │                       │                        │
```

### 3. Token Refresh Flow

```
┌──────────┐          ┌─────────────┐
│  Client  │          │ API Gateway │
└────┬─────┘          └──────┬──────┘
     │                       │
     │  POST /auth/refresh   │
     │  Authorization: Bearer <old_token>
     │──────────────────────>│
     │                       │
     │                       │  Validate old token
     │                       │  (must not be expired)
     │                       │
     │                       │  Generate new JWT
     │                       │  with fresh expiry
     │                       │
     │  {token, expires_in}  │
     │<──────────────────────│
     │                       │
```

### 4. Token Expiration & Re-authentication

```
┌──────────┐          ┌─────────────┐
│  Client  │          │ API Gateway │
└────┬─────┘          └──────┬──────┘
     │                       │
     │  GET /api/documents   │
     │  Authorization: Bearer <expired_token>
     │──────────────────────>│
     │                       │
     │                       │  Validate JWT
     │                       │  Token EXPIRED!
     │                       │
     │  401 Unauthorized     │
     │  {error: "token_expired"}
     │<──────────────────────│
     │                       │
     │  (Client must login again or refresh token)
     │                       │
```

## JWT Token Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        JWT Token                            │
├──────────────┬──────────────────┬───────────────────────────┤
│    Header    │     Payload      │        Signature          │
│   (Base64)   │    (Base64)      │         (Base64)          │
├──────────────┼──────────────────┼───────────────────────────┤
│ {            │ {                │                           │
│   "alg":     │   "sub": "123",  │  HMACSHA256(              │
│     "HS256", │   "username":    │    base64(header) + "." + │
│   "typ":     │     "student@..",│    base64(payload),       │
│     "JWT"    │   "exp": 17...,  │    JWT_SECRET             │
│ }            │   "iat": 17...   │  )                        │
│              │ }                │                           │
└──────────────┴──────────────────┴───────────────────────────┘

Example Token:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiIxMjM0NTY3ODkwIiwidXNlcm5hbWUiOiJzdHVkZW50QHVuaXZlcnNpdHkuZWR1IiwiZXhwIjoxNzAxODc4NDAwfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

## Token Payload Claims

| Claim | Description | Example |
|-------|-------------|---------|
| `sub` | Subject (user ID) | `"user-123-abc"` |
| `username` | User's email/username | `"student@university.edu"` |
| `role` | User role | `"student"` or `"admin"` |
| `iat` | Issued at (Unix timestamp) | `1701792000` |
| `exp` | Expiration (Unix timestamp) | `1701878400` |

## Security Measures

### 1. Token Security

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. HTTPS Only                                              │
│     └── All traffic encrypted in transit                    │
│                                                             │
│  2. Short Token Lifetime                                    │
│     └── Tokens expire after 24 hours (configurable)         │
│                                                             │
│  3. Secure Secret Key                                       │
│     └── JWT_SECRET from environment (never hardcoded)       │
│                                                             │
│  4. Token Validation                                        │
│     ├── Signature verification                              │
│     ├── Expiration check                                    │
│     └── Issuer/audience validation (optional)               │
│                                                             │
│  5. No Sensitive Data in Token                              │
│     └── Only user ID and role, no passwords                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Request Authentication Middleware

```python
from functools import wraps
from flask import request, jsonify
import jwt

def require_auth(f):
    """Authentication middleware decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Extract token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'missing_token'}), 401
        
        # 2. Parse Bearer token
        parts = auth_header.split()
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            return jsonify({'error': 'invalid_token_format'}), 401
        
        token = parts[1]
        
        # 3. Validate token
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'token_expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'invalid_token'}), 401
        
        # 4. Add user info to request context
        request.user_id = payload['sub']
        request.username = payload.get('username')
        
        return f(*args, **kwargs)
    return decorated
```

## Error Responses

| Scenario | HTTP Status | Response |
|----------|-------------|----------|
| No token provided | 401 | `{"error": "missing_token", "message": "Authorization header required"}` |
| Invalid token format | 401 | `{"error": "invalid_token_format", "message": "Use 'Bearer <token>'"}` |
| Expired token | 401 | `{"error": "token_expired", "message": "Token has expired, please login again"}` |
| Invalid signature | 401 | `{"error": "invalid_token", "message": "Token validation failed"}` |
| Insufficient permissions | 403 | `{"error": "forbidden", "message": "You don't have access to this resource"}` |

## Full Authentication Sequence

```
┌────────┐     ┌─────────┐     ┌────────┐     ┌─────┐     ┌────────────┐
│ Client │     │ Gateway │     │  Auth  │     │Redis│     │Microservice│
└───┬────┘     └────┬────┘     └───┬────┘     └──┬──┘     └─────┬──────┘
    │               │              │             │               │
    │ 1. Login      │              │             │               │
    │──────────────>│              │             │               │
    │               │ 2. Validate  │             │               │
    │               │─────────────>│             │               │
    │               │ 3. User OK   │             │               │
    │               │<─────────────│             │               │
    │ 4. JWT Token  │              │             │               │
    │<──────────────│              │             │               │
    │               │              │             │               │
    │ 5. API Request│              │             │               │
    │ + JWT Token   │              │             │               │
    │──────────────>│              │             │               │
    │               │ 6. Check rate limit        │               │
    │               │────────────────────────────>│               │
    │               │ 7. OK                      │               │
    │               │<────────────────────────────│               │
    │               │              │             │               │
    │               │ 8. Validate JWT            │               │
    │               │ (local, no DB call)        │               │
    │               │              │             │               │
    │               │ 9. Forward + X-User-ID     │               │
    │               │────────────────────────────────────────────>│
    │               │ 10. Response               │               │
    │               │<────────────────────────────────────────────│
    │ 11. Response  │              │             │               │
    │<──────────────│              │             │               │
    │               │              │             │               │
```

## Configuration

```bash
# Environment variables
JWT_SECRET=your-256-bit-secret-key-here    # REQUIRED - generate with: openssl rand -base64 32
JWT_EXPIRATION_HOURS=24                     # Token lifetime (default: 24 hours)
JWT_ALGORITHM=HS256                         # Signing algorithm
```
