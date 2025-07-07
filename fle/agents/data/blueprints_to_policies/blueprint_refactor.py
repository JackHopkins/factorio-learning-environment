import json
import os
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Literal, Optional, NamedTuple
from dataclasses import dataclass
import openai
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from cluster.remote.cluster_ips import get_public_ips
from data.blueprints_to_policies.processing_state import ProcessingState
from fle.env import Position
from fle.env import FactorioInstance
from blueprint_analyzer import BlueprintAnalyzer
from fle.env.game_types import Resource

load_dotenv()


@dataclass
class ServerConfig:
    address: str
    tcp_port: int


@dataclass
class RefactorConfig:
    model: Literal["gpt-4", "claude-3", "deepseek-coder"]
    temperature: float = 1
    max_attempts: int = 100
    output_dir: str = "refactor"
    num_workers: int = 4  # Number of parallel workers
    cluster_name: Optional[str] = None  # ECS cluster name if using AWS


class WorkerState:
    def __init__(self, server_config: ServerConfig, worker_id: int):
        self.server_config = server_config
        self.worker_id = worker_id
        self.instance: Optional[FactorioInstance] = None
        self.busy = False
        self.current_blueprint: Optional[str] = None
        self.last_heartbeat = time.time()

    def is_healthy(self) -> bool:
        return (
            time.time() - self.last_heartbeat < 30
        )  # Consider worker dead if no heartbeat for 30s

    def update_heartbeat(self):
        self.last_heartbeat = time.time()


class BlueprintMetrics(NamedTuple):
    total_entities: int
    distinct_entities: int
    successful_attempts: int
    total_attempts: int
    success_rate: float


def count_code_lines(code: str) -> int:
    """Count non-empty, non-comment lines of code."""
    lines = code.split("\n")
    return sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))


