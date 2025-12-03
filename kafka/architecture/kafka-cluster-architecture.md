# Kafka Cluster Architecture

## Overview
This document describes the 3-node Apache Kafka cluster architecture with 3-node Zookeeper ensemble for the Cloud-Based Learning Platform.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          VPC 10.0.0.0/16                                │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Public Subnets (AZs: us-east-1a, 1b)          │  │
│  │  ┌────────────────┐                    ┌────────────────┐        │  │
│  │  │  ALB (Public)  │                    │   NAT Gateway  │        │  │
│  │  │  10.0.1.0/24   │                    │   10.0.2.0/24  │        │  │
│  │  └────────┬───────┘                    └────────┬───────┘        │  │
│  └───────────┼──────────────────────────────────────┼───────────────┘  │
│              │                                       │                  │
│  ┌───────────┼───────────────────────────────────────┼───────────────┐ │
│  │           │         Private Subnets (Containers)  │               │ │
│  │           │         10.0.10.0/24, 10.0.11.0/24    │               │ │
│  │  ┌────────▼─────────┐  ┌──────────────┐  ┌──────▼──────────┐    │ │
│  │  │  API Gateway     │  │ Microservices│  │   Internet via  │    │ │
│  │  │  (Container)     │  │  (5 services)│  │   NAT Gateway   │    │ │
│  │  └──────────────────┘  └──────┬───────┘  └─────────────────┘    │ │
│  └─────────────────────────────────┼────────────────────────────────┘ │
│                                    │                                   │
│  ┌────────────────────────────────┼────────────────────────────────┐  │
│  │        Kafka Subnets (10.0.30.0/24, 10.0.31.0/24)              │  │
│  │                                │                                 │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │              Kafka Cluster (3 Brokers)                   │  │  │
│  │  │                                                           │  │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │  │  │  Kafka Broker 1 │  │  Kafka Broker 2 │  │  Kafka Broker 3  │ │
│  │  │  │  10.0.30.10     │  │  10.0.30.11     │  │  10.0.31.10      │ │
│  │  │  │  AZ: us-east-1a │  │  AZ: us-east-1a │  │  AZ: us-east-1b  │ │
│  │  │  │  Port: 9092     │  │  Port: 9092     │  │  Port: 9092      │ │
│  │  │  │  EBS: 100GB GP3 │  │  EBS: 100GB GP3 │  │  EBS: 100GB GP3  │ │
│  │  │  └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘ │
│  │  └───────────┼──────────────────────┼──────────────────┼──────────┘ │
│  │              │                      │                  │             │
│  │  ┌───────────▼──────────────────────▼──────────────────▼──────────┐ │
│  │  │              Zookeeper Ensemble (3 Nodes)                     │ │
│  │  │                                                                │ │
│  │  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │ │
│  │  │  │  Zookeeper 1   │  │  Zookeeper 2   │  │  Zookeeper 3   │  │ │
│  │  │  │  10.0.30.20    │  │  10.0.30.21    │  │  10.0.31.20    │  │ │
│  │  │  │  AZ: us-east-1a│  │  AZ: us-east-1a│  │  AZ: us-east-1b│  │ │
│  │  │  │  Port: 2181    │  │  Port: 2181    │  │  Port: 2181    │  │ │
│  │  │  │  EBS: 20GB GP3 │  │  EBS: 20GB GP3 │  │  EBS: 20GB GP3 │  │ │
│  │  │  └────────────────┘  └────────────────┘  └────────────────┘  │ │
│  │  └────────────────────────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │           Data Subnets (10.0.20.0/24, 10.0.21.0/24)              │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │  PostgreSQL  │  │  PostgreSQL  │  │  PostgreSQL  │  ...      │  │
│  │  │  (STT)       │  │  (Chat)      │  │  (Document)  │           │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      NLB for Kafka (Internal)                     │  │
│  │                      kafka-nlb.internal                           │  │
│  │                      Port: 9092                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Kafka Brokers

| Component | Specification |
|-----------|---------------|
| **Count** | 3 brokers for high availability |
| **Instance Type** | t3.medium (2 vCPU, 4 GiB RAM) |
| **Storage** | 100GB GP3 EBS volume per broker |
| **Network** | Kafka subnets (10.0.30.0/24, 10.0.31.0/24) |
| **Availability Zones** | Distributed across us-east-1a and us-east-1b |
| **Ports** | 9092 (client), 9093 (inter-broker) |

**Broker Configuration:**
- Broker IDs: 1, 2, 3
- Log directories: `/var/kafka-logs` (mounted on EBS)
- JVM Heap: 2GB
- Replication factor: 2 (minimum)
- Min in-sync replicas: 2

### Zookeeper Ensemble

| Component | Specification |
|-----------|---------------|
| **Count** | 3 nodes for quorum |
| **Instance Type** | t3.small (2 vCPU, 2 GiB RAM) |
| **Storage** | 20GB GP3 EBS volume per node |
| **Network** | Kafka subnets (co-located with brokers) |
| **Availability Zones** | Distributed across us-east-1a and us-east-1b |
| **Ports** | 2181 (client), 2888 (follower), 3888 (election) |

