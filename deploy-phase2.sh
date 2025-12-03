#!/bin/bash

##############################################################################
# Phase 2 Deployment Script for AI Learner Platform
# This script automates the deployment process
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main deployment function
main() {
    print_header "AI Learner Platform - Phase 2 Deployment"
    
    # Step 1: Check prerequisites
    print_info "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_info "✓ Docker and Docker Compose are installed"
    
    # Step 2: Check environment file
    print_info "Checking environment configuration..."
    
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your AWS credentials before continuing."
            print_warning "Run: nano .env"
            exit 1
        else
            print_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi
    
    # Check if AWS credentials are set
    if grep -q "your_access_key_here" .env; then
        print_error "AWS credentials not configured in .env file."
        print_error "Please update .env with your AWS Academy Learner Lab credentials."
        exit 1
    fi
    
    print_info "✓ Environment file configured"
    
    # Step 3: Check AWS connectivity (optional)
    print_info "Checking AWS connectivity..."
    source .env
    
    if command_exists aws; then
        if aws s3 ls > /dev/null 2>&1; then
            print_info "✓ AWS credentials valid"
        else
            print_warning "AWS credentials may be invalid or expired"
            print_warning "Please verify your AWS Academy session is active"
        fi
    else
        print_warning "AWS CLI not installed - skipping AWS connectivity check"
    fi
    
    # Step 4: Stop existing containers
    print_info "Stopping existing containers (if any)..."
    docker-compose -f docker-compose.learner-lab.yml down || true
    print_info "✓ Existing containers stopped"
    
    # Step 5: Build services
    print_header "Building Services"
    print_info "This may take several minutes..."
    
    docker-compose -f docker-compose.learner-lab.yml build --parallel
    
    if [ $? -eq 0 ]; then
        print_info "✓ All services built successfully"
    else
        print_error "Build failed. Please check the error messages above."
        exit 1
    fi
    
    # Step 6: Start infrastructure services
    print_header "Starting Infrastructure Services"
    print_info "Starting Zookeeper and Kafka..."
    
    docker-compose -f docker-compose.learner-lab.yml up -d zookeeper kafka
    
    print_info "Waiting for Kafka to be ready (30 seconds)..."
    sleep 30
    
    # Step 7: Start database services
    print_info "Starting PostgreSQL databases..."
    docker-compose -f docker-compose.learner-lab.yml up -d chat-db document-db quiz-db redis
    
    print_info "Waiting for databases to be ready (15 seconds)..."
    sleep 15
    
    # Step 8: Start microservices
    print_header "Starting Microservices"
    docker-compose -f docker-compose.learner-lab.yml up -d tts-service stt-service chat-service document-service quiz-service
    
    print_info "Waiting for microservices to be ready (20 seconds)..."
    sleep 20
    
    # Step 9: Start API Gateway
    print_info "Starting API Gateway..."
    docker-compose -f docker-compose.learner-lab.yml up -d api-gateway
    
    print_info "Waiting for API Gateway to be ready (10 seconds)..."
    sleep 10
    
    # Step 10: Health checks
    print_header "Running Health Checks"
    
    services=("api-gateway:5000" "tts-service:5001" "stt-service:5002" "chat-service:5003" "document-service:5004" "quiz-service:5005")
    
    all_healthy=true
    for service in "${services[@]}"; do
        service_name="${service%%:*}"
        port="${service##*:}"
        
        if curl -s -f "http://localhost:$port/health" > /dev/null; then
            print_info "✓ $service_name is healthy"
        else
            print_error "✗ $service_name is not responding"
            all_healthy=false
        fi
    done
    
    # Step 11: Display summary
    print_header "Deployment Summary"
    
    if [ "$all_healthy" = true ]; then
        print_info "✓ All services deployed successfully!"
        echo ""
        echo "Service URLs:"
        echo "  API Gateway:    http://localhost:5000"
        echo "  TTS Service:    http://localhost:5001"
        echo "  STT Service:    http://localhost:5002"
        echo "  Chat Service:   http://localhost:5003"
        echo "  Document Service: http://localhost:5004"
        echo "  Quiz Service:   http://localhost:5005"
        echo ""
        echo "Kafka:           localhost:9092"
        echo "PostgreSQL Chat: localhost:5432"
        echo "PostgreSQL Doc:  localhost:5433"
        echo "PostgreSQL Quiz: localhost:5434"
        echo "Redis:           localhost:6379"
        echo ""
        echo "Next Steps:"
        echo "1. Test API Gateway: curl http://localhost:5000/health"
        echo "2. Get JWT token: curl -X POST http://localhost:5000/api/v1/auth/login \\"
        echo "     -H 'Content-Type: application/json' \\"
        echo "     -d '{\"email\":\"user@example.com\",\"password\":\"password\"}'"
        echo "3. View logs: docker-compose -f docker-compose.learner-lab.yml logs -f"
        echo "4. Check status: docker-compose -f docker-compose.learner-lab.yml ps"
        echo ""
        echo "For more information, see README-PHASE2.md"
    else
        print_error "Some services failed health checks. Please check logs:"
        echo ""
        echo "View all logs:"
        echo "  docker-compose -f docker-compose.learner-lab.yml logs"
        echo ""
        echo "View specific service:"
        echo "  docker-compose -f docker-compose.learner-lab.yml logs <service-name>"
        echo ""
        echo "Check service status:"
        echo "  docker-compose -f docker-compose.learner-lab.yml ps"
        exit 1
    fi
}

# Display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -r, --rebuild  Rebuild images from scratch (no cache)"
    echo "  -d, --down     Stop and remove all containers"
    echo "  -l, --logs     Show logs after deployment"
    echo ""
    exit 0
}

# Parse arguments
REBUILD=false
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -r|--rebuild)
            print_info "Rebuild mode enabled"
            REBUILD=true
            shift
            ;;
        -d|--down)
            print_info "Stopping all services..."
            docker-compose -f docker-compose.learner-lab.yml down -v
            print_info "All services stopped and volumes removed"
            exit 0
            ;;
        -l|--logs)
            SHOW_LOGS=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Run main deployment
main

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    print_info "Showing logs (Ctrl+C to exit)..."
    docker-compose -f docker-compose.learner-lab.yml logs -f
fi
