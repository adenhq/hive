/**
 * Environment Generator Script
 *
 * Reads config.yaml and generates .env files for each service.
 * This provides a single source of truth for configuration while
 * maintaining compatibility with standard .env file workflows.
 *
 * Usage: npx tsx scripts/generate-env.ts
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { parse } from 'yaml';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { z } from 'zod'; 

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..');

// ------------------------------------------------------------------
// 1. Define the Validation Schema
// ------------------------------------------------------------------
const ConfigSchema = z.object({
  app: z.object({
    name: z.string().min(1, "App name is required"),
    environment: z.enum(['development', 'production', 'test']).default('development'),
    log_level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  }),
  server: z.object({
    frontend: z.object({
      port: z.number().int().min(1).max(65535, "Invalid frontend port"),
    }),
    backend: z.object({
      port: z.number().int().min(1).max(65535, "Invalid backend port"),
      host: z.string().default('0.0.0.0'),
    }),
  }),
  timescaledb: z.object({
    url: z.string().url("Invalid TimescaleDB URL"),
    port: z.number().int().min(1).max(65535),
  }),
  mongodb: z.object({
    url: z.string().min(1, "MongoDB URL is required"),
    database: z.string().min(1),
    erp_database: z.string().min(1),
    port: z.number().int().min(1).max(65535),
  }),
  redis: z.object({
    url: z.string().min(1, "Redis URL is required"),
    port: z.number().int().min(1).max(65535),
  }),
  auth: z.object({
    jwt_secret: z.string().min(8, "JWT secret must be at least 8 chars"),
    jwt_expires_in: z.string(),
    passphrase: z.string().min(8, "Passphrase must be at least 8 chars"),
  }),
  npm: z.object({
    token: z.string().optional().default(''),
  }),
  cors: z.object({
    origin: z.string().min(1),
  }),
  features: z.object({
    registration: z.boolean(),
    rate_limiting: z.boolean(),
    request_logging: z.boolean(),
    mcp_server: z.boolean(),
  }),
});

// ------------------------------------------------------------------
// 2. Infer Type from Schema (Single Source of Truth)
// ------------------------------------------------------------------
type Config = z.infer<typeof ConfigSchema>;

function loadConfig(): Config {
  const configPath = join(PROJECT_ROOT, 'config.yaml');

  if (!existsSync(configPath)) {
    console.error('Error: config.yaml not found.');
    console.error('Run: cp config.yaml.example config.yaml');
    process.exit(1);
  }

  try {
    const configContent = readFileSync(configPath, 'utf-8');
    const rawConfig = parse(configContent);

    // ------------------------------------------------------------------
    // 3. Validate Data
    // ------------------------------------------------------------------
    return ConfigSchema.parse(rawConfig);

  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('\nConfiguration Validation Failed:');
      error.issues.forEach((err: any) => {
        console.error(`   -> [${err.path.join('.')}] ${err.message}`);
      });
      process.exit(1);
    }
    throw error;
  }
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
NPM_TOKEN=${config.npm.token || ''}

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

function main() {
  // Check for --dry-run flag
  const isDryRun = process.argv.includes('--dry-run');

  console.log(`Generating environment files from config.yaml...${isDryRun ? ' (DRY RUN)' : ''}\n`);

  // This will throw and exit(1) if invalid, effectively testing the config
  const config = loadConfig(); 

  if (isDryRun) {
    console.log('Configuration is valid!');
    console.log('Skipping file generation (dry-run mode).');
    return; // Stop here, don't write files
  }

  // Generate root .env (for docker-compose)
  const rootEnvPath = join(PROJECT_ROOT, '.env');
  writeFileSync(rootEnvPath, generateRootEnv(config));
  console.log(`✓ Generated ${rootEnvPath}`);

  // Generate frontend .env
  const frontendEnvPath = join(PROJECT_ROOT, 'honeycomb', '.env');
  writeFileSync(frontendEnvPath, generateFrontendEnv(config));
  console.log(`✓ Generated ${frontendEnvPath}`);

  // Generate backend .env
  const backendEnvPath = join(PROJECT_ROOT, 'hive', '.env');
  writeFileSync(backendEnvPath, generateBackendEnv(config));
  console.log(`✓ Generated ${backendEnvPath}`);

  console.log('\nDone! Environment files have been generated.');
  console.log('\nNote: These files are git-ignored. Regenerate after editing config.yaml.');
}
main();