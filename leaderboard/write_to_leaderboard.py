import os

import psycopg2
from psycopg2.extras import DictCursor
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class DBClient:
    def __init__(self):
        self.db_config = {
            'dbname': os.getenv("POSTGRES_DATABASE"),
            'user': os.getenv("POSTGRES_USER"),
            'password': os.getenv("POSTGRES_PASSWORD"),
            'host': os.getenv("POSTGRES_HOST"),
            'sslmode': 'require'
        }

    def initialize_tables(self):
        """Create the model_stats table if it doesn't exist"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS model_stats (
                        id SERIAL PRIMARY KEY,
                        model_name TEXT NOT NULL,
                        mean_score DOUBLE PRECISION NOT NULL,
                        cumulative_score DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()

    def record_model_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Record statistics for a model run"""
        with psycopg2.connect(**self.db_config) as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    INSERT INTO model_stats (model_name, mean_score, cumulative_score)
                    VALUES (%s, %s, %s)
                    RETURNING id, created_at
                """, (
                    stats['model_name'],
                    stats['mean_score'],
                    stats['cumulative_score']
                ))

                id, created_at = cur.fetchone()
                stats['id'] = id
                stats['created_at'] = created_at
                return stats

# Example usage
if __name__ == "__main__":
    db = DBClient()

    # Initialize tables
    db.initialize_tables()

    # Example model statistics
    test_stats = {
        'model_name': 'gpt4-factored',
        'mean_score': 0.75,
        'cumulative_score': 2250.0
    }

    # Record the statistics
    result = db.record_model_stats(test_stats)
    print(f"Recorded model stats with ID: {result['id']}")