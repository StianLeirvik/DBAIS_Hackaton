import pg from 'pg'
import { readFileSync, existsSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const { Pool } = pg
const __dirname = path.dirname(fileURLToPath(import.meta.url))

// ---------------------------------------------------------------------------
// Config — env vars take priority (Databricks Apps / CI), then settings.json
// ---------------------------------------------------------------------------
function loadConfig(): { connectionString: string; schema: string } {
  // 1. Environment variables (set in app.yml env: block or Databricks App secrets)
  const envConn   = process.env.DB_CONNECTION_STRING
  const envSchema = process.env.DB_SCHEMA
  if (envConn) {
    return { connectionString: envConn, schema: envSchema ?? 'model_v1' }
  }

  // 2. Local settings.json (never deployed)
  const settingsPath = path.join(__dirname, 'settings.json')
  if (existsSync(settingsPath)) {
    const raw = readFileSync(settingsPath, 'utf-8')
    const s = JSON.parse(raw) as { connectionString: string; schema?: string }
    return { connectionString: s.connectionString, schema: s.schema ?? 'model_v1' }
  }

  throw new Error(
    'No database configuration found. ' +
    'Set DB_CONNECTION_STRING (and optionally DB_SCHEMA) environment variables, ' +
    'or create server/settings.json for local development.',
  )
}

const config = loadConfig()
export const DB_SCHEMA = config.schema

const pool = new Pool({ connectionString: config.connectionString })

export async function getPool(): Promise<InstanceType<typeof Pool>> {
  return pool
}
