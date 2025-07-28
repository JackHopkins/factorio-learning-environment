import random
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from ...templates import Templates


@solver
def generate_throughput_questions(num_questions: int = 2) -> Solver:
    """
    Generate questions about production throughput when connecting entities.
    
    Args:
        num_questions: Number of throughput questions to generate
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        
        if len(entities) < 2:
            state.metadata["error"] = "Not enough entities for throughput questions"
            state.metadata["throughput_questions"] = []
            return state
        
        throughput_questions = []
        
        # Focus on production-related entities
        production_entities = [
            e for e in entities 
            if e.get("name") in ["assembly-machine-1", "assembly-machine-2", "assembly-machine-3",
                                "electric-furnace", "steel-furnace", "stone-furnace", 
                                "electric-mining-drill", "burner-mining-drill"]
        ]
        
        logistics_entities = [
            e for e in entities
            if e.get("name") in ["transport-belt", "fast-transport-belt", "express-transport-belt",
                                "inserter", "fast-inserter", "stack-inserter"]
        ]
        
        if not production_entities:
            production_entities = entities[:len(entities)//2]
        if not logistics_entities:
            logistics_entities = entities[len(entities)//2:]
        
        for _ in range(min(num_questions, min(len(production_entities), len(logistics_entities)))):
            producer = random.choice(production_entities)
            connector = random.choice(logistics_entities)
            
            producer_name = producer.get("name", "unknown")
            connector_name = connector.get("name", "unknown")
            
            producer_pos = producer.get("position", {})
            connector_pos = connector.get("position", {})
            
            # Generate throughput calculation based on entity types
            if "assembly-machine" in producer_name:
                base_speed = {"assembly-machine-1": 0.5, "assembly-machine-2": 0.75, "assembly-machine-3": 1.25}
                speed = base_speed.get(producer_name, 1.0)
                items_per_minute = speed * 60  # assuming 1 item per craft
            elif "furnace" in producer_name:
                base_speed = {"stone-furnace": 1.0, "steel-furnace": 2.0, "electric-furnace": 2.0}
                speed = base_speed.get(producer_name, 1.0)
                items_per_minute = speed * 60
            else:
                items_per_minute = random.randint(30, 120)
            
            # Belt throughput limits
            belt_throughput = {
                "transport-belt": 15 * 60,  # 15 items/second
                "fast-transport-belt": 30 * 60,
                "express-transport-belt": 45 * 60
            }
            
            max_throughput = belt_throughput.get(connector_name, items_per_minute)
            actual_throughput = min(items_per_minute, max_throughput)
            
            question = Templates.productivity_planning(
                factory_state=blueprint,
                entity1_name=producer_name,
                entity1_pos=producer_pos,
                entity2_name=connector_name,
                entity2_pos=connector_pos
            )
            
            answer = f"{actual_throughput:.0f} items per minute"
            
            throughput_questions.append({
                "question": question,
                "answer": answer,
                "producer": producer,
                "connector": connector,
                "calculated_throughput": actual_throughput
            })
        
        state.metadata["throughput_questions"] = throughput_questions
        return state
    
    return solve


@solver
def generate_bottleneck_questions(num_questions: int = 2) -> Solver:
    """
    Generate questions about production bottlenecks in factory setups.
    
    Args:
        num_questions: Number of bottleneck questions to generate
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        
        if len(entities) < 3:
            state.metadata["error"] = "Not enough entities for bottleneck analysis"
            state.metadata["bottleneck_questions"] = []
            return state
        
        bottleneck_questions = []
        
        # Identify potential bottleneck entities
        producers = [e for e in entities if "assembly-machine" in e.get("name", "") or "furnace" in e.get("name", "")]
        transporters = [e for e in entities if "belt" in e.get("name", "") or "inserter" in e.get("name", "")]
        
        for _ in range(min(num_questions, len(producers) + len(transporters))):
            if random.choice([True, False]) and producers:
                # Focus on production bottlenecks
                entity = random.choice(producers)
                entity_name = entity.get("name", "unknown")
                position = entity.get("position", {})
                
                question_types = [
                    f"What limits the production rate of the {entity_name} at ({position.get('x', 0)}, {position.get('y', 0)})?",
                    f"What is the primary bottleneck for the {entity_name} in this setup?",
                    f"How could you increase the throughput of the {entity_name} at ({position.get('x', 0)}, {position.get('y', 0)})?"
                ]
                
                answers = ["input supply rate", "belt speed", "add more inserters"]
                
            else:
                # Focus on logistics bottlenecks
                entity = random.choice(transporters) if transporters else random.choice(entities)
                entity_name = entity.get("name", "unknown")
                position = entity.get("position", {})
                
                question_types = [
                    f"What is the maximum throughput of the {entity_name} at ({position.get('x', 0)}, {position.get('y', 0)})?",
                    f"What would happen if you upgraded the {entity_name} to the next tier?",
                    f"Is the {entity_name} at ({position.get('x', 0)}, {position.get('y', 0)}) a bottleneck in this setup?"
                ]
                
                answers = ["15 items/second", "doubled throughput", "yes"]
            
            question = random.choice(question_types)
            answer = random.choice(answers)
            
            bottleneck_questions.append({
                "question": question,
                "answer": answer,
                "entity": entity,
                "analysis_type": "production" if "assembly-machine" in entity.get("name", "") else "logistics"
            })
        
        state.metadata["bottleneck_questions"] = bottleneck_questions
        return state
    
    return solve


@solver
def generate_optimization_questions(num_questions: int = 2) -> Solver:
    """
    Generate questions about factory optimization and efficiency improvements.
    
    Args:
        num_questions: Number of optimization questions to generate
    """
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])
        
        if not entities:
            state.metadata["error"] = "No entities found for optimization questions"
            state.metadata["optimization_questions"] = []
            return state
        
        optimization_questions = []
        
        for _ in range(num_questions):
            # Count entity types for analysis
            entity_counts = {}
            for entity in entities:
                entity_name = entity.get("name", "unknown")
                entity_counts[entity_name] = entity_counts.get(entity_name, 0) + 1
            
            # Generate optimization suggestions
            question_types = [
                "What is the most effective way to increase production in this factory?",
                "How could you optimize the layout for better efficiency?", 
                "What upgrade would provide the biggest throughput improvement?",
                "How many additional machines would double the production rate?",
                "What is the recommended ratio of inserters to assembly machines?"
            ]
            
            answers = [
                "Add more assembly machines",
                "Use express belts and faster inserters",
                "Upgrade to assembly machine 3",
                f"{max(1, len([e for e in entities if 'assembly-machine' in e.get('name', '')]))}", 
                "1:1 ratio for most setups"
            ]
            
            question = random.choice(question_types)
            answer = random.choice(answers)
            
            optimization_questions.append({
                "question": question,
                "answer": answer,
                "entity_counts": entity_counts,
                "total_entities": len(entities)
            })
        
        state.metadata["optimization_questions"] = optimization_questions
        return state
    
    return solve