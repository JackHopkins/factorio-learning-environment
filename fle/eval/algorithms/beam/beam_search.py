import asyncio
import copy
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from math import floor
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from rich.console import Console

from fle.agents.formatters import ConversationFormatter, DefaultFormatter
from fle.commons.db_client import DBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program
from fle.env import FactorioInstance
from fle.eval.evaluator import Evaluator

from ..mcts import MCTS, GroupedFactorioLogger, InstanceGroup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class ModelFamily(Enum):
    GPT = "gpt"
    LLAMA = "llama"
    GEMINI = "gemini"
    CLAUDE = "claude"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    UNKNOWN = "unknown"


# Token mappings for different model families
MODEL_LOGIT_BIASES = {
    ModelFamily.GPT: {
        "15714": -100,  # 'LINE'
        "193595": -100,  # 'LINES'
        "145968": -100,  # ' CUT'
        "27": -100,  # '<'
        "20225": -100,  # '/>'
        "7032": -100,  # 'while'
    },
    ModelFamily.LLAMA: {
        "8429": -100,  # 'LINE'
        "34708": -100,  # 'LINES'
        "56670": -100,  # '<L'
        "27": -100,  # '<'
        "9883": -100,  # '/>'
        "3556": -100,  # 'while'
        "1418": -100,  # ' while'
    },
    ModelFamily.QWEN: {},  # Placeholder for Qwen-specific biases
    ModelFamily.GEMINI: {},  # Placeholder for Gemini-specific biases
    ModelFamily.CLAUDE: {},  # Placeholder for Claude-specific biases
    ModelFamily.DEEPSEEK: {},  # Placeholder for DeepSeek-specific biases
}


def get_model_family(model_name: str) -> ModelFamily:
    """Determine the model family from the model name."""
    model_name = model_name.lower()

    if any(name in model_name for name in ["gpt-", "ft:gpt-"]):
        return ModelFamily.GPT
    elif "llama" in model_name:
        return ModelFamily.LLAMA
    elif "gemini" in model_name:
        return ModelFamily.GEMINI
    elif "claude" in model_name:
        return ModelFamily.CLAUDE
    elif "qwen" in model_name:
        return ModelFamily.QWEN
    elif "deepseek" in model_name:
        return ModelFamily.DEEPSEEK

    return ModelFamily.UNKNOWN


def get_logit_bias(model_name: str) -> Dict[str, float]:
    """Get the appropriate logit bias dictionary for the given model."""
    family = get_model_family(model_name)
    return MODEL_LOGIT_BIASES.get(family, {})


@dataclass
class ParallelBeamConfig:
    """Configuration for parallel beam search"""

    beam_width: int  # Number of parallel groups (equivalent to beam width)
    expansion_factor: int  # Number of programs to generate per beam position
    system_prompt: str
    initial_state: GameState
    beam_kwargs: Dict[str, Any]
    model: Optional[str] = None

    def __post_init__(self):
        if self.model:
            # Initialize with default beam kwargs if none provided
            if self.beam_kwargs is None:
                self.beam_kwargs = {}

            # Add model-specific logit biases
            logit_bias = get_logit_bias(self.model)
            if logit_bias:
                current_bias = self.beam_kwargs.get("logit_bias", {})
                # Merge with any existing biases, preferring new ones
                current_bias.update(logit_bias)
                self.beam_kwargs["logit_bias"] = current_bias


class BeamGroup(InstanceGroup):
    """Represents a group running one position in the beam"""

    def __init__(
        self,
        group_id: int,
        beam: "BeamSearch",
        evaluator: Evaluator,
        active_instances: List["FactorioInstance"],
        resume_head: Optional[Program] = None,
    ):
        super().__init__(
            group_id=group_id,
            mcts=beam,  # For compatibility with existing code
            evaluator=evaluator,
            active_instances=active_instances,
        )
        self.beam = beam
        self.current_program: Optional[Program] = (
            resume_head  # Initialize with resume head if available
        )
        self.current_state: Optional[GameState] = (
            resume_head.state if resume_head else None
        )
        self.current_conversation: Optional[Conversation] = (
            resume_head.conversation if resume_head else None
        )


