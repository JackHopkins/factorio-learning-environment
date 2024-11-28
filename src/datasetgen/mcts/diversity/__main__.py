import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from datasetgen.mcts.blueprint_scenario_sampler import BlueprintScenarioSampler
from datasetgen.mcts.conversation_formatter import CodeProcessor
from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.diversity.encoder.embedding_encoder import EmbeddingEncoder
from datasetgen.mcts.diversity.encoder.ngram_encoder import NGramEncoder
from datasetgen.mcts.diversity.extractor.code_extractor import CodeExtractor
from datasetgen.mcts.diversity.trace_analyzer import TraceAnalyzer
from datasetgen.mcts.diversity.trace_formatter import TraceFormatter
from factorio_instance import FactorioInstance

load_dotenv()

async def get_blueprints_as_programs():
    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                cache_scripts=False,
                                inventory={})
    sampler = BlueprintScenarioSampler(
        db_config={
            'host': os.getenv("SKILLS_DB_HOST"),
            'port': os.getenv("SKILLS_DB_PORT"),
            'dbname': os.getenv("SKILLS_DB_NAME"),
            'user': os.getenv("SKILLS_DB_USER"),
            'password': os.getenv("SKILLS_DB_PASSWORD")
        },
        system_prompt=instance.get_system_prompt()
    )
    blueprint_programs = await sampler.sample_scenarios(
        instance=instance,
        n_samples=1000
    )
    pass


def main():
    db_client = DBClient(**{
            'host': os.getenv("SKILLS_DB_HOST"),
            'port': os.getenv("SKILLS_DB_PORT"),
            'dbname': os.getenv("SKILLS_DB_NAME"),
            'user': os.getenv("SKILLS_DB_USER"),
            'password': os.getenv("SKILLS_DB_PASSWORD")
    })

    instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                cache_scripts=False,
                                inventory={})
    system_prompt = instance.get_system_prompt()


    trace_formatter = TraceFormatter(system_prompt, CodeProcessor())

    ngram_encoder = NGramEncoder()
    embedding_encoder = EmbeddingEncoder()
    analyzer = TraceAnalyzer(encoder=embedding_encoder, discount_factor=0.95)
    programs = analyzer.get_all_traces(db_client)

    extractor = CodeExtractor(programs)

    # Or with a hypothetical embedding encoder
    #embedding_encoder = EmbeddingEncoder(some_embedding_model)
    #analyzer = TraceAnalyzer(encoder=embedding_encoder, discount_factor=0.95, n_clusters=10)

    selected_traces = analyzer.analyze(programs,
                                       extractor,
                                       samples_per_cluster=1,
                                       output_dir=Path(__file__).parent / 'output' / 'dense')

    trace_formatter.format_traces(programs, selected_traces, Path(__file__).parent / 'output' / 'dense', "gpt_training_data_masked")

# if __name__ == '__main__':
#     main()

if __name__ == '__main__':
    asyncio.run(get_blueprints_as_programs())