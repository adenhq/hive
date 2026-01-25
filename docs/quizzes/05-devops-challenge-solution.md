# DevOps Challenge Solution

**Author:** DevOps Engineer
**Date:** January 2025
**Project:** Hive - AI Agent Framework

---

## Part 1: Infrastructure Analysis (20 points)

### Task 1.1: Docker Deep Dive

#### 1. Services Defined in Docker Setup

Based on the codebase analysis, the Hive project has the following Docker service:

**Tools MCP Server** (`tools/Dockerfile`):
- Python 3.11-slim based container
- Exposes MCP (Model Context Protocol) server on port 4001
- Provides AI agent tools via HTTP transport
- Health check endpoint at `/health`

#### 2. Docker Compose Override Purpose

A `docker-compose.override.yml` would typically be used to:
- Override production settings for local development
- Mount local source code for hot reloading
- Use development-specific environment variables
- Reduce resource constraints for local machines
- Enable debug logging and debugging ports

#### 3. Hot Reload Implementation

For development, hot reload would be implemented via:
- Volume mounting source code: `./src:/app/src`
- Using `--reload` flag with uvicorn/FastMCP
- File watchers that detect changes in mounted directories

#### 4. Volumes Mounted and Rationale

```yaml
volumes:
  - /app/workdir/workspaces  # Workspace persistence
```

**Rationale:**
- **Workspaces:** Persists agent working directories across container restarts
- **Source code:** (dev) Enables live code changes without rebuilding
- **Logs:** (optional) Centralized log collection

#### 5. Networking Mode

The services use Docker's **bridge networking** (default):
- Services communicate via container names as hostnames
- Internal network isolation from host
- Explicit port mapping for external access (4001:4001)

---

### Task 1.2: Service Dependencies

#### 1. Dependency Diagram

```mermaid
graph TB
    subgraph "External Services"
        LLM[LLM Providers<br/>Anthropic/OpenAI]
        BRAVE[Brave Search API]
    end

    subgraph "Hive Infrastructure"
        TOOLS[Tools MCP Server<br/>:4001]
        FRAMEWORK[Agent Framework<br/>core/]
    end

    subgraph "Optional Storage"
        MONGO[(MongoDB<br/>Agent State)]
        REDIS[(Redis<br/>Cache/Sessions)]
    end

    FRAMEWORK --> TOOLS
    TOOLS --> LLM
    TOOLS --> BRAVE
    FRAMEWORK -.-> MONGO
    FRAMEWORK -.-> REDIS
```

#### 2. Startup Order

Recommended startup order:
1. **Redis** (if used) - Session/cache dependency
2. **MongoDB** (if used) - State persistence
3. **Tools MCP Server** - Core tool provider
4. **Agent Framework** - Depends on tools

**Does it matter?** Yes - services should wait for dependencies via health checks.

#### 3. MongoDB Unavailability Impact

If MongoDB is unavailable:
- Agent state persistence fails
- Session data cannot be stored/retrieved
- Historical runs not accessible
- **Mitigation:** Fallback to in-memory storage, circuit breaker pattern

#### 4. Redis Unavailability Impact

If Redis is unavailable:
- Session management degraded
- Caching disabled (increased LLM costs)
- Rate limiting may fail
- **Mitigation:** Fallback to local memory cache, graceful degradation

#### 5. Stateless vs Stateful Services

| Service | Type | Reason |
|---------|------|--------|
| Tools MCP Server | Stateless | No persistent data, can scale horizontally |
| Agent Framework | Stateless* | State stored externally, horizontally scalable |
| MongoDB | Stateful | Persists agent state and history |
| Redis | Stateful | Holds cache and session data |

---

### Task 1.3: Configuration Management

#### 1. Configuration Generation

Configuration is managed through:
- **Environment variables:** Primary configuration method
- **`.env` files:** Local development (`.env.example` as template)
- **pyproject.toml:** Python package and tool configuration
- **Runtime injection:** Kubernetes ConfigMaps/Secrets in production

#### 2. Required Environment Variables

**Tier 1 - Startup Required:**
```bash
ANTHROPIC_API_KEY=<api-key>  # Required for LLM operations
```

**Tier 2 - Tool-Specific:**
```bash
BRAVE_SEARCH_API_KEY=<api-key>  # Required for web_search tool
```

**Server Configuration:**
```bash
MCP_PORT=4001              # MCP server port
MCP_HOST=0.0.0.0          # Server binding address
```

#### 3. Secret Management

**Current Approach:**
- Environment variables
- `.env` files (gitignored)
- Two-tier credential validation

**Recommendations for Production:**
- HashiCorp Vault for secret storage
- AWS Secrets Manager / GCP Secret Manager
- Kubernetes Secrets with encryption at rest
- SOPS for encrypted secrets in git

#### 4. Dev vs Production Config Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| Debug Mode | Enabled | Disabled |
| Log Level | DEBUG | INFO/WARN |
| API Keys | Test/sandbox | Production keys |
| TLS | Optional | Required |
| Resource Limits | None | Enforced |
| Replicas | 1 | 3+ |
| Health Checks | Relaxed | Strict |

---

## Part 2: Deployment Scenarios (25 points)

### Task 2.1: Production Deployment Plan

**Requirements:**
- 100 active agents
- 10,000 LLM requests/day
- 99.9% uptime
- Multi-region support

#### 1. Infrastructure Diagram (AWS)

```mermaid
graph TB
    subgraph "Region: us-east-1 (Primary)"
        subgraph "VPC"
            ALB1[Application Load Balancer]

            subgraph "EKS Cluster"
                TOOLS1[Tools Pods x3]
                AGENT1[Agent Pods x5]
            end

            subgraph "Data Tier"
                DOCDB1[(DocumentDB<br/>Primary)]
                REDIS1[(ElastiCache<br/>Redis)]
            end
        end
    end

    subgraph "Region: eu-west-1 (DR)"
        subgraph "VPC2"
            ALB2[Application Load Balancer]

            subgraph "EKS Cluster 2"
                TOOLS2[Tools Pods x2]
                AGENT2[Agent Pods x3]
            end

            subgraph "Data Tier 2"
                DOCDB2[(DocumentDB<br/>Replica)]
                REDIS2[(ElastiCache<br/>Redis)]
            end
        end
    end

    R53[Route 53<br/>Geo-routing]

    R53 --> ALB1
    R53 --> ALB2
    ALB1 --> TOOLS1
    ALB1 --> AGENT1
    TOOLS1 --> DOCDB1
    TOOLS1 --> REDIS1
    DOCDB1 -.->|Replication| DOCDB2
```

