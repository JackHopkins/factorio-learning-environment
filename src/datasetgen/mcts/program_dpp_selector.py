import asyncio
import os
from typing import List, Tuple
import numpy as np
from dotenv import load_dotenv
from dppy.finite_dpps import FiniteDPP
import torch
from transformers import AutoTokenizer, AutoModel
import json
from tqdm import tqdm

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.program import Program
import logging
load_dotenv()

logger = logging.getLogger(__name__)

class ProgramDPPSelector:
    def __init__(self, db_client: 'DBClient', model_name="microsoft/codebert-base"):
        self.db_client = db_client
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings to unit length."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / (norms + 1e-8)

    def compute_similarity_matrix(self, embeddings: np.ndarray, eps: float = 1e-8) -> np.ndarray:
        """Compute similarity matrix using cosine similarity."""
        # Normalize embeddings first
        embeddings = self.normalize_embeddings(embeddings)

        # Compute pairwise similarities directly
        similarity = embeddings @ embeddings.T

        # Ensure numerical stability
        similarity = np.clip(similarity, -1 + eps, 1 - eps)

        return similarity

    def create_quality_diversity_kernel(self,
                                        embeddings: np.ndarray,
                                        scores: np.ndarray,
                                        alpha: float = 0.5,
                                        eps: float = 1e-10) -> np.ndarray:
        """Create numerically stable L-ensemble kernel matrix with proper normalization."""
        # Normalize embeddings
        embeddings = self.normalize_embeddings(embeddings)

        # Normalize scores using softmax to ensure proper scaling
        scores = np.array(scores, dtype=np.float64)
        scores = scores - np.mean(scores)  # Center scores
        scores = scores / (np.std(scores) + eps)  # Scale scores
        scores = np.exp(scores) / (np.sum(np.exp(scores)) + eps)  # Softmax normalization

        # Create quality matrix with stable exponential scaling
        quality_scores = np.exp(alpha * scores)
        quality_scores = quality_scores / (np.max(quality_scores) + eps)
        quality_matrix = np.diag(quality_scores)

        # Compute similarity matrix using normalized dot product
        similarity = embeddings @ embeddings.T

        # Ensure similarity matrix is properly bounded
        similarity = (similarity + 1) / 2  # Scale to [0, 1]
        similarity = np.clip(similarity, eps, 1 - eps)

        # Combine quality and diversity with proper scaling
        kernel_matrix = quality_matrix @ similarity @ quality_matrix

        # Ensure symmetry
        kernel_matrix = (kernel_matrix + kernel_matrix.T) / 2

        # Add small diagonal term for stability
        kernel_matrix += eps * np.eye(len(kernel_matrix))

        # Ensure PSD and proper scaling
        eigenvals, eigenvecs = np.linalg.eigh(kernel_matrix)
        eigenvals = np.maximum(eigenvals, 0)  # Ensure positive eigenvalues

        # Normalize eigenvalues to sum to k (the desired sample size)
        eigenvals = eigenvals / (np.sum(eigenvals) + eps)

        # Reconstruct kernel matrix
        kernel_matrix = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T

        # Final scaling to ensure proper normalization
        kernel_matrix = kernel_matrix / (np.trace(kernel_matrix) + eps)

        return kernel_matrix

    def get_embedding(self, code: str, max_length: int = 512) -> np.ndarray:
        """Get embeddings for a single code snippet."""
        with torch.no_grad():
            inputs = self.tokenizer(code,
                                    truncation=True,
                                    max_length=max_length,
                                    return_tensors="pt").to(self.device)
            outputs = self.model(**inputs)
            return outputs.last_hidden_state[:, 0, :].cpu().numpy()

    async def select_diverse_programs(self,
                                      version: int = None,
                                      k: int = 1000,
                                      alpha: float = 0.5,
                                      combine_code_conv: bool = True,
                                      max_attempts: int = 3) -> List[Program]:
        """Select diverse programs with improved stability."""
        programs = await self.fetch_programs(version)
        if not programs:
            logger.warning("No programs found")
            return []

        if len(programs) < k:
            logger.warning(f"Requested {k} programs but only {len(programs)} available")
            k = len(programs)

        # Prepare embeddings
        texts = []
        for program in programs:
            text = program.code
            if combine_code_conv and program.conversation:
                conv_text = " ".join(
                    f"{msg.get('content', '')}"
                    for msg in program.conversation.messages
                )
                text = f"{text} {conv_text}"
            texts.append(text)

        logger.info("Generating embeddings...")
        embeddings = np.vstack([
            self.get_embedding(text)
            for text in tqdm(texts)
        ])

        scores = np.array([program.value for program in programs])

        # Try sampling with different stability parameters
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to sample DPP")
                eps = 1e-10 * (10 ** attempt)

                kernel_matrix = self.create_quality_diversity_kernel(
                    embeddings,
                    scores,
                    alpha=alpha,
                    eps=eps
                )

                # Verify kernel properties
                if not np.all(np.isfinite(kernel_matrix)):
                    raise ValueError("Kernel matrix contains invalid values")

                if not np.allclose(kernel_matrix, kernel_matrix.T):
                    raise ValueError("Kernel matrix is not symmetric")

                # Additional verification of eigenvalues
                eigenvals = np.linalg.eigvalsh(kernel_matrix)
                if not np.all(eigenvals >= -1e-10):  # Allow for small numerical errors
                    raise ValueError("Kernel matrix is not PSD")

                # Verify normalization
                if not np.allclose(np.trace(kernel_matrix), 1.0, rtol=1e-5):
                    raise ValueError("Kernel matrix trace is not normalized")

                # Initialize and sample DPP with extra verification
                dpp = FiniteDPP('likelihood', **{'L': kernel_matrix})

                # Verify DPP internals before sampling
                if not dpp.check_random_state():  # This is a custom method we need to add
                    dpp.random_state = np.random.RandomState()

                # Try sampling
                dpp.sample_exact_k_dpp(size=k)

                if not dpp.list_of_samples:
                    raise ValueError("DPP sampling produced no samples")

                selected_indices = dpp.list_of_samples[-1]

                if len(selected_indices) != k:
                    raise ValueError(f"DPP sampling returned {len(selected_indices)} samples instead of {k}")

                logger.info(f"Successfully sampled {len(selected_indices)} items")
                return [programs[i] for i in selected_indices]

            except Exception as e:
                logger.warning(f"DPP sampling attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_attempts - 1:
                    logger.error("All DPP sampling attempts failed. Falling back to score-based selection")
                    return self.fallback_selection(programs, embeddings, k)

    def check_random_state(self):
        """Helper method to verify DPP random state."""
        return hasattr(self, 'random_state') and self.random_state is not None

    def fallback_selection(self, programs: List[Program], embeddings: np.ndarray, k: int) -> List[Program]:
        """Fallback selection method when DPP fails."""
        logger.info("Using fallback selection method")

        selected_indices = []
        remaining_indices = set(range(len(programs)))

        # Always include the best program
        best_idx = max(remaining_indices, key=lambda i: programs[i].value)
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

        # Select rest using a mix of score and diversity
        while len(selected_indices) < k and remaining_indices:
            # Compute diversity scores using normalized embeddings
            embeddings_norm = self.normalize_embeddings(embeddings)
            diversity_scores = np.zeros(len(programs))
            for idx in remaining_indices:
                similarities = [
                    np.dot(embeddings_norm[idx], embeddings_norm[j])
                    for j in selected_indices
                ]
                diversity_scores[idx] = -np.mean(similarities)  # Negative because we want diversity

            # Normalize diversity scores
            diversity_scores = (diversity_scores - diversity_scores.min()) / (
                        diversity_scores.max() - diversity_scores.min() + 1e-8)

            # Combine with program values
            values = np.array([programs[i].value for i in range(len(programs))])
            values = (values - values.min()) / (values.max() - values.min() + 1e-8)

            # Combined score
            scores = 0.5 * values + 0.5 * diversity_scores

            # Select best remaining program
            best_idx = max(remaining_indices, key=lambda i: scores[i])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        return [programs[i] for i in selected_indices]

    async def fetch_programs(self, version: int = None) -> List[Program]:
        """Fetch programs using existing DBClient connection."""
        query = """
            SELECT *
            FROM programs
            WHERE value > 0
            LIMIT 1000
        """
        if version is not None:
            query += " AND version = %s"

        params = (version,) if version is not None else ()

        programs = []
        with self.db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    row_dict = {desc[0]: value for desc, value in zip(cur.description, row)}
                    programs.append(Program.from_row(row_dict))

        return programs


async def create_debiased_dataset(db_client: 'DBClient',
                                  output_file: str,
                                  version: int = None,
                                  k: int = 1000,
                                  alpha: float = 0.5):
    """Create debiased dataset using DPP selection."""
    selector = ProgramDPPSelector(db_client)
    diverse_programs = await selector.select_diverse_programs(
        version=version,
        k=k,
        alpha=alpha
    )

    # Prepare output
    training_examples = []
    for program in diverse_programs:
        training_examples.append({
            'program_id': program.id,
            'code': program.code,
            'value': program.value,
            'conversation': program.conversation.dict() if program.conversation else [],
            'state': program.state.to_raw() if program.state else {},
            'response': program.response
        })

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(training_examples, f, indent=2)

    return len(training_examples)


async def main():
    # Initialize DB client
    db_client = DBClient(**{
        'host': os.getenv("SKILLS_DB_HOST"),
        'port': os.getenv("SKILLS_DB_PORT"),
        'dbname': os.getenv("SKILLS_DB_NAME"),
        'user': os.getenv("SKILLS_DB_USER"),
        'password': os.getenv("SKILLS_DB_PASSWORD")
    })

    # Create debiased dataset
    output_file = "diverse_programs.json"
    num_selected = await create_debiased_dataset(
        db_client,
        output_file,
        k=100,  # Number of programs to select
        alpha=0.5  # Quality-diversity tradeoff - higher means more quality
    )
    print(f"Selected {num_selected} diverse programs")


if __name__ == '__main__':
    asyncio.run(main())