class BlueprintRefactor:
    """
    Refactor Factorio naive blueprint policies using language models to generate more efficient and diverse code.
    """

    def __init__(self, config: RefactorConfig):
        self.config = config
        self.anthropic = Anthropic()
        self.deepseek = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Set up logging
        log_dir = os.path.join(config.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Main logger
        self.logger = logging.getLogger("blueprint_refactor")
        self.logger.setLevel(logging.INFO)

        # File handler for all logs
        fh = logging.FileHandler(os.path.join(log_dir, "refactor.log"))
        fh.setLevel(logging.INFO)

        # Console handler for important logs
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatting
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        # Create worker-specific loggers
        self.worker_loggers = {}
        for i in range(config.num_workers):
            worker_logger = logging.getLogger(f"worker_{i}")
            worker_logger.setLevel(logging.INFO)

            # Worker-specific file handler
            wfh = logging.FileHandler(os.path.join(log_dir, f"worker_{i}.log"))
            wfh.setFormatter(formatter)
            worker_logger.addHandler(wfh)
            worker_logger.addHandler(ch)  # Also log to console

            self.worker_loggers[i] = worker_logger

        # Initialize state management
        self.state_file = os.path.join(config.output_dir, "processing_state.json")
        self.state = ProcessingState.load(self.state_file)

        # Initialize metrics
        self.metrics_df = self._init_metrics_df()

        # Initialize server pool
        self.servers = self._init_server_pool()
        self.worker_states = {}

        # Task queue for work distribution
        self.task_queue = queue.Queue()

        # Results tracking
        self.results_lock = threading.Lock()

    def _init_metrics_df(self) -> pd.DataFrame:
        """Initialize or load existing metrics DataFrame."""
        metrics_file = os.path.join(
            self.config.output_dir, f"refactor_metrics_{self.config.model}.csv"
        )
        if os.path.exists(metrics_file):
            return pd.read_csv(metrics_file)
        return pd.DataFrame(
            columns=[
                "model",
                "blueprint_name",
                "total_entities",
                "distinct_entities",
                "successful_attempts",
                "total_attempts",
                "success_rate",
                "original_loc",
                "min_refactored_loc",
                "max_refactored_loc",
                "avg_refactored_loc",
                "best_compression_ratio",
                "avg_compression_ratio",
            ]
        )

    def _update_metrics(
        self,
        base_name: str,
        blueprint: dict,
        original_loc: int,
        refactored_locs: List[int],
        successful_attempts: int,
        total_attempts: int,
    ):
        """
        Update metrics for a blueprint in a thread-safe manner.

        Args:
            base_name: Name of the blueprint
            blueprint: The blueprint dictionary
            original_loc: Lines of code in original implementation
            refactored_locs: List of lines of code in successful refactors
            successful_attempts: Number of successful refactoring attempts
            total_attempts: Total number of attempts made
        """
        with self.results_lock:
            # Calculate complexity metrics
            total_entities = len(blueprint["entities"])
            distinct_entities = len(
                {entity["name"] for entity in blueprint["entities"]}
            )

            # Calculate code metrics
            if refactored_locs:
                min_loc = min(refactored_locs)
                max_loc = max(refactored_locs)
                avg_loc = sum(refactored_locs) / len(refactored_locs)
                best_compression = original_loc / min_loc if min_loc > 0 else 0
                avg_compression = original_loc / avg_loc if avg_loc > 0 else 0
            else:
                min_loc = max_loc = avg_loc = best_compression = avg_compression = 0

            success_rate = (
                successful_attempts / total_attempts if total_attempts > 0 else 0
            )

            # Create new metrics row
            new_metrics = pd.DataFrame(
                [
                    {
                        "model": self.config.model,
                        "blueprint_name": base_name,
                        "total_entities": total_entities,
                        "distinct_entities": distinct_entities,
                        "successful_attempts": successful_attempts,
                        "total_attempts": total_attempts,
                        "success_rate": success_rate,
                        "original_loc": original_loc,
                        "min_refactored_loc": min_loc,
                        "max_refactored_loc": max_loc,
                        "avg_refactored_loc": avg_loc,
                        "best_compression_ratio": best_compression,
                        "avg_compression_ratio": avg_compression,
                    }
                ]
            )

            # Remove existing metrics for this blueprint/model if any
            self.metrics_df = self.metrics_df[
                ~(
                    (self.metrics_df["blueprint_name"] == base_name)
                    & (self.metrics_df["model"] == self.config.model)
                )
            ]

            # Append new metrics
            self.metrics_df = pd.concat(
                [self.metrics_df, new_metrics], ignore_index=True
            )

            # Save metrics to file
            metrics_path = os.path.join(
                self.config.output_dir, f"refactor_metrics_{self.config.model}.csv"
            )
            self.metrics_df.to_csv(metrics_path, index=False)

            # Log metrics update
            self.logger.info(f"Updated metrics for {base_name}:")
            self.logger.info(f"  Success rate: {success_rate:.2%}")
            self.logger.info(f"  Best compression: {best_compression:.2f}x")
            self.logger.info(f"  Average compression: {avg_compression:.2f}x")

            # Check if blueprint is complete
            if successful_attempts >= self.config.max_attempts:
                self.state.mark_complete(base_name)
                self.state.save(self.state_file)
                self.logger.info(f"Marked {base_name} as complete")

    def _create_more_ore(self, position: Position, size=20):
        """
        We need to create more ore, because some mining templates don't fit on the lab scenario ore deposits.
        :param position: Position to create ore
        :param size: Size of patch
        :return: A lua script to create more ore
        """
        return f"""
/c local surface=game.players[1].surface
local ore=nil
local size={size}
local density=10
for y=-size, size do
	for x=-size, size do
		a=(size+1-math.abs(x))*10
		b=(size+1-math.abs(y))*10
		if a<b then
			ore=math.random(a*density-a*(density-8), a*density+a*(density-8))
		end
		if b<a then
			ore=math.random(b*density-b*(density-8), b*density+b*(density-8))
		end
		if surface.get_tile({position.x}+x, {position.y}+y).collides_with("ground-tile") then
			surface.create_entity({{name="copper-ore", amount=ore, position={{{position.x}+x, {position.y}+y}}}})
		end
	end
end
""".strip()

    def _init_server_pool(self) -> List[ServerConfig]:
        """Initialize the pool of available Factorio servers."""
        if self.config.cluster_name:
            # Get servers from ECS cluster
            ips = get_public_ips(self.config.cluster_name)
            self.logger.info(
                f"Found {len(ips)} servers in ECS cluster {self.config.cluster_name}"
            )
            return [ServerConfig(ip, 27000) for ip in ips]
        else:
            # Use local development setup
            self.logger.info("No cluster name provided - using local server")
            self.config.num_workers = 1
            return [
                ServerConfig("localhost", 27000 + i)
                for i in range(self.config.num_workers)
            ]

    def _worker_heartbeat(self, worker_id: int):
        """Update worker heartbeat and log status."""
        if worker_id in self.worker_states:
            self.worker_states[worker_id].update_heartbeat()
            worker_logger = self.worker_loggers[worker_id]
            state = self.worker_states[worker_id]
            worker_logger.debug(f"Heartbeat - Processing: {state.current_blueprint}")

    def _worker_process(self, worker_id: int):
        """Main worker process for handling blueprint refactoring tasks."""
        worker_logger = self.worker_loggers[worker_id]
        server_config = self.servers[worker_id % len(self.servers)]

        # Initialize worker state
        self.worker_states[worker_id] = WorkerState(server_config, worker_id)
        state = self.worker_states[worker_id]

        worker_logger.info(
            f"Worker {worker_id} starting on {server_config.address}:{server_config.tcp_port}"
        )

        # Start heartbeat thread
        def heartbeat_routine():
            while state.instance is not None:  # Run until worker shuts down
                self._worker_heartbeat(worker_id)
                time.sleep(10)  # Update heartbeat every 30 seconds

        heartbeat_thread = threading.Thread(
            target=heartbeat_routine,
            name=f"heartbeat-{worker_id}",
            daemon=True,  # Make thread daemon so it exits when main thread exits
        )
        heartbeat_thread.start()

        try:
            # Initialize Factorio instance
            state.instance = FactorioInstance(
                address=server_config.address,
                tcp_port=server_config.tcp_port,
                bounding_box=200,
                fast=True,
                cache_scripts=False,
                inventory={},
            )
            time.sleep(3)  # Wait for Factorio to start
            copper_ore_patch = state.instance.get_resource_patch(
                Resource.CopperOre, state.instance.nearest(Resource.CopperOre)
            )
            center_position = copper_ore_patch.bounding_box.center
            create_more_ore_command = self._create_more_ore(center_position)
            state.instance.add_command(create_more_ore_command, raw=True)
            state.instance.execute_transaction()

            expanded_copper_ore_patch = state.instance.get_resource_patch(
                Resource.CopperOre, state.instance.nearest(Resource.CopperOre)
            )
            assert expanded_copper_ore_patch.size != copper_ore_patch.size, (
                f"Failed to expand copper ore patch from {copper_ore_patch.size} to {expanded_copper_ore_patch.size}"
            )

            while True:
                try:
                    # Get next task
                    blueprint_path, code_path = self.task_queue.get_nowait()
                    base_name = os.path.splitext(os.path.basename(code_path))[0]

                    state.current_blueprint = base_name
                    state.busy = True
                    worker_logger.info(f"Processing blueprint: {base_name}")

                    # Process blueprint
                    self._process_single_blueprint(
                        blueprint_path, code_path, state.instance, worker_logger
                    )

                    state.busy = False
                    state.current_blueprint = None
                    self.task_queue.task_done()

                except queue.Empty:
                    break

        except Exception as e:
            worker_logger.error(f"Worker {worker_id} failed: {str(e)}", exc_info=True)
        finally:
            worker_logger.info(f"Worker {worker_id} shutting down")
            if state.instance:
                state.instance.close()

    def code_contains_required_actions(
        self, code, required_actions=["connect_entities", "place_entity_next_to"]
    ):
        return any(action in code for action in required_actions)

    def _process_single_blueprint(
        self,
        blueprint_path: str,
        code_path: str,
        instance: FactorioInstance,
        logger: logging.Logger,
    ):
        """Process a single blueprint with the given Factorio instance."""
        base_name = os.path.splitext(os.path.basename(code_path))[0]

        # Load files
        blueprint, original_code = self.load_blueprint_and_code(
            blueprint_path, code_path
        )
        original_loc = count_code_lines(original_code)
        original_code = original_code.replace("game.", "")

        # Get inventory
        analyzer = BlueprintAnalyzer(blueprint)
        inventory = analyzer.get_inventory()

        # Setup output directory
        base_output_dir = os.path.join(self.config.output_dir, base_name)
        os.makedirs(base_output_dir, exist_ok=True)

        successful_attempts = 0
        total_attempts = 0
        refactored_locs = []

        while (
            successful_attempts < self.config.max_attempts
            and total_attempts < self.config.max_attempts
        ):
            try:
                logger.info(f"Attempt {total_attempts + 1} for `{base_name}`")

                # Get refactored code
                refactored_code = self.get_refactored_code(
                    blueprint, original_code, base_name
                )
                refactored_loc = count_code_lines(refactored_code)
                refactored_code = refactored_code.replace("```python", "").replace(
                    "```", ""
                )

                logger.info("Verifying placement...")
                if self.verify_placement(
                    refactored_code, blueprint, instance, inventory
                ) and self.code_contains_required_actions(refactored_code):
                    # Save successful refactor
                    output_path = os.path.join(
                        base_output_dir,
                        f"place_entity_next_to_{self.config.model}_{successful_attempts + 1}.py",
                    )

                    with open(output_path, "w") as f:
                        f.write(refactored_code)

                    successful_attempts += 1
                    refactored_locs.append(refactored_loc)
                    logger.info(
                        f"Successfully generated refactor {successful_attempts} "
                        f"(Compression: {original_loc / refactored_loc:.2f}x)"
                    )
                else:
                    logger.warning("Refactor failed verification")

            except Exception as e:
                logger.error(
                    f"Error during refactoring attempt: {str(e)}", exc_info=True
                )

            total_attempts += 1
            with self.results_lock:
                self.state.add_attempt(base_name, self.config.model)
                self.state.save(self.state_file)

        # Update metrics
        self._update_metrics(
            base_name,
            blueprint,
            original_loc,
            refactored_locs,
            successful_attempts,
            total_attempts,
        )

    def process_directory(self, implementation_dir: str, blueprints_dir: str):
        """Process all blueprints in parallel across available servers."""
        # Queue up all tasks
        for filename in os.listdir(implementation_dir):
            if filename.endswith(".py"):
                base_name = os.path.splitext(filename)[0]

                # Skip if already completed
                if base_name in self.state.completed_blueprints:
                    self.logger.info(f"Skipping {filename} - already completed")
                    continue

                blueprint_path = os.path.join(
                    blueprints_dir, filename.replace(".py", ".json")
                )
                code_path = os.path.join(implementation_dir, filename)

                if os.path.exists(blueprint_path):
                    self.task_queue.put((blueprint_path, code_path))

        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.config.num_workers) as executor:
            workers = []
            for i in range(self.config.num_workers):
                workers.append(executor.submit(self._worker_process, i))

            # Monitor workers
            while any(not w.done() for w in workers):
                self._log_worker_status()
                time.sleep(30)

        self.logger.info("All workers completed")

    def _log_worker_status(self):
        """Log current status of all workers."""
        status = []
        for worker_id, state in self.worker_states.items():
            status.append(
                f"Worker {worker_id} - "
                f"{'Busy' if state.busy else 'Idle'} - "
                f"Blueprint: {state.current_blueprint or 'None'} - "
                f"Healthy: {state.is_healthy()}"
            )
        self.logger.info("Worker Status:\n" + "\n".join(status))

    def load_blueprint_and_code(
        self, blueprint_path: str, code_path: str
    ) -> tuple[dict, str]:
        """Load the blueprint JSON and corresponding Python code."""
        with open(blueprint_path, "r") as f:
            blueprint = json.loads(f.read())
        with open(code_path, "r") as f:
            original_code = f.read()
        return blueprint, original_code

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get_refactored_code(
        self, blueprint: dict, original_code: str, base_name: str
    ) -> str:
        """Get refactored code from the specified LLM."""
        prompt = f"""You are an expert Python programmer and player of the game Factorio.

Here is a entity layout in JSON called '{base_name}':
```json
{json.dumps(blueprint, indent=2)}
```

The current Python implementation that creates this layout is as follows:
```python
{original_code}
``` 

Please rewrite this code to use `connect_entities` and `place_entity_next_to` methods, while preserving exactly the same functionality. 
The code must produce identical entity placements. Don't redefine any used classes, as these will be imported for you. Think about the overall purpose of the code before refactoring it.

Key requirements:
1. Must use the same Position, Direction, and Prototype classes
2. Must start from the same origin calculation
3. Must use `place_entity_next_to` function to place entities next to each other.
4. Must use `connect_entities` function to create lines of transport belts.
4. Can use any Python features but must maintain compatibility
5. Focus on making the code better, not just shorter
6. Add comments before each section that explains the purpose of the following code given that we are creating a '{base_name}'.
7. Avoid magic numbers and hard-coded values, declare them as variables instead where possible. 
    7a. Specifically, ensure that the bounding box parameters are calculated in terms of the number of entities that we are placing.

:example: place_entity_next_to(Prototype.WoodenChest, Position(x=0, y=0), direction=Direction.UP, spacing=1)
:return: Entity placed (with position of x=0, y=-1)

:example: connect_entities(Position(x=0, y=0), Position(x=0, y=1)), connection_type=Prototype.TransportBelt)
:return: Entity group of transport belts created

Only return python code between ```python and ``` tags, nothing else.
"""

        if "gpt" in self.config.model:
            response = self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content

        elif self.config.model == "claude-3":
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            return response.content[0].text

        elif self.config.model == "deepseek-coder":
            try:
                response = self.deepseek.chat.completions.create(
                    model="deepseek-coder",  # -33b-instruct
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4096,
                    temperature=self.config.temperature,
                )
            except openai.error.OpenAIError as e:
                print(f"Error during DeepSeek request: {str(e)}")
            return response.choices[0].message.content

    def verify_placement(
        self, code: str, blueprint: dict, instance: FactorioInstance, inventory: dict
    ) -> bool:
        """Verify that the refactored code produces identical entity placement."""
        try:
            instance.reset()
            instance.set_inventory(inventory)
            # Execute the code
            score, goal, result = instance.eval_with_error(
                code.replace("game.", ""), timeout=60
            )

            if "error" in result:
                return False

            # Get placed entities and verify
            game_entities = instance.get_entities()
            analyzer = BlueprintAnalyzer(blueprint)
            analyzer.verify_placement(game_entities)
            return True

        except Exception as e:
            print(f"Verification failed: {str(e)}")
            return False

    def calculate_blueprint_complexity(self, blueprint: dict) -> tuple[int, int]:
        """Calculate complexity metrics for a blueprint."""
        total_entities = len(blueprint["entities"])
        distinct_entities = len({entity["name"] for entity in blueprint["entities"]})
        return total_entities, distinct_entities

    # def process_blueprint2(self, blueprint_path: str, code_path: str):
    #     """Process a single blueprint, generating multiple refactored versions."""
    #     base_name = os.path.splitext(os.path.basename(code_path))[0]
    #
    #     # Check if this blueprint is already completed for this model
    #     current_attempts = self.state.get_attempts(base_name, self.config.model)
    #     if current_attempts >= self.config.max_attempts:
    #         print(f"Skipping {base_name} - already completed {current_attempts} attempts")
    #         return
    #
    #     # Load original files
    #     blueprint, original_code = self.load_blueprint_and_code(blueprint_path, code_path)
    #     original_loc = count_code_lines(original_code)
    #
    #     # Remove `game.` prefixes
    #     original_code = original_code.replace("game.", "")
    #
    #     # Calculate complexity metrics
    #     total_entities, distinct_entities = self.calculate_blueprint_complexity(blueprint)
    #
    #     # Get inventory from blueprint
    #     analyzer = BlueprintAnalyzer(blueprint)
    #     inventory = analyzer.get_inventory()
    #
    #     # Generate base output path
    #     base_name = os.path.splitext(os.path.basename(code_path))[0]
    #     base_output_dir = os.path.join(self.config.output_dir, base_name)
    #     os.makedirs(base_output_dir, exist_ok=True)
    #
    #     successful_attempts = 0
    #     total_attempts = 0
    #     refactored_locs = []
    #
    #     while successful_attempts < self.config.max_attempts and total_attempts < self.config.max_attempts * 2:
    #         try:
    #             # Get refactored code
    #             refactored_code = self.get_refactored_code(blueprint, original_code)
    #
    #             # Count lines of refactored code
    #             refactored_loc = count_code_lines(refactored_code)
    #
    #             # Strip out ```python and ```
    #             refactored_code = refactored_code.replace("```python", "").replace("```", "")
    #
    #             # Verify placement
    #             if self.verify_placement(refactored_code, blueprint, inventory):
    #                 # Save successful refactor
    #                 output_path = os.path.join(
    #                     base_output_dir,
    #                     f"refactor_{self.config.model}_{successful_attempts + 1}.py"
    #                 )
    #                 increment = 1
    #                 while os.path.exists(output_path):
    #                     output_path = os.path.join(
    #                         base_output_dir,
    #                         f"refactor_{self.config.model}_{successful_attempts + 1 + increment}.py"
    #                     )
    #                     increment += 1
    #
    #                 with open(output_path, 'w') as f:
    #                     f.write(refactored_code)
    #                 successful_attempts += 1
    #                 refactored_locs.append(refactored_loc)
    #                 print(f"Successfully generated refactor {successful_attempts} "
    #                       f"(Compression: {original_loc / refactored_loc:.2f}x)")
    #             else:
    #                 print("Refactor failed verification")
    #
    #             total_attempts += 1
    #             self.state.add_attempt(base_name, self.config.model)
    #             self.state.save(self.state_file)
    #
    #         except Exception as e:
    #             print(f"Error during refactoring attempt: {str(e)}")
    #             total_attempts += 1
    #             self.state.add_attempt(base_name, self.config.model)
    #             self.state.save(self.state_file)
    #             continue
    #
    #     # Calculate compression metrics
    #     if refactored_locs:
    #         min_loc = min(refactored_locs)
    #         max_loc = max(refactored_locs)
    #         avg_loc = sum(refactored_locs) / len(refactored_locs)
    #         best_compression = original_loc / min_loc if min_loc > 0 else 0
    #         avg_compression = original_loc / avg_loc if avg_loc > 0 else 0
    #     else:
    #         min_loc = max_loc = avg_loc = best_compression = avg_compression = 0
    #
    #     # Record metrics
    #     success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0
    #     new_metrics = pd.DataFrame([{
    #         'model': self.config.model,
    #         'blueprint_name': base_name,
    #         'total_entities': total_entities,
    #         'distinct_entities': distinct_entities,
    #         'successful_attempts': successful_attempts,
    #         'total_attempts': total_attempts,
    #         'success_rate': success_rate,
    #         'original_loc': original_loc,
    #         'min_refactored_loc': min_loc,
    #         'max_refactored_loc': max_loc,
    #         'avg_refactored_loc': avg_loc,
    #         'best_compression_ratio': best_compression,
    #         'avg_compression_ratio': avg_compression
    #     }])
    #     # Remove existing metrics for this blueprint/model if any
    #     self.metrics_df = self.metrics_df[
    #         ~((self.metrics_df['blueprint_name'] == base_name) &
    #           (self.metrics_df['model'] == self.config.model))
    #     ]
    #     self.metrics_df = pd.concat([self.metrics_df, new_metrics], ignore_index=True)
    #     self.save_metrics()
    #
    #     if successful_attempts >= self.config.max_attempts:
    #         self.state.mark_complete(base_name)
    #         self.state.save(self.state_file)

    # def process_directory(self, blueprints_dir: str):
    #     """Process all blueprint/code pairs in a directory."""
    #     for filename in os.listdir(blueprints_dir):
    #         if filename.endswith(".py"):
    #             base_name = os.path.splitext(filename)[0]
    #
    #             # Skip if blueprint is already completed
    #             if base_name in self.state.completed_blueprints:
    #                 print(f"Skipping {filename} - already completed")
    #                 continue
    #
    #             blueprint_path = os.path.join(
    #                 blueprints_dir,
    #                 filename.replace(".py", ".json")
    #             )
    #             code_path = os.path.join(blueprints_dir, filename)
    #
    #             if os.path.exists(blueprint_path):
    #                 print(f"Processing {filename}")
    #                 self.process_blueprint(blueprint_path, code_path)

    def save_metrics(self):
        """Save metrics to CSV file."""
        metrics_path = os.path.join(
            self.config.output_dir,
            f"refactor_metrics_(place_next_to)_{self.config.model}.csv",
        )
        self.metrics_df.to_csv(metrics_path, index=False)

    def analyze_metrics(self) -> pd.DataFrame:
        """Analyze and return summary statistics of the metrics."""
        summary = (
            self.metrics_df.groupby("model")
            .agg(
                {
                    "success_rate": ["mean", "std"],
                    "total_entities": ["mean", "std"],
                    "distinct_entities": ["mean", "std"],
                    "best_compression_ratio": ["mean", "std", "max"],
                    "avg_compression_ratio": ["mean", "std"],
                }
            )
            .round(3)
        )

        # Calculate correlations
        correlations = pd.DataFrame(
            {
                "total_entities_correlation": self.metrics_df.groupby("model").apply(
                    lambda x: x["total_entities"].corr(x["success_rate"])
                ),
                "distinct_entities_correlation": self.metrics_df.groupby("model").apply(
                    lambda x: x["distinct_entities"].corr(x["success_rate"])
                ),
                "complexity_compression_correlation": self.metrics_df.groupby(
                    "model"
                ).apply(
                    lambda x: x["total_entities"].corr(x["best_compression_ratio"])
                ),
            }
        )

        return pd.concat([summary, correlations], axis=1)


if __name__ == "__main__":
    for model in ["deepseek-coder", "claude-3", "gpt-4o"]:
        config = RefactorConfig(
            model=model,
            temperature=1,
            max_attempts=20,
            output_dir="place_next_to_connect",
            num_workers=8,
            cluster_name="FactorioCluster",
        )
        exec_directory = os.path.dirname(os.path.abspath(__file__))
        refactor = BlueprintRefactor(config)
        refactor.process_directory("full", "blueprints/mining")

        # Print analysis
        print("\nMetrics Analysis:")
        print(refactor.analyze_metrics())