**Zookeeper Configuration:**
- Server IDs: 1, 2, 3
- Data directory: `/var/zookeeper-data` (mounted on EBS)
- Tick time: 2000ms
- Init limit: 10
- Sync limit: 5

### Network Load Balancer (NLB)

| Component | Specification |
|-----------|---------------|
| **Type** | Network Load Balancer (Internal) |
| **DNS** | kafka-nlb.internal |
| **Port** | 9092 |
| **Target Group** | All 3 Kafka brokers |
| **Health Check** | TCP:9092 |
| **Stickiness** | Enabled (client affinity) |

## Security Groups

### Kafka Broker Security Group
```
Inbound Rules:
- Port 9092 (TCP) from Private Subnets (10.0.10.0/24, 10.0.11.0/24) - Client connections
- Port 9093 (TCP) from Kafka Subnets (10.0.30.0/24, 10.0.31.0/24) - Inter-broker
- Port 2181 (TCP) from Kafka Subnets - Zookeeper client

Outbound Rules:
- All traffic to 0.0.0.0/0
```

### Zookeeper Security Group
```
Inbound Rules:
- Port 2181 (TCP) from Kafka Subnets (10.0.30.0/24, 10.0.31.0/24) - Client
- Port 2888 (TCP) from Kafka Subnets - Follower
- Port 3888 (TCP) from Kafka Subnets - Election

Outbound Rules:
- All traffic to 0.0.0.0/0
```

## Data Flow

### Microservice to Kafka Connection Flow
```
Microservice Container (Private Subnet)
          ↓
    NLB (kafka-nlb.internal:9092)
          ↓
    Kafka Broker (Round-robin)
          ↓
    Topic Partition (Replicated across brokers)
```

### Kafka Internal Replication Flow
```
Producer → Leader Partition (Broker 1)
                ↓
          Replicate to ISR
                ↓
    ┌───────────┼───────────┐
    ↓           ↓           ↓
Replica 1   Replica 2   Replica 3
(Broker 2)  (Broker 3)  (Broker 1)
```

## High Availability Features

1. **Multi-AZ Deployment**: Brokers and Zookeepers distributed across 2 availability zones
2. **Replication**: Minimum replication factor of 2 for all topics
3. **ISR (In-Sync Replicas)**: Minimum 2 in-sync replicas required for writes
4. **Automated Failover**: Zookeeper manages leader election and broker failover
5. **NLB Health Checks**: Unhealthy brokers automatically removed from rotation
6. **EBS Snapshots**: Automated daily snapshots for disaster recovery

## Monitoring Integration

### CloudWatch Metrics
- Broker CPU/Memory utilization
- Network throughput
- Disk IOPS and throughput
- Partition count and replica lag

### Kafka JMX Metrics
- Messages in/out per second
- Bytes in/out per second
- Under-replicated partitions
- ISR shrink/expand rate
- Leader election rate

### Zookeeper Metrics
- Outstanding requests
- Latency (min/avg/max)
- Connection count
- Watch count

## Capacity Planning

### Current Configuration
- **Storage**: 300GB total (3 × 100GB)
- **Throughput**: ~60 MB/s aggregate (20 MB/s per broker)
- **Messages**: ~50,000 messages/second
- **Retention**: 7 days default

### Scaling Strategy
- **Vertical**: Upgrade to t3.large for more CPU/RAM
- **Horizontal**: Add brokers 4, 5, 6 for increased throughput
- **Storage**: Expand EBS volumes or add additional volumes
- **Partitions**: Increase partition count per topic for parallelism

## Disaster Recovery

### Backup Strategy
1. **EBS Snapshots**: Daily snapshots retained for 7 days
2. **Kafka Mirror Maker**: Optional cross-region replication
3. **Topic Configuration Backup**: Store topic configs in version control
4. **Consumer Offset Backup**: Stored in internal Kafka topic

### Recovery Procedures
1. **Broker Failure**: Automatic leader election, manual broker replacement
2. **AZ Failure**: Traffic routed to remaining AZ, scale up capacity
3. **Data Loss**: Restore from EBS snapshot, replay from earliest offset
4. **Complete Cluster Failure**: Restore from snapshots, reconfigure consumers

## Cost Estimation (Monthly)

| Resource | Quantity | Unit Cost | Total |
|----------|----------|-----------|-------|
| EC2 t3.medium (Kafka) | 3 | $30 | $90 |
| EC2 t3.small (Zookeeper) | 3 | $15 | $45 |
| EBS GP3 100GB | 3 | $8 | $24 |
| EBS GP3 20GB | 3 | $1.60 | $4.80 |
| NLB | 1 | $16.43 + data | $20 |
| Data Transfer | Variable | - | $10 |
| **Total** | | | **~$194/month** |