#### 2. Service Sizing

| Component | CPU | Memory | Replicas | Notes |
|-----------|-----|--------|----------|-------|
| Tools MCP Server | 1 vCPU | 2 GB | 3 | Stateless, auto-scale |
| Agent Runtime | 2 vCPU | 4 GB | 5 | LLM processing |
| DocumentDB | 4 vCPU | 16 GB | 3 | Primary + 2 replicas |
| ElastiCache Redis | 2 vCPU | 8 GB | 2 | Cluster mode |
| ALB | Managed | Managed | 2 | Multi-AZ |

#### 3. Database Setup

**Primary/Replica Architecture:**
```yaml
DocumentDB Cluster:
  Primary: db.r6g.xlarge (us-east-1a)
  Replicas:
    - db.r6g.large (us-east-1b) - Read replica
    - db.r6g.large (us-east-1c) - Read replica
    - db.r6g.large (eu-west-1a) - Cross-region replica (DR)

Backup Strategy:
  - Automated backups: Daily, 7-day retention
  - Manual snapshots: Weekly, 30-day retention
  - Point-in-time recovery: Enabled
  - Cross-region backup: Daily to eu-west-1
```

#### 4. Load Balancing Strategy

```yaml
Application Load Balancer:
  Listeners:
    - HTTPS (443) -> Target Groups

  Target Groups:
    - tools-tg:
        Port: 4001
        Health Check: /health
        Deregistration Delay: 30s
    - agents-tg:
        Port: 8080
        Health Check: /health
        Deregistration Delay: 60s  # Allow agent completion

  Routing Rules:
    - /mcp/* -> tools-tg
    - /api/* -> agents-tg

  WebSocket Support:
    - Sticky sessions enabled
    - Connection draining: 120s
```

#### 5. Estimated Monthly Cost

| Service | Specification | Monthly Cost |
|---------|--------------|--------------|
| EKS Cluster | 2 clusters | $146 |
| EC2 (Nodes) | 10x m6i.xlarge | $1,400 |
| DocumentDB | 4x db.r6g.large | $1,200 |
| ElastiCache | 2x cache.r6g.large | $400 |
| ALB | 2x ALB | $50 |
| Data Transfer | ~500GB | $45 |
| Route 53 | Hosted zones + queries | $10 |
| CloudWatch | Logs + Metrics | $100 |
| Secrets Manager | 20 secrets | $8 |
| **Total** | | **~$3,360/month** |

*Note: Costs may vary based on actual usage and reserved instances.*

---

### Task 2.2: Kubernetes Migration

#### 1. Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hive-tools
  namespace: hive
  labels:
    app: hive-tools
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hive-tools
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: hive-tools
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "4001"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: hive-tools
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
      containers:
        - name: tools
          image: hive/tools:v1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 4001
              protocol: TCP
          env:
            - name: MCP_PORT
              value: "4001"
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: hive-secrets
                  key: anthropic-api-key
            - name: BRAVE_SEARCH_API_KEY
              valueFrom:
                secretKeyRef:
                  name: hive-secrets
                  key: brave-api-key
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 1000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
          volumeMounts:
            - name: workspaces
              mountPath: /app/workdir/workspaces
      volumes:
        - name: workspaces
          persistentVolumeClaim:
            claimName: hive-workspaces
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: hive-tools
```

#### 2. Service and Ingress

```yaml
---
apiVersion: v1
kind: Service
metadata:
  name: hive-tools
  namespace: hive
  labels:
    app: hive-tools
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 4001
      targetPort: http
      protocol: TCP
  selector:
    app: hive-tools
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hive-ingress
  namespace: hive
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.hive.example.com
      secretName: hive-tls
  rules:
    - host: api.hive.example.com
      http:
        paths:
          - path: /mcp
            pathType: Prefix
            backend:
              service:
                name: hive-tools
                port:
                  number: 4001
          - path: /
            pathType: Prefix
            backend:
              service:
                name: hive-api
                port:
                  number: 8080
```

#### 3. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hive-config
  namespace: hive
data:
  MCP_PORT: "4001"
  MCP_HOST: "0.0.0.0"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  ENVIRONMENT: "production"
  ENABLE_METRICS: "true"
  METRICS_PORT: "9090"
  MAX_CONNECTIONS: "100"
  REQUEST_TIMEOUT: "300"
  HEALTHCHECK_INTERVAL: "30"
```

#### 4. Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: hive-secrets
  namespace: hive
type: Opaque
stringData:
  anthropic-api-key: "${ANTHROPIC_API_KEY}"
  brave-api-key: "${BRAVE_SEARCH_API_KEY}"
  mongodb-uri: "mongodb://user:password@mongodb:27017/hive"
  redis-url: "redis://:password@redis:6379/0"
```

*Note: In production, use external-secrets or sealed-secrets for secret management.*

#### 5. HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hive-tools-hpa
  namespace: hive
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hive-tools
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

---

### Task 2.3: High Availability Design

#### 1. Backend Service Failure Handling

```yaml
Strategy: Multi-layer resilience

Layer 1 - Pod Level:
  - Liveness probes detect unresponsive containers
  - Readiness probes remove unhealthy pods from service
  - PodDisruptionBudget ensures minimum availability

Layer 2 - Deployment Level:
  - ReplicaSet maintains desired pod count
  - Rolling updates with zero downtime
  - Automatic rollback on failed deployments

Layer 3 - Service Level:
  - Service mesh (Istio) for traffic management
  - Circuit breakers prevent cascade failures
  - Retry policies with exponential backoff

Layer 4 - Cluster Level:
  - Multi-AZ deployment
  - Node auto-replacement
  - Cluster autoscaler for capacity
```

**PodDisruptionBudget:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: hive-tools-pdb
  namespace: hive
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: hive-tools
```

#### 2. Database Failover Strategy

```yaml
MongoDB/DocumentDB HA:
  Architecture:
    - Primary node: Handles all writes
    - Secondary nodes: Sync via replication
    - Arbiter: Voting in elections

  Automatic Failover:
    - Detection: 10-second heartbeat timeout
    - Election: Secondary with most recent data
    - Promotion: ~30 seconds total failover time

  Application Configuration:
    - Connection string: mongodb+srv://cluster.example.com
    - Read preference: primaryPreferred
    - Write concern: majority
    - Retry writes: enabled

  Cross-Region DR:
    - Global cluster spanning regions
    - RPO: < 1 second (async replication)
    - RTO: < 1 minute (automatic promotion)
```

