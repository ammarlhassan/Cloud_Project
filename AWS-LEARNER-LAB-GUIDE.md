# AWS Learner Lab Deployment Guide

## ⚠️ AWS Learner Lab Limitations & Adaptations

AWS Learner Lab has **significant restrictions** compared to a full AWS account. This guide adapts the Phase 2 implementation to work within these constraints.

---

## 🔒 Known Learner Lab Limitations

### 1. **IAM Restrictions**
- ❌ **Cannot create IAM users, roles, or policies**
- ❌ Cannot use AWS Secrets Manager
- ❌ Cannot create custom IAM instance profiles
- ✅ **Solution**: Use lab-provided `LabRole` for all EC2 instances
- ✅ **Solution**: Store credentials in environment variables (not ideal, but necessary)

### 2. **VPC & Networking Restrictions**
- ❌ **Cannot create VPCs** (must use default VPC)
- ❌ Cannot create Internet Gateways
- ❌ Cannot create NAT Gateways
- ✅ **Solution**: Use the default VPC provided by the lab
- ✅ **Solution**: Deploy in default subnets (typically public subnets)

### 3. **Load Balancer Restrictions**
- ❌ **Cannot create Application Load Balancers (ALB)**
- ❌ **Cannot create Network Load Balancers (NLB)**
- ✅ **Solution**: Use direct instance IPs or a simple DNS round-robin
- ✅ **Solution**: Or deploy a lightweight nginx proxy on one instance

### 4. **Route53 Restrictions**
- ❌ **Cannot create hosted zones**
- ❌ Cannot create DNS records
- ✅ **Solution**: Use `/etc/hosts` file or hardcode IPs
- ✅ **Solution**: Use EC2 private DNS names

### 5. **Service Quotas**
- ⚠️ **Limited EC2 instances** (typically 5-10 instances max)
- ⚠️ **Limited EBS volumes** (typically 10-20 GB total)
- ⚠️ **Instance types restricted** (usually only t2.micro, t2.small, t3.micro available)
- ✅ **Solution**: Deploy smaller cluster (1 Kafka, 1 Zookeeper instead of 3 each)

### 6. **RDS Restrictions**
- ❌ **Cannot create RDS instances** in most Learner Labs
- ✅ **Solution**: Install PostgreSQL directly on EC2 instances
- ✅ **Solution**: Use containerized PostgreSQL

### 7. **ECR Restrictions**
- ❌ **Cannot create ECR repositories**
- ✅ **Solution**: Use Docker Hub for public images
- ✅ **Solution**: Build and run images locally on EC2

### 8. **EKS/ECS Restrictions**
- ❌ **Cannot use EKS (Kubernetes managed service)**
- ❌ Cannot use ECS (Container orchestration)
- ✅ **Solution**: Install Kubernetes manually (k3s, microk8s)
- ✅ **Solution**: Use Docker Compose on EC2

### 9. **Session Time Limits**
- ⚠️ **Lab sessions expire after 4 hours**
- ⚠️ Resources may be deleted when session ends
- ✅ **Solution**: Use infrastructure-as-code for quick re-deployment
- ✅ **Solution**: Take snapshots frequently

### 10. **Budget Restrictions**
- ⚠️ **Limited budget credits** ($50-100 typically)
- ✅ **Solution**: Use smallest instance types
- ✅ **Solution**: Stop instances when not in use

---

## 📋 Adapted Architecture for Learner Lab

### Original Design (Full AWS)
```
3 Kafka Brokers (t3.medium) + 3 Zookeepers (t3.small)
Network Load Balancer
Route53 DNS
Custom VPC with multiple subnets
IAM roles per service
RDS instances
ECR registry
```

### **Learner Lab Adapted Design** ✅
```
1 Kafka Broker (t3.micro/t2.small) + 1 Zookeeper (t3.micro)
OR: All-in-one instance (Kafka + Zookeeper + microservices)
Direct IP access (no load balancer)
Default VPC with default subnets
LabRole for all instances
PostgreSQL on EC2 or in containers
Docker Hub for images
```

