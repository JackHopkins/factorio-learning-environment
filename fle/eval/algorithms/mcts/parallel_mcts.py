import asyncio
import logging
from math import floor
from typing import Any, Dict, List

from fle.eval.algorithms.mcts.grouped_logger import GroupedFactorioLogger
from fle.eval.algorithms.mcts.instance_group import InstanceGroup
from fle.eval.algorithms.mcts.parallel_mcts_config import ParallelMCTSConfig
from fle.eval.evaluator import Evaluator
from rich.console import Console

from fle.commons.db_client import DBClient
from fle.env import FactorioInstance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelMCTS:
    """
    Manages multiple parallel MCTS instances for distributed search
    """

    def __init__(
        self,
        instances: List["FactorioInstance"],
        db_client: DBClient,
        api_factory: "APIFactory",  # noqa
        config: ParallelMCTSConfig,
        version: int,
        version_description: str,
    ):
        """
        Initialize parallel MCTS with configuration

        Args:
            instances: List of Factorio instances to distribute across groups
            db_client: Database client for persistence
            api_factory: Factory for creating language models
            config: Configuration parameters
        """
        self.console = Console()
        self.config = config
        self.db_client = db_client
        self.api_factory = api_factory
        self.version = version
        self.version_description = version_description

        # Validate instance count
        self._validate_instance_count(len(instances), config.n_parallel)

        # Initialize logger
        instances_per_group = floor(len(instances) / config.n_parallel)
        self.logger = GroupedFactorioLogger(
            n_groups=config.n_parallel, instances_per_group=instances_per_group
        )
        self.logger.start()

        # Create instance groups
        self.instance_groups = self._create_instance_groups(instances)

    def _validate_instance_count(self, total_instances: int, n_parallel: int):
        """Validate that we have enough instances for the requested parallelism"""
        min_required = n_parallel * 2  # Need at least 2 instances per group

        if total_instances < min_required:
            raise ValueError(
                f"Need at least {min_required} instances for {n_parallel} parallel searches "
                f"(got {total_instances})"
            )

        instances_per_group = floor(total_instances / n_parallel)
        if instances_per_group < 2:
            raise ValueError(
                f"Not enough instances to allocate at least one active and one holdout "
                f"instance per group (need {n_parallel * 2}, got {total_instances})"
            )

    def _create_instance_groups(
        self, instances: List["FactorioInstance"]
    ) -> List[InstanceGroup]:
        """Create instance groups for parallel execution"""
        instances_per_group = floor(len(instances) / self.config.n_parallel)
        groups = []

        for group_id in range(self.config.n_parallel):
            # Slice instances for this group
            start_idx = group_id * instances_per_group
            end_idx = start_idx + instances_per_group
            group_instances = instances[start_idx:end_idx]

            # Split into active and holdout instances
            # active_instances = group_instances
            # holdout_instance = group_instances[-1]

            # Create evaluator for this group
            evaluator = Evaluator(
                db_client=self.db_client,
                instances=group_instances,
                value_accrual_time=3,
                logger=self.logger,
                error_penalty=self.config.mcts_kwargs["error_penalty"],
            )

            # Create MCTS instance
            mcts = self.config.mcts_class(
                api_factory=self.api_factory,
                db_client=self.db_client,
                evaluator=evaluator,
                sampler=self.config.sampler,
                system_prompt=self.config.system_prompt,
                initial_state=self.config.initial_state,
                **self.config.mcts_kwargs,
            )

            groups.append(
                InstanceGroup(
                    group_id=group_id,
                    mcts=mcts,
                    evaluator=evaluator,
                    active_instances=group_instances,
                    # holdout_instance=holdout_instance
                )
            )

        return groups

    async def search(self, n_iterations: int, skip_failures: bool = False):
        """
        Run parallel MCTS search across all groups

        Args:
            n_iterations: Number of iterations to run
            skip_failures: Whether to skip failed program generations
        """
        try:
            search_tasks = [
                self._run_group_search(group, n_iterations, skip_failures)
                for group in self.instance_groups
            ]
            await asyncio.gather(*search_tasks)

        except Exception as e:
            logger.error(f"Error during parallel search: {str(e)}", exc_info=True)
            raise
        finally:
            self.cleanup()

    async def _run_group_search(
        self, group: InstanceGroup, n_iterations: int, skip_failures: bool
    ):
        """Run search iterations for a single group"""
        try:
            logger.info(f"Starting search for Group {group.group_id}")

            for iteration in range(n_iterations):
                await group.mcts.run_iteration(
                    len(group.active_instances), skip_failures, iteration, n_iterations
                )
                self.logger.update_progress()

        except Exception as e:
            logger.error(f"Error in group {group.group_id}: {str(e)}", exc_info=True)
            raise

    def cleanup(self):
        """Clean up resources"""
        self.logger.stop()
        for group in self.instance_groups:
            if hasattr(group.evaluator, "logger"):
                group.evaluator.logger.stop()

    def get_group_metrics(self, group_id: int) -> Dict[str, Any]:
        """Get metrics for a specific group"""
        if 0 <= group_id < len(self.instance_groups):
            group = self.instance_groups[group_id]
            return {
                "active_instances": len(group.active_instances),
                "total_programs": sum(
                    inst.total_programs
                    for inst in group.evaluator.logger.groups[
                        group_id
                    ].instances.values()
                ),
                "error_count": sum(
                    inst.error_count
                    for inst in group.evaluator.logger.groups[
                        group_id
                    ].instances.values()
                ),
            }
        return {}
