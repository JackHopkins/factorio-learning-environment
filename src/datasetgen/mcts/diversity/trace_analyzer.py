import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import networkx as nx
import numpy as np

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.diversity.extractor.trace_extractor import TraceExtractor
from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.encoder.trace_encoder import TraceEncoder
from sklearn.preprocessing import normalize
import hdbscan
from datasetgen.mcts.diversity.trace_visualiser import TraceVisualizer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TraceAnalyzer:
    def __init__(self,
                 encoder: TraceEncoder,
                 discount_factor: float = 0.95,
                 min_samples: int = 1,  # Added parameter
                 min_cluster_size: int = 2,
                 cluster_selection_epsilon: float = 0.15,  # Reduced from 0.5
                 alpha: float = 0.5,  # Reduced from 1.0
                 cluster_selection_method: str = 'eom'):  # Added parameter
        self.encoder = encoder
        self.discount_factor = discount_factor
        self.min_cluster_size = min_cluster_size
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.alpha = alpha
        self.min_samples = min_samples
        self.cluster_selection_method = cluster_selection_method

    def get_all_traces(self, db_client: DBClient) -> Dict[int, Dict]:
        """Get all programs and build program dictionary"""
        with db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, parent_id, value, response, code
                    FROM programs
                    WHERE value > 0
                """)
                programs = {}
                for row in cur.fetchall():
                    programs[row[0]] = {
                        'id': row[0],
                        'parent_id': row[1],
                        'value': row[2],
                        'response': row[3],
                        'code': row[4],
                        'children': []
                    }

        # Build tree structure
        for prog_id, prog in programs.items():
            if prog['parent_id'] in programs:
                programs[prog['parent_id']]['children'].append(prog_id)

        return programs

    def backpropagate_rewards(self, programs: Dict[int, Dict]) -> None:
        """Update program values with discounted future returns"""
        G = nx.DiGraph()

        # Build graph
        for prog_id, prog in programs.items():
            G.add_node(prog_id)
            if prog['parent_id'] in programs:
                G.add_edge(prog['parent_id'], prog_id)

        # Process nodes in reverse topological order
        for node in reversed(list(nx.topological_sort(G))):
            prog = programs[node]
            children_values = [programs[child_id]['value'] for child_id in prog['children']]
            if children_values:
                # Update value to include discounted future returns
                prog['discounted_value'] = prog['value'] + self.discount_factor * max(children_values)
            else:
                prog['discounted_value'] = prog['value']

    def extract_traces(self, programs: Dict[int, Dict], extractor: TraceExtractor) -> List[Trace]:
        """Extract all complete traces from root to leaf"""
        traces = []
        roots = [pid for pid, prog in programs.items() if prog['parent_id'] is None]

        def build_trace(current_id: int, current_trace: List[int]) -> None:
            prog = programs[current_id]
            current_trace.append(current_id)

            if not prog['children']:  # Leaf node
                text = extractor.extract_from_trace(current_trace)
                traces.append(Trace(
                    programs=current_trace.copy(),
                    value=prog['discounted_value'],
                    text=text
                ))
            else:
                for child_id in prog['children']:
                    build_trace(child_id, current_trace)
            current_trace.pop()

        for root in roots:
            build_trace(root, [])

        return traces

    def cluster_traces(self, X, traces: List[Trace]) -> List[List[Trace]]:
        """Cluster traces using density-based clustering with modifications for more fragmentation"""
        # Normalize the feature vectors
        if isinstance(X, np.ndarray):
            X_normalized = normalize(X)
        else:
            X_normalized = normalize(X.toarray())

        # Configure HDBSCAN with parameters that encourage fragmentation
        logger.debug("Creating HDBScan")
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            alpha=self.alpha,
            metric='euclidean',
            cluster_selection_method=self.cluster_selection_method,
            prediction_data=True
        )

        # Perform clustering
        logger.debug("Clustering...")
        labels = clusterer.fit_predict(X_normalized)

        # Get probabilities for cluster membership
        strengths = clusterer.probabilities_

        # Group traces by cluster with strength threshold
        clusters = defaultdict(list)
        strength_threshold = 0.05

        for trace, label, strength in zip(traces, labels, strengths):
            if label == -1 and strength >= strength_threshold:
                # Create new singleton cluster for strong noise points
                new_label = max(clusters.keys()) + 1 if clusters else 0
                clusters[new_label].append(trace)
            else:
                clusters[label].append(trace)

        # Remove noise cluster if it exists
        if -1 in clusters:
            noise_points = clusters.pop(-1)
            # For each noise point, try to assign to the nearest cluster
            for trace in noise_points:
                trace_idx = traces.index(trace)
                # Find nearest cluster using distances
                if hasattr(clusterer, 'probabilities_'):
                    cluster_probs = clusterer.probabilities_[trace_idx]
                    if cluster_probs.max() > strength_threshold:
                        nearest_cluster = cluster_probs.argmax()
                        clusters[nearest_cluster].append(trace)
                    else:
                        # Create new singleton cluster
                        new_label = max(clusters.keys()) + 1
                        clusters[new_label] = [trace]

        # Split large clusters based on internal distance
        max_cluster_size = 10
        new_clusters = {}
        next_label = max(clusters.keys()) + 1

        for label, cluster in clusters.items():
            if len(cluster) > max_cluster_size:
                # Calculate pairwise distances within cluster
                cluster_indices = [traces.index(t) for t in cluster]
                cluster_vectors = X_normalized[cluster_indices]

                # Use hierarchical clustering to split large clusters
                sub_clusterer = hdbscan.HDBSCAN(
                    min_cluster_size=2,
                    min_samples=1,
                    metric='euclidean',
                    cluster_selection_method='eom'
                )
                sub_labels = sub_clusterer.fit_predict(cluster_vectors)

                # Distribute to new clusters
                for sub_label_idx, sub_label in enumerate(sub_labels):
                    if sub_label == -1:
                        new_clusters[next_label] = [cluster[sub_label_idx]]
                        next_label += 1
                    else:
                        sub_cluster_label = f"{label}_{sub_label}"
                        if sub_cluster_label not in new_clusters:
                            new_clusters[sub_cluster_label] = []
                        new_clusters[sub_cluster_label].append(cluster[sub_label_idx])
            else:
                new_clusters[label] = cluster

        return list(new_clusters.values())

    def sample_traces(self, clustered_traces: List[List[Trace]], samples_per_cluster: int = 1) -> List[Trace]:
        """Sample high-value traces from each cluster"""
        selected_traces = []
        logger.debug("Sampling traces")
        for cluster in clustered_traces:
            # Sort traces by value
            sorted_traces = sorted(cluster, key=lambda t: t.value, reverse=True)
            # Sample from top traces with some randomness
            n_samples = min(samples_per_cluster, len(cluster))
            top_k = min(len(cluster), samples_per_cluster * 2)  # Consider top 2x traces for sampling
            selected_traces.extend(np.random.choice(
                sorted_traces[:top_k],
                size=n_samples,
                replace=False
            ))

        return selected_traces

    def analyze(self, programs: Dict[int, Dict],
                extractor: TraceExtractor,
                samples_per_cluster: int = 1,
                output_dir: Path = None) -> List[Trace]:
        """Main analysis pipeline"""

        # Backpropagate rewards
        logger.debug("Backpropagating rewards")
        self.backpropagate_rewards(programs)

        # Extract all traces
        logger.debug("Extracting traces")
        traces = self.extract_traces(programs, extractor)

        if output_dir:
            visualizer = TraceVisualizer(output_dir)

            # Get embeddings before clustering
            logger.debug("Encoding initial traces")
            X = self.encoder.encode_traces(traces)
            before_viz = visualizer.prepare_visualization_data(
                embeddings=X,
                traces=traces,
                cluster_labels=np.zeros(len(traces)),  # No clusters yet
                selected_indices=[]  # No selections yet
            )
            logger.debug("Plotting initial traces with UMAP")
            visualizer.plot_clusters(before_viz, "Before Clustering")

        # Cluster traces
        logger.debug("Clustering traces")
        clustered_traces = self.cluster_traces(X, traces)

        # Sample diverse, high-value traces
        logger.debug("Sampling traces")
        selected_traces = self.sample_traces(clustered_traces, samples_per_cluster)

        if output_dir:
            # Get embeddings after selection
            selected_indices = [traces.index(trace) for trace in selected_traces]
            after_viz = visualizer.prepare_visualization_data(
                embeddings=X,
                traces=traces,
                cluster_labels=np.array([next((i for i, cluster in enumerate(clustered_traces)
                                               if trace in cluster), -1) for trace in traces]),
                selected_indices=selected_indices
            )
            visualizer.plot_clusters(after_viz, "After Selection")

            # Create summary
            visualizer.create_visualization_summary(before_viz, after_viz)

        return selected_traces