class BeamSearch(MCTS):
    """Beam Search implementation that works as part of parallel beam search"""

    def __init__(
        self,
        api_factory: "APIFactory",  # noqa
        db_client: DBClient,
        evaluator: Evaluator,
        system_prompt: str,
        initial_state: GameState,
        formatter: ConversationFormatter = DefaultFormatter(),
        version=1,
        version_description="",
        presence_penalty=0,
        frequency_penalty=0,
        error_penalty=0,
        logit_bias={},
    ):
        self.llm = api_factory
        self.db = db_client
        self.evaluator = evaluator
        self.system_prompt = system_prompt
        self.initial_state = initial_state
        self.formatter = formatter
        self.version = version
        self.version_description = version_description
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.error_penalty = error_penalty
        self.logit_bias = logit_bias

        self._monitor_task = asyncio.create_task(self._monitor_tasks())
        super().__init__(
            api_factory,
            db_client,
            evaluator,
            None,
            system_prompt,
            initial_state,
            formatter,
            version,
            version_description,
        )

    async def _monitor_tasks(self):
        """Monitor and log task states for debugging"""
        while True:
            try:
                all_tasks = asyncio.all_tasks()
                pending_tasks = [t for t in all_tasks if not t.done()]

                for task in pending_tasks:
                    # Get task name or coroutine name
                    task_name = (
                        task.get_name()
                        if hasattr(task, "get_name")
                        else str(task.get_coro())
                    )

                    # Get task state
                    if task.done():
                        if task.exception():
                            state = f"failed with {task.exception()}"
                        else:
                            state = "completed"
                    else:
                        state = "pending"

                    logger.debug(f"Task {task_name}: {state}")

                # Log summary
                logger.info(
                    f"Tasks - Total: {len(all_tasks)}, Pending: {len(pending_tasks)}"
                )

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in task monitor: {e}")
                await asyncio.sleep(1)

    async def evaluate_candidates(
        self,
        state: GameState,
        conversation: Conversation,
        parent_id: Optional[int],
        n_samples: int,
    ) -> List[Program]:
        """Generate and evaluate candidates from current state"""
        generation_parameters = GenerationParameters(
            n=n_samples,
            model=self.llm.model,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            logit_bias=self.logit_bias,
            max_tokens=2048,
        )

        programs = await self._generate_programs_batch(
            conversation, generation_parameters
        )

        if not programs:
            return []

        for program in programs:
            program.parent_id = parent_id

        evaluated_programs = await self.evaluator.evaluate_batch(programs, state)

        return evaluated_programs