#### 3. Zero-Downtime Deployment Strategy

```yaml
Rolling Update Strategy:
  maxSurge: 1        # Add 1 pod at a time
  maxUnavailable: 0  # Never reduce capacity

Deployment Process:
  1. Create new pod with updated image
  2. Wait for readiness probe to pass
  3. Add new pod to service endpoints
  4. Remove old pod from endpoints
  5. Terminate old pod gracefully
  6. Repeat until all pods updated

Pre-deployment Checks:
  - Run integration tests against staging
  - Verify configuration validity
  - Check resource quotas

Post-deployment Verification:
  - Smoke tests against production
  - Monitor error rates for 10 minutes
  - Automatic rollback if errors spike
```

#### 4. WebSocket Connection Handling During Rolling Updates

```yaml
WebSocket Strategy:

  Pod Termination:
    terminationGracePeriodSeconds: 120
    preStop:
      exec:
        command:
          - /bin/sh
          - -c
          - |
            # Stop accepting new connections
            touch /tmp/shutdown
            # Wait for existing connections to complete
            sleep 90
            # Graceful shutdown
            kill -SIGTERM 1

  Client-Side:
    - Reconnect with exponential backoff
    - Store pending messages in local queue
    - Resume session after reconnect

  Server-Side:
    - Session state in Redis (shared across pods)
    - Connection draining on shutdown signal
    - Sticky sessions via ingress annotation

  Ingress Configuration:
    nginx.ingress.kubernetes.io/affinity: cookie
    nginx.ingress.kubernetes.io/session-cookie-name: HIVE_AFFINITY
    nginx.ingress.kubernetes.io/session-cookie-max-age: "3600"
```

#### 5. Disaster Recovery Plan

```markdown
# Hive Disaster Recovery Plan

## RPO/RTO Targets
- RPO (Recovery Point Objective): 1 hour
- RTO (Recovery Time Objective): 4 hours

## Backup Strategy

### Daily Backups
- Database: Automated snapshots at 02:00 UTC
- Configuration: GitOps repository (Flux/ArgoCD)
- Secrets: Vault snapshots to S3

### Retention Policy
- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

## Disaster Scenarios

### Scenario 1: Single Pod Failure
- Impact: Minimal
- Detection: Kubernetes health checks
- Recovery: Automatic (< 1 minute)
- Action: None required

### Scenario 2: Availability Zone Failure
- Impact: 33% capacity reduction
- Detection: CloudWatch alarms
- Recovery: Automatic pod rescheduling
- Action: Monitor; manual intervention if needed

### Scenario 3: Region Failure
- Impact: Full service outage
- Detection: Route 53 health checks
- Recovery Time: ~30 minutes
- Actions:
  1. Route 53 automatically fails over to DR region
  2. Promote DocumentDB replica to primary
  3. Verify service restoration
  4. Begin root cause analysis

### Scenario 4: Data Corruption
- Impact: Variable
- Detection: Application errors, data validation
- Recovery Time: 2-4 hours
- Actions:
  1. Identify corruption scope
  2. Halt writes to affected collections
  3. Restore from point-in-time backup
  4. Replay transaction logs if needed
  5. Verify data integrity

## Communication Plan
- Incident declared: Slack #incidents, PagerDuty
- Status updates: Every 30 minutes
- Post-incident: Blameless retrospective within 48 hours

## Testing Schedule
- Failover drills: Quarterly
- Full DR test: Annually
- Backup restoration: Monthly
```

---

## Part 3: CI/CD Pipeline (25 points)

### Task 3.1: GitHub Actions Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: Hive CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  PYTHON_VERSION: '3.11'

jobs:
  # ================================
  # Stage 1: Code Quality
  # ================================
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd core
          pip install -e .
          pip install -r requirements-dev.txt

      - name: Run ruff
        run: |
          cd core
          ruff check . --output-format=github

      - name: Run ruff format check
        run: |
          cd core
          ruff format --check .

  type-check:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd core
          pip install -e .
          pip install -r requirements-dev.txt

      - name: Run mypy
        run: |
          cd core
          mypy framework/ --ignore-missing-imports

  # ================================
  # Stage 2: Testing
  # ================================
  unit-tests:
    name: Unit Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd core
          pip install -e .
          pip install -r requirements-dev.txt

      - name: Run unit tests
        run: |
          cd core
          pytest tests/ -v --cov=framework --cov-report=xml -x

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: core/coverage.xml
          flags: unittests-py${{ matrix.python-version }}

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [lint, type-check]
    services:
      mongodb:
        image: mongo:7
        ports:
          - 27017:27017
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd core
          pip install -e .
          pip install -r requirements-dev.txt

      - name: Run integration tests
        env:
          MONGODB_URI: mongodb://localhost:27017/hive_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd core
          pytest tests/integration/ -v --timeout=300

  # ================================
  # Stage 3: Build
  # ================================
  build:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    permissions:
      contents: read
      packages: write
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/tools
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix=
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: ./tools
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  # ================================
  # Stage 4: Security Scanning
  # ================================
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name != 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/tools:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # ================================
  # Stage 5: Deploy to Staging
  # ================================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.hive.example.com
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/setup-kubectl@v3

      - name: Set Kubernetes context
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Deploy to staging
        run: |
          kubectl set image deployment/hive-tools \
            tools=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/tools:${{ github.sha }} \
            -n hive-staging
          kubectl rollout status deployment/hive-tools -n hive-staging --timeout=300s

      - name: Run smoke tests
        run: |
          curl -f https://staging.hive.example.com/health || exit 1

  # ================================
  # Stage 6: Deploy to Production
  # ================================
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://api.hive.example.com
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/setup-kubectl@v3

      - name: Set Kubernetes context
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Deploy to production
        run: |
          kubectl set image deployment/hive-tools \
            tools=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/tools:${{ github.sha }} \
            -n hive
          kubectl rollout status deployment/hive-tools -n hive --timeout=300s

      - name: Run smoke tests
        run: |
          curl -f https://api.hive.example.com/health || exit 1

      - name: Notify on success
        if: success()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Hive deployed to production: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}

  # ================================
  # Rollback Job (Manual Trigger)
  # ================================
  rollback:
    name: Rollback Production
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch'
    environment:
      name: production
    steps:
      - name: Configure kubectl
        uses: azure/setup-kubectl@v3

      - name: Set Kubernetes context
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Rollback deployment
        run: |
          kubectl rollout undo deployment/hive-tools -n hive
          kubectl rollout status deployment/hive-tools -n hive --timeout=300s
