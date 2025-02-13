import asyncio
import argparse
import os
import copy
from dataclasses import dataclass
from typing import Optional
import multiprocessing
from dotenv import load_dotenv

from agents import Python
from agents.agent_abc import AgentABC
from agents.basic_agent import BasicAgent
from eval.open.beam.run import SYSTEM_PROMPT, OBSERVATION_SPACE, MANUAL
from eval.open.db_client import DBClient
from eval.open.independent_runs.simple_evaluator import SimpleFactorioEvaluator
from models.conversation import Conversation
from models.message import Message
from models.game_state import GameState
from models.program import Program
from instance import FactorioInstance
from cluster.local.cluster_ips import get_local_container_ips
from agents.utils.python_parser import PythonParser
from models.response import Response

load_dotenv()

COURTESY_SLEEP = 5

@dataclass
class EvalConfig:
    """Configuration for evaluation"""
    #model: str
    #system_prompt: str
    agent: AgentABC
    initial_state: GameState
    version: int
    version_description: str
    resume_version: Optional[int] = None
    trajectory_length: int = 1000


class TrajectoryRunner:
    """Handles program generation and evaluation for a single trajectory"""

    def __init__(self,
                 #llm_factory: LLMFactory,
                 agent: AgentABC,
                 db_client: DBClient,
                 evaluator: SimpleFactorioEvaluator,
                 config: EvalConfig,
                 process_id: int):
        self.agent = agent
        self.db = db_client
        self.evaluator = evaluator
        self.config = config
        self.iteration_times = []
        self.process_id = process_id


    def _is_model_compatible_with_n_samples(self, model):
        """Check if model supports batch sampling"""
        return "gpt" in model or 'o1' in model or 'gemini' in model


    async def _generate_program(self, conversation: Conversation, response: Response, meta={}) -> Program:
        conversation = copy.deepcopy(conversation)
        try:
            policy = await self.agent.step(conversation, response)

            try:
                messages = conversation.model_dump()['messages']
            except Exception:
                messages = conversation.dict()['messages']

            program = Program(
                code=policy.code,
                conversation=conversation,
                response=response.response,
                token_usage=policy.meta.total_tokens,
                completion_token_usage=policy.meta.output_tokens,
                prompt_token_usage=policy.meta.input_tokens,
                version=self.config.version,
                model=self.agent.model,
                version_description=self.config.version_description,
                meta={"model": self.agent.model, "process_id": self.process_id},
                depth=len(messages) - 2
            )

            if meta:
                program.meta.update(meta)

            return program

        except Exception as e:
            print(f"Program generation failed: {str(e)}")
            return []

    async def get_resume_state(self) -> tuple[Optional[GameState], Optional[Conversation], Optional[int], Optional[int]]:
        """Get the state to resume from"""
        try:
            # Get most recent successful program to resume from
            query = """
            SELECT * FROM programs 
            WHERE version = %s
            AND state_json IS NOT NULL
            AND value IS NOT NULL
            AND meta->>'process_id' = %s::text
            ORDER BY created_at DESC
            LIMIT 1
            """

            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (self.config.resume_version, self.process_id))
                    results = cur.fetchall()

            if not results:
                print(f"No valid programs found for version {self.config.resume_version}")
                return None, None, None, None

            # Choose a program to resume from
            program = Program.from_row(dict(zip([desc[0] for desc in cur.description], results[0])))
            return program.state, program.conversation, program.id, program.depth

        except Exception as e:
            print(f"Error getting resume state: {e}")
            return None, None, None, None

    def get_eta(self, current_iteration):
        """Calculate estimated time remaining"""
        if not self.iteration_times:
            return "calculating..."

        avg_iteration_time = sum(self.iteration_times) / len(self.iteration_times)
        remaining_iterations = self.config.trajectory_length - current_iteration
        seconds_remaining = avg_iteration_time * remaining_iterations

        # Convert to hours:minutes:seconds
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    async def run(self):
        """Run a single trajectory"""
        # Initialize state based on resume or fresh start
        import time
        self.start_time = time.time()

        if self.config.resume_version:
            current_state, current_conversation, parent_id, depth = await self.get_resume_state()
            self.agent.conversation = current_conversation
            if not current_state:
                return
        else:
            current_state = self.config.initial_state
            depth = 0
            instance = self.evaluator.instance
            instance.reset(current_state)
            entities = instance.namespace.get_entities()
            current_conversation = Conversation(messages=[
                Message(role="system", content=self.config.agent.system_prompt),
                Message(role="assistant", content="print(f'Inventory: {inspect_inventory()}')\n"
                                                  "print(f'Entities: {get_entities()}')\n"),
                Message(role="user", content=f"1: ('Inventory: {current_state.inventory.__dict__}')\n"
                                             f"2: ('Entities: {entities}')"),
            ])
            self.agent.conversation = current_conversation
            parent_id = None

        last_response = None
        # Run trajectory
        for iteration in range(depth, self.config.trajectory_length):
            iteration_start = time.time()
            time.sleep(COURTESY_SLEEP) # courtesy sleep
            try:
                program = await self._generate_program(self.agent.conversation, last_response)

                print(f"Generated program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agent.model} - "
                      f"Iteration {iteration}/{self.config.trajectory_length}")

                if not program:
                    continue

                program.parent_id = parent_id

                # Evaluate program
                instance = self.evaluator.instance
                instance.reset(current_state)
                evaluated_program = await self.evaluator.evaluate(program, current_state)

                print(program.code + "\n"+"="*50)
                print("\033[1m\n".join(['>>>\t'+line for line in program.response.strip().replace('\\n', '\n\t').split('\n')]).strip()+"\033[0m")
                print(f"Evaluated program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agent.model} - "
                      f"Iteration {iteration}/{self.config.trajectory_length}")

                if not evaluated_program:
                    continue

                program = evaluated_program
                self.agent.conversation = program.conversation

                last_response = Response(
                    code=program.code,
                    created_at=program.created_at,
                    score=program.value,
                    achievements=program.achievements,
                    step=depth,
                    ticks = program.ticks,
                    flows = program.flows,
                    response=program.response,
                )

                # Save program
                saved_program = await self.db.create_program(program)
                print(f"Saved program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agent.model} - "
                      f"Iteration {iteration}/{self.config.trajectory_length}")

                parent_id = saved_program.id

                # Update state for next iteration
                if program.state:
                    current_state = program.state
                    current_conversation = program.conversation

                # Record iteration time
                iteration_time = time.time() - iteration_start
                self.iteration_times.append(iteration_time)

                # Keep only last 50 iterations for moving average
                if len(self.iteration_times) > 50:
                    self.iteration_times = self.iteration_times[-50:]

                if iteration % 10 == 0:
                    elapsed = time.time() - self.start_time
                    elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
                    eta = self.get_eta(iteration)
                    print(f"\033[92m Process {multiprocessing.current_process().name} - "
                          f"Model: {self.config.agent.model} - "
                          f"Iteration {iteration}/{self.config.trajectory_length} - "
                          f"Value: {program.value:.2f} - "
                          f"Elapsed: {elapsed_str} - "
                          f"ETA: {eta}")

            except Exception as e:
                print(f"Error in iteration {iteration}: {e}")
                continue


