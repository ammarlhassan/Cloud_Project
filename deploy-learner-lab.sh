#!/bin/bash
################################################################################
# AWS Learner Lab - Simplified Kafka Deployment Script
# Deploys single-node Kafka + Zookeeper for learning purposes
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo "=========================================="
echo "  AWS Learner Lab - Kafka Deployment"
echo "=========================================="
echo ""

################################################################################
# Step 1: Check Prerequisites
################################################################################

log_step "Step 1: Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install it first."
    exit 1
fi

# Test AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured."
    log_info "Please configure AWS CLI with Learner Lab credentials:"
    echo ""
    echo "  aws configure set aws_access_key_id <your-key>"
    echo "  aws configure set aws_secret_access_key <your-secret>"
    echo "  aws configure set aws_session_token <your-token>"
    echo "  aws configure set region us-east-1"
    echo ""
    exit 1
fi

log_info "✓ AWS CLI configured"

################################################################################
# Step 2: Get Default VPC and Subnet
################################################################################

log_step "Step 2: Getting default VPC and subnet..."

VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text 2>/dev/null || echo "")

if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
    log_error "No default VPC found. Learner Lab environment may not be ready."
    exit 1
fi

log_info "✓ Default VPC: $VPC_ID"

SUBNET_ID=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0].SubnetId' \
  --output text 2>/dev/null || echo "")

if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" == "None" ]; then
    log_error "No subnet found in default VPC."
    exit 1
fi

log_info "✓ Default Subnet: $SUBNET_ID"

################################################################################
# Step 3: Create Security Group
################################################################################

log_step "Step 3: Creating security group..."

# Check if security group already exists
EXISTING_SG=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=kafka-learner-lab" \
  --query 'SecurityGroups[0].GroupId' \
  --output text 2>/dev/null || echo "None")

if [ "$EXISTING_SG" != "None" ]; then
    log_warn "Security group 'kafka-learner-lab' already exists: $EXISTING_SG"
    log_warn "Deleting existing security group..."
    aws ec2 delete-security-group --group-id $EXISTING_SG 2>/dev/null || true
    sleep 2
fi

KAFKA_SG_ID=$(aws ec2 create-security-group \
  --group-name kafka-learner-lab \
  --description "Kafka security group for learner lab" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId')

log_info "✓ Security Group Created: $KAFKA_SG_ID"

# Add ingress rules
log_info "Adding security group rules..."

aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0 &>/dev/null

aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 9092 --cidr 0.0.0.0/0 &>/dev/null

aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 2181 --cidr 0.0.0.0/0 &>/dev/null

aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol all --source-group $KAFKA_SG_ID &>/dev/null

log_info "✓ Security group rules added"

################################################################################
# Step 4: Create or Use Key Pair
################################################################################

log_step "Step 4: Setting up SSH key pair..."

if [ -f "learner-lab-key.pem" ]; then
    log_warn "Key pair file already exists: learner-lab-key.pem"
    read -p "Do you want to use the existing key? (y/n): " use_existing
    if [ "$use_existing" != "y" ]; then
        log_info "Creating new key pair..."
        rm -f learner-lab-key.pem
        aws ec2 delete-key-pair --key-name learner-lab-key 2>/dev/null || true
        aws ec2 create-key-pair \
          --key-name learner-lab-key \
          --query 'KeyMaterial' \
          --output text > learner-lab-key.pem
        chmod 400 learner-lab-key.pem
    fi
else
    aws ec2 create-key-pair \
      --key-name learner-lab-key \
      --query 'KeyMaterial' \
      --output text > learner-lab-key.pem
    chmod 400 learner-lab-key.pem
fi

log_info "✓ SSH key ready: learner-lab-key.pem"

################################################################################
# Step 5: Get AMI ID
################################################################################

log_step "Step 5: Finding latest Amazon Linux 2023 AMI..."

AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text)

log_info "✓ Using AMI: $AMI_ID"

################################################################################
# Step 6: Launch Kafka Instance
################################################################################

log_step "Step 6: Launching Kafka EC2 instance..."

# Create user data script
cat > /tmp/kafka-userdata.sh <<'EOF'
#!/bin/bash
set -euo pipefail

exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting Kafka installation..."

# Update system
yum update -y
yum install -y java-17-amazon-corretto wget docker

# Start Docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Download Kafka
cd /opt
wget -q https://archive.apache.org/dist/kafka/3.6.1/kafka_2.13-3.6.1.tgz
tar -xzf kafka_2.13-3.6.1.tgz
ln -s kafka_2.13-3.6.1 kafka

# Create directories
mkdir -p /var/kafka-logs
mkdir -p /var/zookeeper-data

# Configure Zookeeper
cat > /opt/kafka/config/zookeeper.properties <<'ZKCFG'
dataDir=/var/zookeeper-data
clientPort=2181
maxClientCnxns=0
admin.enableServer=true
tickTime=2000
initLimit=10
syncLimit=5
ZKCFG

# Configure Kafka
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

cat > /opt/kafka/config/server.properties <<KAFKACFG
broker.id=1
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://${PRIVATE_IP}:9092
log.dirs=/var/kafka-logs
num.partitions=3
default.replication.factor=1
min.insync.replicas=1
log.retention.hours=168
zookeeper.connect=localhost:2181
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
compression.type=snappy
KAFKACFG

# Create systemd service for Zookeeper
cat > /etc/systemd/system/zookeeper.service <<'ZKSVC'
[Unit]
Description=Apache Zookeeper
After=network.target