---

## 🏗️ Recommended Learner Lab Architecture

### **Option 1: Minimal Cluster (Recommended for Learning)**

```
┌─────────────────────────────────────────────────────────────┐
│                     Default VPC                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  EC2 Instance 1: Kafka + Zookeeper                     │ │
│  │  - Type: t3.small or t2.medium (if available)          │ │
│  │  - Private IP: 172.31.x.x                              │ │
│  │  - Kafka Port: 9092                                     │ │
│  │  - Zookeeper Port: 2181                                 │ │
│  │  - Storage: 20 GB GP2                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  EC2 Instance 2: Microservices                         │ │
│  │  - Type: t3.medium or t2.medium                        │ │
│  │  - Docker Compose running:                             │ │
│  │    * API Gateway                                        │ │
│  │    * TTS Service                                        │ │
│  │    * STT Service                                        │ │
│  │    * Chat Service                                       │ │
│  │    * Document Reader Service                            │ │
│  │    * Quiz Service                                       │ │
│  │    * PostgreSQL (containerized)                         │ │
│  │    * Redis (containerized)                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Instance Count**: 2
**Estimated Cost**: $0.05-0.10/hour (~$4-8/month if run 24/7)

### **Option 2: All-in-One (Maximum Learning Lab Compatibility)**

```
┌─────────────────────────────────────────────────────────────┐
│                     Default VPC                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  EC2 Instance: All-in-One Server                       │ │
│  │  - Type: t3.medium (2 vCPU, 4 GB RAM)                  │ │
│  │  - Storage: 30 GB GP2                                   │ │
│  │                                                         │ │
│  │  Running:                                               │ │
│  │  ├── Kafka (single broker)                             │ │
│  │  ├── Zookeeper (single node)                           │ │
│  │  ├── Docker Compose:                                    │ │
│  │  │   ├── API Gateway                                    │ │
│  │  │   ├── 5 Microservices                                │ │
│  │  │   ├── PostgreSQL                                     │ │
│  │  │   └── Redis                                          │ │
│  │  └── Nginx (reverse proxy)                             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Instance Count**: 1
**Estimated Cost**: $0.04-0.06/hour (~$3-5/month if run 24/7)

---

## 🚀 Learner Lab Deployment Steps

### Step 1: Start AWS Learner Lab Session

```bash
# 1. Login to AWS Learner Lab
# 2. Click "Start Lab" button
# 3. Wait for AWS status to turn green
# 4. Click "AWS" to open console
# 5. Download credentials (AWS CLI access)
```

### Step 2: Configure AWS CLI with Lab Credentials

```bash
# Download the credentials file from Learner Lab
# It will have format:
# aws_access_key_id=ASIA...
# aws_secret_access_key=...
# aws_session_token=...

# Configure AWS CLI
aws configure set aws_access_key_id <your-key>
aws configure set aws_secret_access_key <your-secret>
aws configure set aws_session_token <your-token>
aws configure set region us-east-1

# Verify
aws sts get-caller-identity
```

### Step 3: Check Available Resources

```bash
# Check available instance types
aws ec2 describe-instance-type-offerings \
  --region us-east-1 \
  --filters "Name=instance-type,Values=t2.*,t3.*" \
  --query 'InstanceTypeOfferings[*].InstanceType' \
  --output table

# Check default VPC
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true"

# Get default VPC ID
export VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

echo "Default VPC: $VPC_ID"

# Get default subnet
export SUBNET_ID=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0].SubnetId' \
  --output text)

echo "Default Subnet: $SUBNET_ID"
```

### Step 4: Create Security Groups

