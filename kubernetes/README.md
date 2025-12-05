# Kubernetes Manifests

This directory contains Kubernetes manifests for production deployment of the Learner Lab microservices.

## Why Kubernetes?

Docker Compose is excellent for local development, but production deployments require features that only Kubernetes provides:

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| Liveness Probes | ✅ (healthcheck) | ✅ (livenessProbe) |
| **Readiness Probes** | ❌ | ✅ (readinessProbe) |
| **Horizontal Pod Autoscaling (HPA)** | ❌ | ✅ |
| Resource Limits | ⚠️ (Swarm only) | ✅ |
| **Persistent Volume Claims (PVCs)** | ❌ (local volumes) | ✅ |
| Rolling Updates | ⚠️ (Swarm only) | ✅ |
| Secrets Management | ⚠️ (Docker secrets) | ✅ (K8s Secrets) |

## Directory Structure

```
kubernetes/
├── base/                    # Base Kustomize configurations
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   └── configmap.yaml
├── deployments/             # Service deployments with probes
│   ├── api-gateway.yaml
│   ├── tts-service.yaml
│   ├── stt-service.yaml
│   ├── chat-service.yaml
│   ├── document-service.yaml
│   └── quiz-service.yaml
├── services/                # Kubernetes Services
│   └── *.yaml
├── hpa/                     # Horizontal Pod Autoscalers
│   └── *.yaml
├── storage/                 # PersistentVolumeClaims
│   └── *.yaml
├── secrets/                 # Secret templates (DO NOT commit real secrets!)
│   └── *.yaml.template
└── overlays/                # Environment-specific configs
    ├── development/
    └── production/
```

## Deployment

### Prerequisites
- kubectl configured for your cluster
- AWS EKS or similar Kubernetes cluster
- ECR images pushed (see scripts/ecr-setup.sh)

### Deploy to Development
```bash
kubectl apply -k kubernetes/overlays/development
```

### Deploy to Production
```bash
kubectl apply -k kubernetes/overlays/production
```

## Key Differences from Docker Compose

### 1. Readiness Probes
Each deployment includes both liveness AND readiness probes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 40
  periodSeconds: 30
readinessProbe:
  httpGet:
    path: /health/ready  # Separate readiness endpoint
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 2. Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. PersistentVolumeClaims
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: chat-db-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: gp2  # AWS EBS
```
