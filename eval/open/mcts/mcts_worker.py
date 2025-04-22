import copy
import math
from dataclasses import dataclass
from typing import Tuple

from agents import CompletionResult, CompletionReason, Response
from agents.agent_abc import AgentABC
from eval.open.db_client import PostgresDBClient
from eval.open.independent_runs.simple_evaluator import SimpleFactorioEvaluator
from eval.open._mcts_old.samplers.db_sampler import DBSampler
from instance import FactorioInstance
from models.achievements import ProductionFlows
from models.conversation import Conversation
from models.game_state import GameState
from models.message import Message
from models.program import Program
from namespace import FactorioNamespace


@dataclass
class MCTSConfig:
    """Configuration for MCTS search"""
    agent: AgentABC
    sampler: DBSampler
    version: int
    version_description: str
    max_iterations: int = 100  # Maximum iterations per search
    exploration_weight: float = 1.41  # UCT exploration parameter
    batch_size: int = 4  # Number of simulations to run in parallel
    max_depth: int = 50  # Maximum depth of search


class MCTSNode:
    """Represents a node in the MCTS search tree"""

    def __init__(self, program: Program = None, parent=None):
        self.program = program
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.pending_visits = 0  # Track visits that are currently in progress

    def add_child(self, child_program: Program) -> 'MCTSNode':
        """Add a child node with the given program"""
        child = MCTSNode(program=child_program, parent=self)
        self.children.append(child)
        return child

    def get_uct_value(self, exploration_weight: float) -> float:
        """Calculate UCT value for node selection"""
        if self.visits == 0:
            return float('inf')

        # If parent has no visits, handle the division by zero
        if self.parent is None or self.parent.visits == 0:
            return float('inf')

        exploitation = self.value / max(self.visits, 1)
        exploration = exploration_weight * (
                (2 * math.log(self.parent.visits) / max(self.visits, 1)) ** 0.5
        )
        return exploitation + exploration


class MCTSWorker:
    """Worker that manages a single Factorio instance for simulations"""

    def __init__(self, worker_id: int, db_client: PostgresDBClient, config: MCTSConfig,
                 instance_address: str, instance_tcp_port: int):
        self.worker_id = worker_id
        self.db_client = db_client
        self.config = config
        self.instance_address = instance_address
        self.instance_tcp_port = instance_tcp_port
        self.instance = self._create_factorio_instance()
        self.evaluator = SimpleFactorioEvaluator(
            db_client=db_client,
            instance=self.instance,
            value_accrual_time=1,
            error_penalty=0
        )

    def _create_factorio_instance(self) -> FactorioInstance:
        """Create a Factorio instance for this worker"""
        instance = FactorioInstance(
            address=self.instance_address,
            tcp_port=self.instance_tcp_port,
            bounding_box=200,
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=True
        )
        instance.speed(10)
        return instance

    async def simulate(self, node: MCTSNode) -> Tuple[float, Program]:
        """Run a simulation from the given node"""
        try:
            # Reset instance to the starting state from the program
            state = None
            if node.program and node.program.state:
                self.instance.reset(node.program.state)
                state = node.program.state
            else:
                # If no state, use task's starting state
                self.instance.reset(self.config.agent.task.starting_game_state)
                state = self.config.agent.task.starting_game_state

            # Get conversation context from node or create a new one
            if node.program and node.program.conversation:
                conversation = copy.deepcopy(node.program.conversation)
            else:
                # Initialize with system prompt and initial observation
                current_state = self.config.agent.task.starting_game_state
                self.instance.reset(current_state)
                self.instance.set_inventory(**self.config.agent.task.starting_inventory)
                inventory = self.instance.namespace.inspect_inventory()
                entities = self.instance.namespace.get_entities()
                conversation = Conversation(messages=[
                    Message(role="system", content=self.config.agent.system_prompt),
                    Message(role="assistant", content="print(f'Inventory: {inspect_inventory()}')\n"
                                                      "print(f'Entities: {get_entities()}')\n"),
                    Message(role="user", content=f"1: ('Inventory: {inventory}')\n"
                                                 f"2: ('Entities: {entities}')"),
                ])
                state = GameState.from_instance(self.instance)

            # Create response object from previous iteration
            last_response = None
            if node.program:
                last_response = Response(
                    code=node.program.code,
                    created_at=node.program.created_at,
                    score=node.program.value,
                    achievements=node.program.achievements,
                    step=node.program.depth // 2,  # Convert depth to step count
                    ticks=node.program.ticks,
                    flows=node.program.flows if node.program.flows else ProductionFlows.from_dict({}),
                    response=node.program.response,
                    task=node.program.meta.get('task_response', {})
                )

            # Generate next program using agent
            generated_program = await self._generate_program(conversation, last_response, self.instance.namespace)

            # If program generation failed, return failure
            if not generated_program:
                return 0.0, None

            # Set parent ID if we have a parent program
            if node.program:
                generated_program.parent_id = node.program.id

            # Evaluate the program
            evaluated_program, task_response = await self.evaluator.evaluate(
                generated_program,
                state,
                self.config.agent.task
            )

            # Check if the task was successfully completed
            if task_response and task_response.success:
                # Task was completed - great success!
                completion_result = CompletionResult(
                    step=node.program.depth // 2 if node.program else 0,
                    reason=CompletionReason.SUCCESS
                )
                await self.config.agent.end(evaluated_program.conversation, completion_result)

            # Return the results
            return evaluated_program.value, evaluated_program

        except Exception as e:
            print(f"Worker {self.worker_id} simulation error: {e}")
            return 0.0, None

    async def _generate_program(self, conversation: Conversation, response: Response,
                                namespace: FactorioNamespace) -> Program:
        """Generate a program using the agent"""
        conversation = copy.deepcopy(conversation)
        try:
            policy = await self.config.agent.step(conversation, response, namespace)

            if not policy:
                raise Exception("Policy not valid Python. Skipping.")

            try:
                messages = conversation.model_dump()['messages']
            except Exception:
                messages = conversation.dict()['messages']

            program = Program(
                code=policy.code,
                conversation=conversation,
                response=response.response if response else None,
                token_usage=policy.meta.total_tokens,
                completion_token_usage=policy.meta.output_tokens,
                prompt_token_usage=policy.meta.input_tokens,
                version=self.config.version,
                model=self.config.agent.model,
                version_description=self.config.version_description,
                meta={"model": self.config.agent.model, "worker_id": self.worker_id},
                depth=len(messages) - 2
            )

            return program

        except Exception as e:
            print(f"Program generation failed: {str(e)}")
            return None