```bash
# Create security group for Kafka
KAFKA_SG_ID=$(aws ec2 create-security-group \
  --group-name kafka-learner-lab \
  --description "Kafka security group for learner lab" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId')

echo "Kafka SG: $KAFKA_SG_ID"

# Allow Kafka port from anywhere (simplification for lab)
aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 9092 --cidr 0.0.0.0/0

# Allow Zookeeper
aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 2181 --cidr 0.0.0.0/0

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# Allow all traffic within the security group
aws ec2 authorize-security-group-ingress \
  --group-id $KAFKA_SG_ID \
  --protocol all \
  --source-group $KAFKA_SG_ID

# Create security group for microservices
SERVICES_SG_ID=$(aws ec2 create-security-group \
  --group-name services-learner-lab \
  --description "Microservices security group" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId')

echo "Services SG: $SERVICES_SG_ID"

# Allow HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id $SERVICES_SG_ID \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SERVICES_SG_ID \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-id $SERVICES_SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# Allow all traffic within security group
aws ec2 authorize-security-group-ingress \
  --group-id $SERVICES_SG_ID \
  --protocol all \
  --source-group $SERVICES_SG_ID

# Allow traffic from Kafka SG
aws ec2 authorize-security-group-ingress \
  --group-id $SERVICES_SG_ID \
  --protocol all \
  --source-group $KAFKA_SG_ID
```

### Step 5: Create Key Pair

```bash
# Create SSH key pair
aws ec2 create-key-pair \
  --key-name learner-lab-key \
  --query 'KeyMaterial' \
  --output text > learner-lab-key.pem

# Set permissions
chmod 400 learner-lab-key.pem

echo "Key pair created: learner-lab-key.pem"
```

### Step 6: Launch Kafka Instance

```bash
# Get latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text)

echo "Using AMI: $AMI_ID"

# Create user data script for Kafka + Zookeeper
cat > kafka-userdata.sh <<'EOF'
#!/bin/bash
set -euo pipefail

# Update system
yum update -y
yum install -y java-17-amazon-corretto wget docker

# Start Docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Download Kafka
cd /opt
wget https://archive.apache.org/dist/kafka/3.6.1/kafka_2.13-3.6.1.tgz
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
ZKCFG

# Configure Kafka
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

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

[Install]
WantedBy=multi-user.target
KAFKASVC

# Start services
systemctl daemon-reload
systemctl enable zookeeper kafka
systemctl start zookeeper
sleep 10
systemctl start kafka

# Wait for Kafka to be ready
sleep 30

# Create topics
/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic document.uploaded --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic document.processed --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic notes.generated --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic quiz.requested --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic quiz.generated --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.transcription.requested --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.transcription.completed --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.generation.requested --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic audio.generation.completed --partitions 3 --replication-factor 1 --if-not-exists

/opt/kafka/bin/kafka-topics.sh --create --bootstrap-server localhost:9092 \
  --topic chat.message --partitions 3 --replication-factor 1 --if-not-exists

echo "Kafka and Zookeeper setup complete!"
EOF

# Launch EC2 instance
KAFKA_INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.small \
  --key-name learner-lab-key \
  --security-group-ids $KAFKA_SG_ID \
  --subnet-id $SUBNET_ID \
  --user-data file://kafka-userdata.sh \
  --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=20,VolumeType=gp2}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=kafka-learner-lab}]' \
  --output text --query 'Instances[0].InstanceId')

echo "Kafka instance launched: $KAFKA_INSTANCE_ID"

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $KAFKA_INSTANCE_ID

# Get instance public IP
KAFKA_PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $KAFKA_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

KAFKA_PRIVATE_IP=$(aws ec2 describe-instances \
  --instance-ids $KAFKA_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

echo "================================"
echo "Kafka Instance Ready!"
echo "Instance ID: $KAFKA_INSTANCE_ID"
echo "Public IP: $KAFKA_PUBLIC_IP"
echo "Private IP: $KAFKA_PRIVATE_IP"
echo "================================"
echo "Wait 5-10 minutes for Kafka to fully start"
echo "Then SSH: ssh -i learner-lab-key.pem ec2-user@$KAFKA_PUBLIC_IP"
echo "Check Kafka: sudo systemctl status kafka"
echo "List topics: /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092"
```

### Step 7: Verify Kafka Installation

