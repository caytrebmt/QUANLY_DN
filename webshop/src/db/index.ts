import pg from 'pg';
import fs from 'fs';
import path from 'path';

const { Pool } = pg;

// PostgreSQL Connection Pool configuration
const connectionString =
  process.env.SUPABASE_DATABASE_URL ||
  process.env.DATABASE_URL ||
  process.env.POSTGRES_URL;

const isSupabase = connectionString ? (connectionString.includes('supabase.co') || connectionString.includes('supabase.com')) : false;
const useSsl = isSupabase || process.env.NODE_ENV === 'production' || (connectionString ? connectionString.includes('sslmode=require') : false);

export const pool = new Pool(
  connectionString
    ? {
        connectionString,
        ssl: useSsl ? { rejectUnauthorized: false } : false,
        max: 10,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
      }
    : {
        host: process.env.PGHOST || 'localhost',
        port: Number(process.env.PGPORT || 5432),
        user: process.env.PGUSER || 'postgres',
        password: process.env.PGPASSWORD || 'postgres',
        database: process.env.PGDATABASE || 'erpacc_db',
      }
);

let isConnected = false;

// Test DB Connection
export async function testDbConnection(): Promise<boolean> {
  try {
    const client = await pool.connect();
    const res = await client.query('SELECT NOW()');
    client.release();
    isConnected = true;
    console.log(`[Database] Successfully connected to PostgreSQL at ${res.rows[0].now}`);
    return true;
  } catch (err: any) {
    isConnected = false;
    console.warn(`[Database Warning] Could not connect to PostgreSQL DB (${err.message}). Using fallback in-memory handler.`);
    return false;
  }
}

export function isDbConnected(): boolean {
  return isConnected;
}

// Execute query helper with parameters
export async function query(text: string, params?: any[]) {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    console.log(`[DB Query] executed in ${duration}ms, rows: ${res.rowCount}`);
    return res;
  } catch (error) {
    console.error(`[DB Error] Query failed: ${text}`, error);
    throw error;
  }
}

// Auto-run schema.sql if DATABASE_URL is active and requested
export async function autoMigrateDatabase() {
  const connected = await testDbConnection();
  if (!connected) return;

  try {
    const schemaPath = path.join(process.cwd(), 'webshop', 'schema.sql');
    if (fs.existsSync(schemaPath)) {
      console.log('[Database] Applying schema.sql migrations...');
      const sql = fs.readFileSync(schemaPath, 'utf8');
      await pool.query(sql);
      console.log('[Database] Migrations applied successfully!');
    }
  } catch (err) {
    console.error('[Database Migration Error]', err);
  }
}