```

---

### Task 3.2: Testing Strategy

#### 1. Unit Tests - LLM Mocking

```python
# tests/unit/test_agent_with_mock_llm.py
import pytest
from unittest.mock import AsyncMock, patch
from framework.llm import LLMClient

class MockLLMResponse:
    """Mock LLM response for testing."""
    def __init__(self, content: str, tool_calls: list = None):
        self.content = content
        self.tool_calls = tool_calls or []

@pytest.fixture
def mock_llm():
    """Fixture that provides a mocked LLM client."""
    with patch('framework.llm.LLMClient') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client

@pytest.mark.asyncio
async def test_agent_processes_tool_call(mock_llm):
    """Test agent correctly processes LLM tool calls."""
    # Arrange
    mock_llm.complete.return_value = MockLLMResponse(
        content="I'll search for that.",
        tool_calls=[{
            "name": "web_search",
            "arguments": {"query": "test query"}
        }]
    )

    # Act
    agent = Agent(llm=mock_llm)
    result = await agent.run("Search for test query")

    # Assert
    assert mock_llm.complete.called
    assert result.tool_calls[0]["name"] == "web_search"

@pytest.fixture
def llm_response_fixture():
    """Reusable LLM response scenarios."""
    return {
        "simple_response": MockLLMResponse("Hello, world!"),
        "tool_call": MockLLMResponse(
            "Using tool",
            tool_calls=[{"name": "calculator", "arguments": {"expr": "2+2"}}]
        ),
        "error": Exception("API rate limit exceeded"),
    }
```

#### 2. Integration Tests - Real Databases

```python
# tests/integration/test_database_integration.py
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def mongodb_client():
    """Provide MongoDB client for integration tests."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.hive_test
    yield db
    # Cleanup
    await client.drop_database("hive_test")
    client.close()

@pytest.fixture(scope="session")
async def redis_client():
    """Provide Redis client for integration tests."""
    client = redis.from_url("redis://localhost:6379/15")
    yield client
    # Cleanup
    await client.flushdb()
    await client.close()

@pytest.mark.asyncio
async def test_agent_state_persistence(mongodb_client, redis_client):
    """Test that agent state is correctly persisted."""
    # Arrange
    agent_id = "test-agent-123"
    state = {"step": 1, "context": {"user": "test"}}

    # Act - Save state
    await mongodb_client.agent_states.insert_one({
        "_id": agent_id,
        "state": state
    })
    await redis_client.set(f"agent:{agent_id}:session", "active")

    # Assert - Retrieve state
    saved_state = await mongodb_client.agent_states.find_one({"_id": agent_id})
    session = await redis_client.get(f"agent:{agent_id}:session")

    assert saved_state["state"] == state
    assert session == b"active"
```

#### 3. E2E Tests - User Flows

```python
# tests/e2e/test_user_flows.py
import pytest
from playwright.async_api import async_playwright

@pytest.fixture(scope="session")
async def browser():
    """Provide browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.mark.asyncio
async def test_create_agent_flow(browser):
    """E2E test: User creates and runs an agent."""
    page = await browser.new_page()

    # Navigate to application
    await page.goto("http://localhost:3000")

    # Create new agent
    await page.click('[data-testid="create-agent-btn"]')
    await page.fill('[data-testid="agent-name-input"]', "Test Agent")
    await page.fill('[data-testid="agent-goal-input"]', "Search for information")
    await page.click('[data-testid="submit-agent-btn"]')

    # Wait for agent creation
    await page.wait_for_selector('[data-testid="agent-created-message"]')

    # Run agent
    await page.click('[data-testid="run-agent-btn"]')
    await page.wait_for_selector('[data-testid="agent-running"]')

    # Verify completion
    await page.wait_for_selector('[data-testid="agent-completed"]', timeout=60000)

    result = await page.inner_text('[data-testid="agent-result"]')
    assert "Search results" in result

    await page.close()

@pytest.mark.asyncio
async def test_error_handling_flow(browser):
    """E2E test: Application handles errors gracefully."""
    page = await browser.new_page()
    await page.goto("http://localhost:3000")

    # Trigger error state
    await page.click('[data-testid="invalid-action-btn"]')

    # Verify error message displayed
    error_msg = await page.wait_for_selector('[data-testid="error-message"]')
    assert await error_msg.is_visible()

    # Verify recovery option available
    retry_btn = await page.query_selector('[data-testid="retry-btn"]')
    assert retry_btn is not None

    await page.close()
```

#### 4. Load Tests - Agent Traffic Simulation

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between
import json

class AgentUser(HttpUser):
    """Simulates agent API traffic."""
    wait_time = between(1, 3)

    def on_start(self):
        """Setup: Create test agent on user start."""
        response = self.client.post("/api/agents", json={
            "name": f"LoadTest-{self.environment.runner.user_count}",
            "goal": "Test goal"
        })
        self.agent_id = response.json().get("id")

    @task(5)
    def run_agent(self):
        """Primary task: Execute agent runs."""
        self.client.post(f"/api/agents/{self.agent_id}/run", json={
            "input": "Search for test data"
        })

    @task(3)
    def check_status(self):
        """Check agent status."""
        self.client.get(f"/api/agents/{self.agent_id}/status")

    @task(2)
    def get_history(self):
        """Retrieve agent run history."""
        self.client.get(f"/api/agents/{self.agent_id}/history")

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health")

class MCPUser(HttpUser):
    """Simulates MCP tool server traffic."""
    wait_time = between(0.5, 2)

    @task(10)
    def call_tool(self):
        """Call MCP tool."""
        self.client.post("/mcp/tools/web_search", json={
            "query": "test search"
        })

    @task(5)
    def list_tools(self):
        """List available tools."""
        self.client.get("/mcp/tools")
```

**Load Test Configuration:**
```yaml
# tests/load/config.yml
scenarios:
  smoke:
    users: 10
    spawn_rate: 2
    duration: 60s

  load:
    users: 100
    spawn_rate: 10
    duration: 300s

  stress:
    users: 500
    spawn_rate: 50
    duration: 600s

  spike:
    stages:
      - users: 10, duration: 60s
      - users: 500, duration: 30s
      - users: 10, duration: 60s
```

#### 5. Chaos Tests - Failure Simulation

