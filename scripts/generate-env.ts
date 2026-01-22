/**
 * Environment Generator Script
 *
 * Reads config.yaml and generates .env files for each service.
 * This provides a single source of truth for configuration while
 * maintaining compatibility with standard .env file workflows.
 *
 * Usage: npx tsx scripts/generate-env.ts [--dry-run]
 *
 * Options:
 *   --dry-run  Validate config.yaml without generating files
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { parse } from 'yaml';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { z } from 'zod';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..');

// Validation schema for config.yaml
const ConfigSchema = z.object({
  app: z.object({
    name: z.string().min(1, 'Application name cannot be empty'),
    environment: z.enum(['development', 'production', 'test'], {
      message: 'Environment must be one of: development, production, test',
    }),
    log_level: z.enum(['debug', 'info', 'warn', 'error'], {
      message: 'Log level must be one of: debug, info, warn, error',
    }),
  }),
  server: z.object({
    frontend: z.object({
      port: z.number().int().min(1, 'Port must be >= 1').max(65535, 'Port must be <= 65535'),
    }),
    backend: z.object({
      port: z.number().int().min(1, 'Port must be >= 1').max(65535, 'Port must be <= 65535'),
      host: z.string().min(1, 'Host cannot be empty'),
    }),
  }),
  timescaledb: z.object({
    url: z.string().url('TimescaleDB URL must be a valid URL').or(
      z.string().regex(/^postgresql:\/\/.+/, 'TimescaleDB URL must start with postgresql://')
    ),
    port: z.number().int().min(1, 'Port must be >= 1').max(65535, 'Port must be <= 65535'),
  }),
  mongodb: z.object({
    url: z.string().regex(/^mongodb:\/\/.+/, 'MongoDB URL must start with mongodb://'),
    database: z.string().min(1, 'Database name cannot be empty'),
    erp_database: z.string().min(1, 'ERP database name cannot be empty'),
    port: z.number().int().min(1, 'Port must be >= 1').max(65535, 'Port must be <= 65535'),
  }),
  redis: z.object({
    url: z.string().regex(/^redis:\/\/.+/, 'Redis URL must start with redis://'),
    port: z.number().int().min(1, 'Port must be >= 1').max(65535, 'Port must be <= 65535'),
  }),
  auth: z.object({
    jwt_secret: z.string().min(32, 'JWT secret must be at least 32 characters for security'),
    jwt_expires_in: z.string().regex(/^\d+[smhd]$/, 'JWT expiration must be in format: 1h, 7d, 30d, etc.'),
    passphrase: z.string().min(8, 'Passphrase must be at least 8 characters'),
  }),
  npm: z.object({
    token: z.string(), // Can be empty string
  }),
  cors: z.object({
    origin: z.string().url('CORS origin must be a valid URL'),
  }),
  features: z.object({
    registration: z.boolean(),
    rate_limiting: z.boolean(),
    request_logging: z.boolean(),
    mcp_server: z.boolean(),
  }),
});

type Config = z.infer<typeof ConfigSchema>;

function loadConfig(): Config {
  const configPath = join(PROJECT_ROOT, 'config.yaml');

  if (!existsSync(configPath)) {
    console.error('❌ Error: config.yaml not found.');
    console.error('Run: cp config.yaml.example config.yaml');
    process.exit(1);
  }

  let parsedConfig: unknown;
  try {
    const configContent = readFileSync(configPath, 'utf-8');
    parsedConfig = parse(configContent);
  } catch (error) {
    console.error('❌ Error: Failed to parse config.yaml');
    if (error instanceof Error) {
      console.error(`   ${error.message}`);
    }
    console.error('\nPlease check that config.yaml is valid YAML format.');
    process.exit(1);
  }

  // Validate the parsed config against the schema
  const result = ConfigSchema.safeParse(parsedConfig);

  if (!result.success) {
    console.error('❌ Error: config.yaml validation failed\n');
    console.error('The following issues were found:\n');

    // Format validation errors in a user-friendly way
    const errors = result.error.issues;
    errors.forEach((error, index) => {
      const path = error.path.join('.');
      console.error(`  ${index + 1}. Field: ${path}`);
      console.error(`     Issue: ${error.message}`);
      if (error.code === 'invalid_type') {
        console.error(`     Expected: ${error.expected}, Received: ${(error as any).received}`);
      }
      console.error('');
    });

    console.error('Please fix these issues in config.yaml and try again.');
    console.error('See config.yaml.example for reference.\n');
    process.exit(1);
  }

  return result.data;
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

function main() {
  const args = process.argv.slice(2);
  const isDryRun = args.includes('--dry-run');

  if (isDryRun) {
    console.log('🔍 Validating config.yaml (dry-run mode)...\n');
  } else {
    console.log('Generating environment files from config.yaml...\n');
  }

  const config = loadConfig();

  if (isDryRun) {
    console.log('✅ config.yaml is valid!\n');
    console.log('Configuration summary:');
    console.log(`  App: ${config.app.name} (${config.app.environment})`);
    console.log(`  Frontend port: ${config.server.frontend.port}`);
    console.log(`  Backend port: ${config.server.backend.port}`);
    console.log(`  Log level: ${config.app.log_level}`);
    console.log(`  Features enabled: ${Object.entries(config.features).filter(([_, v]) => v).map(([k]) => k).join(', ') || 'none'}`);
    console.log('\nRun without --dry-run to generate .env files.');
    return;
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

  console.log('\n✅ Done! Environment files have been generated.');
  console.log('\nNote: These files are git-ignored. Regenerate after editing config.yaml.');
}

main();
