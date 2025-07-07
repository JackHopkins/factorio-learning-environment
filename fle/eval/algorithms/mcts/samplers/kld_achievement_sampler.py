import math
from collections import Counter
from typing import Dict, Optional, Tuple, List

import numpy as np
import psycopg2
import tenacity
from psycopg2.extras import DictCursor
from tenacity import retry_if_exception_type, wait_exponential

from fle.commons.db_client import DBClient
from fle.commons.models.program import Program

from .db_sampler import DBSampler


class KLDiversityAchievementSampler(DBSampler):
    """
    A sampler that promotes diversity in achievements by computing KL divergence
    between achievement distributions and sampling based on maximum divergence.
    """

    def __init__(
        self, db_client: DBClient, window_size: int = 300, temperature: float = 1.0
    ):
        """
        Initialize the KL divergence-based achievement sampler.

        Args:
            db_client: Database client for accessing programs
            window_size: Number of recent programs to consider for diversity calculation
            temperature: Temperature parameter for softmax sampling (higher = more uniform)
        """
        super().__init__(db_client)
        self.window_size = window_size
        self.temperature = temperature

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """
        Normalize scores to reduce variance and prevent domination by extreme values.
        Uses a combination of robust scaling and sigmoid transformation.

        Args:
            scores: Array of KL divergence scores

        Returns:
            Normalized scores array
        """
        if len(scores) < 2:
            return scores

        # Use robust scaling to handle outliers
        q25, q75 = np.percentile(scores, [25, 75])
        iqr = q75 - q25
        if iqr == 0:
            # If IQR is 0, use standard scaling
            scores = (scores - scores.mean()) / (scores.std() + 1e-10)
        else:
            # Robust scaling using IQR
            scores = (scores - q25) / iqr

        # Apply sigmoid transformation to squash values to [0,1]
        scores = 1 / (1 + np.exp(-scores))

        return scores

    def _compute_achievement_frequencies(self, achievements_json: Dict) -> Counter:
        """
        Compute frequencies of achievement key-value pairs in a single program.

        Args:
            achievements_json: JSON object containing achievements

        Returns:
            Counter of achievement key-value pairs
        """
        frequencies = Counter()
        if not achievements_json:
            return frequencies

        static_achievements = achievements_json.get("static", {})
        dynamic_achievements = achievements_json.get("dynamic", {})

        for key, value in static_achievements.items():
            try:
                # Convert value to float for numerical operations
                freq = float(value)
                frequencies["static-" + key] = freq
            except (ValueError, TypeError):
                # If value can't be converted to float, skip this achievement
                continue

        for key, value in dynamic_achievements.items():
            try:
                # Convert value to float for numerical operations
                freq = float(value)
                frequencies["dynamic-" + key] = freq
            except (ValueError, TypeError):
                # If value can't be converted to float, skip this achievement
                continue

        return frequencies

    def _compute_kl_divergence(self, p: Counter, q: Counter) -> float:
        """
        Compute KL divergence between two achievement frequency distributions.

        Args:
            p: First distribution as a Counter
            q: Second distribution as a Counter

        Returns:
            KL divergence value
        """
        # Get all unique achievement pairs
        all_pairs = set(p.keys()) | set(q.keys())

        # Add smoothing to handle zeros
        epsilon = 1e-10
        p_total = sum(p.values()) + epsilon * len(all_pairs)
        q_total = sum(q.values()) + epsilon * len(all_pairs)

        kld = 0.0
        for pair in all_pairs:
            p_prob = (p[pair] + epsilon) / p_total
            q_prob = (q[pair] + epsilon) / q_total
            kld += p_prob * math.log(p_prob / q_prob)

        return kld

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def sample_parent(self, version: int = 1, **kwargs) -> Optional[Program]:
        """
        Sample a parent program based on achievement diversity.

        Args:
            version: Version of programs to sample from
            **kwargs: Additional sampling parameters

        Returns:
            Sampled Program object or None if no valid programs found
        """
        try:
            with self.db_client.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # Fetch recent programs with achievements
                    cur.execute(
                        """
                            SELECT id, achievements_json
                            FROM programs
                            WHERE version = %s 
                            AND achievements_json IS NOT NULL
                            ORDER BY created_at DESC
                            LIMIT %s
                        """,
                        (version, self.window_size),
                    )

                    results = cur.fetchall()
                    if not results:
                        return None

                    # Compute frequency distributions for each program
                    programs: List[Tuple[int, Counter]] = [
                        (
                            row["id"],
                            self._compute_achievement_frequencies(
                                row["achievements_json"]
                            ),
                        )
                        for row in results
                    ]

                    if len(programs) < 2:
                        # If only one program, return it
                        program_id = programs[0][0]
                    else:
                        # Compute pairwise KL divergences
                        diversity_scores = []
                        for i, (prog_id, freq1) in enumerate(programs):
                            # Sum of KL divergences against all other programs
                            total_kld = sum(
                                self._compute_kl_divergence(freq1, freq2)
                                for j, (_, freq2) in enumerate(programs)
                                if i != j
                            )
                            diversity_scores.append((prog_id, total_kld))

                        # Apply softmax to diversity scores
                        scores = np.array([score for _, score in diversity_scores])
                        normalized_scores = self._normalize_scores(scores)

                        normalized_scores = (
                            normalized_scores / self.temperature
                        )  # Apply temperature scaling
                        softmax_probs = np.exp(
                            normalized_scores - np.max(normalized_scores)
                        )
                        softmax_probs = softmax_probs / softmax_probs.sum()

                        # Sample program ID based on softmax probabilities
                        program_ids = [prog_id for prog_id, _ in diversity_scores]
                        program_id = np.random.choice(program_ids, p=softmax_probs)

                    # Fetch the selected program
                    cur.execute(f"SELECT * FROM programs WHERE id = {int(program_id)}")

                    row = cur.fetchone()
                    return Program.from_row(dict(row)) if row else None

        except Exception as e:
            print(f"Error sampling parent: {e}")
            raise e
