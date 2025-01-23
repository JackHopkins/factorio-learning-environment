# Initialize components
from factorio_instance import FactorioInstance
from skills.composition.factorio_complexity_calculator import FactorioComplexityCalculator
from skills.composition.factorio_graph_executor import FactorioGraphExecutor
from skills.composition.factorio_graph_generator import FactorioGraphGenerator
from skills.composition.factorio_implementation_dao import FactorioImplementationDAO

generator = FactorioGraphGenerator()
factorio_instance = FactorioInstance(address='localhost', bounding_box=200, tcp_port=27000, fast=True)
factorio_instance.speed(10)

# Load and process objective
objectives = generator.load_objectives("../objectives.yaml")
dao = FactorioImplementationDAO(generator.llm_factory)

# Execute graph
executor = FactorioGraphExecutor(factorio_instance, generator.llm_factory, dao)

for objective in objectives:
    for i in range(10):
        try:
            print(f"Objective: {objective}")
            graph = generator.objective_to_graph(objective)
            print(f"Graph: {graph}")
            implementation, final_inventory, attempts, score = executor.execute_graph(graph, objective, max_repair_attempts=20)
            complexity = FactorioComplexityCalculator.calculate_complexity(implementation)
            dao.save_execution(implementation, graph, objective, final_inventory, complexity, attempts, score)
            break
        except Exception as e:
            print(f"Failed to execute graph: {e}")
            continue