```python
# tests/chaos/test_resilience.py
import pytest
import asyncio
from chaos_toolkit import run_experiment

CHAOS_EXPERIMENTS = {
    "pod_failure": {
        "title": "Random Pod Termination",
        "description": "Terminate random hive-tools pod",
        "method": [
            {
                "type": "action",
                "name": "terminate-pod",
                "provider": {
                    "type": "python",
                    "module": "chaosk8s.pod.actions",
                    "func": "terminate_pods",
                    "arguments": {
                        "label_selector": "app=hive-tools",
                        "ns": "hive",
                        "qty": 1
                    }
                }
            }
        ],
        "steady-state-hypothesis": {
            "title": "Service remains available",
            "probes": [
                {
                    "type": "probe",
                    "name": "health-check",
                    "tolerance": True,
                    "provider": {
                        "type": "http",
                        "url": "https://api.hive.example.com/health",
                        "timeout": 5
                    }
                }
            ]
        }
    },

    "network_latency": {
        "title": "Network Latency Injection",
        "description": "Add 500ms latency to database calls",
        "method": [
            {
                "type": "action",
                "name": "inject-latency",
                "provider": {
                    "type": "python",
                    "module": "chaosistio.fault.actions",
                    "func": "add_delay_fault",
                    "arguments": {
                        "virtual_service_name": "mongodb",
                        "fixed_delay": "500ms",
                        "percentage": 100
                    }
                }
            }
        ]
    },

    "resource_exhaustion": {
        "title": "Memory Pressure",
        "description": "Simulate memory pressure on nodes",
        "method": [
            {
                "type": "action",
                "name": "stress-memory",
                "provider": {
                    "type": "python",
                    "module": "chaosk8s.node.actions",
                    "func": "stress_memory",
                    "arguments": {
                        "workers": 2,
                        "vm_bytes": "1G",
                        "duration": 60
                    }
                }
            }
        ]
    }
}

@pytest.mark.chaos
@pytest.mark.parametrize("experiment_name", CHAOS_EXPERIMENTS.keys())
async def test_chaos_experiment(experiment_name):
    """Run chaos experiment and verify system resilience."""
    experiment = CHAOS_EXPERIMENTS[experiment_name]

    # Run experiment
    result = await run_experiment(experiment)

    # Verify steady state maintained
    assert result["steady-state-met"], f"Experiment {experiment_name} failed"
```

---

### Task 3.3: Environment Management

| Environment | Purpose | Data | Who Can Access |
|-------------|---------|------|----------------|
| Local | Development | Mock | Developers |
| Dev | Integration | Sanitized | Engineering |
| Staging | Pre-prod | Copy of prod | Engineering + QA |
| Production | Live | Real | Restricted |

#### Local Environment

```yaml
Provisioning:
  Method: docker-compose
  Command: docker-compose up -d
  Infrastructure: Local machine

Data Management:
  - Mock data in fixtures
  - SQLite for local database
  - In-memory Redis
  - Seed scripts for test data

Deployment:
  - Manual: docker-compose up
  - Hot reload enabled
  - Debug mode on

Access Control:
  - No restrictions
  - Test API keys only
  - Local network only
```

**docker-compose.local.yml:**
```yaml
version: '3.8'
services:
  tools:
    build: ./tools
    ports:
      - "4001:4001"
    volumes:
      - ./tools/src:/app/src
    environment:
      - DEBUG=true
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    command: python mcp_server.py --reload
```

#### Dev Environment

```yaml
Provisioning:
  Method: Terraform + Kubernetes
  Infrastructure: AWS EKS (shared cluster)
  Namespace: hive-dev

Data Management:
  - Sanitized production snapshot (weekly)
  - PII removed via data masking
  - Separate database instance
  - Reset capability via script

Deployment:
  - Automatic on develop branch push
  - No approval required
  - Feature branch deployments supported

Access Control:
  - VPN required
  - SSO authentication
  - Engineering team only
  - Read-only production data access
```

#### Staging Environment

```yaml
Provisioning:
  Method: Terraform (same as production)
  Infrastructure: AWS EKS (dedicated cluster)
  Namespace: hive-staging

Data Management:
  - Daily production data sync
  - Subset of production data (10%)
  - Full anonymization pipeline
  - Separate credentials

Deployment:
  - Automatic after Dev tests pass
  - Requires passing integration tests
  - Same artifacts as production
  - Blue-green deployment

Access Control:
  - VPN required
  - SSO authentication
  - Engineering + QA
  - Write access for QA testing
```

#### Production Environment

```yaml
Provisioning:
  Method: Terraform
  Infrastructure: AWS EKS (dedicated cluster, multi-AZ)
  Namespace: hive

Data Management:
  - Real customer data
  - Strict GDPR compliance
  - Daily backups
  - 30-day retention
  - Encryption at rest

Deployment:
  - Manual approval required (2 approvers)
  - Change advisory board review
  - Maintenance window preferred
  - Automatic rollback on failure
  - Canary deployment (10% traffic)

Access Control:
  - VPN + MFA required
  - Role-based access (RBAC)
  - Just-in-time access for incidents
  - Full audit logging
  - SOC 2 compliance
  - Break-glass procedure documented
```

---

## Part 4: Observability & Operations (30 points)

### Task 4.1: Monitoring Stack

#### 1. Key Metrics (10+)

**System Metrics:**
1. `cpu_usage_percent` - CPU utilization per pod
2. `memory_usage_bytes` - Memory consumption
3. `disk_io_operations` - Disk I/O operations
4. `network_bytes_in/out` - Network traffic

**Application Metrics:**
5. `http_requests_total` - Total HTTP requests (by status code)
6. `http_request_duration_seconds` - Request latency histogram
7. `active_connections` - Current WebSocket connections
8. `agent_runs_total` - Total agent executions

**Business Metrics:**
9. `llm_tokens_used` - LLM token consumption
10. `llm_requests_total` - LLM API calls (by provider)
11. `llm_request_duration_seconds` - LLM response time
12. `tool_calls_total` - Tool usage (by tool name)
13. `agent_success_rate` - Percentage of successful runs
14. `agent_completion_time` - Time to complete agent tasks

#### 2. Logging Strategy

```yaml
Logging Configuration:
  Format: JSON structured logs
  Fields:
    - timestamp
    - level
    - service
    - trace_id
    - span_id
    - message
    - error (if applicable)
    - context (request details)

  Log Levels:
    Production: INFO
    Staging: DEBUG
    Development: DEBUG

  Aggregation:
    Stack: Loki + Grafana
    Retention: 30 days (hot), 1 year (cold storage)
    Index: By service, level, trace_id

  Sensitive Data:
    - Redact API keys
    - Mask PII fields
    - No raw user input logged
```