[Service]
Type=simple
User=root
Environment="JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto"
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
ZKSVC

# Create systemd service for Kafka
cat > /etc/systemd/system/kafka.service <<'KAFKASVC'
[Unit]
Description=Apache Kafka
After=network.target zookeeper.service
Requires=zookeeper.service

[Service]
Type=simple
User=root
Environment="JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto"
Environment="KAFKA_HEAP_OPTS=-Xmx1G -Xms1G"
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
KAFKASVC

# Start services
systemctl daemon-reload
systemctl enable zookeeper kafka
systemctl start zookeeper

echo "Waiting for Zookeeper to start..."
sleep 15

systemctl start kafka

echo "Waiting for Kafka to start..."
sleep 30

# Create topics
echo "Creating Kafka topics..."

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic document.uploaded --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic document.processed --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic notes.generated --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic quiz.requested --partitions 3 --replication-factor 1 \
  --config retention.ms=259200000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic quiz.generated --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.transcription.requested --partitions 3 --replication-factor 1 \
  --config retention.ms=259200000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.transcription.completed --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.generation.requested --partitions 3 --replication-factor 1 \
  --config retention.ms=259200000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.generation.completed --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic chat.message --partitions 3 --replication-factor 1 \
  --config retention.ms=2592000000 --if-not-exists

echo "Kafka and Zookeeper setup complete!"
echo "Instance IP: ${PRIVATE_IP}"

# Create helpful aliases
cat >> /home/ec2-user/.bashrc <<'ALIASES'
alias kafka-topics='kafka-topics.sh --bootstrap-server localhost:9092'
alias kafka-producer='kafka-console-producer.sh --bootstrap-server localhost:9092'
alias kafka-consumer='kafka-console-consumer.sh --bootstrap-server localhost:9092'
ALIASES

EOF

# Launch instance
log_info "Launching EC2 instance (this may take a moment)..."

KAFKA_INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name learner-lab-key \
  --security-group-ids $KAFKA_SG_ID \
  --subnet-id $SUBNET_ID \
  --user-data file:///tmp/kafka-userdata.sh \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp2}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=kafka-learner-lab},{Key=Project,Value=CloudLearningPlatform}]' \
  --output text --query 'Instances[0].InstanceId')

log_info "✓ Instance launched: $KAFKA_INSTANCE_ID"

# Wait for instance to be running
log_info "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $KAFKA_INSTANCE_ID

# Get instance details
KAFKA_PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $KAFKA_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

KAFKA_PRIVATE_IP=$(aws ec2 describe-instances \
  --instance-ids $KAFKA_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

################################################################################
# Step 7: Create S3 Buckets
################################################################################

log_step "Step 7: Creating S3 buckets..."

BUCKETS=(
  "tts-service-storage-learnerlab"
  "stt-service-storage-learnerlab"
  "chat-service-storage-learnerlab"
  "document-reader-storage-learnerlab"
  "quiz-service-storage-learnerlab"
)

for bucket in "${BUCKETS[@]}"; do
  if aws s3 ls "s3://$bucket" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$bucket" --region us-east-1
    log_info "✓ Created bucket: $bucket"
  else
    log_warn "Bucket already exists: $bucket"
  fi
done

################################################################################
# Step 8: Save Configuration
################################################################################

log_step "Step 8: Saving configuration..."

cat > kafka-config.env <<EOF
# Kafka Configuration for Learner Lab
# Generated: $(date)

KAFKA_INSTANCE_ID=$KAFKA_INSTANCE_ID
KAFKA_PUBLIC_IP=$KAFKA_PUBLIC_IP
KAFKA_PRIVATE_IP=$KAFKA_PRIVATE_IP
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_PRIVATE_IP}:9092
ZOOKEEPER_CONNECT=${KAFKA_PRIVATE_IP}:2181

# S3 Buckets
S3_TTS_BUCKET=tts-service-storage-learnerlab
S3_STT_BUCKET=stt-service-storage-learnerlab
S3_CHAT_BUCKET=chat-service-storage-learnerlab
S3_DOCUMENT_BUCKET=document-reader-storage-learnerlab
S3_QUIZ_BUCKET=quiz-service-storage-learnerlab

# AWS Configuration
AWS_REGION=us-east-1
VPC_ID=$VPC_ID
SUBNET_ID=$SUBNET_ID
SECURITY_GROUP_ID=$KAFKA_SG_ID
EOF

log_info "✓ Configuration saved to: kafka-config.env"

################################################################################
# Deployment Complete
################################################################################

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Instance Details:"
echo "  Instance ID:  $KAFKA_INSTANCE_ID"
echo "  Public IP:    $KAFKA_PUBLIC_IP"
echo "  Private IP:   $KAFKA_PRIVATE_IP"
echo ""
echo "Next Steps:"
echo ""
echo "1. Wait 5-10 minutes for Kafka to fully start"
echo ""
echo "2. SSH into the instance:"
echo "   ssh -i learner-lab-key.pem ec2-user@$KAFKA_PUBLIC_IP"
echo ""
echo "3. Check Kafka status:"
echo "   sudo systemctl status kafka"
echo "   sudo systemctl status zookeeper"
echo ""
echo "4. List topics:"
echo "   /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092"
echo ""
echo "5. Test producer/consumer:"
echo "   echo 'test' | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic test"
echo "   /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test --from-beginning"
echo ""
echo "Configuration file: kafka-config.env"
echo "SSH Key: learner-lab-key.pem"
echo ""
echo "=========================================="
