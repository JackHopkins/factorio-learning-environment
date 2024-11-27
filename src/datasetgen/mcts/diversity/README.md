# Diversity

A Python module for analyzing and extracting diverse, high-performing traces from program trees. This module helps reduce redundancy in training data by clustering similar program traces while preserving high-value exemplars.

## Overview

The module implements a pipeline that:
1. Extracts complete program traces from a tree structure
2. Backpropagates rewards through the tree
3. Clusters similar traces using configurable encoding strategies
4. Samples high-value traces from each cluster

## Features

- Flexible trace encoding via dependency injection
- Reward backpropagation with configurable discount factor
- Clustering-based trace diversity
- Value-weighted sampling within clusters
- Async database operations with connection pooling
- Retries for database operations with exponential backoff

## Embedding Features
For diversity sampling, we can encode combinations of:
- Code 
- Objectives (Reasoning)
- Responses
- Game state changes

## Embedding Approaches
The compute vectors for each program in the trace, we can use dense or sparse approaches.

### NGram Encoding
The NGramEncoder class uses the GPT tokenizer to generate n-gram features for each program in the trace. These features are then used to compute similarity between traces.

### Dense Encoding
We can use pre-trained models like BERT or GPT to generate dense embeddings for each program. These embeddings capture semantic similarity and are used to compute trace diversity.

### Cosine / Euclidean Distance
The distance between programs is computed as the 

## Installation

```bash
# Core dependencies
pip install numpy scikit-learn networkx tiktoken psycopg2-binary tenacity

# Optional: for embedding-based encoding
pip install sentence-transformers  # or your preferred embedding library
```

## Usage

### Basic Usage

```python
from trace_analysis import TraceAnalyzer, NGramEncoder

# Initialize encoder and analyzer
encoder = NGramEncoder()  # Uses GPT tokenizer for n-gram features
analyzer = TraceAnalyzer(
    encoder=encoder,
    discount_factor=0.95,
    n_clusters=10
)

# Run analysis
traces = await analyzer.analyze(
    db_client=your_db_client,
    samples_per_cluster=3
)
```

### Custom Encoder

Implement your own encoding strategy by subclassing `TraceEncoder`:

```python
from trace_analysis import TraceEncoder
import numpy as np

class CustomEncoder(TraceEncoder):
    def encode_traces(self, traces: List[Trace]) -> np.ndarray:
        # Your encoding logic here
        pass

# Use with analyzer
analyzer = TraceAnalyzer(encoder=CustomEncoder())
```

## Architecture

### Core Classes

- `TraceAnalyzer`: Main class orchestrating the analysis pipeline
- `TraceEncoder`: Abstract base class for trace encoding strategies
- `NGramEncoder`: Default implementation using n-gram features
- `Trace`: Dataclass representing a complete path through the program tree

### Database Schema

The module expects a PostgreSQL database with the following schema for the `programs` table:

```sql
CREATE TABLE programs (
    id bigint PRIMARY KEY,
    code text NOT NULL,
    value double precision DEFAULT 0.0,
    visits integer DEFAULT 0,
    parent_id bigint REFERENCES programs,
    response text,
    -- Additional fields omitted for brevity
);
```

## Design Decisions

1. **Encoder Abstraction**: Uses dependency injection for encoding strategy, allowing easy experimentation with different approaches (n-grams, embeddings, etc.).

2. **Trace Sampling**: Implements a two-stage sampling process:
   - First clusters traces to ensure diversity
   - Then samples high-value traces within each cluster

3. **Database Handling**:
   - Uses connection pooling for efficient resource use
   - Implements retry logic for resilience
   - Async operations for better performance

4. **Value Backpropagation**: Uses NetworkX for efficient tree traversal and reward propagation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=trace_analysis tests/
```

## License

MIT License - See LICENSE file for details.