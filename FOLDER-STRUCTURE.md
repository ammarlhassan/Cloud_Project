# Cloud_Project Folder Structure

```
Cloud_Project/
│
├── api-gateway/                          # API Gateway Service
│   └── src/
│       ├── app.py                        # Gateway implementation (610 lines)
│       └── requirements.txt              # Python dependencies
│
├── microservices/                        # All Microservices
│   ├── chat/                            # Chat Service
│   │   └── src/
│   │       ├── app.py                   # Chat service (541 lines)
│   │       └── requirements.txt
│   │
│   ├── document-reader/                 # Document Processing Service
│   │   └── src/
│   │       ├── app.py                   # Document service (664 lines)
│   │       └── requirements.txt
│   │
│   ├── quiz/                            # Quiz Service
│   │   └── src/
│   │       ├── app.py                   # Quiz service (699 lines)
│   │       └── requirements.txt
│   │
│   ├── stt/                             # Speech-to-Text Service
│   │   └── src/
│   │       ├── app.py                   # STT service (454 lines)
│   │       └── requirements.txt
│   │
│   └── tts/                             # Text-to-Speech Service
│       └── src/
│           ├── app.py                   # TTS service (388 lines)
│           └── requirements.txt
│
├── docker/                               # Docker Configuration
│   ├── dockerfiles/                     # Individual Dockerfiles
│   │   ├── Dockerfile.chat              # Chat service Dockerfile
│   │   ├── Dockerfile.document          # Document service Dockerfile
│   │   ├── Dockerfile.gateway           # Gateway Dockerfile
│   │   ├── Dockerfile.quiz              # Quiz service Dockerfile
│   │   ├── Dockerfile.stt               # STT service Dockerfile
│   │   └── Dockerfile.tts               # TTS service Dockerfile
│   │
│   └── docker-compose.learner-lab.yml   # Moved from root (legacy)
│
├── kafka/                                # Kafka Documentation & Scripts
│   ├── architecture/
│   │   └── kafka-cluster-architecture.md
│   │
│   ├── patterns/
│   │   └── kafka-integration-patterns.md
│   │
│   ├── scripts/
│   │   ├── kafka-cluster-deployment.sh
│   │   └── kafka-topic-creation.sh
│   │
│   └── topics/
│       └── kafka-topics-specification.md
│
├── docs/                                 # Additional Documentation (if exists)
│
├── kubernetes/                           # Kubernetes configs (if exists)
│
├── orchestration/                        # Orchestration files (if exists)
│
├── .env.example                          # Environment variables template
├── .gitignore                           # Git ignore rules
│
├── docker-compose.learner-lab.yml       # Main Docker Compose file (383 lines)
│
├── deploy-phase2.sh                     # Automated deployment script (executable)
├── deploy-learner-lab.sh                # Original deployment script
├── verify-phase2.sh                     # Verification script (executable)
├── generate-phase2-artifacts.sh         # Artifact generation script
│
├── AWS-LEARNER-LAB-GUIDE.md            # AWS setup guide
├── IMPLEMENTATION-SUMMARY.md            # Implementation details
├── PHASE2-README.md                     # Phase 2 documentation
├── PHASE2-SUMMARY.md                    # Quick reference (246 lines)
├── PROJECT-STATUS.md                    # Project status report
├── QUICK-START.md                       # Quick start guide
├── README.md                            # Main README
├── README-PHASE2.md                     # Comprehensive Phase 2 guide (681 lines)
│
└── CSE363-Cloud-Based+Learning+Platform-Project+Requirements.pdf
```

## Summary

### 📊 Statistics
- **Total Services**: 6 microservices + 1 API Gateway
- **Total Python Files**: 7 (app.py files)
- **Total Lines of Code**: ~3,356 lines
- **Dockerfiles**: 6
- **Docker Compose Files**: 1 main file (383 lines)
- **Documentation Files**: 8 markdown files
- **Scripts**: 4 bash scripts

### 🔑 Key Directories

1. **api-gateway/** - Entry point for all API requests
2. **microservices/** - 5 core microservices (chat, document-reader, quiz, stt, tts)
3. **docker/** - All Dockerfiles and compose configuration
4. **kafka/** - Kafka documentation and deployment scripts

### 📝 Key Files

- `docker-compose.learner-lab.yml` - Main orchestration file
- `deploy-phase2.sh` - Automated deployment
- `verify-phase2.sh` - Verification script
- `README-PHASE2.md` - Complete documentation
- `.env.example` - Environment template
