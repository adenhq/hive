# Docker Hub Toolkit

Native integration with Docker Hub for Hive agents.

## Overview
The Docker Hub toolkit allows agents to list repositories for users/organizations, fetch image tags, and retrieve detailed tag metadata, supporting automation and infrastructure awareness tasks.

## Requirements
- `httpx` library (installed as a base dependency)
- Docker Hub Personal Access Token (PAT)

## Configuration
Requires the following environment variable or credential:
- `DOCKER_HUB_TOKEN`: Docker Hub Personal Access Token.

## Available Tools

### Repository Management
- `dockerhub_list_repositories`: List repositories for a specific user or organization.

### Tag Management
- `dockerhub_list_tags`: List all image tags for a repository.
- `dockerhub_get_tag_metadata`: Get detailed information (digest, size, OS/Arch) for a specific tag.

## Setup Instructions
1. Log in to [Docker Hub](https://hub.docker.com/).
2. Navigate to **Account Settings → Security**.
3. Create a new **Access Token** with 'Read-only' permissions.
4. Copy the token and set it in your environment:
   ```bash
   export DOCKER_HUB_TOKEN=your_token_here
   ```
