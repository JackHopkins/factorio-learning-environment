import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from umap import UMAP

from datasetgen.mcts.diversity.trace import Trace


@dataclass
class ClusterVisualization:
    """Stores visualization data for clusters"""
    embeddings_2d: np.ndarray
    traces: List[Trace]
    cluster_labels: np.ndarray
    values: np.ndarray
    selected_indices: List[int]


class TraceVisualizer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.umap = UMAP(
            n_components=2,
            metric='cosine',
            n_neighbors=15,
            min_dist=0.1,
            random_state=42
        )

    def prepare_visualization_data(
            self,
            embeddings: np.ndarray,
            traces: List[Trace],
            cluster_labels: np.ndarray,
            selected_indices: List[int]
    ) -> ClusterVisualization:
        """Prepare data for visualization using UMAP"""
        # Handle sparse matrices
        if not isinstance(embeddings, np.ndarray):
            embeddings = embeddings.toarray()

        # Safe normalization - handle zero vectors
        norms = np.linalg.norm(embeddings, axis=1)
        # Replace zero norms with 1 to avoid division by zero
        norms[norms == 0] = 1
        embeddings_norm = embeddings / norms[:, np.newaxis]

        # Handle cases where we have very few samples
        n_neighbors = min(15, len(traces) - 1)  # Ensure n_neighbors is less than sample size
        if n_neighbors < 2:
            # If we have too few samples, just return simple 2D coordinates
            embeddings_2d = np.zeros((len(traces), 2))
            return ClusterVisualization(
                embeddings_2d=embeddings_2d,
                traces=traces,
                cluster_labels=cluster_labels,
                values=np.array([trace.value for trace in traces]),
                selected_indices=selected_indices
            )

        # Update UMAP parameters
        self.umap = UMAP(
            n_components=2,
            metric='cosine',
            n_neighbors=n_neighbors,
            min_dist=0.1,
            #random_state=42 # Commented for parallelism
        )

        # Reduce dimensionality
        embeddings_2d = self.umap.fit_transform(embeddings_norm)

        values = np.array([trace.value for trace in traces])

        return ClusterVisualization(
            embeddings_2d=embeddings_2d,
            traces=traces,
            cluster_labels=cluster_labels,
            values=values,
            selected_indices=selected_indices
        )

    def plot_clusters(self, viz_data: ClusterVisualization, title: str) -> None:
        """Create interactive scatter plot of clusters"""
        # Create figure
        fig = go.Figure()

        # Plot all points
        unique_labels = np.unique(viz_data.cluster_labels)
        for label in unique_labels:
            mask = viz_data.cluster_labels == label
            if label == -1:
                name = 'Noise'
                color = 'grey'
            else:
                name = f'Cluster {label}'
                color = None  # Let plotly choose color

            fig.add_trace(go.Scatter(
                x=viz_data.embeddings_2d[mask, 0],
                y=viz_data.embeddings_2d[mask, 1],
                mode='markers',
                name=name,
                marker=dict(
                    size=10,
                    color=viz_data.values[mask] if color is None else color,
                    colorscale='Viridis',
                    showscale=True if color is None else False,
                    colorbar=dict(title='Value') if color is None else None
                ),
                text=[f"Value: {v:.2f}<br>Text: {t.text[:100]}..."
                      for v, t in zip(viz_data.values[mask], np.array(viz_data.traces)[mask])],
                hoverinfo='text'
            ))

        # Highlight selected points
        fig.add_trace(go.Scatter(
            x=viz_data.embeddings_2d[viz_data.selected_indices, 0],
            y=viz_data.embeddings_2d[viz_data.selected_indices, 1],
            mode='markers',
            name='Selected',
            marker=dict(
                size=15,
                color='red',
                symbol='circle-open'
            )
        ))

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="UMAP Dimension 1",
            yaxis_title="UMAP Dimension 2",
            showlegend=True,
            width=1000,
            height=800
        )
        fig.write_image(self.output_dir / f"{title.lower().replace(' ', '_')}.jpeg")
        # Save plot
        #fig.write_html(self.output_dir / f"{title.lower().replace(' ', '_')}.html")

    def create_visualization_summary(self,
                                     before_viz: ClusterVisualization,
                                     after_viz: ClusterVisualization) -> None:
        """Create summary statistics and save as JSON"""
        summary = {
            "before": {
                "num_traces": len(before_viz.traces),
                "num_clusters": len(np.unique(before_viz.cluster_labels[before_viz.cluster_labels != -1])),
                "noise_points": int(np.sum(before_viz.cluster_labels == -1)),
                "value_stats": {
                    "mean": float(np.mean(before_viz.values)),
                    "std": float(np.std(before_viz.values)),
                    "min": float(np.min(before_viz.values)),
                    "max": float(np.max(before_viz.values))
                }
            },
            "after": {
                "num_selected": len(after_viz.selected_indices),
                "value_stats": {
                    "mean": float(np.mean(after_viz.values[after_viz.selected_indices])),
                    "std": float(np.std(after_viz.values[after_viz.selected_indices])),
                    "min": float(np.min(after_viz.values[after_viz.selected_indices])),
                    "max": float(np.max(after_viz.values[after_viz.selected_indices]))
                }
            }
        }

        with open(self.output_dir / "visualization_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)