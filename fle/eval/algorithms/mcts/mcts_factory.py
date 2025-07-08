import dataclasses
import json
from datetime import datetime
from typing import Optional, Dict, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import argparse
from pathlib import Path
import questionary
from dataclasses import asdict

from .samplers import BeamSampler
from fle.commons.models.game_state import GameState
from fle.agents.llm.api_factory import APIFactory


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
        "34708": -100,  # 'INES'
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


class MCTSType(Enum):
    CHUNKED = "chunked"
    PLANNING = "planning"
    NORMAL = "mcts"
    OBJECTIVE = "objective"


class SamplerType(Enum):
    KLD = "kld"
    WEIGHTED_REWARD = "weighted reward"
    BEAM = "beam"


@dataclass
class SamplerConfig:
    temperature: Optional[float] = 0.7
    compression_strength: Optional[float] = None
    max_conversation_length: Optional[int] = 30
    adaptive_period: Optional[int] = 200
    window_size: Optional[int] = 200
    beam_width: Optional[int] = 8
    exploration_prob: Optional[float] = 0.1
    maximum_lookback: int = 20


@dataclass
class BaseConfig:
    mcts_type: MCTSType
    system_prompt: str
    version: int
    version_description: Optional[str] = ""
    n_parallel: int = 4
    max_steps: int = 1000
    skip_failures: bool = False
    model: Optional[str] = None
    sampler_type: Optional[SamplerType] = None
    presence_penalty: float = 0
    frequency_penalty: float = 0
    error_penalty: float = -10


@dataclass
class PlanningConfig(BaseConfig):
    planning_model: str = "claude-3-5-sonnet-20241022"
    executor_model: str = (
        "ft:gpt-4o-2024-08-06:paperplane-ai:fact-instruct-1:ATSVGf4d:ckpt-step-214"
    )
    objective_model: str = (
        "ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91"
    )
    step_executor_prompt_path: Path = Path(
        "../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_supervised"
    )
    step_generator_prompt_path: Path = Path(
        "../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_generator"
    )
    step_judge_prompt_path: Path = Path(
        "../../../data/prompts/bottoms_up_prompts/finetuning_prompts/step_judge"
    )
    example_plan_prompt_path: Path = Path(
        "../../../data/prompts/bottoms_up_prompts/finetuning_prompts/executor_plan"
    )
    max_steps_per_objective: int = 8
    number_of_steps_for_judge: int = 3
    n_parallel: int = 8


@dataclass
class ChunkedConfig(BaseConfig):
    max_conversation_length: int = 50
    _logit_bias: Dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self):
        if self.model:
            self._logit_bias = get_logit_bias(self.model)

    @property
    def logit_bias(self) -> Dict[str, float]:
        return self._logit_bias


@dataclass
class ObjectiveConfig(ChunkedConfig):
    objective_model: str = "ft:gpt-4o-mini-2024-07-18:paperplane-ai:plans-tree:AcZ8gHSo"


def _get_sampler(
    sampler_type: SamplerType,
    db_client,
    compression_strength=None,
    max_conversation_length=20,
    adaptive_period=200,
    window_size: int = 300,
    temperature: float = 1.0,
    beam_width: int = 8,
    exploration_prob=0.1,
    maximum_lookback=10,
):
    from fle.eval.algorithms.mcts.samplers import KLDiversityAchievementSampler
    from fle.eval.algorithms.mcts.samplers import DynamicRewardWeightedSampler

    if sampler_type == SamplerType.KLD:
        return KLDiversityAchievementSampler(db_client, window_size, temperature)
    elif sampler_type == SamplerType.BEAM:
        return BeamSampler(
            db_client, beam_width, max_conversation_length, exploration_prob
        )
    return DynamicRewardWeightedSampler(
        db_client,
        compression_strength,
        max_conversation_length,
        adaptive_period,
        maximum_lookback,
    )


