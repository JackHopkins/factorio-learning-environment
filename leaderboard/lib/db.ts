// lib/db.ts
import { Pool } from 'pg';

let pool: Pool | null = null;

export function getPool() {
    if (!pool) {
        pool = new Pool({
            connectionString: process.env.POSTGRES_URL,
            ssl: process.env.NODE_ENV === 'production' ? {
                rejectUnauthorized: false
            } : false
        });
    }
    return pool;
}

export type ModelStats = {
    version: number;
    description: string;
    mean: number;
    std_dev: number;
    max_depth: number;
    latest_depth: number;
    sample_size: number;
    latest_created_at: string;
    cumulative_score: number;
}

export async function getLeaderboardData(): Promise<ModelStats[]> {
    const pool = getPool();
    const client = await pool.connect();

    try {
        const result = await client.query(`
      WITH latest_depths AS (
        SELECT DISTINCT ON (version)
          version,
          depth as latest_depth
        FROM programs
        ORDER BY version, created_at DESC
      ),
      stats AS (
        SELECT
          version,
          MIN(REPLACE(SUBSTRING(version_description FROM 'model:([^\n]+)'), 'model:', '')) as description,
          AVG(raw_reward) as mean,
          STDDEV(raw_reward) as std_dev,
          MAX(depth) as max_depth,
          COUNT(*) as sample_size,
          MAX(created_at) as latest_created_at,
          SUM(raw_reward) as cumulative_score
        FROM programs
        WHERE depth <= 3000
        GROUP BY version
      )
      SELECT
        s.version,
        s.description,
        ROUND(s.mean::numeric, 3) as mean,
        ROUND(s.std_dev::numeric, 3) as std_dev,
        s.max_depth,
        ld.latest_depth,
        s.sample_size,
        s.latest_created_at,
        ROUND(s.cumulative_score::numeric, 2) as cumulative_score
      FROM stats s
      JOIN latest_depths ld USING (version)
      ORDER BY s.cumulative_score DESC;
    `);

        return result.rows;
    } finally {
        client.release();
    }
}