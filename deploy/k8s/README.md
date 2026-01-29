# Kubernetes Deployment Manifests

Deploy the Hive Agent Framework to Kubernetes for scalable, production-ready agent execution.

## Quick Start

```bash
# 1. Create secrets (required)
kubectl create secret generic hive-secrets \
  --from-literal=ANTHROPIC_API_KEY=<your-api-key>

# 2. Apply manifests
kubectl apply -f deploy/k8s/

# 3. Verify deployment
kubectl get pods -l app=hive
kubectl logs -l app=hive -f
```

## Manifests

| File | Description |
|------|-------------|
| `deployment.yaml` | Deployment with replicas, resource limits, health probes |
| `service.yaml` | ClusterIP service for internal networking |
| `configmap.yaml` | Non-sensitive configuration values |

## Configuration

### Required Secrets

Create before deploying:

```bash
kubectl create secret generic hive-secrets \
  --from-literal=ANTHROPIC_API_KEY=<your-api-key>
```

### ConfigMap Customization

Override defaults:

```bash
kubectl create configmap hive-config \
  --from-literal=LOG_LEVEL=DEBUG \
  --from-literal=DEFAULT_MODEL=claude-3-opus-20240229 \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Resource Limits

Default resources (adjust in `deployment.yaml`):

| Resource | Request | Limit |
|----------|---------|-------|
| Memory | 512Mi | 2Gi |
| CPU | 250m | 1000m |
| Storage | 10Gi | - |

## Scaling

```bash
# Scale replicas
kubectl scale deployment hive-tools --replicas=5

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment hive-tools \
  --min=2 --max=10 --cpu-percent=70
```

## Health Checks

The deployment includes:
- **Liveness probe**: Restarts unhealthy pods
- **Readiness probe**: Routes traffic only to ready pods

Endpoint: `GET /health` on port 4001

## Cloud Provider Notes

### AWS EKS
Uncomment the AWS annotations in `service.yaml` for NLB.

### GCP GKE
Uncomment the GCP annotations for internal load balancer.

### Azure AKS
Uncomment the Azure annotations for internal load balancer.

## Troubleshooting

```bash
# Check pod status
kubectl describe pod -l app=hive

# View logs
kubectl logs -l app=hive --tail=100

# Shell into container
kubectl exec -it deployment/hive-tools -- /bin/bash

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp
```
