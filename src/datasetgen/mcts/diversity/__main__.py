import os
from pathlib import Path

from dotenv import load_dotenv

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.diversity.ngram_encoder import NGramEncoder
from datasetgen.mcts.diversity.trace_analyzer import TraceAnalyzer

load_dotenv()

def main():
    db_client = DBClient(**{
            'host': os.getenv("SKILLS_DB_HOST"),
            'port': os.getenv("SKILLS_DB_PORT"),
            'dbname': os.getenv("SKILLS_DB_NAME"),
            'user': os.getenv("SKILLS_DB_USER"),
            'password': os.getenv("SKILLS_DB_PASSWORD")
    })
    ngram_encoder = NGramEncoder()
    analyzer = TraceAnalyzer(encoder=ngram_encoder, discount_factor=0.95)

    # Or with a hypothetical embedding encoder
    #embedding_encoder = EmbeddingEncoder(some_embedding_model)
    #analyzer = TraceAnalyzer(encoder=embedding_encoder, discount_factor=0.95, n_clusters=10)

    selected_traces = analyzer.analyze(db_client, samples_per_cluster=3, output_dir=Path(__file__).parent())


if __name__ == '__main__':
    main()