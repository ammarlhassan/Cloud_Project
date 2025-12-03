#!/bin/bash
################################################################################
# Kafka Cluster Deployment Script
# Purpose: Deploy 3-node Kafka cluster + 3-node Zookeeper ensemble on AWS EC2
# Author: Cloud-Based Learning Platform Team
# Version: 1.0
################################################################################

set -euo pipefail

# Configuration
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-us-east-1}"
VPC_ID="vpc-xxxxxxxxx"  # Replace with actual VPC ID from Phase 1
KAFKA_SUBNET_1="subnet-xxxxxxxxx"  # 10.0.30.0/24 (us-east-1a)
KAFKA_SUBNET_2="subnet-yyyyyyyyy"  # 10.0.31.0/24 (us-east-1b)
KEY_PAIR_NAME="cloud-learning-platform-key"

# Kafka configuration
KAFKA_VERSION="3.6.1"
SCALA_VERSION="2.13"
KAFKA_INSTANCE_TYPE="t3.medium"
KAFKA_EBS_SIZE="100"
KAFKA_EBS_TYPE="gp3"

# Zookeeper configuration
ZK_INSTANCE_TYPE="t3.small"
ZK_EBS_SIZE="20"
ZK_EBS_TYPE="gp3"

# AMI ID (Amazon Linux 2023)
AMI_ID="ami-0c02fb55e34f31a28"  # Update for your region

# Security Group IDs (created in Phase 1)
KAFKA_SG_ID="sg-xxxxxxxxx"
ZK_SG_ID="sg-yyyyyyyyy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# Step 1: Create Security Groups
################################################################################

create_security_groups() {
    log_info "Creating security groups for Kafka and Zookeeper..."

    # Kafka Broker Security Group
    KAFKA_SG_ID=$(aws ec2 create-security-group \
        --group-name "kafka-broker-sg-${ENVIRONMENT}" \
        --description "Security group for Kafka brokers" \
        --vpc-id "$VPC_ID" \
        --region "$AWS_REGION" \
        --output text --query 'GroupId')

    log_info "Created Kafka SG: $KAFKA_SG_ID"

    # Kafka inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id "$KAFKA_SG_ID" \
        --ip-permissions \
            IpProtocol=tcp,FromPort=9092,ToPort=9092,IpRanges='[{CidrIp=10.0.10.0/24},{CidrIp=10.0.11.0/24}]' \
            IpProtocol=tcp,FromPort=9093,ToPort=9093,IpRanges='[{CidrIp=10.0.30.0/24},{CidrIp=10.0.31.0/24}]' \
            IpProtocol=tcp,FromPort=2181,ToPort=2181,IpRanges='[{CidrIp=10.0.30.0/24},{CidrIp=10.0.31.0/24}]' \
        --region "$AWS_REGION"

    # Zookeeper Security Group
    ZK_SG_ID=$(aws ec2 create-security-group \
        --group-name "zookeeper-sg-${ENVIRONMENT}" \
        --description "Security group for Zookeeper ensemble" \
        --vpc-id "$VPC_ID" \
        --region "$AWS_REGION" \
        --output text --query 'GroupId')

    log_info "Created Zookeeper SG: $ZK_SG_ID"

    # Zookeeper inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id "$ZK_SG_ID" \
        --ip-permissions \
            IpProtocol=tcp,FromPort=2181,ToPort=2181,IpRanges='[{CidrIp=10.0.30.0/24},{CidrIp=10.0.31.0/24}]' \
            IpProtocol=tcp,FromPort=2888,ToPort=2888,IpRanges='[{CidrIp=10.0.30.0/24},{CidrIp=10.0.31.0/24}]' \
            IpProtocol=tcp,FromPort=3888,ToPort=3888,IpRanges='[{CidrIp=10.0.30.0/24},{CidrIp=10.0.31.0/24}]' \
        --region "$AWS_REGION"

    log_info "Security groups created successfully"
}

################################################################################
# Step 2: Deploy Zookeeper Ensemble
################################################################################

