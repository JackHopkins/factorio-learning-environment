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
                 active_instances: List['FactorioInstance']):
        super().__init__(
            group_id=group_id,
            mcts=beam,  # For compatibility with existing code
            evaluator=evaluator,
            active_instances=active_instances
        )
        self.beam = beam
        self.current_program: Optional[Program] = None
        self.current_state: Optional[GameState] = None
        self.current_conversation: Optional[Conversation] = None


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

        # Reuse necessary methods from MCTS
        # self._verify_response_is_python = MCTS._verify_response_is_python
        # self._extract_code_from_choice = MCTS._extract_code_from_choice
        # self._is_model_compatible_with_n_samples = MCTS._is_model_compatible_with_n_samples
        # self._generate_programs_batch = MCTS._generate_programs_batch
        # self._process_openai_response = MCTS._process_openai_response
        # self._generate_parallel = MCTS._generate_parallel
        # self._create_program = MCTS._create_program

    # async def _generate_programs_batch(self,
    #                                    conversation: Conversation,
    #                                    generation_params: GenerationParameters,
    #                                    meta={}) -> List[Program]:
    #     """Modified to handle multiple conversations for batch generation"""
    #     programs = []
    #     n = generation_params.n
    #
    #
    #     if self._is_model_compatible_with_n_samples(generation_params.model) and hasattr(self.llm, "acall"):
    #         conversation = copy.deepcopy(conversation)
    #         formatted = await self.formatter.format_conversation(conversation)
    #         formatted_messages = self.formatter.to_llm_messages(
    #             formatted
    #         )
    #         try:
    #             messages = conversation.model_dump()['messages']
    #         except Exception:
    #             messages = conversation.dict()['messages']
    #         # Use OpenAI's native n parameter support
    #         response = await self.llm.acall(
    #             messages=formatted_messages,
    #             n_samples=generation_params.n,
    #             temperature=generation_params.temperature,
    #             max_tokens=generation_params.max_tokens,
    #             logit_bias=generation_params.logit_bias,
    #             stop_sequences=generation_params.stop_sequences,
    #             model=generation_params.model,
    #             presence_penalty=self.presence_penalty,
    #             frequency_penalty=self.frequency_penalty
    #         )
    #         return await self._process_openai_response(response, conversation, generation_params, messages, meta)
    #     else:
    #         # Create a separate conversation copy for each potential program
    #         conversations = [copy.deepcopy(conversation) for _ in range(n)]
    #         # Process each conversation independently
    #         for i, conversation in enumerate(conversations[:n]):  # Limit to requested n samples
    #             formatted = await self.formatter.format_conversation(conversation)
    #             formatted_messages = self.formatter.to_llm_messages(
    #                 formatted
    #             )
    #             try:
    #                 messages = conversation.model_dump()['messages']
    #             except Exception:
    #                 messages = conversation.dict()['messages']
    #
    #             if self._is_model_compatible_with_n_samples(generation_params.model) and hasattr(self.llm, "acall"):
    #                 # Use OpenAI's native n parameter support
    #                 response = await self.llm.acall(
    #                     messages=formatted_messages,
    #                     n_samples=generation_params.n,
    #                     temperature=generation_params.temperature,
    #                     max_tokens=generation_params.max_tokens,
    #                     logit_bias=generation_params.logit_bias,
    #                     stop_sequences=generation_params.stop_sequences,
    #                     model=generation_params.model,
    #                     presence_penalty=self.presence_penalty,
    #                     frequency_penalty=self.frequency_penalty
    #                 )
    #                 return await self._process_openai_response(response, conversation, generation_params, messages, meta)
    #             else:
    #                 # Make parallel calls for other providers
    #                 #conversation.messages = formatted_messages
    #                 responses =  await self._generate_parallel(
    #                     conversation,
    #                     generation_params,
    #                     formatted_messages,
    #                     messages,
    #                     meta
    #                 )
    #
    #                 for response in responses:
    #                     if response and self._verify_response_is_python(response):
    #                         code = self._extract_code_from_choice(response)
    #                         if code:
    #                             # Create program with its independent conversation copy
    #                             program = await self._create_program(
    #                                 code=code,
    #                                 conversation=conversation,  # Use the independent conversation for this program
    #                                 response=response
    #                             )
    #                             if program:
    #                                 programs.append(program)
    #
    #         return programs
    #
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
                 base_port=27015):


        self.console = Console()
        self.config = config
        self.db_client = db_client
        self.llm_factory = llm_factory
        self.version = version
        self.version_description = version_description
        self.current_depth = current_depth
        self.formatter = formatter
        # Validate instance count
        self._validate_instance_count(len(instances), config.beam_width)

        # Initialize logger
        instances_per_group = floor(len(instances) / config.beam_width)
        self.logger = GroupedFactorioLogger(
            n_groups=config.beam_width,
            instances_per_group=instances_per_group,
            base_port = base_port
        )
        self.logger.start()

        # Create beam groups
        self.beam_groups = self._create_beam_groups(instances)

    def _validate_instance_count(self, total_instances: int, beam_width: int):
        """Validate we have enough instances for the requested beam width"""
        min_required = beam_width  # Need at least one instance per beam position

        if total_instances < min_required:
            raise ValueError(
                f"Need at least {min_required} instances for beam width {beam_width} "
                f"(got {total_instances})"
            )

    def _create_beam_groups(self, instances: List['FactorioInstance']) -> List[BeamGroup]:
        """Create groups for parallel beam search"""
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

            groups.append(BeamGroup(
                group_id=group_id,
                beam=beam,
                evaluator=evaluator,
                active_instances=group_instances
            ))

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
        """Run one iteration of parallel beam search"""
        try:
            for iteration in range(n_iterations*5):
                logger.info(f"Starting iteration {iteration}")

                # Generate and evaluate candidates in parallel
                generation_tasks = []
                for group in self.beam_groups:
                    if iteration == 0:
                        # Initialize with starting state
                        state = self.config.initial_state
                        group.evaluator.instances[0].reset(state)
                        entities = group.evaluator.instances[0].get_entities()
                        conversation = Conversation(messages=[
                            Message(role="system", content=self.config.system_prompt),
                            Message(role="assistant", content="print(f'Inventory: {inspect_inventory()}')\n"
                                                              "print(f'Entities: {get_entities()}')\n"),
                            Message(role="user", content=f"1: ('Inventory: {state.inventory.__dict__}')\n"
                                                         f"2: ('Entities: {entities}')"),
                        ])
                        parent_id = None
                    else:
                        state = group.current_state
                        conversation = copy.deepcopy(group.current_conversation)
                        parent_id = group.current_program.id if group.current_program else None

                    task = group.beam.evaluate_candidates(
                        state=state,
                        conversation=conversation,
                        parent_id=parent_id,
                        n_samples=self.config.expansion_factor,

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
        """Run parallel beam search"""
        try:
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