class ParallelBeamSearch:
    """Manages parallel beam search across multiple instance groups"""

    def __init__(
        self,
        instances: List["FactorioInstance"],
        db_client: DBClient,
        api_factory: "APIFactory",  # noqa
        config: ParallelBeamConfig,
        version: int,
        version_description: str,
        current_depth=0,
        formatter: ConversationFormatter = DefaultFormatter(),
        base_port=27000,
        resume_version=False,
        resume_heads: Optional[List[Program]] = None,
    ):
        self.console = Console()
        self.config = config
        self.db_client = db_client
        self.api_factory = api_factory
        self.version = version
        self.version_description = version_description
        self.current_depth = current_depth
        self.formatter = formatter
        self.resume_version = resume_version
        self.resume_heads = resume_heads

        self._hanging_detector = asyncio.Event()
        self._last_progress_time = time.time()
        self._progress_timeout = 300  # 5 minutes timeout

        if self.resume_version:
            if not self.resume_heads or len(self.resume_heads) != config.beam_width:
                print(
                    f"Number of resume heads ({len(self.resume_heads) if self.resume_heads else 0}) "
                    f"doesn't match beam width ({config.beam_width})"
                )
                config.beam_width = len(self.resume_heads)

        # Validate instance count
        self._validate_instance_count(len(instances), config.beam_width)

        # Initialize logger
        instances_per_group = floor(len(instances) / config.beam_width)
        self.logger = GroupedFactorioLogger(
            n_groups=config.beam_width,
            instances_per_group=instances_per_group,
            base_port=base_port,
            resume_version=resume_version,
        )
        self.logger.start()

        self._monitor_task = None
        self._monitoring_active = True

        # Create beam groups
        self.beam_groups = self._create_beam_groups(instances)

    # async def _monitor_progress(self):
    #     """Monitor for hanging operations"""
    #     while True:
    #         try:
    #             await asyncio.sleep(30)  # Check every 30 seconds
    #             current_time = time.time()
    #             if current_time - self._last_progress_time > self._progress_timeout:
    #                 print(f"Operation potentially hanging - no progress for {self._progress_timeout} seconds")
    #                 self._hanging_detector.set()
    #                 return
    #         except Exception as e:
    #             print(f"Error in progress monitor: {e}")
    #             return

    async def _verify_version_compatibility(self):
        """Verify that resuming version is compatible with current configuration"""
        metadata = await self.db_client.get_version_metadata(self.version)
        if not metadata:
            raise ValueError(f"No metadata found for version {self.version}")

        # Check model compatibility
        if self.api_factory.model + "\n" not in metadata.get("version_description"):
            raise ValueError(
                f"Model mismatch: Version uses {metadata.get('model')}, "
                f"but current config uses {self.api_factory.model}"
            )

        # Check other relevant configuration parameters
        if "beam" not in metadata.get("version_description", "").lower():
            raise ValueError(f"Version {self.version} is not from a beam search run")

    def _validate_instance_count(self, total_instances: int, beam_width: int):
        """Validate we have enough instances for the requested beam width"""
        min_required = beam_width  # Need at least one instance per beam position

        if total_instances < min_required:
            raise ValueError(
                f"Need at least {min_required} instances for beam width {beam_width} "
                f"(got {total_instances})"
            )

    def _create_beam_groups(
        self, instances: List["FactorioInstance"]
    ) -> List[BeamGroup]:
        """Create groups for parallel beam search, optionally using resume states"""
        instances_per_group = floor(len(instances) / self.config.beam_width)
        groups = []

        for group_id in range(self.config.beam_width):
            # Slice instances for this group
            start_idx = group_id * instances_per_group
            end_idx = start_idx + instances_per_group
            group_instances = instances[start_idx:end_idx]

            # Create evaluator for this group
            evaluator = Evaluator(
                db_client=self.db_client,
                instances=group_instances,
                value_accrual_time=3,
                logger=self.logger,
                error_penalty=self.config.beam_kwargs.get("error_penalty", 0),
            )

            # Create beam search instance
            beam = BeamSearch(
                api_factory=self.api_factory,
                db_client=self.db_client,
                evaluator=evaluator,
                formatter=self.formatter,
                system_prompt=self.config.system_prompt,
                initial_state=self.config.initial_state,
                version=self.version,
                version_description=self.version_description,
                **self.config.beam_kwargs,
            )
            # Pass resume head directly to BeamGroup if available
            resume_head = (
                self.resume_heads[group_id]
                if self.resume_version and self.resume_heads
                else None
            )

            group = BeamGroup(
                group_id=group_id,
                beam=beam,
                evaluator=evaluator,
                active_instances=group_instances,
                resume_head=resume_head,
            )

            # Reset instance to resumed state if available
            if resume_head:
                group.evaluator.instances[0].reset(resume_head.state)

            groups.append(group)

        return groups

    async def _select_top_k_programs(
        self, all_programs: List[Program], k: int
    ) -> List[Program]:
        """Select top k programs based on scores"""
        sorted_programs = sorted(
            [p for p in all_programs if p.state is not None and p.value is not None],
            key=lambda p: p.value,
            reverse=True,
        )
        return sorted_programs[:k]

    async def _generate_group_candidates(self, group, iteration):
        """Generate candidates for a single beam group with proper error handling"""
        try:
            if iteration == 0 and not self.resume_version:
                state = self.config.initial_state
                group.evaluator.instances[0].reset(state)
                entities = group.evaluator.instances[0].namespace.get_entities()
                conversation = Conversation(
                    messages=[
                        Message(role="system", content=self.config.system_prompt),
                        Message(
                            role="assistant",
                            content="print(f'Inventory: {inspect_inventory()}')\n"
                            "print(f'Entities: {get_entities()}')\n",
                        ),
                        Message(
                            role="user",
                            content=f"1: ('Inventory: {state.inventories[0].__dict__}')\n"
                            f"2: ('Entities: {entities}')",
                        ),
                    ]
                )
                parent_id = None
            else:
                if not group.current_program:
                    raise ValueError("No current program available for beam group")
                state = group.current_state
                conversation = copy.deepcopy(group.current_conversation)
                parent_id = group.current_program.id

            result = await group.beam.evaluate_candidates(
                state=state,
                conversation=conversation,
                parent_id=parent_id,
                n_samples=self.config.expansion_factor,
            )

            if not result:
                print(f"No candidates generated for group {group.group_id}")

            return result
        except Exception as e:
            print(
                f"Error generating candidates for group {group.group_id}: {e}",
                exc_info=True,
            )
            return []

    async def _update_beam_groups(self, best_programs):
        """Update beam groups with proper connection handling"""
        update_tasks = []
        try:
            with self.db_client.get_connection() as conn:
                for group, program in zip(self.beam_groups, best_programs):
                    if program:
                        update_tasks.append(
                            self._update_single_group(conn, group, program)
                        )

                if update_tasks:
                    await asyncio.gather(*update_tasks)

            self.current_depth += 1
            self.logger.update_progress()
        except Exception as e:
            logger.error(f"Error updating beam groups: {e}")
            raise

    async def _create_program(self, cur, program: Program) -> Optional[int]:
        """Create a new program entry in the database using the provided cursor.

        Args:
            cur: Database cursor from the connection
            program: Program object to store
        Returns:
            int: The ID of the created program
        """
        query = """
            INSERT INTO programs (
                code, value, visits, parent_id, state_json, conversation_json,
                completion_token_usage, prompt_token_usage, token_usage, response,
                holdout_value, raw_reward, version, version_description, model, meta,
                achievements_json, instance, depth, advantage, ticks
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, created_at;
        """

        try:
            # Prepare values with proper null handling
            cur.execute(
                query,
                (
                    program.code,
                    program.value,
                    0,  # visits starts at 0
                    program.parent_id,
                    program.state.to_raw() if program.state else None,
                    json.dumps(program.conversation.dict()),
                    getattr(program, "completion_token_usage", None),
                    getattr(program, "prompt_token_usage", None),
                    getattr(program, "token_usage", None),
                    getattr(program, "response", None),
                    getattr(program, "holdout_value", None),
                    getattr(program, "raw_reward", None),
                    self.version,
                    self.version_description,
                    getattr(program, "model", None),
                    json.dumps(getattr(program, "meta", {})),
                    json.dumps(getattr(program, "achievements", [])),
                    getattr(program, "instance", None),
                    program.depth / 2,  # Maintain the depth division from original
                    getattr(program, "advantage", None),
                    getattr(program, "ticks", None),
                ),
            )

            # Get the inserted program's ID and created_at timestamp
            id, created_at = cur.fetchone()

            # Update the program object
            program.id = id
            program.created_at = created_at

            return id

        except Exception as e:
            logger.error(f"Error creating program in database: {e}")
            # Let the error propagate up to be handled by the connection context
            raise

    async def _update_single_group(self, conn, group, program):
        """Update a single beam group using provided connection"""
        try:
            group.current_program = program
            group.current_state = program.state
            group.current_conversation = copy.deepcopy(program.conversation)
            program.depth = self.current_depth * 2

            # Use the provided connection
            with conn.cursor() as cur:
                # Your program creation SQL here
                await self._create_program(cur, program)

        except Exception as e:
            logger.error(f"Error updating group {group.group_id}: {e}")
            raise

    async def _run_beam_iteration(self, n_iterations: int):
        """Run beam search iterations with improved monitoring"""
        monitor_task = asyncio.create_task(self._monitor_progress())

        try:
            for iteration in range(n_iterations * 5):
                iteration_start = time.time()
                logger.info(f"Starting iteration {iteration}")

                # Generate and evaluate candidates in parallel
                all_programs = []
                tasks = []

                # Create individual tasks for each group
                for group in self.beam_groups:
                    task = asyncio.create_task(
                        self._generate_group_candidates(group, iteration)
                    )
                    tasks.append(task)

                # Wait for tasks with individual timeouts
                for task in tasks:
                    try:
                        # Wait for each task individually with timeout
                        programs = await asyncio.wait_for(task, timeout=240)
                        if programs:
                            all_programs.extend(programs)
                    except asyncio.TimeoutError:
                        task.cancel()  # Cancel timed out tasks
                        try:
                            await task  # Wait for cancellation to complete
                        except asyncio.CancelledError:
                            pass
                        continue
                    except Exception as e:
                        print(f"Error in generation task: {e}")
                        continue

                # Update progress tracking
                self._last_progress_time = time.time()

                if not all_programs:
                    print(f"No valid programs generated in iteration {iteration}")
                    # Wait a bit before continuing to next iteration
                    await asyncio.sleep(1)
                    continue

                # Select top k programs
                best_programs = await self._select_top_k_programs(
                    all_programs, self.config.beam_width
                )

                if not best_programs:
                    logger.warning(
                        f"No valid programs selected in iteration {iteration}"
                    )
                    continue

                try:
                    # Use separate timeout for database operations
                    await asyncio.wait_for(
                        self._update_beam_groups(best_programs), timeout=60
                    )
                except asyncio.TimeoutError:
                    print(f"Database update timed out in iteration {iteration}")
                    continue
                except Exception as e:
                    print(f"Error updating beam groups: {e}")
                    continue

                iteration_time = time.time() - iteration_start
                logger.info(
                    f"Iteration {iteration} completed in {iteration_time:.2f} seconds"
                )

                if self.current_depth > n_iterations:
                    return

        except Exception as e:
            print(f"Error during beam search: {str(e)}", exc_info=True)
            raise
        finally:
            # Cancel monitor task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            # Cancel any remaining tasks
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()

    async def search(self, n_iterations: int):
        """Run parallel beam search with resume support"""
        try:
            if self.resume_version:
                print(
                    f"Resuming search from version {self.version} at depth {self.current_depth}"
                )

            # Start monitors before search
            # await self.start_monitors()
            await self._run_beam_iteration(n_iterations)
        finally:
            # Stop monitors and cleanup
            # await self.stop_monitors()
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        try:
            self.logger.stop()
            for group in self.beam_groups:
                if hasattr(group.evaluator, "logger"):
                    group.evaluator.logger.stop()
            if hasattr(self.db_client, "cleanup"):
                await self.db_client.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def get_group_metrics(self, group_id: int) -> Dict[str, Any]:
        """Get metrics for a specific beam group"""
        if 0 <= group_id < len(self.beam_groups):
            group = self.beam_groups[group_id]
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
                "current_score": group.current_program.value
                if group.current_program
                else None,
            }
        return {}

    async def start_monitors(self):
        """Start both monitoring tasks"""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(
                self._monitor_tasks(), name="task_monitor"
            )
        if self._progress_monitor_task is None:
            self._progress_monitor_task = asyncio.create_task(
                self._monitor_progress(), name="progress_monitor"
            )

    async def stop_monitors(self):
        """Stop monitoring tasks gracefully"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        if self._progress_monitor_task:
            self._progress_monitor_task.cancel()
            try:
                await self._progress_monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_tasks(self):
        """Monitor and log task states for debugging"""
        while self._monitoring_active:
            try:
                all_tasks = asyncio.all_tasks()
                pending_tasks = [t for t in all_tasks if not t.done()]

                # Group tasks by their names/types
                task_groups = {}
                for task in pending_tasks:
                    name = (
                        task.get_name()
                        if hasattr(task, "get_name")
                        else str(task.get_coro())
                    )
                    if "generate_group_candidates" in name:
                        group = "generation"
                    elif "create_program" in name:
                        group = "database"
                    elif "evaluate" in name:
                        group = "evaluation"
                    else:
                        group = "other"

                    task_groups.setdefault(group, []).append(task)

                # Log summary by group
                for group, tasks in task_groups.items():
                    logger.info(f"{group.capitalize()} tasks - Count: {len(tasks)}")
                    for task in tasks:
                        if task.done():
                            if task.exception():
                                logger.error(f"Task failed: {task.exception()}")
                            status = "completed" if task.done() else "pending"
                            logger.debug(f"Task {task.get_name()}: {status}")

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in task monitor: {e}")
                await asyncio.sleep(1)

    async def _monitor_progress(self):
        """Monitor for hanging operations"""
        while self._monitoring_active:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                current_time = time.time()
                if current_time - self._last_progress_time > self._progress_timeout:
                    logger.warning(
                        f"Operation potentially hanging - no progress for {self._progress_timeout} seconds"
                    )
                    self._hanging_detector.set()
                    return
            except Exception as e:
                logger.error(f"Error in progress monitor: {e}")
                await asyncio.sleep(1)
