"""
Database analysis utilities for querying evaluation results from PostgreSQL.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

from fle.commons.db_client import create_db_client, DBClient


class DatabaseAnalyzer:
    """Handles querying and aggregating evaluation results from the database"""

    def __init__(self, db_client: Optional[DBClient] = None):
        """Initialize with optional database client"""
        self.db_client = db_client
        self._connection_created = False

    async def ensure_connection(self):
        """Ensure database connection is established"""
        if self.db_client is None:
            self.db_client = await create_db_client()
            self._connection_created = True

    async def cleanup(self):
        """Clean up database connection if created internally"""
        if self._connection_created and self.db_client:
            await self.db_client.cleanup()

    async def get_results_by_version(self, versions: List[int]) -> pd.DataFrame:
        """Get all results for specific versions

        Args:
            versions: List of version numbers to query

        Returns:
            DataFrame with all program results
        """
        await self.ensure_connection()

        version_list = ", ".join(str(v) for v in versions)
        query = f"""
        SELECT 
            id, version, version_description, model, instance, depth, value, 
            raw_reward, achievements_json, response, token_usage, 
            completion_token_usage, prompt_token_usage, created_at, meta,
            ticks, timing_metrics_json
        FROM programs 
        WHERE version IN ({version_list})
        ORDER BY version, instance, depth
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_results_by_model_and_task(
        self,
        model: str,
        task_pattern: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Get results filtered by model and task

        Args:
            model: Model name (e.g., "gpt-4o")
            task_pattern: Task pattern to match in version_description
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            DataFrame with filtered results
        """
        await self.ensure_connection()

        conditions = [
            f"model = '{model}'",
            f"version_description LIKE '%{task_pattern}%'",
        ]

        if start_date:
            conditions.append(f"created_at >= '{start_date.isoformat()}'")
        if end_date:
            conditions.append(f"created_at <= '{end_date.isoformat()}'")

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT 
            id, version, version_description, model, instance, depth, value,
            raw_reward, achievements_json, response, token_usage,
            completion_token_usage, prompt_token_usage, created_at, meta,
            ticks, timing_metrics_json
        FROM programs 
        WHERE {where_clause}
        ORDER BY version, instance, depth
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_trajectory_summaries(self, versions: List[int]) -> pd.DataFrame:
        """Get trajectory-level summaries for analysis

        Args:
            versions: List of version numbers

        Returns:
            DataFrame with one row per trajectory (version + instance)
        """
        await self.ensure_connection()

        version_list = ", ".join(str(v) for v in versions)
        query = f"""
        WITH trajectory_stats AS (
            SELECT 
                version,
                version_description,
                model,
                instance,
                MAX(depth) as max_depth,
                MAX(value) as final_reward,
                MAX(raw_reward) as max_raw_reward,
                COUNT(*) as num_steps,
                SUM(token_usage) as total_tokens,
                SUM(completion_token_usage) as total_completion_tokens,
                MIN(created_at) as start_time,
                MAX(created_at) as end_time,
                STRING_AGG(
                    CASE WHEN achievements_json != '{{}}' AND achievements_json IS NOT NULL 
                         THEN achievements_json 
                         ELSE NULL END, 
                    '; '
                ) as all_achievements,
                STRING_AGG(DISTINCT meta::text, '; ') as meta_aggregated
            FROM programs
            WHERE version IN ({version_list})
            GROUP BY version, version_description, model, instance
        )
        SELECT 
            *,
            EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds
        FROM trajectory_stats
        ORDER BY version, instance
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_trajectory_summaries_by_sweep(self, sweep_id: str) -> pd.DataFrame:
        """Get trajectory-level summaries for a specific sweep

        Args:
            sweep_id: Sweep identifier to filter by

        Returns:
            DataFrame with one row per trajectory (version + instance)
        """
        await self.ensure_connection()

        query = """
        WITH trajectory_stats AS (
            SELECT 
                version,
                version_description,
                model,
                instance,
                MAX(depth) as max_depth,
                MAX(value) as final_reward,
                MAX(raw_reward) as max_raw_reward,
                COUNT(*) as num_steps,
                SUM(token_usage) as total_tokens,
                SUM(completion_token_usage) as total_completion_tokens,
                MIN(created_at) as start_time,
                MAX(created_at) as end_time,
                STRING_AGG(
                    CASE WHEN achievements_json != '{{}}' AND achievements_json IS NOT NULL 
                         THEN achievements_json 
                         ELSE NULL END, 
                    '; '
                ) as all_achievements,
                STRING_AGG(DISTINCT meta::text, '; ') as meta_aggregated
            FROM programs
            WHERE meta->>'sweep_id' = %s
            GROUP BY version, version_description, model, instance
        )
        SELECT 
            *,
            EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds
        FROM trajectory_stats
        ORDER BY version, instance
        """

        results = await self.db_client.execute_query(query, (sweep_id,))
        return pd.DataFrame(results)

    async def get_model_comparison(
        self,
        models: List[str],
        task_pattern: Optional[str] = None,
        min_trajectories: int = 5,
    ) -> pd.DataFrame:
        """Compare performance across models

        Args:
            models: List of model names to compare
            task_pattern: Optional task pattern to filter by
            min_trajectories: Minimum number of trajectories required per model

        Returns:
            DataFrame with model comparison metrics
        """
        await self.ensure_connection()

        model_list = "', '".join(models)
        conditions = [f"model IN ('{model_list}')"]

        if task_pattern:
            conditions.append(f"version_description LIKE '%{task_pattern}%'")

        where_clause = " AND ".join(conditions)

        query = f"""
        WITH trajectory_final_scores AS (
            SELECT 
                version,
                version_description, 
                model,
                instance,
                MAX(value) as final_reward,
                MAX(raw_reward) as final_raw_reward,
                MAX(depth) as trajectory_length,
                SUM(token_usage) as total_tokens
            FROM programs
            WHERE {where_clause}
            GROUP BY version, version_description, model, instance
        ),
        model_stats AS (
            SELECT 
                model,
                COUNT(*) as num_trajectories,
                AVG(final_reward) as mean_reward,
                STDDEV(final_reward) as std_reward,
                MIN(final_reward) as min_reward,
                MAX(final_reward) as max_reward,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY final_reward) as median_reward,
                AVG(final_raw_reward) as mean_raw_reward,
                AVG(trajectory_length) as mean_trajectory_length,
                AVG(total_tokens) as mean_tokens_per_trajectory,
                COUNT(CASE WHEN final_reward > 0 THEN 1 END) as success_count
            FROM trajectory_final_scores
            GROUP BY model
            HAVING COUNT(*) >= {min_trajectories}
        )
        SELECT 
            *,
            success_count::float / num_trajectories as success_rate
        FROM model_stats
        ORDER BY mean_reward DESC
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_task_breakdown(
        self, model: Optional[str] = None, min_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get performance breakdown by task type

        Args:
            model: Optional model filter
            min_date: Optional minimum date filter

        Returns:
            DataFrame with task-level performance metrics
        """
        await self.ensure_connection()

        conditions = []
        if model:
            conditions.append(f"model = '{model}'")
        if min_date:
            conditions.append(f"created_at >= '{min_date.isoformat()}'")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
        WITH trajectory_scores AS (
            SELECT 
                version,
                version_description,
                model,
                instance,
                MAX(value) as final_reward,
                MAX(raw_reward) as final_raw_reward,
                CASE 
                    WHEN version_description LIKE '%throughput%' THEN 'throughput'
                    WHEN version_description LIKE '%unbounded%' THEN 'unbounded'  
                    ELSE 'other'
                END as task_type,
                -- Extract task name from version description
                SPLIT_PART(SPLIT_PART(version_description, 'type:', 2), '\n', 1) as task_name
            FROM programs
            {where_clause}
            GROUP BY version, version_description, model, instance
        )
        SELECT 
            task_type,
            task_name,
            COUNT(*) as num_trajectories,
            AVG(final_reward) as mean_reward,
            STDDEV(final_reward) as std_reward,
            MIN(final_reward) as min_reward,
            MAX(final_reward) as max_reward,
            COUNT(CASE WHEN final_reward > 0 THEN 1 END) as success_count,
            COUNT(CASE WHEN final_reward > 0 THEN 1 END)::float / COUNT(*) as success_rate
        FROM trajectory_scores
        GROUP BY task_type, task_name
        ORDER BY task_type, mean_reward DESC
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_recent_results(self, hours: int = 24) -> pd.DataFrame:
        """Get results from the last N hours for monitoring

        Args:
            hours: Number of hours to look back

        Returns:
            DataFrame with recent results
        """
        await self.ensure_connection()

        cutoff_time = datetime.now() - timedelta(hours=hours)

        query = f"""
        SELECT 
            version, version_description, model, instance, depth, value,
            raw_reward, created_at, token_usage, meta
        FROM programs
        WHERE created_at >= '{cutoff_time.isoformat()}'
        ORDER BY created_at DESC
        """

        results = await self.db_client.execute_query(query)
        return pd.DataFrame(results)

    async def get_version_metadata(
        self, versions: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Get metadata for specific versions

        Args:
            versions: List of version numbers

        Returns:
            Dictionary mapping version -> metadata
        """
        await self.ensure_connection()

        version_list = ", ".join(str(v) for v in versions)
        query = f"""
        SELECT DISTINCT
            version,
            version_description,
            model,
            MIN(created_at) as start_time,
            MAX(created_at) as end_time,
            COUNT(DISTINCT instance) as num_instances,
            COUNT(*) as total_steps
        FROM programs
        WHERE version IN ({version_list})
        GROUP BY version, version_description, model
        ORDER BY version
        """

        results = await self.db_client.execute_query(query)

        metadata = {}
        for row in results:
            metadata[row["version"]] = {
                "version_description": row["version_description"],
                "model": row["model"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "num_instances": row["num_instances"],
                "total_steps": row["total_steps"],
            }

        return metadata
