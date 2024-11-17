# Factorio Program Synthesis via MCTS

A Monte Carlo Tree Search (MCTS) implementation for discovering optimal Factorio automation programs using large language models. This system uses parallel program evaluation and maintains dialogue context to iteratively improve factory automation strategies.

## Overview

This implementation uses MCTS to explore the space of possible Factorio automation programs. Unlike traditional MCTS which explores discrete action spaces, this version:

1. Uses LLMs to generate complete Python programs
2. Maintains dialogue between the LLM and game environment
3. Evaluates programs in parallel across multiple Factorio instances
4. Computes relative advantages against a holdout instance
5. Tracks successful program trajectories

## Core Components

### GameState
Handles serialization and deserialization of Factorio game state:
```python
@dataclass
class GameState:
    entities: List[Dict[str, Any]]
    inventory: Dict[str, int]
    timestamp: float
```

### Conversation
Manages dialogue context between LLM and environment:
```python
@dataclass
class Conversation:
    messages: List[Dict[str, str]]
```

### Program
Represents a candidate solution with its context:
```python
@dataclass
class Program:
    code: str
    conversation: Conversation
    value: float
    visits: int
    state: Optional[GameState]
```

### FactorioEvaluator
Handles parallel program evaluation:
```python
class FactorioEvaluator:
    def evaluate_programs(self, 
                         programs: List[Program],
                         timeout: int) -> Tuple[List[float], List[GameState], List[str]]
```

## Usage

1. Initialize Factorio instances:
```python
instances = [
    FactorioInstance(
        address=f"server{i}",
        tcp_port=34197,
        bounding_box=200,
        fast=True,
        cache_scripts=False,
        inventory={}
    ) for i in range(4)  # 3 main + 1 holdout
]
```

2. Setup MCTS components:
```python
llm = LLMFactory("anthropic/claude-3-opus-20240229")
evaluator = FactorioEvaluator(instances)
initial_state = GameState.from_instance(instances[0])
mcts = MCTS(llm, evaluator, initial_state)
```

3. Run search:
```python
best_programs = await mcts.search(
    n_iterations=100,
    samples_per_iteration=5,
    timeout=60
)
```

## Key Features

### Parallel Evaluation
- Programs are evaluated across multiple Factorio instances
- One instance is held out for computing relative advantages
- Helps normalize rewards across different game states

### Dialogue Management
- Maintains conversation history between LLM and environment
- Includes game state updates and execution results
- Helps LLM learn from previous attempts

### Program Selection
- Uses softmax over rewards for parent selection
- Balances exploration and exploitation
- Maintains diversity in program population

### State Tracking
- Serializes complete game state after each program
- Tracks entity positions and properties
- Maintains inventory state

## Configuration Options

- `n_iterations`: Number of MCTS search iterations
- `samples_per_iteration`: Programs to generate per iteration
- `timeout`: Maximum program execution time
- `exploration_constant`: UCT exploration parameter (default 1.41)

## Implementation Details

### LLM Integration
- Supports multiple LLM providers (Anthropic, OpenAI, DeepSeek)
- Handles different response formats
- Manages conversation context and message formatting

### Program Execution
```python
reward, result, response = instance.eval(program.code, timeout=timeout)
```
- Returns reward (factory growth metric)
- Captures execution output
- Handles timeouts and errors

### State Management
```python
@classmethod
def from_instance(cls, instance: 'FactorioInstance') -> 'GameState':
    return cls(
        entities=[entity.dict() for entity in instance.get_entities()],
        inventory=instance.inspect_inventory()
    )
```
- Captures complete game state
- Handles serialization for storage/analysis
- Maintains entity and inventory state

## Best Practices

1. **Program Generation**
   - Keep programs focused and atomic
   - Handle errors gracefully
   - Verify resource availability

2. **State Management**
   - Capture complete state after each program
   - Track entity relationships
   - Monitor resource consumption

3. **Evaluation**
   - Use sufficient timeout for complex programs
   - Monitor parallel instance health
   - Handle evaluation failures gracefully

## Future Improvements

1. **Program Analysis**
   - Add program similarity metrics
   - Implement program mutation operators
   - Track resource usage patterns

2. **Performance Optimization**
   - Add caching for similar programs
   - Implement batch LLM requests
   - Optimize state serialization

3. **Learning Enhancement**
   - Add program pattern extraction
   - Implement template learning
   - Track successful strategies
   
## Dependencies

- Python 3.8+
- Factorio server instances
- LLM API access (Anthropic/OpenAI/DeepSeek)
- Asyncio for parallel execution

## License

MIT License