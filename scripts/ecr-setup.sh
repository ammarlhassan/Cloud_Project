#!/bin/bash
# =============================================================================
# ECR Setup and Vulnerability Scanning Script
# CSE363 Phase 2 - Container Registry Configuration
# =============================================================================
# This script handles:
# 1. ECR Repository creation with lifecycle policies
# 2. Image vulnerability scanning configuration
# 3. Image push to ECR
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="learner-lab"

# Service names
SERVICES=(
    "api-gateway"
    "tts-service"
    "stt-service"
    "chat-service"
    "document-service"
    "quiz-service"
)

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or expired."
        log_info "For Learner Lab: Get credentials from AWS Details > Show"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# -----------------------------------------------------------------------------
# Get AWS Account ID
# -----------------------------------------------------------------------------
get_account_id() {
    aws sts get-caller-identity --query Account --output text
}

# -----------------------------------------------------------------------------
# Create ECR Repository with Scanning Enabled
# -----------------------------------------------------------------------------
create_ecr_repository() {
    local repo_name="$1"
    local full_name="${PROJECT_NAME}/${repo_name}"
    
    log_info "Creating ECR repository: ${full_name}"
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names "${full_name}" --region "${AWS_REGION}" &> /dev/null; then
        log_warn "Repository ${full_name} already exists"
        return 0
    fi
    
    # Create repository with image scanning enabled
    aws ecr create-repository \
        --repository-name "${full_name}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --image-tag-mutability MUTABLE \
        --encryption-configuration encryptionType=AES256
    
    log_success "Created repository: ${full_name}"
}

