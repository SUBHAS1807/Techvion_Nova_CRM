const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

let dbType = 'sqlite';
let pgPool = null;
let sqliteDb = null;

// Initialize Database connection
function initDatabase() {
  const dbUrl = process.env.DATABASE_URL;
  
  // If PostgreSQL URL is provided and explicitly enabled, we can use pg
  if (dbUrl && dbUrl.startsWith('postgresql://') && process.env.USE_POSTGRES === 'true') {
    try {
      const { Pool } = require('pg');
      pgPool = new Pool({
        connectionString: dbUrl,
        max: 20,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000,
      });
      dbType = 'postgres';
      console.log('✅ Connected to PostgreSQL Database');
      return;
    } catch (e) {
      console.warn('⚠️ PostgreSQL initialization failed, falling back to SQLite:', e.message);
    }
  }

  // SQLite Default (High performance, file-based, zero-friction)
  try {
    const Database = require('better-sqlite3');
    const dbDir = path.join(__dirname, '..', 'data');
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }
    const dbPath = path.join(dbDir, 'technovion_crm.db');
    sqliteDb = new Database(dbPath);
    sqliteDb.pragma('journal_mode = WAL');
    sqliteDb.pragma('synchronous = NORMAL');
    dbType = 'sqlite';
    console.log(`✅ Connected to SQLite Database (${dbPath})`);
  } catch (err) {
    console.error('❌ Failed to initialize SQLite database:', err);
    throw err;
  }
}

initDatabase();

/**
 * Universal async query function supporting both Postgres and SQLite.
 * Translates $1, $2 parameter placeholders to ? if using SQLite.
 */
const query = async (text, params = []) => {
  if (dbType === 'postgres' && pgPool) {
    return await pgPool.query(text, params);
  }

  // SQLite execution
  try {
    let sqliteQuery = text;
    // Replace $1, $2... with ?
    sqliteQuery = sqliteQuery.replace(/\$(\d+)/g, '?');
    
    // Clean up Postgres specific functions if any
    sqliteQuery = sqliteQuery.replace(/NOW\(\)/gi, "datetime('now', 'localtime')");
    sqliteQuery = sqliteQuery.replace(/ILIKE/gi, 'LIKE');
    sqliteQuery = sqliteQuery.replace(/BOOLEAN/gi, 'INTEGER');
    sqliteQuery = sqliteQuery.replace(/TRUE/gi, '1');
    sqliteQuery = sqliteQuery.replace(/FALSE/gi, '0');

    const trimmed = sqliteQuery.trim();
    const isSelect = trimmed.toUpperCase().startsWith('SELECT') || trimmed.toUpperCase().startsWith('PRAGMA') || trimmed.toUpperCase().startsWith('WITH');

    if (isSelect) {
      const stmt = sqliteDb.prepare(sqliteQuery);
      const rows = stmt.all(...params);
      return { rows, rowCount: rows.length };
    } else {
      const stmt = sqliteDb.prepare(sqliteQuery);
      const info = stmt.run(...params);
      return { rows: [], rowCount: info.changes, lastInsertRowid: info.lastInsertRowid };
    }
  } catch (error) {
    console.error('SQL Error:', error.message, 'in query:', text);
    throw error;
  }
};

const getDbType = () => dbType;

module.exports = {
  query,
  getDbType,
  getPool: () => pgPool,
  getSqlite: () => sqliteDb,
};