deploy_zookeeper_node() {
    local NODE_ID=$1
    local SUBNET_ID=$2
    local PRIVATE_IP=$3

    log_info "Deploying Zookeeper node $NODE_ID..."

    # User data script for Zookeeper
    cat > "/tmp/zk-userdata-${NODE_ID}.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

# Update system
yum update -y
yum install -y java-17-amazon-corretto wget

# Download and install Zookeeper
cd /opt
wget https://archive.apache.org/dist/zookeeper/zookeeper-3.8.3/apache-zookeeper-3.8.3-bin.tar.gz
tar -xzf apache-zookeeper-3.8.3-bin.tar.gz
ln -s apache-zookeeper-3.8.3-bin zookeeper

# Create data directory
mkdir -p /var/zookeeper-data
chown -R ec2-user:ec2-user /var/zookeeper-data

# Configure Zookeeper
cat > /opt/zookeeper/conf/zoo.cfg <<ZKCFG
tickTime=2000
initLimit=10
syncLimit=5
dataDir=/var/zookeeper-data
clientPort=2181
maxClientCnxns=60
admin.enableServer=true
4lw.commands.whitelist=*

# Zookeeper ensemble
server.1=10.0.30.20:2888:3888
server.2=10.0.30.21:2888:3888
server.3=10.0.31.20:2888:3888
ZKCFG

# Set server ID
echo "__NODE_ID__" > /var/zookeeper-data/myid

# Create systemd service
cat > /etc/systemd/system/zookeeper.service <<ZKSVC
[Unit]
Description=Apache Zookeeper
After=network.target

[Service]
Type=forking
User=ec2-user
Environment="JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto"
ExecStart=/opt/zookeeper/bin/zkServer.sh start
ExecStop=/opt/zookeeper/bin/zkServer.sh stop
ExecReload=/opt/zookeeper/bin/zkServer.sh restart
Restart=on-failure

[Install]
WantedBy=multi-user.target
ZKSVC

# Start Zookeeper
systemctl daemon-reload
systemctl enable zookeeper
systemctl start zookeeper

# CloudWatch agent installation
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

EOF

    # Replace NODE_ID placeholder
    sed -i "s/__NODE_ID__/$NODE_ID/g" "/tmp/zk-userdata-${NODE_ID}.sh"

    # Launch EC2 instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --instance-type "$ZK_INSTANCE_TYPE" \
        --key-name "$KEY_PAIR_NAME" \
        --subnet-id "$SUBNET_ID" \
        --private-ip-address "$PRIVATE_IP" \
        --security-group-ids "$ZK_SG_ID" \
        --user-data "file:///tmp/zk-userdata-${NODE_ID}.sh" \
        --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":$ZK_EBS_SIZE,\"VolumeType\":\"$ZK_EBS_TYPE\",\"Encrypted\":true}}]" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=zookeeper-${NODE_ID}-${ENVIRONMENT}},{Key=Environment,Value=${ENVIRONMENT}},{Key=Service,Value=zookeeper}]" \
        --iam-instance-profile "Name=zookeeper-instance-profile" \
        --region "$AWS_REGION" \
        --output text --query 'Instances[0].InstanceId')

    log_info "Zookeeper node $NODE_ID launched: $INSTANCE_ID"
    echo "$INSTANCE_ID"
}

deploy_zookeeper_ensemble() {
    log_info "Deploying Zookeeper ensemble..."

    # Node 1: us-east-1a
    ZK1_ID=$(deploy_zookeeper_node "1" "$KAFKA_SUBNET_1" "10.0.30.20")

    # Node 2: us-east-1a
    ZK2_ID=$(deploy_zookeeper_node "2" "$KAFKA_SUBNET_1" "10.0.30.21")

    # Node 3: us-east-1b
    ZK3_ID=$(deploy_zookeeper_node "3" "$KAFKA_SUBNET_2" "10.0.31.20")

    log_info "Waiting for Zookeeper instances to be running..."
    aws ec2 wait instance-running --instance-ids "$ZK1_ID" "$ZK2_ID" "$ZK3_ID" --region "$AWS_REGION"

    log_info "Zookeeper ensemble deployed successfully"
}

################################################################################
# Step 3: Deploy Kafka Brokers
################################################################################