```bash
# Wait 10 minutes, then SSH into instance
ssh -i learner-lab-key.pem ec2-user@$KAFKA_PUBLIC_IP

# On the instance:
sudo systemctl status zookeeper
sudo systemctl status kafka

# List topics
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Test producer
echo "test message" | /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic test

# Test consumer
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic test \
  --from-beginning
```

---

## 💡 Using S3 in Learner Lab

```bash
# S3 usually works in Learner Lab
# Create buckets
aws s3 mb s3://tts-service-storage-learnerlab
aws s3 mb s3://stt-service-storage-learnerlab
aws s3 mb s3://chat-service-storage-learnerlab
aws s3 mb s3://document-reader-storage-learnerlab
aws s3 mb s3://quiz-service-storage-learnerlab

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket tts-service-storage-learnerlab \
  --versioning-configuration Status=Enabled

# Test upload
echo "test" > test.txt
aws s3 cp test.txt s3://tts-service-storage-learnerlab/
aws s3 ls s3://tts-service-storage-learnerlab/
```

---

## ⚙️ Environment Variables for Services

Since we can't use Secrets Manager in Learner Lab:

```bash
# Create .env file
cat > .env <<EOF
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_PRIVATE_IP}:9092

# S3 Configuration (Learner Lab)
AWS_REGION=us-east-1
S3_TTS_BUCKET=tts-service-storage-learnerlab
S3_STT_BUCKET=stt-service-storage-learnerlab
S3_CHAT_BUCKET=chat-service-storage-learnerlab
S3_DOCUMENT_BUCKET=document-reader-storage-learnerlab
S3_QUIZ_BUCKET=quiz-service-storage-learnerlab

# Database Configuration (if using containerized PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=cloudlearning
POSTGRES_PASSWORD=changeme123

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Settings
ENVIRONMENT=learner-lab
LOG_LEVEL=INFO
EOF
```

---

## 📊 Cost Optimization Tips

1. **Stop instances when not in use**
   ```bash
   aws ec2 stop-instances --instance-ids $KAFKA_INSTANCE_ID
   aws ec2 start-instances --instance-ids $KAFKA_INSTANCE_ID
   ```

2. **Use smallest instance types**
   - t3.micro or t2.micro for testing
   - t3.small for Kafka

3. **Delete unused resources**
   ```bash
   # Delete S3 objects
   aws s3 rm s3://bucket-name --recursive

   # Terminate instances
   aws ec2 terminate-instances --instance-ids $INSTANCE_ID
   ```

4. **Monitor your budget**
   - Check Learner Lab credits regularly
   - Session expires after 4 hours

---

## 🔄 Quick Re-deployment Script

Save this for when your lab session expires:

```bash
#!/bin/bash
# redeploy-learner-lab.sh

# Re-configure AWS CLI with new session credentials
aws configure set aws_access_key_id <new-key>
aws configure set aws_secret_access_key <new-secret>
aws configure set aws_session_token <new-token>

# Get VPC and Subnet
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
export SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text)

# Recreate security groups and instances
# (Use scripts from Step 4 onwards)
```

---

## 📝 Summary: Learner Lab vs Production

| Feature | Production (Original) | Learner Lab (Adapted) |
|---------|----------------------|----------------------|
| Kafka Brokers | 3 nodes | 1 node |
| Zookeeper | 3 nodes | 1 node |
| Replication Factor | 2 | 1 |
| Instance Type | t3.medium | t3.small or t3.micro |
| Load Balancer | NLB | None (direct IP) |
| VPC | Custom multi-subnet | Default VPC |
| IAM | Custom roles | LabRole |
| RDS | Managed RDS | PostgreSQL on EC2/Docker |
| ECR | Private registry | Docker Hub |
| DNS | Route53 | Direct IP or /etc/hosts |
| Total Cost | $200+/month | $5-10/month |

---

## ✅ Next Steps

1. Deploy Kafka using the script above
2. Wait 10 minutes for full startup
3. Verify topics are created
4. Deploy microservices using Docker Compose
5. Connect services to Kafka using private IP
6. Test the complete workflow

---

**Remember**: Learner Lab sessions expire! Always use infrastructure-as-code scripts for quick re-deployment.
