from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import networkx as nx
import numpy as np
from sklearn.cluster import KMeans

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.diversity.trace import Trace
from datasetgen.mcts.diversity.trace_encoder import TraceEncoder
from sklearn.preprocessing import normalize
import hdbscan
from datasetgen.mcts.diversity.trace_visualiser import TraceVisualizer


class TraceAnalyzer:
    def __init__(self,
                 encoder: TraceEncoder,
                 discount_factor: float = 0.95,
                 min_cluster_size: int = 5,
                 cluster_selection_epsilon: float = 0.5,
                 alpha: float = 1.0):
        self.encoder = encoder
        self.discount_factor = discount_factor
        self.min_cluster_size = min_cluster_size
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.alpha = alpha

    def get_all_traces(self, db_client: DBClient) -> Dict[int, Dict]:
        """Get all programs and build program dictionary"""
        with db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, parent_id, value, response 
                    FROM programs
                """)
                programs = {}
                for row in cur.fetchall():
                    programs[row[0]] = {
                        'id': row[0],
                        'parent_id': row[1],
                        'value': row[2],
                        'response': row[3],
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

    def extract_traces(self, programs: Dict[int, Dict]) -> List[Trace]:
        """Extract all complete traces from root to leaf"""
        traces = []
        roots = [pid for pid, prog in programs.items() if prog['parent_id'] is None]

        def build_trace(current_id: int, current_trace: List[int]) -> None:
            prog = programs[current_id]
            current_trace.append(current_id)

            if not prog['children']:  # Leaf node
                text = " ".join(programs[pid]['response'] if programs[pid]['response'] else '' for pid in current_trace)
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

    def cluster_traces(self, traces: List[Trace]) -> List[List[Trace]]:
        """Cluster traces using density-based clustering"""
        # Convert traces to feature vectors using the encoder
        X = self.encoder.encode_traces(traces[:500])

        # Normalize the feature vectors
        if isinstance(X, np.ndarray):
            X_normalized = normalize(X)
        else:
            # For sparse matrices
            X_normalized = normalize(X.toarray())

        # Configure HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            alpha=self.alpha,
            # Use euclidean metric since as we normalized the vectors, it is equivalent to cosine.
            metric='euclidean',
            # Configure core distance calculation
            min_samples=None,  # Let HDBSCAN determine this automatically
            cluster_selection_method='eom'  # Excess of Mass - tends to produce more conservative clusters
        )

        # Perform clustering
        labels = clusterer.fit_predict(X_normalized)

        # Group traces by cluster
        clusters = defaultdict(list)
        for trace, label in zip(traces, labels):
            # Note: -1 label indicates noise points in HDBSCAN
            clusters[label].append(trace)

        # Handle noise points (label -1) - could be their own cluster or merged based on nearest neighbors
        if -1 in clusters:
            noise_points = clusters.pop(-1)
            if len(noise_points) >= self.min_cluster_size:
                # If we have enough noise points, make them their own cluster
                clusters[max(clusters.keys()) + 1] = noise_points
            else:
                # Assign each noise point to the nearest cluster
                for trace in noise_points:
                    # Find nearest cluster using probabilities
                    trace_idx = traces.index(trace)
                    if hasattr(clusterer, 'probabilities_'):
                        # Get cluster with highest probability
                        cluster_probs = clusterer.probabilities_[trace_idx]
                        if cluster_probs.max() > 0:
                            nearest_cluster = np.argmax(cluster_probs)
                            clusters[nearest_cluster].append(trace)

        return list(clusters.values())

    def sample_traces(self, clustered_traces: List[List[Trace]], samples_per_cluster: int = 3) -> List[Trace]:
        """Sample high-value traces from each cluster"""
        selected_traces = []

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

    def analyze(self, db_client: DBClient, samples_per_cluster: int = 3, output_dir: Path = None) -> List[Trace]:
        """Main analysis pipeline"""
        # Get all programs and build tree
        programs = self.get_all_traces(db_client)

        # Backpropagate rewards
        self.backpropagate_rewards(programs)

        # Extract all traces
        traces = self.extract_traces(programs)

        if output_dir:
            visualizer = TraceVisualizer(output_dir)

            # Get embeddings before clustering
            X = self.encoder.encode_traces(traces)
            before_viz = visualizer.prepare_visualization_data(
                embeddings=X,
                traces=traces,
                cluster_labels=np.zeros(len(traces)),  # No clusters yet
                selected_indices=[]  # No selections yet
            )
            visualizer.plot_clusters(before_viz, "Before Clustering")

        # Cluster traces
        clustered_traces = self.cluster_traces(traces)

        # Sample diverse, high-value traces
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