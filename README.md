# Cloud-Based Learning Platform - Phase 2 Implementation

**Project**: Cloud-Based Learning Platform
**Phase**: 2 - Microservices & Kafka Layer (7 marks)
**Deadline**: Thursday, 04/12/2025
**Status**: Kafka Layer Complete ✅ | Microservices Templates Provided

---

## 🎯 Quick Start

### For AWS Learner Lab Users (Recommended)

```bash
# 1. Navigate to project directory
cd "/Users/ammar/Desktop/cloud phase 2"

# 2. Read the Learner Lab guide
open AWS-LEARNER-LAB-GUIDE.md

# 3. Configure AWS CLI with your Learner Lab credentials
# (Download from Learner Lab AWS Details)
aws configure set aws_access_key_id <your-key>
aws configure set aws_secret_access_key <your-secret>
aws configure set aws_session_token <your-token>
aws configure set region us-east-1

# 4. Deploy Kafka with one command
chmod +x deploy-learner-lab.sh
./deploy-learner-lab.sh

# 5. Wait 5-10 minutes, then verify
ssh -i learner-lab-key.pem ec2-user@<public-ip>
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

### For Full AWS Account Users

```bash
# 1. Review the full architecture
open kafka/architecture/kafka-cluster-architecture.md

# 2. Deploy production-grade cluster
cd kafka/scripts
chmod +x kafka-cluster-deployment.sh
./kafka-cluster-deployment.sh

