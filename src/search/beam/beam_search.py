import asyncio
import copy
import logging
from enum import Enum
from math import floor
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from rich.console import Console

from search.db_client import DBClient
from search.factorio_evaluator import FactorioEvaluator
from search.mcts.grouped_logger import GroupedFactorioLogger
from search.mcts.mcts import MCTS
from search.model.instance_group import InstanceGroup
from search.model.conversation import Conversation, Message, GenerationParameters
from search.model.game_state import GameState
from search.model.program import Program
from search.mcts.formatters.conversation_formatter import ConversationFormatter, DefaultFormatter
from factorio_instance import FactorioInstance

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
        "7032": -100  # 'while'
    },
    ModelFamily.LLAMA: {
        "8429": -100,  # 'LINE'
        "34708": -100,  # 'LINES'
        "56670": -100,  # '<L'
        "27": -100,  # '<'
        "9883": -100,  # '/>'
        "3556": -100,  # 'while'
        "1418": -100  # ' while'
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
                current_bias = self.beam_kwargs.get('logit_bias', {})
                # Merge with any existing biases, preferring new ones
                current_bias.update(logit_bias)
                self.beam_kwargs['logit_bias'] = current_bias


class BeamGroup(InstanceGroup):
    """Represents a group running one position in the beam"""

    def __init__(self,
                 group_id: int,
                 beam: 'BeamSearch',
                 evaluator: FactorioEvaluator,
                 active_instances: List['FactorioInstance'],
                 resume_head: Optional[Program] = None):
        super().__init__(
            group_id=group_id,
            mcts=beam,  # For compatibility with existing code
            evaluator=evaluator,
            active_instances=active_instances
        )
        self.beam = beam
        self.current_program: Optional[Program] = resume_head  # Initialize with resume head if available
        self.current_state: Optional[GameState] = resume_head.state if resume_head else None
        self.current_conversation: Optional[Conversation] = resume_head.conversation if resume_head else None


class BeamSearch(MCTS):
    """Beam Search implementation that works as part of parallel beam search"""

    def __init__(self,
                 llm_factory: 'LLMFactory',
                 db_client: DBClient,
                 evaluator: FactorioEvaluator,
                 system_prompt: str,
                 initial_state: GameState,
                 formatter: ConversationFormatter = DefaultFormatter(),
                 version=1,
                 version_description="",
                 presence_penalty=0,
                 frequency_penalty=0,
                 error_penalty=0,
                 logit_bias={}
                 ):

        self.llm = llm_factory
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

        super().__init__(llm_factory, db_client, evaluator, None, system_prompt, initial_state, formatter, version, version_description)

    async def evaluate_candidates(self,
                                  state: GameState,
                                  conversation: Conversation,
                                  parent_id: Optional[int],
                                  n_samples: int) -> List[Program]:
        """Generate and evaluate candidates from current state"""
        generation_parameters = GenerationParameters(
            n=n_samples,
            model=self.llm.model,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            logit_bias=self.logit_bias,
            max_tokens=2048
        )

        programs = await self._generate_programs_batch(
            conversation,
            generation_parameters
        )

        if not programs:
            return []

        for program in programs:
            program.parent_id = parent_id

        evaluated_programs = await self.evaluator.evaluate_batch(
            programs,
            state
        )

        return evaluated_programs


class ParallelBeamSearch:
    """Manages parallel beam search across multiple instance groups"""

    def __init__(self,
                 instances: List['FactorioInstance'],
                 db_client: DBClient,
                 llm_factory: 'LLMFactory',
                 config: ParallelBeamConfig,
                 version: int,
                 version_description: str,
                 current_depth=0,
                 formatter: ConversationFormatter = DefaultFormatter(),
                 base_port=27000,
                 resume_version=False,
                 resume_heads: Optional[List[Program]] = None
                 ):


        self.console = Console()
        self.config = config
        self.db_client = db_client
        self.llm_factory = llm_factory
        self.version = version
        self.version_description = version_description
        self.current_depth = current_depth
        self.formatter = formatter
        self.resume_version = resume_version
        self.resume_heads = resume_heads

        if self.resume_version:
            if not self.resume_heads or len(self.resume_heads) != config.beam_width:
                raise ValueError(f"Number of resume heads ({len(self.resume_heads) if self.resume_heads else 0}) "
                                 f"doesn't match beam width ({config.beam_width})")

        # Validate instance count
        self._validate_instance_count(len(instances), config.beam_width)

        # Initialize logger
        instances_per_group = floor(len(instances) / config.beam_width)
        self.logger = GroupedFactorioLogger(
            n_groups=config.beam_width,
            instances_per_group=instances_per_group,
            base_port = base_port,
            resume_version=resume_version
        )
        self.logger.start()

        # Create beam groups
        self.beam_groups = self._create_beam_groups(instances)


    async def _verify_version_compatibility(self):
        """Verify that resuming version is compatible with current configuration"""
        metadata = await self.db_client.get_version_metadata(self.version)
        if not metadata:
            raise ValueError(f"No metadata found for version {self.version}")

        # Check model compatibility
        if self.llm_factory.model+'\n' not in metadata.get('version_description'):
            raise ValueError(f"Model mismatch: Version uses {metadata.get('model')}, "
                             f"but current config uses {self.llm_factory.model}")

        # Check other relevant configuration parameters
        if 'beam' not in metadata.get('version_description', '').lower():
            raise ValueError(f"Version {self.version} is not from a beam search run")

    def _validate_instance_count(self, total_instances: int, beam_width: int):
        """Validate we have enough instances for the requested beam width"""
        min_required = beam_width  # Need at least one instance per beam position

        if total_instances < min_required:
            raise ValueError(
                f"Need at least {min_required} instances for beam width {beam_width} "
                f"(got {total_instances})"
            )

    def _create_beam_groups(self, instances: List['FactorioInstance']) -> List[BeamGroup]:
        """Create groups for parallel beam search, optionally using resume states"""
        instances_per_group = floor(len(instances) / self.config.beam_width)
        groups = []

        for group_id in range(self.config.beam_width):
            # Slice instances for this group
            start_idx = group_id * instances_per_group
            end_idx = start_idx + instances_per_group
            group_instances = instances[start_idx:end_idx]

            # Create evaluator for this group
            evaluator = FactorioEvaluator(
                db_client=self.db_client,
                instances=group_instances,
                value_accrual_time=3,
                logger=self.logger,
                error_penalty=self.config.beam_kwargs.get('error_penalty', 0)
            )

            # Create beam search instance
            beam = BeamSearch(
                llm_factory=self.llm_factory,
                db_client=self.db_client,
                evaluator=evaluator,
                formatter=self.formatter,
                system_prompt=self.config.system_prompt,
                initial_state=self.config.initial_state,
                version=self.version,
                version_description=self.version_description,
                **self.config.beam_kwargs
            )
            # Pass resume head directly to BeamGroup if available
            resume_head = self.resume_heads[group_id] if self.resume_version and self.resume_heads else None

            group = BeamGroup(
                group_id=group_id,
                beam=beam,
                evaluator=evaluator,
                active_instances=group_instances,
                resume_head=resume_head
            )

            # Reset instance to resumed state if available
            if resume_head:
                group.evaluator.instances[0].reset(resume_head.state)

            groups.append(group)

        return groups

    async def _select_top_k_programs(self, all_programs: List[Program], k: int) -> List[Program]:
        """Select top k programs based on scores"""
        sorted_programs = sorted(
            [p for p in all_programs if p.state is not None and p.value is not None],
            key=lambda p: p.value,
            reverse=True
        )
        return sorted_programs[:k]

    async def _run_beam_iteration(self, n_iterations: int):
        """Run beam search iterations"""
        try:
            for iteration in range(n_iterations * 5):
                logger.info(f"Starting iteration {iteration}")

                # Generate and evaluate candidates in parallel
                generation_tasks = []
                for group in self.beam_groups:
                    if iteration == 0 and not self.resume_version:
                        # Initialize with starting state for new runs only
                        state = self.config.initial_state
                        group.evaluator.instances[0].reset(state)
                        entities = group.evaluator.instances[0].namespace.get_entities()
                        conversation = Conversation(messages=[
                            Message(role="system", content=self.config.system_prompt),
                            Message(role="assistant", content="print(f'Inventory: {inspect_inventory()}')\n"
                                                           "print(f'Entities: {get_entities()}')\n"),
                            Message(role="user", content=f"1: ('Inventory: {state.inventory.__dict__}')\n"
                                                       f"2: ('Entities: {entities}')"),
                        ])
                        parent_id = None
                    else:
                        # Use current state/conversation with proper parent linkage
                        if not group.current_program:
                            raise ValueError("No current program available for beam group")

                        state = group.current_state
                        conversation = copy.deepcopy(group.current_conversation)
                        parent_id = group.current_program.id  # This maintains the correct lineage

                    task = group.beam.evaluate_candidates(
                        state=state,
                        conversation=conversation,
                        parent_id=parent_id,
                        n_samples=self.config.expansion_factor
                    )
                    generation_tasks.append(task)

                # Wait for all evaluations
                all_programs = []
                for programs in await asyncio.gather(*generation_tasks):
                    all_programs.extend(programs)

                # Select top k programs
                best_programs = await self._select_top_k_programs(
                    all_programs,
                    self.config.beam_width
                )

                # Assign best programs to beam groups
                for group, program in zip(self.beam_groups, best_programs):
                    group.current_program = program
                    group.current_state = program.state
                    group.current_conversation = copy.deepcopy(program.conversation)

                    # We need to double it, because in the DBClient, we halve it
                    # in expectation of depth being the full conversation length in the MCTS implementation
                    program.depth = self.current_depth * 2


                    # Save program to database
                    await self.db_client.create_program(program)

                if best_programs:
                    self.current_depth += 1

                self.logger.update_progress()

                # Log best current score
                if best_programs:
                    best_score = best_programs[0].value
                    print(f"Best score at iteration {iteration}: {best_score}")
                    logger.info(f"Best score at iteration {iteration}: {best_score}")

                if self.current_depth > n_iterations:
                    return

        except Exception as e:
            logger.error(f"Error during beam search: {str(e)}", exc_info=True)
            raise

    async def search(self, n_iterations: int):
        """Run parallel beam search with resume support"""
        try:
            if self.resume_version:
                print(f"Resuming search from version {self.version} at depth {self.current_depth}")

            await self._run_beam_iteration(n_iterations)
        finally:
            self.cleanup()
    def cleanup(self):
        """Clean up resources"""
        self.logger.stop()
        for group in self.beam_groups:
            if hasattr(group.evaluator, 'logger'):
                group.evaluator.logger.stop()

    def get_group_metrics(self, group_id: int) -> Dict[str, Any]:
        """Get metrics for a specific beam group"""
        if 0 <= group_id < len(self.beam_groups):
            group = self.beam_groups[group_id]
            return {
                'active_instances': len(group.active_instances),
                'total_programs': sum(
                    inst.total_programs
                    for inst in group.evaluator.logger.groups[group_id].instances.values()
                ),
                'error_count': sum(
                    inst.error_count
                    for inst in group.evaluator.logger.groups[group_id].instances.values()
                ),
                'current_score': group.current_program.value if group.current_program else None
            }
        return {}