deploy_kafka_broker() {
    local BROKER_ID=$1
    local SUBNET_ID=$2
    local PRIVATE_IP=$3

    log_info "Deploying Kafka broker $BROKER_ID..."

    # User data script for Kafka
    cat > "/tmp/kafka-userdata-${BROKER_ID}.sh" <<'EOF'
#!/bin/bash
set -euo pipefail

# Update system
yum update -y
yum install -y java-17-amazon-corretto wget

# Download and install Kafka
cd /opt
wget https://archive.apache.org/dist/kafka/3.6.1/kafka_2.13-3.6.1.tgz
tar -xzf kafka_2.13-3.6.1.tgz
ln -s kafka_2.13-3.6.1 kafka

# Create log directory
mkdir -p /var/kafka-logs
chown -R ec2-user:ec2-user /var/kafka-logs

# Configure Kafka
cat > /opt/kafka/config/server.properties <<KAFKACFG
# Broker configuration
broker.id=__BROKER_ID__
listeners=PLAINTEXT://:9092,INTERNAL://:9093
advertised.listeners=PLAINTEXT://__PRIVATE_IP__:9092,INTERNAL://__PRIVATE_IP__:9093
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,INTERNAL:PLAINTEXT
inter.broker.listener.name=INTERNAL

# Zookeeper connection
zookeeper.connect=10.0.30.20:2181,10.0.30.21:2181,10.0.31.20:2181
zookeeper.connection.timeout.ms=18000

# Log configuration
log.dirs=/var/kafka-logs
num.partitions=3
default.replication.factor=2
min.insync.replicas=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# Replication configuration
replica.lag.time.max.ms=30000
replica.socket.timeout.ms=30000
replica.socket.receive.buffer.bytes=65536

# Network configuration
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Performance tuning
compression.type=snappy
message.max.bytes=1048576

# Group coordinator configuration
offsets.topic.replication.factor=2
transaction.state.log.replication.factor=2
transaction.state.log.min.isr=2

# JMX monitoring
KAFKACFG

# JVM configuration
cat > /opt/kafka/bin/kafka-server-start-jvm.sh <<JVMCFG
export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:G1HeapRegionSize=16M"
export JMX_PORT=9999
JVMCFG

# Create systemd service
cat > /etc/systemd/system/kafka.service <<KAFKASVC
[Unit]
Description=Apache Kafka
After=network.target zookeeper.service
Requires=network.target

[Service]
Type=simple
User=ec2-user
Environment="JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto"
ExecStart=/bin/bash -c 'source /opt/kafka/bin/kafka-server-start-jvm.sh && /opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties'
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
KAFKASVC

# Wait for Zookeeper to be ready
sleep 30

# Start Kafka
systemctl daemon-reload
systemctl enable kafka
systemctl start kafka

# CloudWatch agent installation
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

EOF

    # Replace placeholders
    sed -i "s/__BROKER_ID__/$BROKER_ID/g" "/tmp/kafka-userdata-${BROKER_ID}.sh"
    sed -i "s/__PRIVATE_IP__/$PRIVATE_IP/g" "/tmp/kafka-userdata-${BROKER_ID}.sh"

    # Launch EC2 instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --instance-type "$KAFKA_INSTANCE_TYPE" \
        --key-name "$KEY_PAIR_NAME" \
        --subnet-id "$SUBNET_ID" \
        --private-ip-address "$PRIVATE_IP" \
        --security-group-ids "$KAFKA_SG_ID" \
        --user-data "file:///tmp/kafka-userdata-${BROKER_ID}.sh" \
        --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"VolumeSize\":$KAFKA_EBS_SIZE,\"VolumeType\":\"$KAFKA_EBS_TYPE\",\"Encrypted\":true,\"Iops\":3000}}]" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=kafka-broker-${BROKER_ID}-${ENVIRONMENT}},{Key=Environment,Value=${ENVIRONMENT}},{Key=Service,Value=kafka}]" \
        --iam-instance-profile "Name=kafka-instance-profile" \
        --region "$AWS_REGION" \
        --output text --query 'Instances[0].InstanceId')

    log_info "Kafka broker $BROKER_ID launched: $INSTANCE_ID"
    echo "$INSTANCE_ID"
}