**Example structured log:**
```json
{
  "timestamp": "2025-01-25T10:30:00Z",
  "level": "INFO",
  "service": "hive-tools",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "Tool execution completed",
  "tool": "web_search",
  "duration_ms": 234,
  "success": true
}
```

#### 3. Distributed Tracing

```yaml
Tracing Configuration:
  Backend: Jaeger / Tempo
  Sampling: 10% normal, 100% errors

  Instrumentation:
    - HTTP requests (automatic)
    - Database queries (manual)
    - LLM API calls (manual)
    - Tool executions (manual)

  Context Propagation:
    Headers: W3C Trace Context
    Format: traceparent, tracestate

  Key Spans:
    1. agent_run - Full agent execution
    2. llm_call - Individual LLM request
    3. tool_call - Tool execution
    4. db_query - Database operations
```

#### 4. Dashboard Designs

**Dashboard 1: Service Health Overview**
```
┌─────────────────────────────────────────────────────────────┐
│                    HIVE SERVICE HEALTH                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Request Rate   │  Error Rate     │  P99 Latency            │
│  ████████ 1.2k  │  ██ 0.3%        │  ███████ 245ms          │
├─────────────────┴─────────────────┴─────────────────────────┤
│                  Request Rate Over Time                      │
│  ^                                                           │
│  │    ╭──╮   ╭────╮                                         │
│  │ ╭──╯  ╰───╯    ╰──────╮                                  │
│  │─╯                      ╰──                               │
│  └──────────────────────────────────────────────>           │
├─────────────────────────────────────────────────────────────┤
│  Pod Status:  ● tools-1 ● tools-2 ● tools-3                 │
│  Uptime: 99.97%  │  Last Deploy: 2h ago                     │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard 2: Agent Performance**
```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT PERFORMANCE                         │
├──────────────────────────┬──────────────────────────────────┤
│  Active Agents           │  Success Rate                     │
│  ████████████ 87         │  ████████████████████ 98.5%       │
├──────────────────────────┴──────────────────────────────────┤
│  Agent Completion Time Distribution                          │
│  < 1s  ████████████████████████████████ 45%                 │
│  1-5s  ██████████████████ 30%                               │
│  5-30s ████████ 15%                                         │
│  > 30s ████ 10%                                             │
├─────────────────────────────────────────────────────────────┤
│  Top Tools Used (24h)                                        │
│  1. web_search    ████████████████ 5,234                    │
│  2. calculator    ████████ 2,891                            │
│  3. file_read     ██████ 1,567                              │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard 3: LLM Usage & Costs**
```
┌─────────────────────────────────────────────────────────────┐
│                    LLM USAGE & COSTS                         │
├─────────────────────────────────────────────────────────────┤
│  Daily Token Usage                                           │
│  ^                                                           │
│  │         ╭──────╮                                         │
│  │    ╭────╯      ╰────╮                                    │
│  │────╯                 ╰──────                             │
│  └──────────────────────────────────────────────>           │
│  Input: 2.3M tokens  │  Output: 890K tokens                 │
├──────────────────────────┬──────────────────────────────────┤
│  Cost Today              │  Monthly Budget                   │
│  $127.45                 │  $3,000 ██████████░░░ 65%         │
├──────────────────────────┴──────────────────────────────────┤
│  By Provider (24h)                                           │
│  Anthropic  ████████████████████ 78%  $99.41                │
│  OpenAI     ████████ 22%              $28.04                │
└─────────────────────────────────────────────────────────────┘
```

#### 5. Docker Compose for Monitoring

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

  loki:
    image: grafana/loki:2.9.0
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki/loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.0
    container_name: promtail
    volumes:
      - ./monitoring/promtail/promtail-config.yml:/etc/promtail/config.yml
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    restart: unless-stopped

  jaeger:
    image: jaegertracing/all-in-one:1.52
    container_name: jaeger
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.ignored-mount-points=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

---