# -----------------------------------------------------------------------------
# Set ECR Lifecycle Policy
# -----------------------------------------------------------------------------
# This policy:
# - Keeps only the last 10 tagged images
# - Removes untagged images after 1 day
# - Helps manage storage costs and remove vulnerable old images
# -----------------------------------------------------------------------------
set_lifecycle_policy() {
    local repo_name="$1"
    local full_name="${PROJECT_NAME}/${repo_name}"
    
    log_info "Setting lifecycle policy for: ${full_name}"
    
    local policy=$(cat <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Remove untagged images after 1 day",
            "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        },
        {
            "rulePriority": 2,
            "description": "Keep only last 10 tagged images",
            "selection": {
                "tagStatus": "tagged",
                "tagPrefixList": ["v", "1.", "2.", "latest"],
                "countType": "imageCountMoreThan",
                "countNumber": 10
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
)
    
    aws ecr put-lifecycle-policy \
        --repository-name "${full_name}" \
        --region "${AWS_REGION}" \
        --lifecycle-policy-text "${policy}"
    
    log_success "Lifecycle policy set for: ${full_name}"
}

# -----------------------------------------------------------------------------
# Get Vulnerability Scan Results
# -----------------------------------------------------------------------------
get_scan_results() {
    local repo_name="$1"
    local image_tag="${2:-latest}"
    local full_name="${PROJECT_NAME}/${repo_name}"
    
    log_info "Getting vulnerability scan results for: ${full_name}:${image_tag}"
    
    # Wait for scan to complete (max 5 minutes)
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local status=$(aws ecr describe-image-scan-findings \
            --repository-name "${full_name}" \
            --image-id imageTag="${image_tag}" \
            --region "${AWS_REGION}" \
            --query 'imageScanStatus.status' \
            --output text 2>/dev/null || echo "PENDING")
        
        if [ "$status" = "COMPLETE" ]; then
            break
        elif [ "$status" = "FAILED" ]; then
            log_error "Scan failed for ${full_name}:${image_tag}"
            return 1
        fi
        
        log_info "Scan status: ${status}. Waiting..."
        sleep 10
        ((attempt++))
    done
    
    # Get scan findings
    aws ecr describe-image-scan-findings \
        --repository-name "${full_name}" \
        --image-id imageTag="${image_tag}" \
        --region "${AWS_REGION}" \
        --query 'imageScanFindings.findingSeverityCounts' \
        --output table
}

# -----------------------------------------------------------------------------
# Build and Push Image to ECR
# -----------------------------------------------------------------------------
build_and_push() {
    local service_name="$1"
    local version="${2:-1.0.0}"
    local account_id=$(get_account_id)
    local ecr_registry="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    local full_name="${PROJECT_NAME}/${service_name}"
    local image_uri="${ecr_registry}/${full_name}:${version}"
    
    log_info "Building and pushing: ${image_uri}"
    
    # Login to ECR
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${ecr_registry}"
    
    # Map service name to Dockerfile
    local dockerfile="docker/dockerfiles/Dockerfile.${service_name//-service/}"
    if [ "$service_name" = "api-gateway" ]; then
        dockerfile="docker/dockerfiles/Dockerfile.gateway"
    fi
    
    # Build image
    docker build \
        -f "${dockerfile}" \
        --build-arg VERSION="${version}" \
        -t "${image_uri}" \
        -t "${ecr_registry}/${full_name}:latest" \
        .
    
    # Push image (triggers scan)
    docker push "${image_uri}"
    docker push "${ecr_registry}/${full_name}:latest"
    
    log_success "Pushed: ${image_uri}"
    
    # Get scan results
    log_info "Waiting for vulnerability scan..."
    sleep 5
    get_scan_results "${service_name}" "${version}"
}

# -----------------------------------------------------------------------------
# Local Vulnerability Scanning with Trivy
# -----------------------------------------------------------------------------
local_scan_with_trivy() {
    local image_name="$1"
    
    if ! command -v trivy &> /dev/null; then
        log_warn "Trivy not installed. Install with: brew install trivy"
        log_info "Skipping local scan..."
        return 0
    fi
    
    log_info "Running Trivy scan on: ${image_name}"
    
    trivy image \
        --severity HIGH,CRITICAL \
        --exit-code 1 \
        --no-progress \
        "${image_name}" || {
        log_warn "Vulnerabilities found in ${image_name}"
        return 1
    }
    
    log_success "No HIGH/CRITICAL vulnerabilities in ${image_name}"
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
    local action="${1:-setup}"
    
    check_prerequisites
    
    case "$action" in
        setup)
            log_info "Setting up ECR repositories..."
            for service in "${SERVICES[@]}"; do
                create_ecr_repository "$service"
                set_lifecycle_policy "$service"
            done
            log_success "ECR setup complete!"
            
            local account_id=$(get_account_id)
            echo ""
            log_info "Add to your .env file:"
            echo "ECR_REGISTRY=${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}"
            ;;
        
        push)
            local service="${2:-}"
            local version="${3:-1.0.0}"
            
            if [ -z "$service" ]; then
                log_info "Pushing all services..."
                for svc in "${SERVICES[@]}"; do
                    build_and_push "$svc" "$version"
                done
            else
                build_and_push "$service" "$version"
            fi
            ;;
        
        scan)
            local service="${2:-}"
            local version="${3:-latest}"
            
            if [ -z "$service" ]; then
                log_info "Scanning all services..."
                for svc in "${SERVICES[@]}"; do
                    get_scan_results "$svc" "$version"
                done
            else
                get_scan_results "$service" "$version"
            fi
            ;;
        
        local-scan)
            local image="${2:-}"
            if [ -z "$image" ]; then
                log_error "Usage: $0 local-scan <image-name>"
                exit 1
            fi
            local_scan_with_trivy "$image"
            ;;
        
        *)
            echo "Usage: $0 {setup|push|scan|local-scan}"
            echo ""
            echo "Commands:"
            echo "  setup              Create ECR repositories with scanning enabled"
            echo "  push [service]     Build and push image(s) to ECR"
            echo "  scan [service]     Get vulnerability scan results from ECR"
            echo "  local-scan <image> Run local Trivy scan on an image"
            exit 1
            ;;
    esac
}

main "$@"
