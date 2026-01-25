# Architecture Overview

This document describes the high-level architecture of Hive.

## System Overview

```mermaid
flowchart LR
    Client["Client<br/>(Web Browser)"]
    Client --> DockerNetwork
    subgraph DockerNetwork["Docker Network"]

        direction TB

        subgraph Honeycomb["honeycomb<br/>(Frontend)<br/>React + Vite<br/>Port: 3000"]

            spacerH2[" "]
            Nginx["Nginx<br/>(production)"]
            
            spacerH2 ~~~ Nginx
        end

        subgraph Hive["hive<br/>(Backend)<br/>Express + TypeScript<br/>Port: 4000"]

            spacerB2[" "]
            Routes["Routes<br/>/api, /health"]
            Controllers["Controllers"]
            Services["Services"]                        
            
            spacerB2 ~~~ Services
            Routes --> Controllers
            Controllers --> Services
        end
        
        Honeycomb --> Hive
             
    end
    
    Services --> Database[("Database<br/>(PostgreSQL/etc)")]
    
    style spacerH2 fill:none,stroke:none
    style spacerB2 fill:none,stroke:none

    classDef clientStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px,color:#000
    classDef frontendStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    classDef backendStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#000
    classDef databaseStyle fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef componentStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000

    class Client clientStyle
    class Nginx,Routes,Controllers,Services componentStyle
    class Honeycomb frontendStyle
    class Hive backendStyle
    class Database databaseStyle

    linkStyle 3 stroke:#1b5e20,stroke-width:2px
    linkStyle 4 stroke:#1b5e20,stroke-width:2px
    linkStyle 6 stroke:#1b5e20,stroke-width:2px
```

## Components

### Frontend (honeycomb/)

The frontend is a single-page application built with:

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing

**Key Directories:**

| Directory | Purpose |
|-----------|---------|
| `src/components/` | Reusable UI components |
| `src/pages/` | Page-level components (routes) |
| `src/hooks/` | Custom React hooks |
| `src/services/` | API client and external services |
| `src/types/` | TypeScript type definitions |
| `src/utils/` | Utility functions |
| `src/styles/` | Global styles and CSS |

**Production Build:**
- Vite builds static assets
- Nginx serves the built files
- API requests proxied to backend

### Backend (hive/)

The backend is a RESTful API built with:

- **Express** - Web framework
- **TypeScript** - Type safety
- **Zod** - Runtime validation
- **Helmet** - Security headers

**Key Directories:**

| Directory | Purpose |
|-----------|---------|
| `src/routes/` | API route definitions |
| `src/controllers/` | Request handlers |
| `src/services/` | Business logic |
| `src/middleware/` | Express middleware |
| `src/models/` | Data models |
| `src/types/` | TypeScript types |
| `src/utils/` | Utility functions |
| `src/config/` | Configuration loading |

**API Structure:**

```
GET  /health           # Health check endpoints
GET  /health/ready     # Readiness probe
GET  /health/live      # Liveness probe

GET  /api              # API info
GET  /api/users        # Example resource
```

## Request Flow

1. **Client** makes HTTP request
2. **Nginx** (production) or **Vite** (dev) receives request
3. Static assets served directly; API requests proxied
4. **Express** receives API request
5. **Middleware** processes (auth, logging, validation)
6. **Router** matches route to controller
7. **Controller** handles request, calls services
8. **Service** executes business logic
9. **Response** returned to client

## Configuration System

```
config.yaml
    │
    ▼
generate-env.ts  ──────────────────┐
    │                              │
    ▼                              ▼
.env (root)              honeycomb/.env
    │                              │
    ▼                              ▼
docker-compose.yml        Vite (frontend)
    │
    ▼
hive/.env
    │
    ▼
Express (backend)
```

## Docker Architecture

**Production:**
```
docker-compose.yml
├── honeycomb (frontend)
│   └── Dockerfile (multi-stage: build → nginx)
└── hive (backend)
    └── Dockerfile (multi-stage: build → node)
```

**Development:**
```
docker-compose.yml + docker-compose.override.yml
├── honeycomb (frontend)
│   └── Dockerfile.dev (vite dev server)
└── hive (backend)
    └── Dockerfile.dev (tsx watch)
```

## Scaling Considerations

### Horizontal Scaling

Both frontend and backend are stateless and can be scaled horizontally:

```yaml
# docker-compose.yml
services:
  hive:
    deploy:
      replicas: 3
```

### Database

- Use connection pooling
- Consider read replicas for heavy read loads
- Implement caching layer if needed

### Caching

Options for caching:
- Redis for session/cache storage
- CDN for static assets
- HTTP caching headers

## Security

### Frontend
- Served over HTTPS (configure in nginx/reverse proxy)
- CSP headers via nginx
- No sensitive data in client code

### Backend
- Helmet.js for security headers
- CORS configured for specific origins
- Input validation with Zod
- JWT for authentication
- Rate limiting (configurable)

## Monitoring

### Health Checks
- `/health` - Overall health
- `/health/ready` - Ready to accept traffic
- `/health/live` - Process is alive

### Logging
- Structured JSON logs in production
- Configurable log levels
- Request logging via Morgan

## Development Workflow

1. Edit code in `honeycomb/` or `hive/`
2. Hot reload updates automatically
3. Run tests: `npm run test`
4. Lint: `npm run lint`
5. Build: `npm run build`