### Task 4.2: Alerting Rules

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: hive-critical
    rules:
      # Alert 1: High Error Rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
          runbook_url: "https://wiki.example.com/runbooks/high-error-rate"

      # Alert 2: Service Down
      - alert: ServiceDown
        expr: up{job="hive-tools"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Hive service is down"
          description: "{{ $labels.instance }} has been down for more than 1 minute"
          runbook_url: "https://wiki.example.com/runbooks/service-down"

      # Alert 3: High Latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
          > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency detected"
          description: "P99 latency is {{ $value | humanizeDuration }} (threshold: 2s)"

      # Alert 4: Budget Exceeded
      - alert: LLMBudgetExceeded
        expr: |
          sum(increase(llm_cost_dollars_total[24h])) > 500
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Daily LLM budget exceeded"
          description: "LLM costs today: ${{ $value | printf \"%.2f\" }} (budget: $500)"

      # Alert 5: Database Connection Issues
      - alert: DatabaseConnectionFailures
        expr: |
          sum(rate(mongodb_connection_errors_total[5m])) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failures"
          description: "{{ $value | printf \"%.1f\" }} connection errors/sec"

      # Alert 6: Memory Pressure
      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes{container="tools"}
          / container_spec_memory_limit_bytes{container="tools"} > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }} of limit"

      # Alert 7: Pod Restart Loop
      - alert: PodRestartLoop
        expr: |
          increase(kube_pod_container_status_restarts_total{namespace="hive"}[1h]) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Pod in restart loop"
          description: "{{ $labels.pod }} has restarted {{ $value }} times in the last hour"

      # Alert 8: LLM Provider Errors
      - alert: LLMProviderErrors
        expr: |
          sum(rate(llm_requests_total{status="error"}[5m]))
          / sum(rate(llm_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High LLM provider error rate"
          description: "{{ $value | humanizePercentage }} of LLM requests are failing"

      # Alert 9: Disk Space Low
      - alert: DiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Only {{ $value | humanizePercentage }} disk space remaining"

      # Alert 10: Certificate Expiring
      - alert: CertificateExpiringSoon
        expr: |
          (probe_ssl_earliest_cert_expiry - time()) / 86400 < 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "SSL certificate expiring soon"
          description: "Certificate expires in {{ $value | printf \"%.0f\" }} days"
```

---

### Task 4.3: Incident Response Runbook

```markdown
# Runbook: High Agent Latency

**Severity:** P2 - Major Impact
**Owner:** Platform Team
**Last Updated:** January 2025

---

## Symptoms

- Agent response times > 10s (normal: 2s)
- Dashboard showing degraded status
- User complaints about slow agents
- Increased timeout errors in logs

---

## Detection Mechanism

**Automated Detection:**
1. Prometheus alert `HighLatency` fires when P99 > 2s for 5 minutes
2. Synthetic monitoring detects response time degradation
3. Error rate alerts may fire for timeouts

**Manual Detection:**
- User reports via support tickets
- Slack #hive-alerts channel notifications
- Grafana dashboard anomaly

---

## Initial Triage

### Immediate Actions (First 5 minutes)

- [ ] Acknowledge incident in PagerDuty
- [ ] Create incident channel: #inc-YYYYMMDD-latency
- [ ] Notify stakeholders in #hive-incidents

### Quick Health Checks

```bash
# Check service health
kubectl get pods -n hive -l app=hive-tools
curl -w "%{time_total}" https://api.hive.example.com/health

# Check recent deployments
kubectl rollout history deployment/hive-tools -n hive

# Check resource usage
kubectl top pods -n hive
```

### Initial Questions

1. [ ] Is this affecting all agents or specific ones?
2. [ ] Is the backend healthy? (health endpoint responding?)
3. [ ] Are databases responsive?
4. [ ] Did a deployment happen recently?
5. [ ] Are external APIs (LLM providers) having issues?

---

## Diagnostic Decision Tree

```
                    High Latency Detected
                            │
                            ▼
                  ┌─────────────────┐
                  │ Backend Health? │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
         Unhealthy                   Healthy
              │                         │
              ▼                         ▼
    Check Pod Status          ┌─────────────────┐
    (See Resolution A)        │ Database Slow?  │
                              └────────┬────────┘
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                        Yes                        No
                          │                         │
                          ▼                         ▼
                  Check MongoDB            ┌─────────────────┐
                  (See Resolution B)       │ LLM API Slow?   │
                                           └────────┬────────┘
                                                    │
                                       ┌────────────┴────────────┐
                                       ▼                         ▼
                                     Yes                        No
                                       │                         │
                                       ▼                         ▼
                               Check LLM Status         Check Application
                               (See Resolution C)       (See Resolution D)
```

---

## Resolution Steps

### Resolution A: Pod/Service Issues

**Symptoms:** Pods crashing, not ready, high restarts

```bash
# Check pod status
kubectl describe pod -n hive -l app=hive-tools

# Check recent events
kubectl get events -n hive --sort-by='.lastTimestamp'

# Check logs for errors
kubectl logs -n hive -l app=hive-tools --tail=100 | grep -i error
```

**Actions:**
1. If OOMKilled: Increase memory limits
2. If CrashLoopBackOff: Check logs for startup errors
3. If stuck in Pending: Check node resources
4. **Quick fix:** Restart deployment
   ```bash
   kubectl rollout restart deployment/hive-tools -n hive
   ```

### Resolution B: Database Issues

**Symptoms:** Slow queries, connection timeouts

```bash
# Check MongoDB status
mongosh --eval "db.serverStatus()"

# Check slow queries
mongosh --eval "db.currentOp({'secs_running': {\$gt: 5}})"

# Check connection pool
mongosh --eval "db.serverStatus().connections"
```

**Actions:**
1. Kill long-running queries if blocking
2. Check index usage on slow queries
3. Scale up read replicas if under load
4. **Quick fix:** Restart application connections
   ```bash
   kubectl rollout restart deployment/hive-tools -n hive
   ```

### Resolution C: LLM Provider Issues

**Symptoms:** High latency on LLM calls, API errors

```bash
# Check LLM provider status pages
# - https://status.anthropic.com
# - https://status.openai.com

# Check our metrics
curl -s localhost:9090/api/v1/query?query=llm_request_duration_seconds
```

**Actions:**
1. If provider outage: Switch to backup provider (if configured)
2. If rate limited: Reduce concurrent requests
3. If our issue: Check API key validity
4. **Quick fix:** Enable LLM request caching (increases hit rate)

### Resolution D: Application Issues

**Symptoms:** High CPU, inefficient code paths

```bash
# Check CPU profiling
kubectl exec -it <pod> -- python -m cProfile -s cumtime

# Check memory profiling
kubectl exec -it <pod> -- python -m memory_profiler

# Check for blocking operations
kubectl logs <pod> | grep -i "took.*seconds"
```

**Actions:**
1. Identify hot code paths
2. Check for N+1 query issues
3. Verify async operations are non-blocking
4. **Quick fix:** Scale horizontally
   ```bash
   kubectl scale deployment/hive-tools --replicas=5 -n hive
   ```

---

## Escalation Path

| Time Since Detection | Action |
|---------------------|--------|
| 0-15 minutes | On-call engineer investigates |
| 15-30 minutes | Escalate to senior engineer |
| 30-60 minutes | Escalate to engineering manager |
| 1+ hours | Consider rollback, executive notification |

---

## Post-Mortem Template

```markdown
# Incident Post-Mortem: [Title]

**Date:** YYYY-MM-DD
**Duration:** X hours Y minutes
**Severity:** P1/P2/P3
**Author:** [Name]

## Summary
[2-3 sentence summary of what happened]

## Timeline (all times UTC)
- HH:MM - Alert fired
- HH:MM - On-call acknowledged
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

## Impact
- Users affected: X
- Requests failed: Y
- Revenue impact: $Z (if applicable)

## Root Cause
[Detailed explanation of what caused the incident]

## Resolution
[What was done to fix the immediate issue]

## Lessons Learned
### What went well
-

### What went poorly
-

### Where we got lucky
-

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | YYYY-MM-DD | Open |
| [Action 2] | [Name] | YYYY-MM-DD | Open |

## Supporting Information
- [Link to dashboard during incident]
- [Link to relevant logs]
- [Link to Slack thread]
```

---

## Part 5: Security Hardening (Bonus - 20 points)

### Task 5.1: Security Audit

#### 1. Network - Exposed Ports Analysis

| Port | Service | Necessary? | Recommendation |
|------|---------|------------|----------------|
| 4001 | MCP Server | Yes | Restrict to internal network only |
| 9090 | Prometheus | Internal | Add authentication |
| 3000 | Grafana | Internal | Enforce SSO |
| 27017 | MongoDB | Internal | VPC only, no public access |
| 6379 | Redis | Internal | VPC only, require AUTH |

**Recommendations:**
- Use Network Policies to restrict pod-to-pod communication
- Implement service mesh (Istio) for mTLS
- No public-facing database ports

```yaml
# Network Policy Example
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: hive-tools-netpol
  namespace: hive
spec:
  podSelector:
    matchLabels:
      app: hive-tools
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: hive
        - podSelector:
            matchLabels:
              app: ingress-nginx
      ports:
        - port: 4001
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: hive
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - port: 443  # HTTPS for LLM APIs
```

#### 2. Secrets Management Review

**Current State:**
- Environment variables in containers
- `.env` files (gitignored)
- Kubernetes Secrets (base64 encoded)

**Issues:**
- Secrets visible in pod spec
- No rotation mechanism
- No audit trail

**Recommendations:**
1. Use External Secrets Operator with AWS Secrets Manager
2. Implement secret rotation (quarterly minimum)
3. Enable secret scanning in CI/CD
4. Use sealed-secrets for GitOps

```yaml
# External Secrets Example
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: hive-secrets
  namespace: hive
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: hive-secrets
  data:
    - secretKey: anthropic-api-key
      remoteRef:
        key: hive/production/anthropic
        property: api_key
```

#### 3. API Authentication Analysis

**Current Implementation:**
- API key validation via environment variable
- Two-tier credential validation (startup vs. tool-level)

**Recommendations:**
1. Implement OAuth 2.0 / OIDC for user authentication
2. Use JWT tokens with short expiration
3. Add rate limiting per API key
4. Implement API key scopes/permissions

```python
# Recommended auth middleware
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["RS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### 4. Container Security Scanning

**Recommended Tools:**
1. **Trivy** - Vulnerability scanning for images
2. **Snyk** - Dependency scanning
3. **Falco** - Runtime security monitoring
4. **OPA/Gatekeeper** - Policy enforcement

```yaml
# CI/CD Security Scanning Addition
security-scan:
  runs-on: ubuntu-latest
  steps:
    - name: Trivy vulnerability scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ env.IMAGE }}
        severity: 'HIGH,CRITICAL'
        exit-code: '1'

    - name: Snyk dependency scan
      uses: snyk/actions/docker@master
      with:
        image: ${{ env.IMAGE }}
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