deploy_kafka_cluster() {
    log_info "Deploying Kafka cluster..."

    # Broker 1: us-east-1a
    KAFKA1_ID=$(deploy_kafka_broker "1" "$KAFKA_SUBNET_1" "10.0.30.10")

    # Broker 2: us-east-1a
    KAFKA2_ID=$(deploy_kafka_broker "2" "$KAFKA_SUBNET_1" "10.0.30.11")

    # Broker 3: us-east-1b
    KAFKA3_ID=$(deploy_kafka_broker "3" "$KAFKA_SUBNET_2" "10.0.31.10")

    log_info "Waiting for Kafka instances to be running..."
    aws ec2 wait instance-running --instance-ids "$KAFKA1_ID" "$KAFKA2_ID" "$KAFKA3_ID" --region "$AWS_REGION"

    log_info "Kafka cluster deployed successfully"
}

################################################################################
# Step 4: Create Network Load Balancer
################################################################################

create_nlb() {
    log_info "Creating Network Load Balancer for Kafka..."

    # Create NLB
    NLB_ARN=$(aws elbv2 create-load-balancer \
        --name "kafka-nlb-${ENVIRONMENT}" \
        --type network \
        --scheme internal \
        --subnets "$KAFKA_SUBNET_1" "$KAFKA_SUBNET_2" \
        --tags "Key=Name,Value=kafka-nlb-${ENVIRONMENT}" "Key=Environment,Value=${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --output text --query 'LoadBalancers[0].LoadBalancerArn')

    log_info "NLB created: $NLB_ARN"

    # Create target group
    TG_ARN=$(aws elbv2 create-target-group \
        --name "kafka-tg-${ENVIRONMENT}" \
        --protocol TCP \
        --port 9092 \
        --vpc-id "$VPC_ID" \
        --health-check-protocol TCP \
        --health-check-port 9092 \
        --health-check-interval-seconds 30 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 2 \
        --region "$AWS_REGION" \
        --output text --query 'TargetGroups[0].TargetGroupArn')

    log_info "Target group created: $TG_ARN"

    # Register Kafka brokers
    aws elbv2 register-targets \
        --target-group-arn "$TG_ARN" \
        --targets "Id=${KAFKA1_ID}" "Id=${KAFKA2_ID}" "Id=${KAFKA3_ID}" \
        --region "$AWS_REGION"

    # Create listener
    aws elbv2 create-listener \
        --load-balancer-arn "$NLB_ARN" \
        --protocol TCP \
        --port 9092 \
        --default-actions "Type=forward,TargetGroupArn=${TG_ARN}" \
        --region "$AWS_REGION"

    log_info "NLB listener created successfully"
}

################################################################################
# Step 5: Create Route53 Record
################################################################################

create_dns_record() {
    log_info "Creating Route53 DNS record..."

    NLB_DNS=$(aws elbv2 describe-load-balancers \
        --names "kafka-nlb-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --output text --query 'LoadBalancers[0].DNSName')

    # Create Route53 record (assuming hosted zone exists)
    HOSTED_ZONE_ID="Z1234567890ABC"  # Replace with actual hosted zone ID

    cat > /tmp/route53-change.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "kafka-nlb.internal",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${NLB_DNS}"}]
    }
  }]
}
EOF

    aws route53 change-resource-record-sets \
        --hosted-zone-id "$HOSTED_ZONE_ID" \
        --change-batch "file:///tmp/route53-change.json" \
        --region "$AWS_REGION"

    log_info "DNS record created: kafka-nlb.internal -> $NLB_DNS"
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "Starting Kafka cluster deployment for environment: $ENVIRONMENT"

    # Step 1: Create security groups
    create_security_groups

    # Step 2: Deploy Zookeeper ensemble
    deploy_zookeeper_ensemble

    # Wait for Zookeeper to stabilize
    log_info "Waiting 60 seconds for Zookeeper ensemble to stabilize..."
    sleep 60

    # Step 3: Deploy Kafka cluster
    deploy_kafka_cluster

    # Wait for Kafka to stabilize
    log_info "Waiting 60 seconds for Kafka cluster to stabilize..."
    sleep 60

    # Step 4: Create NLB
    create_nlb

    # Step 5: Create DNS record
    create_dns_record

    log_info "Kafka cluster deployment completed successfully!"
    log_info "Kafka brokers accessible at: kafka-nlb.internal:9092"
}

# Run main function
main "$@"
