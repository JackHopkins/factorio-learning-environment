// lib/db.ts
import { Pool } from 'pg';

let pool: Pool | null = null;

export function getPool() {
    if (!pool) {
        pool = new Pool({
            connectionString: process.env.POSTGRES_URL,
            ssl: {
                rejectUnauthorized: false
            }
        });
    }
    return pool;
}

export type ModelStats = {
    id: number;
    model_name: string;
    mean_score: number;
    cumulative_score: number;
    created_at: string;
}

export async function getLeaderboardData(): Promise<ModelStats[]> {
    const pool = getPool();
    const client = await pool.connect();

    try {
        const result = await client.query(`
      SELECT *
      FROM model_stats
      ORDER BY cumulative_score DESC;
    `);

        return result.rows;
    } finally {
        client.release();
    }
}