#### 5. Database Hardening

**MongoDB Security Checklist:**
- [ ] Enable authentication (SCRAM-SHA-256)
- [ ] Create application-specific users with minimal privileges
- [ ] Enable TLS for all connections
- [ ] Disable JavaScript execution
- [ ] Enable audit logging
- [ ] Bind to private IP only
- [ ] Enable encryption at rest

```yaml
# MongoDB secure configuration
security:
  authorization: enabled
  javascriptEnabled: false

net:
  bindIp: 127.0.0.1
  tls:
    mode: requireTLS
    certificateKeyFile: /etc/ssl/mongodb.pem
    CAFile: /etc/ssl/ca.pem

auditLog:
  destination: file
  format: JSON
  path: /var/log/mongodb/audit.log
```

---

### Task 5.2: SOC 2 Compliance Checklist

#### 1. Access Control Improvements

| Requirement | Current State | Action Needed |
|-------------|--------------|---------------|
| Unique user IDs | Partial | Implement SSO with unique identifiers |
| Role-based access | Basic | Implement RBAC in Kubernetes |
| Least privilege | Not enforced | Define minimal role permissions |
| MFA | Not required | Require MFA for all access |
| Access reviews | Not performed | Quarterly access reviews |

**Implementation:**
```yaml
# Kubernetes RBAC Example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: hive-developer
  namespace: hive
rules:
  - apiGroups: [""]
    resources: ["pods", "logs"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: []  # No exec access

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: hive-operator
  namespace: hive
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "update"]
```

#### 2. Audit Logging Requirements

**Required Logs:**
- All authentication attempts (success/failure)
- Authorization decisions
- Data access events
- Configuration changes
- Administrative actions

**Implementation:**
```yaml
# Kubernetes Audit Policy
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
    resources:
      - group: ""
        resources: ["secrets", "configmaps"]

  - level: RequestResponse
    users: ["system:serviceaccount:hive:hive-tools"]
    verbs: ["create", "update", "delete"]
    resources:
      - group: ""
        resources: ["pods"]
```

**Log Retention:**
- Minimum 1 year for audit logs
- Tamper-evident storage (immutable)
- Centralized logging with access controls

#### 3. Encryption Requirements

| Data State | Requirement | Implementation |
|------------|-------------|----------------|
| In Transit | TLS 1.2+ | Enforce via ingress, service mesh |
| At Rest | AES-256 | EBS encryption, MongoDB encryption |
| In Memory | Minimize PII | Secure coding practices |
| Backups | Encrypted | AWS backup encryption |

**TLS Configuration:**
```yaml
# Ingress TLS Policy
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.2 TLSv1.3"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256"
```

#### 4. Data Retention Policies

| Data Type | Retention Period | Destruction Method |
|-----------|-----------------|-------------------|
| Application logs | 1 year | Automated deletion |
| Audit logs | 7 years | Archive, then secure delete |
| User data | As needed | Upon request/account deletion |
| Backups | 30 days active, 1 year archive | Secure overwrite |
| Session data | 24 hours | Automatic expiration |

**Implementation:**
```yaml
# Loki retention configuration
retention_deletes_enabled: true
retention_period: 8760h  # 1 year

# S3 lifecycle policy for archives
Lifecycle:
  Rules:
    - ID: AuditLogRetention
      Status: Enabled
      Transitions:
        - Days: 90
          StorageClass: GLACIER
      Expiration:
        Days: 2555  # 7 years
```

#### 5. Incident Response Requirements

**Required Components:**

1. **Incident Response Plan**
   - Documented procedures
   - Defined roles and responsibilities
   - Communication templates
   - Regular testing (annual)

2. **Detection Capabilities**
   - Real-time alerting
   - Log aggregation and analysis
   - Anomaly detection

3. **Response Procedures**
   - Incident classification matrix
   - Escalation procedures
   - Evidence preservation
   - Customer notification process

4. **Recovery**
   - Business continuity plan
   - Disaster recovery procedures
   - Tested backup restoration

**Incident Classification:**
| Severity | Description | Response Time | Example |
|----------|-------------|---------------|---------|
| P1 - Critical | Service down, data breach | 15 minutes | Complete outage |
| P2 - Major | Significant degradation | 1 hour | 50% capacity |
| P3 - Minor | Limited impact | 4 hours | Single feature |
| P4 - Low | Minimal impact | 24 hours | Cosmetic issue |

---

## Submission Checklist

- [x] Part 1 infrastructure analysis
- [x] Part 2 deployment designs and manifests
- [x] Part 3 CI/CD pipeline YAML
- [x] Part 4 monitoring and alerting configs
- [x] Part 5 security analysis (Bonus)

---

**Total Points: 100 + 20 (Bonus) = 120 possible points**
