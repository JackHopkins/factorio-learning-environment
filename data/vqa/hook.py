# qa_hook.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from inspect_ai.hooks import Hooks, SampleEnd, TaskStart, hooks, TaskEnd

from inspect_ai.log import EvalConfig, EvalLog, EvalSample

class VQAPairsSerializer:
    """Serializer for VQA pairs that collects and saves QA data to JSONL files."""

    def __init__(self, output_dir: str = "./dataset"):
        """
        Initialize the serializer.

        Args:
            output_dir: Directory where JSONL files will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_qa_pairs(self, sample: EvalSample) -> List[Dict[str, Any]]:
        """
        Collect all QA pairs from a sample's metadata.

        Args:
            sample: The evaluation sample containing QA pairs in metadata

        Returns:
            List of QA pair dictionaries with normalized structure
        """
        qa_pairs = []
        metadata = sample.metadata

        # Collect from different task types
        task_qa_fields = [
            # Basic tasks
            ("basic_questions", self._normalize_basic_qa),
            ("position_questions", self._normalize_position_qa),
            ("counting_questions", self._normalize_counting_qa),

            # Spatial reasoning tasks
            ("spatial_questions", self._normalize_spatial_qa),

            # State prediction tasks
            ("state_questions", self._normalize_state_qa),
            ("inventory_questions", self._normalize_inventory_qa),

            # Denoising tasks
            ("qa_pairs", self._normalize_denoising_qa),

            # Action prediction tasks
            ("next_action_questions", self._normalize_action_qa),
            ("construction_order_questions", self._normalize_construction_qa),

            # Productivity planning tasks
            ("throughput_questions", self._normalize_throughput_qa),
            ("bottleneck_questions", self._normalize_bottleneck_qa),
            ("optimization_questions", self._normalize_optimization_qa),
        ]

        for field_name, normalizer in task_qa_fields:
            if field_name in metadata:
                field_data = metadata[field_name]
                if isinstance(field_data, list):
                    for qa in field_data:
                        normalized = normalizer(qa, metadata)
                        if 'image_id' not in normalized.keys():
                            normalized['image_id'] = metadata['image']
                        if normalized:
                            qa_pairs.append(normalized)

        return qa_pairs

    def _normalize_basic_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize basic QA pairs (entity name/position questions)."""
        return {
            "task_type": "basic",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "entity_properties": qa.get("entity_properties", {}),
            "position": qa.get("position", {}),
        }

    def _normalize_position_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize position QA pairs."""
        return {
            "task_type": "position",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "entity": qa.get("entity", {}),
            "context": qa.get("context", {}),
        }

    def _normalize_counting_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize counting QA pairs."""
        return {
            "task_type": "counting",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "explanation": qa.get("explanation", ""),
            "context": qa.get("context", {}),
        }

    def _normalize_spatial_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize spatial reasoning QA pairs."""
        return {
            "task_type": "spatial_reasoning",
            "question": qa.get("question", "") or qa.get("spatial_question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "metadata": qa.get("metadata", {}),
            "nearby_entities": qa.get("nearby_entities", []),
        }

    def _normalize_state_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize state prediction QA pairs."""
        return {
            "task_type": "state_prediction",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "entity_type": qa.get("entity_type", ""),
        }

    def _normalize_inventory_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize inventory QA pairs."""
        return {
            "task_type": "inventory",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "item": qa.get("item", ""),
            "quantity": qa.get("quantity", 0),
        }

    def _normalize_denoising_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize denoising QA pairs."""
        base = {
            "task_type": "denoising",
            "question": qa.get("question", "") or qa.get("spatial_question", ""),
            "answer": qa.get("answer", ""),
            "image_id": qa.get("image", "") or metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "removed_entity": qa.get("removed_entity", {}),
            "position": qa.get("position", {}),
        }

        # Include validation results if present
        if "validation_result" in qa:
            base["validation_result"] = qa["validation_result"]

        # Include spatial context if present
        if "nearby_entities" in qa:
            base["nearby_entities"] = qa["nearby_entities"]

        return base

    def _normalize_action_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize action prediction QA pairs."""
        return {
            "task_type": "action_prediction",
            "question": qa.get("question_prompt", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "previous_actions": [a.get("action", "") for a in qa.get("previous_actions", [])],
            "split_point": qa.get("split_point", 0),
        }

    def _normalize_construction_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize construction order QA pairs."""
        return {
            "task_type": "construction_order",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "entity_names": qa.get("entity_names", []),
        }

    def _normalize_throughput_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize throughput QA pairs."""
        return {
            "task_type": "throughput",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "calculated_throughput": qa.get("calculated_throughput", 0),
        }

    def _normalize_bottleneck_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize bottleneck QA pairs."""
        return {
            "task_type": "bottleneck",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "analysis_type": qa.get("analysis_type", ""),
        }

    def _normalize_optimization_qa(self, qa: Dict, metadata: Dict) -> Dict[str, Any]:
        """Normalize optimization QA pairs."""
        return {
            "task_type": "optimization",
            "question": qa.get("question", ""),
            "answer": qa.get("answer", ""),
            "image_id": metadata.get("image", ""),
            "blueprint_file": metadata.get("filename", ""),
            "entity_counts": qa.get("entity_counts", {}),
            "total_entities": qa.get("total_entities", 0),
        }

    def save_qa_pairs(self, qa_pairs: List[Dict[str, Any]], task_name: str,
                      timestamp: Optional[str] = None) -> Path:
        """
        Save QA pairs to a JSONL file.

        Args:
            qa_pairs: List of normalized QA pair dictionaries
            task_name: Name of the task (used in filename)
            timestamp: Optional timestamp string (defaults to current time)

        Returns:
            Path to the saved JSONL file
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{task_name}_{timestamp}.jsonl"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            for qa_pair in qa_pairs:
                # Add metadata
                qa_pair["timestamp"] = timestamp
                qa_pair["task_name"] = task_name

                # Write as JSONL
                f.write(json.dumps(qa_pair) + '\n')

        return filepath

    def save_from_eval_log(self, eval_log: EvalLog) -> Path:
        """
        Extract and save all QA pairs from an evaluation log.

        Args:
            eval_log: The evaluation log containing samples with QA pairs

        Returns:
            Path to the saved JSONL file
        """
        all_qa_pairs = []

        for sample in eval_log.samples:
            qa_pairs = self.collect_qa_pairs(sample)
            all_qa_pairs.extend(qa_pairs)

        # Extract task name from eval metadata
        task_name = eval_log.eval.task or "unknown_task"
        timestamp = eval_log.eval.created or datetime.now().strftime("%Y%m%d_%H%M%S")

        return self.save_qa_pairs(all_qa_pairs, task_name, timestamp)

    def merge_jsonl_files(self, pattern: str = "*.jsonl", output_file: str = "merged_qa_pairs.jsonl") -> Path:
        """
        Merge multiple JSONL files into a single file.

        Args:
            pattern: Glob pattern to match JSONL files
            output_file: Name of the merged output file

        Returns:
            Path to the merged file
        """
        merged_path = self.output_dir / output_file

        with open(merged_path, 'w') as outfile:
            for jsonl_file in self.output_dir.glob(pattern):
                if jsonl_file.name != output_file:  # Don't read the output file
                    with open(jsonl_file, 'r') as infile:
                        for line in infile:
                            outfile.write(line)

        return merged_path

    def load_qa_pairs(self, filepath: Path) -> List[Dict[str, Any]]:
        """
        Load QA pairs from a JSONL file.

        Args:
            filepath: Path to the JSONL file

        Returns:
            List of QA pair dictionaries
        """
        qa_pairs = []
        with open(filepath, 'r') as f:
            for line in f:
                qa_pairs.append(json.loads(line))
        return qa_pairs

    def get_statistics(self, filepath: Path) -> Dict[str, Any]:
        """
        Get statistics about QA pairs in a JSONL file.

        Args:
            filepath: Path to the JSONL file

        Returns:
            Dictionary with statistics
        """
        qa_pairs = self.load_qa_pairs(filepath)

        task_types = {}
        for qa in qa_pairs:
            task_type = qa.get("task_type", "unknown")
            task_types[task_type] = task_types.get(task_type, 0) + 1

        return {
            "total_qa_pairs": len(qa_pairs),
            "task_types": task_types,
            "unique_images": len(set(qa.get("image_id", "") for qa in qa_pairs)),
            "unique_blueprints": len(set(qa.get("blueprint_file", "") for qa in qa_pairs)),
        }

@hooks(
    name="vqa_pairs_hook",
    description="Parses logs and outputs JSONL format."
)
class VQAPairsHook(Hooks):
    """Hook that automatically serializes QA pairs after evaluation."""

    def __init__(self, output_dir: str = "./../../dataset"):
        self.serializer = VQAPairsSerializer(output_dir)

    async def on_task_end(self, task: TaskEnd):
        """Called after evaluation completes."""
        log = task.log
        filepath = self.serializer.save_from_eval_log(log)
        stats = self.serializer.get_statistics(filepath)

        print(f"\nVQA Pairs saved to: {filepath}")
        print(f"Statistics: {json.dumps(stats, indent=2)}")

        return log

    # def __call__(self, log: EvalLog):
    #     """Called after evaluation completes."""
    #     filepath = self.serializer.save_from_eval_log(log)
    #     stats = self.serializer.get_statistics(filepath)
    #
    #     print(f"\nVQA Pairs saved to: {filepath}")
    #     print(f"Statistics: {json.dumps(stats, indent=2)}")
    #
    #     return log