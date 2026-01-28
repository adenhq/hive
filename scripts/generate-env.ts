/**
 * Environment Generator Script
 *
 * Reads config.yaml and generates .env files for each service.
 * This provides a single source of truth for configuration while
 * maintaining compatibility with standard .env file workflows.
 *
 * Usage: npx tsx scripts/generate-env.ts
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs';
import { parse } from 'yaml';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..');

interface Config {
  app: {
    name: string;
    environment: string;
    log_level: string;
  };
  server: {
    frontend: {
      port: number;
    };
    backend: {
      port: number;
      host: string;
    };
  };
  timescaledb: {
    url: string;
    port: number;
  };
  mongodb: {
    url: string;
    database: string;
    erp_database: string;
    port: number;
  };
  redis: {
    url: string;
    port: number;
  };
  auth: {
    jwt_secret: string;
    jwt_expires_in: string;
    passphrase: string;
  };
  npm: {
    token: string;
  };
  cors: {
    origin: string;
  };
  features: {
    registration: boolean;
    rate_limiting: boolean;
    request_logging: boolean;
    mcp_server: boolean;
  };
}

function loadConfig(): Config {
  const configPath = join(PROJECT_ROOT, 'config.yaml');

  if (!existsSync(configPath)) {
    console.error('Error: config.yaml not found.');
    console.error('Run: cp config.yaml.example config.yaml');
    process.exit(1);
  }

  const configContent = readFileSync(configPath, 'utf-8');
  return parse(configContent) as Config;
}

function generateRootEnv(config: Config): string {
  return `# Generated from config.yaml - do not edit directly
# Regenerate with: npm run generate:env

# Application
NODE_ENV=${config.app.environment}
APP_NAME=${config.app.name}
LOG_LEVEL=${config.app.log_level}

# Ports
FRONTEND_PORT=${config.server.frontend.port}
BACKEND_PORT=${config.server.backend.port}
TSDB_PORT=${config.timescaledb.port}
MONGODB_PORT=${config.mongodb.port}
REDIS_PORT=${config.redis.port}

# API URL for frontend
VITE_API_URL=http://localhost:${config.server.backend.port}

# MongoDB
MONGODB_DBNAME=${config.mongodb.database}
MONGODB_ERP_DBNAME=${config.mongodb.erp_database}

# Authentication
JWT_SECRET=${config.auth.jwt_secret}
PASSPHRASE=${config.auth.passphrase}

# NPM (for Docker builds with private packages)
NPM_TOKEN=${config.npm.token}

# CORS
CORS_ORIGIN=${config.cors.origin}
`;
}

function generateFrontendEnv(config: Config): string {
  return `# Generated from config.yaml - do not edit directly
# Regenerate with: npm run generate:env

VITE_API_URL=http://localhost:${config.server.backend.port}
VITE_APP_NAME=${config.app.name}
VITE_APP_ENV=${config.app.environment}
`;
}

function generateBackendEnv(config: Config): string {
  return `# Generated from config.yaml - do not edit directly
# Regenerate with: npm run generate:env

# Server
NODE_ENV=${config.app.environment}
PORT=${config.server.backend.port}

# Application
LOG_LEVEL=${config.app.log_level}

# TimescaleDB (PostgreSQL)
TSDB_PG_URL=${config.timescaledb.url}

# MongoDB
MONGODB_URL=${config.mongodb.url}
MONGODB_DBNAME=${config.mongodb.database}
MONGODB_ERP_DBNAME=${config.mongodb.erp_database}

# Redis
REDIS_URL=${config.redis.url}

# Authentication
JWT_SECRET=${config.auth.jwt_secret}
PASSPHRASE=${config.auth.passphrase}

# Features
FEATURE_MCP_SERVER=${config.features.mcp_server}
`;
}

function createOrAppend(path: string, content: string) {
  let options = {};
  if (existsSync(path)) {
    options['flag'] = 'a';
  } else {
    mkdirSync(dirname(path), { recursive: true });
  }
  writeFileSync(path, content, options);
}

function main() {
  console.log('Generating environment files from config.yaml...\n');

  const config = loadConfig();

  // Generate root .env (for docker-compose)
  const rootEnvPath = join(PROJECT_ROOT, '.env');
  createOrAppend(rootEnvPath, generateRootEnv(config));
  console.log(`✓ Generated ${rootEnvPath}`);

  // Generate frontend .env
  const frontendEnvPath = join(PROJECT_ROOT, 'honeycomb', '.env');
  createOrAppend(frontendEnvPath, generateFrontendEnv(config));
  console.log(`✓ Generated ${frontendEnvPath}`);

  // Generate backend .env
  const backendEnvPath = join(PROJECT_ROOT, 'hive', '.env');
  createOrAppend(backendEnvPath, generateBackendEnv(config));
  console.log(`✓ Generated ${backendEnvPath}`);

  console.log('\nDone! Environment files have been generated.');
  console.log('\nNote: These files are git-ignored. Regenerate after editing config.yaml.');
}

main();