class MCTSFactory:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not MCTSFactory._initialized:
            self.db_client = None
            self.api_factory = None
            self.instances = None
            self.sampler = None
            MCTSFactory._initialized = True

    def initialize(
        self,
        instances,
        db_client,
        config: Union[BaseConfig, PlanningConfig, ChunkedConfig],
        sampler_config: SamplerConfig,
    ):
        self.instances = instances
        self.db_client = db_client
        self.config = config
        self.api_factory = APIFactory(model=config.model)
        self.sampler = _get_sampler(
            config.sampler_type, db_client, **sampler_config.__dict__
        )

    def create_mcts(
        self, config: Union[BaseConfig, PlanningConfig, ChunkedConfig, ObjectiveConfig]
    ):
        if not all([self.instances, self.db_client, self.api_factory, self.sampler]):
            raise ValueError("Factory not initialized. Call initialize() first.")

        if config.mcts_type == MCTSType.CHUNKED:
            return self._create_chunked_mcts(config)
        elif config.mcts_type == MCTSType.PLANNING:
            return self._create_planning_mcts(config)
        elif config.mcts_type == MCTSType.OBJECTIVE:
            return self._create_objective_mcts(config)
        elif config.mcts_type == MCTSType.NORMAL:
            return self._create_mcts(config)

        raise ValueError(f"Unknown MCTS type: {config.mcts_type}")

    def _create_mcts(self, config: BaseConfig):
        from eval.algorithms.mcts import MCTS
        from eval.algorithms.mcts import ParallelMCTS
        from eval.algorithms.mcts import ParallelMCTSConfig

        mcts_config = ParallelMCTSConfig(
            n_parallel=config.n_parallel,
            system_prompt=config.system_prompt,
            initial_state=GameState.from_instance(self.instances[0]),
            mcts_class=MCTS,
            sampler=self.sampler,
            mcts_kwargs={
                "version": config.version,
                "version_description": config.version_description,
                "error_penalty": config.error_penalty,
            },
        )
        return ParallelMCTS(
            instances=self.instances,
            db_client=self.db_client,
            api_factory=self.api_factory,
            config=mcts_config,
            version=config.version,
            version_description=config.version_description,
        )

    def _create_chunked_mcts(self, config: ChunkedConfig):
        from .mcts import ChunkedMCTS
        from .parallel_mcts import ParallelMCTS
        from .parallel_mcts_config import ParallelMCTSConfig
        from fle.agents.formatters.conversation_formatter_abc import (
            StructurePreservingFormatter,
        )

        mcts_config = ParallelMCTSConfig(
            n_parallel=config.n_parallel,
            system_prompt=config.system_prompt,
            initial_state=GameState.from_instance(self.instances[0]),
            mcts_class=ChunkedMCTS,
            sampler=self.sampler,
            mcts_kwargs={
                "logit_bias": config.logit_bias,
                "version": config.version,
                "version_description": config.version_description,
                "formatter": StructurePreservingFormatter(planning=True),
                "presence_penalty": config.presence_penalty,
                "frequency_penalty": config.frequency_penalty,
                "error_penalty": config.error_penalty,
            },
        )

        return ParallelMCTS(
            instances=self.instances,
            db_client=self.db_client,
            api_factory=self.api_factory,
            config=mcts_config,
            version=config.version,
            version_description=config.version_description,
        )

    def _create_objective_mcts(self, config: ObjectiveConfig):
        from eval.algorithms.mcts import ObjectiveMCTS
        from eval.algorithms.mcts import ParallelMCTS
        from eval.algorithms.mcts import ParallelMCTSConfig
        from fle.agents.formatters.conversation_formatter_abc import (
            StructurePreservingFormatter,
        )

        mcts_config = ParallelMCTSConfig(
            n_parallel=config.n_parallel,
            system_prompt=config.system_prompt,
            initial_state=GameState.from_instance(self.instances[0]),
            mcts_class=ObjectiveMCTS,
            sampler=self.sampler,
            mcts_kwargs={
                "objective_model": config.objective_model,
                "logit_bias": config.logit_bias,
                "version": config.version,
                "version_description": config.version_description,
                "formatter": StructurePreservingFormatter(planning=True),
                "presence_penalty": config.presence_penalty,
                "frequency_penalty": config.frequency_penalty,
                "error_penalty": config.error_penalty,
            },
        )

        return ParallelMCTS(
            instances=self.instances,
            db_client=self.db_client,
            api_factory=self.api_factory,
            config=mcts_config,
            version=config.version,
            version_description=config.version_description,
        )

    def _create_planning_mcts(self, config: PlanningConfig):
        from eval.algorithms.mcts import PlanningMCTS
        from eval.algorithms.mcts import ParallelPlanningMCTS
        from eval.algorithms.mcts import ParallelMCTSConfig

        game_state = GameState.from_instance(self.instances[0])
        mcts_config = ParallelMCTSConfig(
            n_parallel=config.n_parallel,
            mcts_class=PlanningMCTS,
            sampler=self.sampler,
            system_prompt=config.system_prompt,
            initial_state=game_state,
            max_steps_per_objective=config.max_steps_per_objective,
            number_of_steps_for_judge=config.number_of_steps_for_judge,
            mcts_kwargs={
                "planning_model": config.planning_model,
                "executor_model": config.executor_model,
                "objective_model": config.objective_model,
                "step_executor_prompt_path": config.step_executor_prompt_path,
                "step_generator_prompt_path": config.step_generator_prompt_path,
                "step_judge_prompt_path": config.step_judge_prompt_path,
                "example_plan_prompt_path": config.example_plan_prompt_path,
                "system_prompt": config.system_prompt,
                "initial_state": game_state,
                "error_penalty": config.error_penalty,
            },
        )

        return ParallelPlanningMCTS(
            instances=self.instances,
            db_client=self.db_client,
            api_factory=self.api_factory,
            config=mcts_config,
            version=config.version,
            version_description=config.version_description,
        )

    @staticmethod
    def get_config_from_cli(
        default_version=42,
    ) -> Tuple[Union[BaseConfig, PlanningConfig, ChunkedConfig], SamplerConfig]:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--type",
            choices=["chunked", "planning", "normal", "objective"],
            help="MCTS type",
        )
        parser.add_argument(
            "--no-interactive", action="store_true", help="Skip interactive prompts"
        )
        args, _ = parser.parse_known_args()

        if args.no_interactive:
            config, sampler_config = MCTSFactory._get_config_from_args(parser)
        else:
            config, sampler_config = MCTSFactory._get_config_interactive(
                args.type, default_version
            )

        # Save the configuration
        MCTSFactory._save_config(config, sampler_config)

        return config, sampler_config

    @staticmethod
    def _get_config_from_args(
        parser,
    ) -> Tuple[Union[BaseConfig, PlanningConfig, ChunkedConfig], SamplerConfig]:
        parser.add_argument("--model", required=True)
        parser.add_argument("--version", type=int, required=True)
        parser.add_argument("--version-description", required=True)
        parser.add_argument("--n-parallel", type=int, default=4)
        parser.add_argument("--error-penalty", type=float, default=-10)
        parser.add_argument("--temperature", type=float, default=0.7)
        parser.add_argument("--compression-strength", type=float, default=None)
        parser.add_argument("--max-conversation-length", type=int, default=30)
        parser.add_argument("--adaptive-period", type=int, default=200)
        parser.add_argument("--window-size", type=int, default=200)

        # Planning-specific arguments
        parser.add_argument("--planning-model", default="claude-3-5-sonnet-20241022")
        parser.add_argument(
            "--executor-model",
            default="ft:gpt-4o-2024-08-06:paperplane-ai:fact-instruct-1:ATSVGf4d:ckpt-step-214",
        )
        parser.add_argument(
            "--objective-model",
            default="ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91",
        )
        parser.add_argument(
            "--step-executor-prompt-path",
            default="../../prompts/bottoms_up_prompts/finetuning_prompts/step_supervised",
        )
        parser.add_argument(
            "--step-generator-prompt-path",
            default="../../prompts/bottoms_up_prompts/finetuning_prompts/step_generator",
        )
        parser.add_argument(
            "--step-judge-prompt-path",
            default="../../prompts/bottoms_up_prompts/finetuning_prompts/step_judge",
        )
        parser.add_argument(
            "--example-plan-prompt-path",
            default="../../prompts/bottoms_up_prompts/finetuning_prompts/executor_plan",
        )

        args = parser.parse_args()
        mcts_type = MCTSType(args.type)

        if mcts_type == MCTSType.PLANNING:
            mcts_config = PlanningConfig(
                mcts_type=mcts_type,
                model=args.model,
                version=args.version,
                version_description=args.version_description,
                n_parallel=args.n_parallel,
                system_prompt="",
                planning_model=args.planning_model,
                executor_model=args.executor_model,
                objective_model=args.objective_model,
                step_executor_prompt_path=Path(args.step_executor_prompt_path),
                step_generator_prompt_path=Path(args.step_generator_prompt_path),
                step_judge_prompt_path=Path(args.step_judge_prompt_path),
                example_plan_prompt_path=Path(args.example_plan_prompt_path),
                error_penalty=args.error_penalty,
            )
        elif mcts_type == MCTSType.CHUNKED:
            mcts_config = ChunkedConfig(
                mcts_type=mcts_type,
                model=args.model,
                version=args.version,
                version_description=args.version_description,
                n_parallel=args.n_parallel,
                system_prompt="",
                error_penalty=args.error_penalty,
            )
        elif mcts_type == MCTSType.OBJECTIVE:
            mcts_config = ObjectiveConfig(
                objective_model=args.objective_model,
                mcts_type=mcts_type,
                model=args.model,
                version=args.version,
                version_description=args.version_description,
                n_parallel=args.n_parallel,
                system_prompt="",
                error_penalty=args.error_penalty,
            )
        else:
            mcts_config = BaseConfig(
                mcts_type=mcts_type,
                model=args.model,
                version=args.version,
                version_description=args.version_description,
                n_parallel=args.n_parallel,
                system_prompt="",
                error_penalty=args.error_penalty,
            )

        sampler_config = SamplerConfig(
            temperature=args.temperature,
            compression_strength=args.compression_strength,
            max_conversation_length=args.max_conversation_length,
            adaptive_period=args.adaptive_period,
            window_size=args.window_size,
        )

        return mcts_config, sampler_config

    @staticmethod
    def _get_config_interactive(
        default_type=None, default_version=42
    ) -> Tuple[Union[BaseConfig, PlanningConfig, ChunkedConfig], SamplerConfig]:
        mcts_type = (
            default_type
            or questionary.select(
                "Select MCTS type:",
                choices=["chunked", "normal", "planning", "objective"],
                instruction="Choose MCTS algorithm variant. Planning is recommended for complex tasks.",
            ).ask()
        )

        model = "gpt-4o"
        if mcts_type != "planning":
            model = questionary.select(
                "Model name:",
                choices=[
                    "gemini-2.0-flash-exp",
                    "gemini-2.0-flash-thinking-exp-1219",
                    "gemini-exp-1206",
                    "deepseek-chat",
                    "gpt-4o",
                    "claude-3-5-sonnet-20241022",
                    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                    "meta-llama/Meta-Llama-3.3-8B-Instruct-Turbo",
                    "Qwen/Qwen2.5-7B-Instruct-Turbo",
                    "Qwen/Qwen2.5-72B-Instruct-Turbo",
                    "ft:gpt-4o-mini-2024-07-18:paperplane-ai:mcts-pruned-masked:AYIViDdb",
                ],
                instruction="Model to use for program synthesis.",
            ).ask()

        base_config = {
            "mcts_type": MCTSType(mcts_type),
            "model": model,
            "version": int(
                questionary.text(
                    "Version:",
                    default=str(default_version),
                    instruction="The run version number. Higher versions may include bug fixes or improvements.",
                ).ask()
            ),
            "n_parallel": int(
                questionary.text("Number of parallel instances:", default="4").ask()
            ),
            "presence_penalty": float(
                questionary.text(
                    "Fixed presence penalty applied across previously sampled logits. -2 to 2.",
                    default="0",
                ).ask()
            ),
            "frequency_penalty": float(
                questionary.text(
                    "Dynamic frequency penalty applied across previously sampled logits. -2 to 2.",
                    default="0",
                ).ask()
            ),
            "error_penalty": float(
                questionary.text(
                    "Penalty applied when there is an execution error(e.g. syntax error).",
                    default="-10",
                ).ask()
            ),
            "system_prompt": "",
        }

        if mcts_type == "planning":
            mcts_config = PlanningConfig(
                **base_config,
                planning_model=questionary.text(
                    "Planning model:",
                    default="claude-3-5-sonnet-20241022",
                    instruction="The model that samples plans by reasoning over objectives and game states.",
                ).ask(),
                executor_model=questionary.text(
                    "Executor model:",
                    default="ft:gpt-4o-2024-08-06:paperplane-ai:fact-instruct-1:ATSVGf4d:ckpt-step-214",
                    instruction="The model that samples programs.",
                ).ask(),
                objective_model=questionary.text(
                    "Objective model:",
                    default="ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91",
                    instruction="The model that generates new objectives.",
                ).ask(),
                max_steps_per_objective=int(
                    questionary.text(
                        "Maximum steps per objective:",
                        default="12",
                    ).ask()
                ),
                number_of_steps_for_judge=int(
                    questionary.text(
                        "Number of steps for judge:",
                        default="3",
                        instruction="The branching factor for the planning tree. Higher values increase quality but use more tokens.",
                    ).ask()
                ),
            )
        elif mcts_type == "objective":
            mcts_config = ObjectiveConfig(
                **base_config,
                objective_model=questionary.text(
                    "Objective model:",
                    default="ft:gpt-4o-mini-2024-07-18:paperplane-ai:plans-tree:AcZ8gHSo",
                    instruction="The model that samples objectives.",
                ).ask(),
            )
        elif mcts_type == "chunked":
            mcts_config = ChunkedConfig(**base_config)
        else:
            mcts_config = BaseConfig(**base_config)

        # Sampler configuration
        mcts_config.sampler_type = SamplerType(
            questionary.select(
                "Select MCTS node sampler type:",
                choices=["weighted reward", "kld", "beam"],
                instruction="Choose the sampling method for selecting actions. KLD priorities varied game states. Weighted reward prioritizes high-reward states.",
            ).ask()
        )

        skip_failures = questionary.select(
            "Skip failures?",
            choices=["no", "yes"],
            instruction="Shall we skip nodes that trigger an exception/error?",
        ).ask()

        mcts_config.skip_failures = skip_failures == "yes"

        if mcts_config.sampler_type == SamplerType.KLD:
            sampler_config = SamplerConfig(
                temperature=float(
                    questionary.text(
                        "Temperature:",
                        default="1",
                        instruction="Higher values are closer to uniform sampling. Zero means greedy sampling from reward.",
                    ).ask()
                ),
                window_size=int(
                    questionary.text(
                        "Window size:",
                        default="100",
                        instruction="The number of recent programs to consider when sampling the next node",
                    ).ask()
                ),
                maximum_lookback=int(
                    questionary.text("Maximum lookback steps", default="20").ask()
                ),
            )
        elif mcts_config.sampler_type == SamplerType.BEAM:
            sampler_config = SamplerConfig(
                beam_width=int(
                    questionary.text(
                        "Beam width:",
                        default="8",
                        instruction="The number of nodes to keep in the beam for sampling subsequent nodes",
                    ).ask()
                ),
                exploration_prob=float(
                    questionary.text(
                        "Exploration probability:",
                        default="0.1",
                        instruction="The probability to sample outside of the beam (for exploration)",
                    ).ask()
                ),
                maximum_lookback=int(
                    questionary.text("Maximum lookback steps", default="20").ask()
                ),
            )
        else:  # WEIGHTED_REWARD
            compression_strength = float(
                questionary.text(
                    "Compression strength:",
                    instruction="Between 0-1. Higher values mean more exploration. Lower means more exploitation. -1 means adaptively cycle",
                    default="-1",
                ).ask()
            )

            if compression_strength < 0:
                compression_strength = None

            sampler_config = SamplerConfig(
                compression_strength=compression_strength,
                max_conversation_length=int(
                    questionary.text(
                        "Maximum conversation length:",
                        instruction="The maximum number of assistant actions in the dialogue",
                        default="100",
                    ).ask()
                ),
            )

            if compression_strength is not None:
                sampler_config.adaptive_period = int(
                    questionary.text(
                        "Adaptive period:",
                        instruction="The period for cycling exploration and exploitation",
                        default="50",
                    ).ask()
                )

            sampler_config.maximum_lookback = int(
                questionary.text("Maximum lookback steps", default="20").ask()
            )

        # Generate version description
        version_description = ""
        for key, value in mcts_config.__dict__.items():
            if isinstance(value, Path):
                value = str(value)
            version_description += f"{key}:{value}\n"

        for key, value in sampler_config.__dict__.items():
            if isinstance(value, Path):
                value = str(value)
            version_description += f"{key}:{value}\n"

        mcts_config.version_description = version_description

        return mcts_config, sampler_config

    @staticmethod
    def _save_config(
        config: Union[BaseConfig, PlanningConfig, ChunkedConfig],
        sampler_config: SamplerConfig,
    ):
        """Save the run configuration to a JSON file"""
        runs_dir = Path(f"runs/{config.version}")
        runs_dir.mkdir(exist_ok=True)

        # Convert configs to dictionaries, excluding complex objects
        config_dict = {
            k: str(v) if isinstance(v, (Path, MCTSType, SamplerType)) else v
            for k, v in asdict(config).items()
            if not k.endswith("_model") and not isinstance(v, (Path, type(None)))
        }

        sampler_dict = {
            k: v for k, v in dataclasses.asdict(sampler_config).items() if v is not None
        }

        # Combine configurations
        save_data = {
            "mcts_config": config_dict,
            "sampler_config": sampler_dict,
            "timestamp": datetime.now().isoformat(),
        }

        # Save to file
        config_file = runs_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(save_data, f, indent=2)
