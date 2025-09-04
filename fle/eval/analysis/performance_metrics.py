"""
Performance metrics calculation for evaluation analysis.
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
import math


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""

    # Basic statistics
    num_trajectories: int
    mean_reward: float
    std_reward: float
    median_reward: float
    min_reward: float
    max_reward: float

    # Success metrics
    success_count: int
    success_rate: float
    pass_at_1: float  # Best single performance
    pass_at_k: Optional[Dict[int, float]] = None  # Pass@k for different k values

    # Efficiency metrics
    mean_tokens: Optional[float] = None
    mean_steps: Optional[float] = None
    tokens_per_success: Optional[float] = None

    # Statistical significance
    confidence_interval_95: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        result = {
            "num_trajectories": self.num_trajectories,
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "median_reward": self.median_reward,
            "min_reward": self.min_reward,
            "max_reward": self.max_reward,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "pass_at_1": self.pass_at_1,
        }

        if self.pass_at_k:
            result["pass_at_k"] = self.pass_at_k
        if self.mean_tokens:
            result["mean_tokens"] = self.mean_tokens
        if self.mean_steps:
            result["mean_steps"] = self.mean_steps
        if self.tokens_per_success:
            result["tokens_per_success"] = self.tokens_per_success
        if self.confidence_interval_95:
            result["ci_95_lower"], result["ci_95_upper"] = self.confidence_interval_95

        return result


class PerformanceAnalyzer:
    """Utility class for calculating performance metrics"""

    @staticmethod
    def calculate_metrics(
        df: pd.DataFrame,
        reward_column: str = "final_reward",
        success_threshold: float = 0.0,
        token_column: Optional[str] = None,
        step_column: Optional[str] = None,
        k_values: List[int] = [1, 3, 5, 8],
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from trajectory data

        Args:
            df: DataFrame with trajectory-level results
            reward_column: Column name containing final rewards
            success_threshold: Threshold for considering a trajectory successful
            token_column: Optional column with token counts
            step_column: Optional column with step counts
            k_values: List of k values for pass@k calculation

        Returns:
            PerformanceMetrics object
        """
        if len(df) == 0:
            return PerformanceAnalyzer._empty_metrics()

        rewards = df[reward_column].values

        # Basic statistics
        num_trajectories = len(rewards)
        mean_reward = float(np.mean(rewards))
        std_reward = float(np.std(rewards))
        median_reward = float(np.median(rewards))
        min_reward = float(np.min(rewards))
        max_reward = float(np.max(rewards))

        # Success metrics
        successes = rewards > success_threshold
        success_count = int(np.sum(successes))
        success_rate = float(success_count / num_trajectories)
        pass_at_1 = max_reward if max_reward > success_threshold else 0.0

        # Pass@k calculation
        pass_at_k = None
        if len(k_values) > 0:
            pass_at_k = {}
            for k in k_values:
                if k <= num_trajectories:
                    pass_at_k[k] = PerformanceAnalyzer.calculate_pass_at_k(successes, k)

        # Efficiency metrics
        mean_tokens = None
        mean_steps = None
        tokens_per_success = None

        if token_column and token_column in df.columns:
            mean_tokens = float(df[token_column].mean())
            if success_count > 0:
                tokens_per_success = float(
                    df[df[reward_column] > success_threshold][token_column].mean()
                )

        if step_column and step_column in df.columns:
            mean_steps = float(df[step_column].mean())

        # Statistical significance (95% confidence interval for success rate)
        confidence_interval_95 = None
        if num_trajectories >= 5:  # Only calculate if we have enough data
            confidence_interval_95 = PerformanceAnalyzer.binomial_confidence_interval(
                success_count, num_trajectories, 0.95
            )

        return PerformanceMetrics(
            num_trajectories=num_trajectories,
            mean_reward=mean_reward,
            std_reward=std_reward,
            median_reward=median_reward,
            min_reward=min_reward,
            max_reward=max_reward,
            success_count=success_count,
            success_rate=success_rate,
            pass_at_1=pass_at_1,
            pass_at_k=pass_at_k,
            mean_tokens=mean_tokens,
            mean_steps=mean_steps,
            tokens_per_success=tokens_per_success,
            confidence_interval_95=confidence_interval_95,
        )

    @staticmethod
    def calculate_pass_at_k(successes: np.ndarray, k: int) -> float:
        """Calculate pass@k metric

        Pass@k is the probability that at least one of k randomly sampled
        trajectories is successful.

        Args:
            successes: Boolean array indicating success for each trajectory
            k: Number of samples to consider

        Returns:
            Pass@k probability
        """
        n = len(successes)
        if k >= n:
            return float(np.any(successes))

        c = np.sum(successes)  # Number of successes
        if c == 0:
            return 0.0
        if c == n:
            return 1.0

        # Calculate pass@k using the formula:
        # pass@k = 1 - (n-c choose k) / (n choose k)
        # Where c is number of successes, n is total samples

        try:
            prob = 1.0 - (math.comb(n - c, k) / math.comb(n, k))
            return max(0.0, min(1.0, prob))
        except (ValueError, OverflowError):
            # Fallback to empirical estimation if combinatorics fail
            return PerformanceAnalyzer._empirical_pass_at_k(successes, k)

    @staticmethod
    def _empirical_pass_at_k(
        successes: np.ndarray, k: int, num_samples: int = 10000
    ) -> float:
        """Empirically estimate pass@k by sampling"""
        n = len(successes)
        count = 0

        for _ in range(num_samples):
            sampled_indices = np.random.choice(n, k, replace=False)
            if np.any(successes[sampled_indices]):
                count += 1

        return float(count / num_samples)

    @staticmethod
    def binomial_confidence_interval(
        successes: int, trials: int, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate binomial confidence interval for success rate

        Args:
            successes: Number of successful trials
            trials: Total number of trials
            confidence: Confidence level (e.g., 0.95 for 95%)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if trials == 0:
            return (0.0, 0.0)

        alpha = 1 - confidence

        # Use Wilson score interval for better coverage with small samples
        z = stats.norm.ppf(1 - alpha / 2)
        p = successes / trials

        denominator = 1 + z**2 / trials
        center = (p + z**2 / (2 * trials)) / denominator
        margin = (
            z * math.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator
        )

        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)

        return (lower, upper)

    @staticmethod
    def compare_models(
        metrics_dict: Dict[str, PerformanceMetrics],
        primary_metric: str = "success_rate",
    ) -> pd.DataFrame:
        """Compare performance metrics across models

        Args:
            metrics_dict: Dictionary mapping model names to PerformanceMetrics
            primary_metric: Metric to sort by

        Returns:
            DataFrame with model comparison
        """
        rows = []

        for model_name, metrics in metrics_dict.items():
            row = {"model": model_name}
            row.update(metrics.to_dict())
            rows.append(row)

        df = pd.DataFrame(rows)

        if primary_metric in df.columns:
            df = df.sort_values(primary_metric, ascending=False)

        return df

    @staticmethod
    def statistical_significance_test(
        metrics1: PerformanceMetrics,
        metrics2: PerformanceMetrics,
        metric: str = "success_rate",
    ) -> Dict[str, Any]:
        """Test statistical significance between two models

        Args:
            metrics1: First model metrics
            metrics2: Second model metrics
            metric: Metric to compare

        Returns:
            Dictionary with test results
        """
        if metric == "success_rate":
            # Two-proportion z-test
            n1, n2 = metrics1.num_trajectories, metrics2.num_trajectories
            x1, x2 = metrics1.success_count, metrics2.success_count

            p1, p2 = x1 / n1, x2 / n2
            p_pool = (x1 + x2) / (n1 + n2)

            se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

            if se > 0:
                z_score = (p1 - p2) / se
                p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            else:
                z_score = 0.0
                p_value = 1.0

            return {
                "test_type": "two_proportion_z_test",
                "z_score": z_score,
                "p_value": p_value,
                "significant_at_05": p_value < 0.05,
                "difference": p1 - p2,
            }
        else:
            return {"error": f"Statistical test not implemented for metric: {metric}"}

    @staticmethod
    def _empty_metrics() -> PerformanceMetrics:
        """Return empty metrics for edge cases"""
        return PerformanceMetrics(
            num_trajectories=0,
            mean_reward=0.0,
            std_reward=0.0,
            median_reward=0.0,
            min_reward=0.0,
            max_reward=0.0,
            success_count=0,
            success_rate=0.0,
            pass_at_1=0.0,
        )