def create_factorio_instance(instance_id: int) -> FactorioInstance:
    """Create a single Factorio instance"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = FactorioInstance(
        address=ips[instance_id],
        tcp_port=tcp_ports[instance_id],
        bounding_box=200,
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=False
    )
    instance.speed(10)
    return instance


async def create_db_client() -> DBClient:
    """Create database client with connection pool"""
    return DBClient(
        max_conversation_length=40,
        min_connections=2,
        max_connections=5,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )


async def run_trajectory(process_id: int, config: EvalConfig):
    """Entry point for running a single trajectory"""
    # Initialize components
    db_client = await create_db_client()
    #llm_factory = LLMFactory(model=config.model)
    instance = create_factorio_instance(process_id)

    evaluator = SimpleFactorioEvaluator(
        db_client=db_client,
        instance=instance,
        value_accrual_time=1,
        error_penalty=0
    )

    runner = TrajectoryRunner(config.agent, db_client, evaluator, config, process_id)
    await runner.run()

    await db_client.cleanup()


def run_process(process_id: int, config: EvalConfig):
    """Process entry point"""
    asyncio.run(run_trajectory(process_id, config))


async def get_next_version() -> int:
    """Get next available version number"""
    db_client = await create_db_client()
    version = await db_client.get_largest_version()
    await db_client.cleanup()
    return version + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-versions', type=str, help='Comma-separated list of versions to resume from')
    args = parser.parse_args()

    # Model configurations
    model_configs = [
        #{"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "resume_version": 488},
        #{"model": "gpt-4o-mini", "resume_version": None},
        {"model": "gpt-4o", "resume_version": 532},
       # {"model": "gpt-4o-mini", "resume_version": 505},
        #{"model": "deepseek-chat", "resume_version": 507}
        #{"model": "deepseek-chat", "resume_version": None},#491},
        #{"model": "claude-3-5-sonnet-20241022", "resume_version": None}#517}#516}
        #{"model": "gpt-4o", "resume_version": 524}
        #{"model": "claude-3-5-sonnet-20241022", "resume_version": 527}
        #{"model": 'o3-mini', "resume_version": 510}#509 }#508}
    ]
    # model_configs = [
    #     {"model": "gpt-4o-mini", "resume_version": 487}
    # ]

    # Create initial state and get system prompt
    instance = create_factorio_instance(0)
    initial_state = GameState.from_instance(instance)
    API_SCHEMA = instance.get_system_prompt()
    system_prompt = SYSTEM_PROMPT + '\n\n' + API_SCHEMA + '\n\n# Observations:\n' + OBSERVATION_SPACE + '\n\n' + MANUAL + '\n```'

    run_configs = [
        { "agent": BasicAgent(model="gpt-4o", system_prompt=system_prompt), "resume_version": None}
    ]

    # Update resume versions if provided
    if args.resume_versions:
        versions = [int(v.strip()) if v.strip() else None for v in args.resume_versions.split(',')]
        for i, version in enumerate(versions[:len(model_configs)]):
            if version is not None:
                model_configs[i]["resume_version"] = version


    # Get starting version number for new runs
    base_version = asyncio.run(get_next_version())

    processes = []
    for run_idx, run_config in enumerate(run_configs):
        config = EvalConfig(
            agent=run_config["agent"],
            initial_state=initial_state,
            version=run_config["resume_version"] if run_config["resume_version"] else base_version + run_idx,
            version_description=f"model:{run_config['model']}\ntype:simple_trajectory",
            resume_version=run_config["resume_version"],
            trajectory_length=5000
        )

        # Start 4 processes for each model
        RUNS_PER_MODEL = 4
        for process_id in range(RUNS_PER_MODEL):
            global_process_id = (run_idx * RUNS_PER_MODEL) + process_id# + 16
            p = multiprocessing.Process(
                target=run_process,
                args=(global_process_id, config)
            )
            p.start()
            processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    main()