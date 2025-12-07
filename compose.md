version: "3.9"

services:

  # --------------------------
  # Postgres DBs
  # --------------------------
  chat-db:
    image: postgres:15-alpine
    container_name: chat-db
    hostname: chat-db
    environment:
      POSTGRES_DB: chat_db
      POSTGRES_USER: ${CHAT_DB_USER:?CHAT_DB_USER is required}
      POSTGRES_PASSWORD: ${CHAT_DB_PASSWORD:?CHAT_DB_PASSWORD is required}
    ports:
      - "5432:5432"
    networks:
      - learner-lab-network
    volumes:
      - chat-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d chat_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  document-db:
    image: postgres:15-alpine
    container_name: document-db
    hostname: document-db
    environment:
      POSTGRES_DB: document_db
      POSTGRES_USER: ${DOCUMENT_DB_USER:?DOCUMENT_DB_USER is required}
      POSTGRES_PASSWORD: ${DOCUMENT_DB_PASSWORD:?DOCUMENT_DB_PASSWORD is required}
    ports:
      - "5433:5432"
    networks:
      - learner-lab-network
    volumes:
      - document-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d document_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  quiz-db:
    image: postgres:15-alpine
    container_name: quiz-db
    hostname: quiz-db
    environment:
      POSTGRES_DB: quiz_db
      POSTGRES_USER: ${QUIZ_DB_USER:?QUIZ_DB_USER is required}
      POSTGRES_PASSWORD: ${QUIZ_DB_PASSWORD:?QUIZ_DB_PASSWORD is required}
    ports:
      - "5434:5432"
    networks:
      - learner-lab-network
    volumes:
      - quiz-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d quiz_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    networks:
      - learner-lab-network
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # --------------------------
  # Microservices
  # --------------------------
  tts-service:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.tts
    image: ${ECR_REGISTRY:-localhost}/tts-service:${TTS_VERSION:-1.0.0}
    container_name: tts-service
    hostname: tts-service
    ports:
      - "5001:5001"
    networks:
      - learner-lab-network
    environment:
      KAFKA_BOOTSTRAP_SERVERS: "10.0.30.111:9092,10.0.30.53:9092,10.0.31.72:9092"
      ZOOKEEPER_HOSTS: "10.0.31.247:2181,10.0.30.226:2181,10.0.30.186:2181"
      PORT: 5001

  stt-service:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.stt
    image: ${ECR_REGISTRY:-localhost}/stt-service:${STT_VERSION:-1.0.0}
    container_name: stt-service
    hostname: stt-service
    ports:
      - "5002:5002"
    networks:
      - learner-lab-network
    environment:
      KAFKA_BOOTSTRAP_SERVERS: "10.0.30.111:9092,10.0.30.53:9092,10.0.31.72:9092"
      ZOOKEEPER_HOSTS: "10.0.31.247:2181,10.0.30.226:2181,10.0.30.186:2181"
      PORT: 5002

  chat-service:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.chat
    image: ${ECR_REGISTRY:-localhost}/chat-service:${CHAT_VERSION:-1.0.0}
    container_name: chat-service
    hostname: chat-service
    ports:
      - "5003:5003"
    networks:
      - learner-lab-network
    environment:
      DB_HOST: chat-db
      DB_PORT: 5432
      DB_NAME: chat_db
      DB_USER: ${CHAT_DB_USER:?CHAT_DB_USER is required}
      DB_PASSWORD: ${CHAT_DB_PASSWORD:?CHAT_DB_PASSWORD is required}
      KAFKA_BOOTSTRAP_SERVERS: "10.0.30.111:9092,10.0.30.53:9092,10.0.31.72:9092"
      ZOOKEEPER_HOSTS: "10.0.31.247:2181,10.0.30.226:2181,10.0.30.186:2181"
      PORT: 5003

  document-service:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.document
    image: ${ECR_REGISTRY:-localhost}/document-service:${DOCUMENT_VERSION:-1.0.0}
    container_name: document-service
    hostname: document-service
    ports:
      - "5004:5004"
    networks:
      - learner-lab-network
    environment:
      DB_HOST: document-db
      DB_PORT: 5432
      DB_NAME: document_db
      DB_USER: ${DOCUMENT_DB_USER:?DOCUMENT_DB_USER is required}
      DB_PASSWORD: ${DOCUMENT_DB_PASSWORD:?DOCUMENT_DB_PASSWORD is required}
      KAFKA_BOOTSTRAP_SERVERS: "10.0.30.111:9092,10.0.30.53:9092,10.0.31.72:9092"
      ZOOKEEPER_HOSTS: "10.0.31.247:2181,10.0.30.226:2181,10.0.30.186:2181"
      PORT: 5004

  quiz-service:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.quiz
    image: ${ECR_REGISTRY:-localhost}/quiz-service:${QUIZ_VERSION:-1.0.0}
    container_name: quiz-service
    hostname: quiz-service
    ports:
      - "5005:5005"
    networks:
      - learner-lab-network
    environment:
      DB_HOST: quiz-db
      DB_PORT: 5432
      DB_NAME: quiz_db
      DB_USER: ${QUIZ_DB_USER:?QUIZ_DB_USER is required}
      DB_PASSWORD: ${QUIZ_DB_PASSWORD:?QUIZ_DB_PASSWORD is required}
      KAFKA_BOOTSTRAP_SERVERS: "10.0.30.111:9092,10.0.30.53:9092,10.0.31.72:9092"
      ZOOKEEPER_HOSTS: "10.0.31.247:2181,10.0.30.226:2181,10.0.30.186:2181"
      PORT: 5005

  api-gateway:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.gateway
    image: ${ECR_REGISTRY:-localhost}/api-gateway:${GATEWAY_VERSION:-1.0.0}
    container_name: api-gateway
    hostname: api-gateway
    ports:
      - "5000:5000"
    networks:
      - learner-lab-network
    environment:
      TTS_SERVICE_URL: http://tts-service:5001
      STT_SERVICE_URL: http://stt-service:5002
      CHAT_SERVICE_URL: http://chat-service:5003
      DOCUMENT_SERVICE_URL: http://document-service:5004
      QUIZ_SERVICE_URL: http://quiz-service:5005
      PORT: 5000

# --------------------------
# Volumes
# --------------------------
volumes:
  chat-db-data:
  document-db-data:
  quiz-db-data:
  redis-data:

# --------------------------
# Networks
# --------------------------
networks:
  learner-lab-network:
    external: true
