# Phase 2: Microservices & Kafka Layer - Implementation Guide

**Project**: Cloud-Based Learning Platform
**Phase**: 2 - Microservices Development & Event Integration
**Deadline**: Thursday, 04/12/2025
**Marks**: 7 out of 20 total

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [Deliverables Checklist](#deliverables-checklist)
4. [Directory Structure](#directory-structure)
5. [Implementation Status](#implementation-status)
6. [Quick Start Guide](#quick-start-guide)
7. [Deployment Instructions](#deployment-instructions)
8. [Testing and Verification](#testing-and-verification)
9. [Troubleshooting](#troubleshooting)
10. [Requirements Mapping](#requirements-mapping)

---

## Overview

Phase 2 implements the complete microservices architecture and event-driven communication layer for the Cloud-Based Learning Platform. This includes:

- **Kafka Infrastructure**: 3-node cluster + 3-node Zookeeper
- **API Gateway**: Single entry point with Kong/custom implementation
- **Five Microservices**: TTS, STT, Chat, Document Reader, Quiz
- **Event-Driven Architecture**: Implementing Event Sourcing, CQRS, Saga, and Event Notification patterns
- **Containerization**: Docker + Kubernetes/Swarm orchestration
- **Storage Isolation**: Dedicated S3 buckets and PostgreSQL databases per service

---

## Architecture Summary

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│                     (Web, Mobile, Desktop)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                     │
│                      (Public, SSL/TLS)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                     (Kong / Custom)                              │
│  - JWT Authentication                                            │
│  - Rate Limiting                                                 │
│  - Request/Response Transformation                               │
│  - API Versioning (v1)                                           │
│  - CORS Policies                                                 │
│  - Logging & Monitoring                                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────┬────────────┐
        │            │            │             │            │
        ▼            ▼            ▼             ▼            ▼
   ┌────────┐  ┌────────┐  ┌──────────┐  ┌─────────┐  ┌────────┐
   │  TTS   │  │  STT   │  │   Chat   │  │Document │  │  Quiz  │
   │Service │  │Service │  │  Service │  │ Reader  │  │Service │
   └───┬────┘  └───┬────┘  └────┬─────┘  └────┬────┘  └───┬────┘
       │           │            │             │            │
       └───────────┴────────────┴─────────────┴────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────┐
        │          Apache Kafka (3-node cluster)        │
        │  - Event Streaming                            │
        │  - Asynchronous Communication                 │
        │  - 10 Topics (document.*, quiz.*, audio.*)    │
        │  - Replication Factor: 2                      │
        │  - Min ISR: 2                                 │
        └───────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   ┌─────────┐           ┌──────────┐          ┌──────────┐
   │   S3    │           │PostgreSQL│          │  Redis   │
   │Buckets  │           │Databases │          │  Cache   │
   │(5 Total)│           │(4 Total) │          │(Optional)│
   └─────────┘           └──────────┘          └──────────┘
```

### Service-Level Architecture

Each microservice follows this pattern:

```
┌────────────────────────────────────────┐
│         Microservice Container          │
│  ┌──────────────────────────────────┐  │
│  │      FastAPI Application         │  │
│  │  - REST API Endpoints            │  │
│  │  - Request Validation            │  │
│  │  - Business Logic                │  │
│  │  - Health Checks                 │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │      Kafka Integration           │  │
│  │  - Producer (publish events)     │  │
│  │  - Consumer (subscribe events)   │  │
│  │  - Event Handlers                │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │     Storage Integration          │  │
│  │  - S3 Client (dedicated bucket)  │  │
│  │  - PostgreSQL (dedicated DB)     │  │
│  │  - Redis (optional cache)        │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

---

## Deliverables Checklist

### 1. Kafka Infrastructure ✓

- [x] **Architecture Design**
  - [x] 3-node Kafka cluster specification
  - [x] 3-node Zookeeper ensemble specification
  - [x] Network Load Balancer configuration
  - [x] Security groups and network design
  - [x] High availability and disaster recovery plan

- [x] **Topic Definitions**
  - [x] 10 topics with complete schemas
  - [x] Partitioning strategies
  - [x] Replication and retention policies
  - [x] Producer/consumer specifications

- [x] **Deployment Scripts**
  - [x] Kafka cluster deployment script
  - [x] Topic creation and management script
  - [x] Monitoring and alerting setup

- [x] **Integration Patterns**
  - [x] Event Sourcing implementation
  - [x] CQRS pattern with examples
  - [x] Saga pattern for distributed transactions
  - [x] Event Notification pattern

### 2. API Gateway ⏳

- [ ] **Architecture Design**
  - [ ] Gateway architecture document
  - [ ] Route definitions for all services
  - [ ] Authentication flow diagrams

- [ ] **Configuration Files**
  - [ ] Kong declarative configuration (or custom implementation)
  - [ ] JWT authentication setup
  - [ ] Rate limiting policies
  - [ ] CORS configuration
  - [ ] Request/response transformation rules

- [ ] **API Documentation**
  - [ ] Complete OpenAPI 3.0 specification
  - [ ] All endpoints documented
  - [ ] Request/response examples
  - [ ] Authentication requirements

### 3. Microservices ⏳

For each of the 5 microservices (TTS, STT, Chat, Document Reader, Quiz):

- [ ] **Service Implementation**
  - [ ] FastAPI application structure
  - [ ] All API endpoints implemented
  - [ ] Request/response models
  - [ ] Input validation
  - [ ] Error handling
  - [ ] Health check endpoints

- [ ] **Kafka Integration**
  - [ ] Producer implementation
  - [ ] Consumer implementation
  - [ ] Event handlers
  - [ ] Example code

- [ ] **Storage Integration**
  - [ ] S3 bucket configuration
  - [ ] PostgreSQL database schema
  - [ ] Redis cache setup (where applicable)
  - [ ] Storage isolation enforcement

### 4. Containerization ⏳

- [ ] **Docker Implementation**
  - [ ] Dockerfile for each service (6 total: 5 services + API Gateway)
  - [ ] Multi-stage builds
  - [ ] Environment variable configuration
  - [ ] Health check implementation
  - [ ] Image optimization

- [ ] **Local Development**
  - [ ] Docker Compose configuration
  - [ ] Local Kafka setup
  - [ ] Local database setup
  - [ ] Development environment documentation

- [ ] **Container Registry**
  - [ ] ECR repository structure
  - [ ] Image tagging strategy
  - [ ] CI pipeline outline
  - [ ] Image scanning configuration

### 5. Orchestration ⏳

- [ ] **Kubernetes Manifests** (or Docker Swarm)
  - [ ] Deployment manifests for all services
  - [ ] Service discovery configuration
  - [ ] ConfigMaps and Secrets
  - [ ] Persistent Volume Claims
  - [ ] Resource limits and requests
  - [ ] Horizontal Pod Autoscaler
  - [ ] Readiness and liveness probes

---

## Directory Structure

```
cloud phase 2/
├── PHASE2-README.md                          # This file
├── CSE363-Cloud-Based+Learning+Platform-Project+Requirements.pdf
│
├── kafka/
│   ├── architecture/
│   │   └── kafka-cluster-architecture.md     # ✓ Complete architecture
│   ├── topics/
│   │   └── kafka-topics-specification.md     # ✓ All 10 topics defined
│   ├── scripts/
│   │   ├── kafka-cluster-deployment.sh       # ✓ Deployment automation
│   │   └── kafka-topic-creation.sh           # ✓ Topic management
│   └── patterns/
│       └── kafka-integration-patterns.md     # ✓ All 4 patterns
│
├── api-gateway/
│   ├── architecture/
│   │   └── api-gateway-architecture.md       # ⏳ To be created
│   ├── config/
│   │   ├── kong.yml                          # ⏳ Kong configuration
│   │   ├── jwt-auth-config.yml               # ⏳ JWT setup
│   │   └── rate-limiting.yml                 # ⏳ Rate limits
│   ├── openapi/
│   │   └── openapi-spec.yml                  # ⏳ Complete API spec
│   └── src/
│       └── main.py                           # ⏳ Custom gateway (if used)
│
├── microservices/
│   ├── tts/
│   │   ├── src/
│   │   │   ├── main.py                       # ⏳ FastAPI app
│   │   │   ├── api/                          # ⏳ API routes
│   │   │   ├── kafka/                        # ⏳ Kafka integration
│   │   │   ├── storage/                      # ⏳ S3 integration
│   │   │   └── models/                       # ⏳ Data models
│   │   ├── requirements.txt                  # ⏳ Python dependencies
│   │   └── README.md                         # ⏳ Service documentation
│   │
│   ├── stt/                                  # ⏳ Similar structure
│   ├── chat/                                 # ⏳ Similar structure
│   ├── document-reader/                      # ⏳ Similar structure
│   └── quiz/                                 # ⏳ Similar structure
│
├── docker/
│   ├── dockerfiles/
│   │   ├── Dockerfile.tts                    # ⏳ TTS service
│   │   ├── Dockerfile.stt                    # ⏳ STT service
│   │   ├── Dockerfile.chat                   # ⏳ Chat service
│   │   ├── Dockerfile.document-reader        # ⏳ Document Reader
│   │   ├── Dockerfile.quiz                   # ⏳ Quiz service
│   │   └── Dockerfile.api-gateway            # ⏳ API Gateway
│   └── docker-compose.yml                    # ⏳ Local development
│
├── kubernetes/
│   ├── deployments/
│   │   ├── tts-deployment.yml                # ⏳ TTS deployment
│   │   ├── stt-deployment.yml                # ⏳ STT deployment
│   │   ├── chat-deployment.yml               # ⏳ Chat deployment
│   │   ├── document-reader-deployment.yml    # ⏳ Document Reader
│   │   └── quiz-deployment.yml               # ⏳ Quiz deployment
│   ├── services/
│   │   └── service-*.yml                     # ⏳ Service definitions
│   ├── configmaps/
│   │   └── config-*.yml                      # ⏳ Configuration
│   ├── secrets/
│   │   └── secrets-*.yml                     # ⏳ Secrets (template)
│   └── autoscaling/
│       └── hpa-*.yml                         # ⏳ Horizontal autoscalers
│
├── orchestration/
│   └── ecr-setup.md                          # ⏳ ECR configuration
│
└── docs/
    └── requirements-mapping.md               # ⏳ Requirement traceability
```

---

## Implementation Status

### Completed (Kafka Layer) ✓

**Files Created**:
1. `kafka/architecture/kafka-cluster-architecture.md` - Complete 3-node cluster design with Zookeeper, NLB, security groups, HA strategy, cost estimation
2. `kafka/topics/kafka-topics-specification.md` - All 10 topics with JSON schemas, partitioning strategies, retention policies, producer/consumer groups
3. `kafka/scripts/kafka-cluster-deployment.sh` - Automated deployment script for EC2 instances, security groups, NLB setup
4. `kafka/scripts/kafka-topic-creation.sh` - Topic creation and management automation
5. `kafka/patterns/kafka-integration-patterns.md` - Comprehensive implementation of Event Sourcing, CQRS, Saga, and Event Notification patterns with Python code examples

**What's Included**:
- ✓ Architecture diagrams (ASCII art)
- ✓ Network design and security groups
- ✓ Complete topic schemas with JSON examples
- ✓ Producer/consumer code samples
- ✓ Pattern implementations with real use cases
- ✓ Deployment automation scripts
- ✓ Monitoring and disaster recovery procedures

### In Progress (API Gateway & Microservices) ⏳

The remaining artifacts follow a template-based approach and will include:

**API Gateway**:
- Kong declarative configuration OR custom Python FastAPI gateway
- JWT authentication with token validation
- Rate limiting per endpoint and per user
- CORS policies for web access
- OpenAPI 3.0 specification for all endpoints
- Request logging and monitoring

**Each Microservice** (TTS, STT, Chat, Document Reader, Quiz):
- Complete FastAPI implementation
- All endpoints from PDF specification
- Kafka producer/consumer integration
- S3 and PostgreSQL integration
- Input validation and error handling
- Health check endpoints (/health, /ready)
- Comprehensive documentation

**Containerization**:
- Optimized Dockerfiles with multi-stage builds
- Docker Compose for local development
- Kubernetes deployment manifests
- Resource limits and autoscaling
- Health/readiness probes

---

## Quick Start Guide

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Docker installed
- kubectl installed (for Kubernetes)
- Python 3.11+
- Access to EC2, S3, RDS, ECR

### Step 1: Deploy Kafka Cluster

```bash
cd kafka/scripts

# Set environment variables
export ENVIRONMENT=prod
export AWS_REGION=us-east-1

# Make scripts executable
chmod +x kafka-cluster-deployment.sh
chmod +x kafka-topic-creation.sh

# Deploy Kafka cluster (requires Phase 1 VPC/subnets to be ready)
./kafka-cluster-deployment.sh

# Create topics
./kafka-topic-creation.sh create
```

### Step 2: Verify Kafka Setup

```bash
# SSH into one of the Kafka brokers
ssh -i your-key.pem ec2-user@<kafka-broker-ip>

# List topics
/opt/kafka/bin/kafka-topics.sh --list \
  --bootstrap-server kafka-nlb.internal:9092

# Check topic details
/opt/kafka/bin/kafka-topics.sh --describe \
  --bootstrap-server kafka-nlb.internal:9092 \
  --topic document.uploaded
```

### Step 3: Deploy Microservices (once implemented)

```bash
# Build Docker images
cd docker/dockerfiles
docker build -f Dockerfile.tts -t tts-service:v1.0.0 ../../microservices/tts
docker build -f Dockerfile.stt -t stt-service:v1.0.0 ../../microservices/stt
# ... repeat for all services

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag tts-service:v1.0.0 <account-id>.dkr.ecr.us-east-1.amazonaws.com/tts-service:v1.0.0
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/tts-service:v1.0.0

# Deploy to Kubernetes
kubectl apply -f kubernetes/deployments/
kubectl apply -f kubernetes/services/
kubectl apply -f kubernetes/autoscaling/
```

### Step 4: Test the System

```bash
# Check all pods are running
kubectl get pods

# Test API Gateway
curl -X POST https://api.cloudlearning.com/v1/api/documents/upload \
  -H "Authorization: Bearer <jwt-token>" \
  -F "file=@lecture_notes.pdf"

# Monitor Kafka topics
kafka-console-consumer.sh \
  --bootstrap-server kafka-nlb.internal:9092 \
  --topic document.uploaded \
  --from-beginning
```

---

## Deployment Instructions

### Environment Setup

Each service requires environment variables:

```bash
# Common variables
ENVIRONMENT=prod
AWS_REGION=us-east-1
KAFKA_BOOTSTRAP_SERVERS=kafka-nlb.internal:9092
LOG_LEVEL=INFO

# Service-specific variables
# TTS Service
S3_BUCKET=tts-service-storage-prod
REDIS_HOST=redis.internal
REDIS_PORT=6379

# STT Service
S3_BUCKET=stt-service-storage-prod
POSTGRES_HOST=stt-db.internal
POSTGRES_DB=stt_service
POSTGRES_USER=stt_user
POSTGRES_PASSWORD=<from-secrets-manager>

# Similar for other services...
```

### Database Setup

Each service with PostgreSQL needs schema initialization:

```sql
-- STT Service Database
CREATE DATABASE stt_service;
CREATE USER stt_user WITH ENCRYPTED PASSWORD '<password>';
GRANT ALL PRIVILEGES ON DATABASE stt_service TO stt_user;

-- Create tables (see individual service schemas)
```

### S3 Bucket Setup

```bash
# Create S3 buckets
aws s3 mb s3://tts-service-storage-prod --region us-east-1
aws s3 mb s3://stt-service-storage-prod --region us-east-1
aws s3 mb s3://chat-service-storage-prod --region us-east-1
aws s3 mb s3://document-reader-storage-prod --region us-east-1
aws s3 mb s3://quiz-service-storage-prod --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket tts-service-storage-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket tts-service-storage-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Repeat for all buckets...
```

---

## Testing and Verification

### Unit Tests

Each service should have unit tests:

```bash
cd microservices/tts
pytest tests/ -v
```

### Integration Tests

Test Kafka event flows:

```python
# Test document upload → quiz generation saga
import requests
import time

# 1. Upload document
response = requests.post(
    'http://api-gateway/v1/api/documents/upload',
    headers={'Authorization': 'Bearer <token>'},
    files={'file': open('test.pdf', 'rb')}
)
document_id = response.json()['document_id']

# 2. Wait for processing
time.sleep(30)

# 3. Request quiz
response = requests.post(
    f'http://api-gateway/v1/api/quiz/generate',
    headers={'Authorization': 'Bearer <token>'},
    json={
        'document_id': document_id,
        'question_count': 10
    }
)
quiz_id = response.json()['quiz_id']

# 4. Verify quiz was generated
response = requests.get(
    f'http://api-gateway/v1/api/quiz/{quiz_id}',
    headers={'Authorization': 'Bearer <token>'}
)
assert response.status_code == 200
```

### Load Testing

```bash
# Use Apache Bench or k6
ab -n 1000 -c 10 -H "Authorization: Bearer <token>" \
  http://api-gateway/v1/api/tts/synthesize
```

---

## Troubleshooting

### Common Issues

**1. Kafka brokers not starting**
```bash
# Check Zookeeper
ssh ec2-user@<zk-ip>
sudo systemctl status zookeeper
sudo journalctl -u zookeeper -f

# Check Kafka logs
ssh ec2-user@<kafka-ip>
sudo journalctl -u kafka -f
```

**2. Services can't connect to Kafka**
```bash
# Verify NLB health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# Test connectivity from service subnet
telnet kafka-nlb.internal 9092
```

**3. Pod startup failures**
```bash
# Check pod logs
kubectl logs <pod-name>

# Describe pod for events
kubectl describe pod <pod-name>

# Check resource constraints
kubectl top pods
```

**4. S3 access denied**
```bash
# Verify IAM role attached to pod
kubectl describe pod <pod-name> | grep "Service Account"

# Check IAM policy
aws iam get-role-policy --role-name <service-role> --policy-name S3Access
```

---

## Requirements Mapping

This section maps Phase 2 project requirements to implementation artifacts.

### Kafka Requirements → Implementation

| Requirement | Implementation File | Status |
|-------------|-------------------|--------|
| 3-node Kafka cluster | `kafka/architecture/kafka-cluster-architecture.md` | ✓ |
| 3-node Zookeeper | `kafka/architecture/kafka-cluster-architecture.md` | ✓ |
| 10 Kafka topics | `kafka/topics/kafka-topics-specification.md` | ✓ |
| Topic schemas | `kafka/topics/kafka-topics-specification.md` | ✓ |
| Replication factor ≥2 | `kafka/topics/kafka-topics-specification.md` | ✓ |
| Partitioning strategy | `kafka/topics/kafka-topics-specification.md` | ✓ |
| Producer/consumer groups | `kafka/topics/kafka-topics-specification.md` | ✓ |
| Deployment scripts | `kafka/scripts/kafka-cluster-deployment.sh` | ✓ |
| Topic creation scripts | `kafka/scripts/kafka-topic-creation.sh` | ✓ |
| Event Sourcing | `kafka/patterns/kafka-integration-patterns.md` | ✓ |
| CQRS | `kafka/patterns/kafka-integration-patterns.md` | ✓ |
| Saga Pattern | `kafka/patterns/kafka-integration-patterns.md` | ✓ |
| Event Notification | `kafka/patterns/kafka-integration-patterns.md` | ✓ |
| Monitoring plan | `kafka/architecture/kafka-cluster-architecture.md` | ✓ |

### API Gateway Requirements → Implementation

| Requirement | Implementation File | Status |
|-------------|-------------------|--------|
| Single entry point | `api-gateway/architecture/` | ⏳ |
| Route definitions | `api-gateway/config/kong.yml` | ⏳ |
| JWT authentication | `api-gateway/config/jwt-auth-config.yml` | ⏳ |
| Rate limiting | `api-gateway/config/rate-limiting.yml` | ⏳ |
| API versioning | `api-gateway/openapi/openapi-spec.yml` | ⏳ |
| CORS policies | `api-gateway/config/kong.yml` | ⏳ |
| Request logging | `api-gateway/config/kong.yml` | ⏳ |
| OpenAPI specification | `api-gateway/openapi/openapi-spec.yml` | ⏳ |

### Microservices Requirements → Implementation

| Service | Requirement | Implementation File | Status |
|---------|------------|-------------------|--------|
| TTS | Python 3.11 container | `docker/dockerfiles/Dockerfile.tts` | ⏳ |
| TTS | S3 storage | `microservices/tts/src/storage/` | ⏳ |
| TTS | API endpoints | `microservices/tts/src/api/` | ⏳ |
| TTS | Kafka integration | `microservices/tts/src/kafka/` | ⏳ |
| STT | Python 3.11 container | `docker/dockerfiles/Dockerfile.stt` | ⏳ |
| STT | PostgreSQL DB | `microservices/stt/database/schema.sql` | ⏳ |
| STT | API endpoints | `microservices/stt/src/api/` | ⏳ |
| STT | Kafka integration | `microservices/stt/src/kafka/` | ⏳ |
| Chat | Python 3.11 container | `docker/dockerfiles/Dockerfile.chat` | ⏳ |
| Chat | PostgreSQL + Redis | `microservices/chat/src/storage/` | ⏳ |
| Chat | API endpoints | `microservices/chat/src/api/` | ⏳ |
| Chat | Kafka integration | `microservices/chat/src/kafka/` | ⏳ |
| Document | Python 3.11 container | `docker/dockerfiles/Dockerfile.document-reader` | ⏳ |
| Document | PostgreSQL + S3 | `microservices/document-reader/src/storage/` | ⏳ |
| Document | API endpoints | `microservices/document-reader/src/api/` | ⏳ |
| Document | Kafka integration | `microservices/document-reader/src/kafka/` | ⏳ |
| Quiz | Python 3.11 container | `docker/dockerfiles/Dockerfile.quiz` | ⏳ |
| Quiz | PostgreSQL + S3 | `microservices/quiz/src/storage/` | ⏳ |
| Quiz | API endpoints | `microservices/quiz/src/api/` | ⏳ |
| Quiz | Kafka integration | `microservices/quiz/src/kafka/` | ⏳ |

### Containerization Requirements → Implementation

| Requirement | Implementation File | Status |
|-------------|-------------------|--------|
| Dockerfiles for all services | `docker/dockerfiles/Dockerfile.*` | ⏳ |
| Multi-stage builds | `docker/dockerfiles/Dockerfile.*` | ⏳ |
| Health checks | All Dockerfiles | ⏳ |
| Environment variables | All service implementations | ⏳ |
| Docker Compose | `docker/docker-compose.yml` | ⏳ |
| Kubernetes deployments | `kubernetes/deployments/*.yml` | ⏳ |
| Service discovery | `kubernetes/services/*.yml` | ⏳ |
| Resource limits | `kubernetes/deployments/*.yml` | ⏳ |
| Autoscaling | `kubernetes/autoscaling/*.yml` | ⏳ |
| ECR setup | `orchestration/ecr-setup.md` | ⏳ |

---

## Next Steps

To complete Phase 2 implementation:

1. **API Gateway**: Create Kong configuration and OpenAPI specification
2. **Microservices**: Implement all 5 services with complete functionality
3. **Dockerfiles**: Create optimized containers for all services
4. **Kubernetes**: Deploy manifests for orchestration
5. **Testing**: Integration and load testing
6. **Documentation**: Complete API documentation and deployment guides

---

## Contact and Support

For questions or issues:
- Review the project requirements PDF
- Check individual README files in each directory
- Refer to Kafka documentation: https://kafka.apache.org/documentation/
- Refer to FastAPI documentation: https://fastapi.tiangolo.com/
- Refer to Kubernetes documentation: https://kubernetes.io/docs/

---

## Version History

- **v1.0** (2025-11-29): Initial Phase 2 implementation with complete Kafka layer
- **v1.1** (TBD): API Gateway and microservices completion
- **v1.2** (TBD): Full containerization and orchestration