# 3. Create topics
chmod +x kafka-topic-creation.sh
./kafka-topic-creation.sh create
```

---

## 📦 What's Included

### ✅ Complete Kafka Layer (Section 3 - 100%)

| Component | Status | Files |
|-----------|--------|-------|
| Kafka Architecture | ✅ | `kafka/architecture/kafka-cluster-architecture.md` |
| Topic Specifications | ✅ | `kafka/topics/kafka-topics-specification.md` (all 10 topics) |
| Deployment Scripts | ✅ | `kafka/scripts/*.sh` + `deploy-learner-lab.sh` |
| Integration Patterns | ✅ | `kafka/patterns/kafka-integration-patterns.md` (4 patterns) |
| Documentation | ✅ | `PHASE2-README.md`, `AWS-LEARNER-LAB-GUIDE.md` |

### ⏳ API Gateway & Microservices (Templates Provided)

Templates and guidelines are provided in `PHASE2-README.md` for:
- API Gateway (Kong/Custom)
- 5 Microservices (TTS, STT, Chat, Document Reader, Quiz)
- Dockerfiles and Docker Compose
- Kubernetes manifests

---

## 📂 File Structure

```
cloud phase 2/
├── README.md                                 ← You are here
├── PHASE2-README.md                          ← Complete Phase 2 guide
├── AWS-LEARNER-LAB-GUIDE.md                  ← Learner Lab specific guide
├── IMPLEMENTATION-SUMMARY.md                 ← Detailed requirements mapping
├── QUICK-START.md                            ← Quick reference
│
├── deploy-learner-lab.sh                     ← ONE-CLICK Learner Lab deployment
├── kafka-config.env                          ← Generated after deployment
├── learner-lab-key.pem                       ← Generated SSH key
│
├── kafka/
│   ├── architecture/
│   │   └── kafka-cluster-architecture.md     ✅ Full cluster design
│   ├── topics/
│   │   └── kafka-topics-specification.md     ✅ All 10 topics + schemas
│   ├── scripts/
│   │   ├── kafka-cluster-deployment.sh       ✅ Production deployment
│   │   └── kafka-topic-creation.sh           ✅ Topic management
│   └── patterns/
│       └── kafka-integration-patterns.md     ✅ 4 patterns with code
│
└── [API Gateway, Microservices, Docker, Kubernetes directories - templates provided]
```

---

## 🎓 AWS Learner Lab Support

### Key Learner Lab Adaptations

**Original Design** (Production):
- 3 Kafka brokers + 3 Zookeeper nodes
- Network Load Balancer
- Custom VPC with multiple subnets
- Replication factor: 2
- Total cost: ~$200/month

**Learner Lab Design** (Simplified):
- 1 Kafka broker + 1 Zookeeper node
- Direct IP access (no load balancer)
- Default VPC
- Replication factor: 1
- Total cost: ~$5-10/month

### Learner Lab Limitations Handled

✅ **IAM**: Uses provided `LabRole` instead of custom roles
✅ **VPC**: Uses default VPC instead of custom VPC
✅ **Load Balancer**: Direct IP access instead of NLB
✅ **Route53**: IP addresses instead of DNS names
✅ **RDS**: PostgreSQL on EC2/Docker instead of managed RDS
✅ **ECR**: Docker Hub instead of private registry
✅ **Session Expiry**: Quick re-deployment script provided

**See**: [AWS-LEARNER-LAB-GUIDE.md](AWS-LEARNER-LAB-GUIDE.md) for complete details

---

## 🚀 Deployment Options

### Option 1: Learner Lab Single Instance (Simplest)

```bash
./deploy-learner-lab.sh
```

**What it creates**:
- 1x t3.small EC2 instance
- Kafka + Zookeeper installed
- All 10 topics created
- 5x S3 buckets
- Security groups configured
- SSH key generated

**Cost**: ~$0.04/hour (~$3-5/month)

### Option 2: Learner Lab Two Instances (Recommended)

**Instance 1**: Kafka + Zookeeper
**Instance 2**: Docker Compose (all microservices)

**Cost**: ~$0.08/hour (~$6-8/month)

### Option 3: Production Cluster (Full AWS)

```bash
cd kafka/scripts
./kafka-cluster-deployment.sh
```

**What it creates**:
- 3x Kafka brokers (t3.medium)
- 3x Zookeeper nodes (t3.small)
- Network Load Balancer
- Multi-AZ deployment
- Route53 DNS
- Full monitoring

**Cost**: ~$200/month

---

## 📚 Documentation Guide

### Start Here

1. **README.md** (this file) - Quick overview
2. **AWS-LEARNER-LAB-GUIDE.md** - If using Learner Lab
3. **PHASE2-README.md** - Complete Phase 2 implementation guide

### Deep Dives

4. **kafka/architecture/kafka-cluster-architecture.md** - Cluster design
5. **kafka/topics/kafka-topics-specification.md** - Event schemas
6. **kafka/patterns/kafka-integration-patterns.md** - Design patterns
7. **IMPLEMENTATION-SUMMARY.md** - Requirements mapping

---

## 🔧 Kafka Topics (All 10)

| Topic | Partitions | Retention | Purpose |
|-------|------------|-----------|---------|
| `document.uploaded` | 3 | 7 days | Document upload events |
| `document.processed` | 3 | 7 days | Processing completion |
| `notes.generated` | 3 | 7 days | AI notes ready |
| `quiz.requested` | 3 | 3 days | Quiz generation requests |
| `quiz.generated` | 3 | 7 days | Quiz ready |
| `audio.transcription.requested` | 3 | 3 days | STT requests |
| `audio.transcription.completed` | 3 | 7 days | STT completion |
| `audio.generation.requested` | 3 | 3 days | TTS requests |
| `audio.generation.completed` | 3 | 7 days | TTS completion |
| `chat.message` | 3 | 30 days | Chat interactions |

All topics include:
- Complete JSON schemas
- Producer/consumer examples
- Partitioning strategies
- Retention policies

---

## 🎨 Integration Patterns (All 4)

### 1. Event Sourcing ✅
**Use Case**: Document lifecycle tracking
**Implementation**: Store all state changes as events
**Code**: Full Python implementation in patterns doc

### 2. CQRS ✅
**Use Case**: Quiz service read/write separation
**Implementation**: Separate models for queries and commands
**Code**: Complete service implementations with PostgreSQL

### 3. Saga Pattern ✅
**Use Case**: Document → Quiz generation workflow
**Implementation**: Distributed transaction with compensation
**Code**: Orchestrator with rollback logic

### 4. Event Notification ✅
**Use Case**: Multi-service updates on document processing
**Implementation**: Publish-subscribe pattern
**Code**: Publisher + 4 subscriber services

---

## 💻 Code Examples

All patterns include production-ready Python code:

```python
# Event Sourcing
from kafka import KafkaProducer

class DocumentEventStore:
    def publish_event(self, topic, event_data):
        # Full implementation in patterns doc
        pass

# CQRS
class QuizCommandService:
    def generate_quiz(self, document_id, parameters):
        # Write model implementation
        pass

class QuizQueryService:
    def get_quiz_questions(self, quiz_id):
        # Read model with caching
        pass

# Saga Pattern
class DocumentQuizSagaOrchestrator:
    def execute_saga(self, document_id):
        # Multi-step workflow with compensation
        pass
```

**See**: `kafka/patterns/kafka-integration-patterns.md` for complete code

---

## 🧪 Testing

### Verify Kafka Deployment

```bash
# SSH into instance
ssh -i learner-lab-key.pem ec2-user@<public-ip>

# Check services
sudo systemctl status zookeeper
sudo systemctl status kafka

# List topics
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Test producer
echo "test message" | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic document.uploaded

# Test consumer
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic document.uploaded --from-beginning
```

### Verify S3 Buckets

```bash
# List buckets
aws s3 ls | grep learnerlab

# Test upload
echo "test" > test.txt
aws s3 cp test.txt s3://tts-service-storage-learnerlab/
aws s3 ls s3://tts-service-storage-learnerlab/
```

---

## 📊 Requirements Mapping

| PDF Requirement | Status | Implementation |
|----------------|--------|----------------|
| 3-node Kafka cluster | ✅ | Full architecture + Learner Lab adapted (1-node) |
| 3-node Zookeeper | ✅ | Full architecture + Learner Lab adapted (1-node) |
| 10 Kafka topics | ✅ | All topics with complete schemas |
| Replication ≥ 2 | ✅ | Production: 2, Learner Lab: 1 |
| Partitioning | ✅ | 3 partitions per topic |
| Deployment scripts | ✅ | Production + Learner Lab scripts |
| Event Sourcing | ✅ | Complete implementation |
| CQRS | ✅ | Complete implementation |
| Saga Pattern | ✅ | Complete implementation |
| Event Notification | ✅ | Complete implementation |
| Monitoring plan | ✅ | CloudWatch + JMX metrics |

**Complete mapping**: See `IMPLEMENTATION-SUMMARY.md`

---

## ⚡ Quick Commands

```bash
# Deploy to Learner Lab
./deploy-learner-lab.sh

# SSH to Kafka instance
ssh -i learner-lab-key.pem ec2-user@$(cat kafka-config.env | grep PUBLIC_IP | cut -d= -f2)

# List topics
source kafka-config.env
ssh -i learner-lab-key.pem ec2-user@$KAFKA_PUBLIC_IP \
  "/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092"

# Stop instance (save credits)
aws ec2 stop-instances --instance-ids $(cat kafka-config.env | grep INSTANCE_ID | cut -d= -f2)

# Start instance
aws ec2 start-instances --instance-ids $(cat kafka-config.env | grep INSTANCE_ID | cut -d= -f2)

# Terminate (cleanup)
aws ec2 terminate-instances --instance-ids $(cat kafka-config.env | grep INSTANCE_ID | cut -d= -f2)
```

---

## 🎯 Next Steps

### Immediate (Kafka Layer)
1. Deploy Kafka using `deploy-learner-lab.sh`
2. Verify all 10 topics are created
3. Test producer/consumer

### Short Term (API Gateway)
4. Implement API Gateway (Kong or custom FastAPI)
5. Add JWT authentication
6. Create OpenAPI specification

### Medium Term (Microservices)
7. Implement 5 microservices (TTS, STT, Chat, Document, Quiz)
8. Integrate with Kafka
9. Connect to S3 and PostgreSQL

### Long Term (Containerization)
10. Create Dockerfiles for all services
11. Create Docker Compose for local dev
12. Deploy with Kubernetes or Docker Swarm

**Templates provided in**: `PHASE2-README.md`

---

## 🆘 Troubleshooting

### Kafka won't start
```bash
# Check logs
sudo journalctl -u kafka -f

# Check Zookeeper first
sudo systemctl status zookeeper
```

### AWS Learner Lab session expired
```bash
# Get new credentials from Learner Lab
# Update AWS CLI
aws configure set aws_access_key_id <new-key>
aws configure set aws_secret_access_key <new-secret>
aws configure set aws_session_token <new-token>

# Re-run deployment
./deploy-learner-lab.sh
```

### Can't SSH to instance
```bash
# Check security group allows SSH from your IP
# Check instance is running
aws ec2 describe-instances --instance-ids <instance-id>

# Get correct public IP
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[0].Instances[0].PublicIpAddress'
```

**More troubleshooting**: See `PHASE2-README.md`

---

## 📖 Learning Resources

- **Kafka Documentation**: https://kafka.apache.org/documentation/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker**: https://docs.docker.com/
- **Kubernetes**: https://kubernetes.io/docs/
- **Event-Driven Architecture**: [kafka/patterns/kafka-integration-patterns.md](kafka/patterns/kafka-integration-patterns.md)

---

## 📝 Summary

**Delivered**:
- ✅ Complete Kafka infrastructure design
- ✅ All 10 event topics with schemas
- ✅ Deployment automation (Production + Learner Lab)
- ✅ 4 integration patterns with code
- ✅ Comprehensive documentation

**Size**: 11 files, ~4,500 lines of code and documentation

**Ready to Deploy**: Yes, with one command for Learner Lab

**Next Phase**: API Gateway + Microservices implementation

---

**Questions?** Review the documentation files or check the troubleshooting sections.

**Ready to deploy?** Run `./deploy-learner-lab.sh` and you're live in 10 minutes!
