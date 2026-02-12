# Docker Setup Guide

This guide explains how to run Hive using Docker, which is especially useful for Windows users who want to avoid WSL/Git Bash requirements.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/adenhq/hive.git
cd hive
```

### 2. Configure API Keys

Create a `.env` file in the project root with your API keys:

```bash
# .env
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
MISTRAL_API_KEY=your_mistral_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
```

> **Note:** You only need to set the API keys for the LLM providers you plan to use.

### 3. Build and Run

```bash
docker-compose up --build
```

This will:
- Build the Docker image with all dependencies
- Install Python packages using `uv`
- Install Playwright browsers for web automation
- Launch the interactive TUI (Terminal User Interface)

### 4. Interact with the TUI

The Hive TUI will appear in your terminal. You can:
- Browse available agents in `exports/` and `examples/templates/`
- Select and run agents
- View execution logs and monitoring data
- Interact with running agents

## Running Specific Agents

To run a specific agent instead of the TUI:

```bash
docker-compose run --rm hive run exports/your_agent_name --input '{"key": "value"}'
```

## Alternative: Run in Interactive Shell

To get a shell inside the container:

```bash
docker exec -it hive-framework /bin/bash
```

Then you can run commands directly:

```bash
hive tui              # Launch the TUI
hive run exports/agent_name --input '{...}'  # Run a specific agent
hive --help           # View all available commands
```

## Volume Mounts

The `docker-compose.yml` configuration mounts:

- **Project directory** (`./` → `/app`): Your local code is synced to the container
- **Credentials** (`~/.hive` → `/root/.hive`): Persists API keys and configuration across container restarts
- **Virtual environments**: Excluded from sync to avoid conflicts between host and container

## Troubleshooting

### Line Ending Issues (Windows)

If you encounter errors like `/usr/bin/env: 'bash\r': No such file or directory`, this is caused by Windows-style line endings (CRLF) in shell scripts.

**Solution:** The Dockerfile automatically fixes this using `dos2unix`. If you still encounter issues:

1. Ensure you're using the latest version of the Dockerfile
2. Rebuild the image: `docker-compose build --no-cache`

### Permission Issues

If you encounter permission errors with the `.hive` directory:

```bash
# On Linux/macOS
chmod -R 755 ~/.hive

# On Windows (PowerShell)
# The container will create the directory with appropriate permissions
```

### Container Won't Start

1. **Check Docker is running**: `docker --version`
2. **Check logs**: `docker logs hive-framework`
3. **Rebuild from scratch**: `docker-compose down && docker-compose up --build`

## Development Workflow

### Making Code Changes

Since your local directory is mounted into the container, changes to your code are immediately reflected. However, you may need to restart the container for some changes:

```bash
# Restart the container
docker-compose restart

# Or rebuild if you changed dependencies
docker-compose up --build
```

### Running Tests

```bash
docker-compose run --rm hive bash -c "cd core && pytest tests/ -v"
```

### Running Linters

```bash
docker-compose run --rm hive bash -c "make check"
```

## Comparison: Docker vs Native Setup

| Aspect | Docker | Native (quickstart.sh) |
|--------|--------|------------------------|
| **Windows Support** | ✅ Works on all Windows versions | ⚠️ Requires WSL or Git Bash |
| **Setup Time** | Slower initial build (~5-10 min) | Faster (~2-5 min) |
| **Isolation** | ✅ Fully isolated environment | ❌ Uses system Python |
| **Portability** | ✅ Consistent across all platforms | ⚠️ May vary by OS |
| **Development** | Requires container restart for some changes | Immediate changes |
| **Resource Usage** | Higher (container overhead) | Lower (native execution) |

## When to Use Docker

Docker is recommended if you:
- Are on **Windows** and want to avoid WSL setup
- Want a **consistent environment** across different machines
- Need **isolation** from your system Python installation
- Are **deploying** to production (Docker provides a production-ready setup)

## When to Use Native Setup

Native setup (`./quickstart.sh`) is recommended if you:
- Are on **Linux or macOS** with Python 3.11+ already installed
- Want **faster iteration** during development
- Prefer **direct access** to Python tools and debuggers
- Have **limited disk space** (Docker images can be large)

## Advanced Configuration

### Custom Dockerfile

If you need to customize the Docker image (e.g., add system dependencies):

1. Edit the `Dockerfile`
2. Add your custom steps
3. Rebuild: `docker-compose build`

### Environment Variables

You can pass additional environment variables in `docker-compose.yml`:

```yaml
environment:
  - ANTHROPIC_API_KEY
  - CUSTOM_VAR=value
```

### Port Mapping (Future)

Currently, Hive runs as a TUI application without web ports. If future versions add a web interface, you can expose ports in `docker-compose.yml`:

```yaml
ports:
  - "8000:8000"  # Example for future web UI
```

## Next Steps

- **[Getting Started Guide](getting-started.md)** - Learn how to build your first agent
- **[TUI Guide](tui-selection-guide.md)** - Master the interactive dashboard
- **[Developer Guide](developer-guide.md)** - Deep dive into agent development
- **[Configuration Guide](configuration.md)** - Advanced configuration options

## Support

If you encounter issues with Docker setup:
- Check the [GitHub Issues](https://github.com/adenhq/hive/issues)
- Join the [Discord community](https://discord.com/invite/MXE49hrKDk)
- Review the [Contributing Guide](../CONTRIBUTING.md)
