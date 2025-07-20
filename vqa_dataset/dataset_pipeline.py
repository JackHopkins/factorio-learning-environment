"""
Main dataset generation pipeline for Factorio blueprint VQA.
"""

import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict

from vqa_dataset.blueprint_loader import BlueprintLoader
from vqa_dataset.blueprint_renderer import BlueprintRenderer
from vqa_dataset.question_generator import QuestionGenerator, VQAExample
from vqa_dataset.inspect_solver import create_vqa_dataset, FactorioBlueprintAnalyzer


class VQADatasetPipeline:
    """
    Complete pipeline for generating Factorio blueprint VQA datasets.
    """
    
    def __init__(
        self, 
        blueprints_dir: str,
        output_dir: str = "vqa_dataset/output",
        rendered_images_dir: str = "vqa_dataset/rendered_images"
    ):
        self.blueprints_dir = Path(blueprints_dir)
        self.output_dir = Path(output_dir)
        self.rendered_images_dir = Path(rendered_images_dir)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rendered_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.loader = BlueprintLoader(str(self.blueprints_dir))
        self.renderer = BlueprintRenderer(str(self.rendered_images_dir))
        self.generator = QuestionGenerator()
        
    async def run_pipeline(
        self,
        blueprint_subdirs: Optional[List[str]] = None,
        max_blueprints: int = 100,
        min_entities: int = 1,
        max_entities: int = 200,
        questions_per_blueprint: int = 8,
        render_images: bool = True,
        question_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete VQA dataset generation pipeline.
        
        Args:
            blueprint_subdirs: Subdirectories to load blueprints from
            max_blueprints: Maximum number of blueprints to process
            min_entities: Minimum entities per blueprint
            max_entities: Maximum entities per blueprint
            questions_per_blueprint: Number of questions per blueprint
            render_images: Whether to render blueprint images
            question_types: Types of questions to generate
        
        Returns:
            Dictionary containing pipeline results and statistics
        """
        print("Starting VQA dataset generation pipeline...")
        
        # Step 1: Load blueprints
        print("Step 1: Loading blueprints...")
        blueprints = await self._load_blueprints(
            blueprint_subdirs, max_blueprints, min_entities, max_entities
        )
        print(f"Loaded {len(blueprints)} blueprints")
        
        # Step 2: Render images (optional)
        rendered_images = {}
        if render_images:
            print("Step 2: Rendering blueprint images...")
            rendered_images = await self._render_blueprints(blueprints)
            print(f"Rendered {len(rendered_images)} images")
        else:
            print("Step 2: Skipping image rendering")
        
        # Step 3: Generate questions
        print("Step 3: Generating VQA questions...")
        questions = await self._generate_questions(
            blueprints, questions_per_blueprint, question_types
        )
        print(f"Generated {len(questions)} questions")
        
        # Step 4: Create dataset files
        print("Step 4: Creating dataset files...")
        dataset_info = await self._create_dataset_files(
            blueprints, questions, rendered_images
        )
        
        # Step 5: Generate statistics
        print("Step 5: Generating statistics...")
        statistics = self._generate_statistics(blueprints, questions, rendered_images)
        
        pipeline_results = {
            "blueprints_count": len(blueprints),
            "questions_count": len(questions),
            "rendered_images_count": len(rendered_images),
            "dataset_info": dataset_info,
            "statistics": statistics,
            "output_directory": str(self.output_dir),
            "rendered_images_directory": str(self.rendered_images_dir)
        }
        
        # Save pipeline results
        results_file = self.output_dir / "pipeline_results.json"
        with open(results_file, 'w') as f:
            json.dump(pipeline_results, f, indent=2)
        
        print(f"Pipeline completed successfully!")
        print(f"Results saved to: {results_file}")
        
        return pipeline_results
    
    async def _load_blueprints(
        self, 
        blueprint_subdirs: Optional[List[str]], 
        max_blueprints: int,
        min_entities: int, 
        max_entities: int
    ) -> Dict[str, Any]:
        """Load and filter blueprints."""
        if blueprint_subdirs is None:
            blueprint_subdirs = ['example', 'other', 'balancing']
        
        # Load all blueprints
        blueprints = self.loader.load_all_blueprints(blueprint_subdirs)
        
        # Filter by complexity
        blueprints = self.loader.filter_blueprints_by_complexity(
            blueprints, min_entities, max_entities
        )
        
        # Limit number of blueprints
        if max_blueprints < len(blueprints):
            blueprint_items = list(blueprints.items())[:max_blueprints]
            blueprints = dict(blueprint_items)
        
        return blueprints
    
    async def _render_blueprints(self, blueprints: Dict[str, Any]) -> Dict[str, str]:
        """Render blueprint images."""
        try:
            rendered_images = await self.renderer.render_blueprints_batch(blueprints)
            return rendered_images
        except Exception as e:
            print(f"Error during rendering: {e}")
            return {}
        finally:
            self.renderer.cleanup()
    
    async def _generate_questions(
        self, 
        blueprints: Dict[str, Any], 
        questions_per_blueprint: int,
        question_types: Optional[List[str]]
    ) -> List[VQAExample]:
        """Generate VQA questions for blueprints."""
        questions = self.generator.generate_questions_batch(
            blueprints, 
            num_questions_per_blueprint=questions_per_blueprint,
            question_types=question_types
        )
        return questions
    
    async def _create_dataset_files(
        self, 
        blueprints: Dict[str, Any], 
        questions: List[VQAExample],
        rendered_images: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create various dataset file formats."""
        dataset_info = {}
        
        # 1. Create JSON dataset file
        json_dataset = []
        for question in questions:
            entry = {
                "question": question.question,
                "answer": question.answer,
                "question_type": question.question_type,
                "blueprint_name": question.blueprint_name,
                "image_path": rendered_images.get(question.blueprint_name),
                "metadata": question.metadata
            }
            json_dataset.append(entry)
        
        json_file = self.output_dir / "vqa_dataset.json"
        with open(json_file, 'w') as f:
            json.dump(json_dataset, f, indent=2)
        dataset_info["json_file"] = str(json_file)
        
        # 2. Create CSV dataset file
        import csv
        csv_file = self.output_dir / "vqa_dataset.csv"
        with open(csv_file, 'w', newline='') as f:
            if questions:
                fieldnames = ['question', 'answer', 'question_type', 'blueprint_name', 'image_path']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for question in questions:
                    writer.writerow({
                        'question': question.question,
                        'answer': question.answer,
                        'question_type': question.question_type,
                        'blueprint_name': question.blueprint_name,
                        'image_path': rendered_images.get(question.blueprint_name, "")
                    })
        dataset_info["csv_file"] = str(csv_file)
        
        # 3. Create Inspect AI dataset file
        try:
            inspect_dataset = create_vqa_dataset(blueprints, questions, rendered_images)
            inspect_file = self.output_dir / "inspect_dataset.json"
            
            # Convert to JSON format
            inspect_data = []
            for sample in inspect_dataset:
                inspect_data.append({
                    "input": sample.input,
                    "target": sample.target,
                    "metadata": sample.metadata
                })
            
            with open(inspect_file, 'w') as f:
                json.dump(inspect_data, f, indent=2)
            dataset_info["inspect_file"] = str(inspect_file)
            
        except Exception as e:
            print(f"Failed to create Inspect dataset: {e}")
        
        # 4. Create blueprint metadata file
        blueprint_metadata = {}
        for name, blueprint in blueprints.items():
            blueprint_metadata[name] = {
                "total_entities": blueprint.get_total_entity_count(),
                "unique_entity_types": blueprint.get_unique_entity_types(),
                "entity_counts": dict(blueprint.get_entity_counts()),
                "dimensions": blueprint.get_dimensions(),
                "bounding_box": blueprint.get_bounding_box()
            }
        
        metadata_file = self.output_dir / "blueprint_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(blueprint_metadata, f, indent=2)
        dataset_info["metadata_file"] = str(metadata_file)
        
        return dataset_info
    
    def _generate_statistics(
        self, 
        blueprints: Dict[str, Any], 
        questions: List[VQAExample],
        rendered_images: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate comprehensive statistics."""
        
        # Blueprint statistics
        blueprint_stats = self.loader.get_blueprint_statistics(blueprints)
        
        # Question statistics
        question_stats = self.generator.get_question_statistics(questions)
        
        # Image statistics
        image_stats = {
            "total_images": len(rendered_images),
            "images_with_questions": len(set(q.blueprint_name for q in questions if q.blueprint_name in rendered_images)),
            "average_questions_per_image": len(questions) / len(rendered_images) if rendered_images else 0
        }
        
        # Combined statistics
        statistics = {
            "blueprints": blueprint_stats,
            "questions": question_stats,
            "images": image_stats,
            "coverage": {
                "blueprints_with_questions": len(set(q.blueprint_name for q in questions)),
                "blueprints_with_images": len(rendered_images),
                "questions_with_images": sum(1 for q in questions if q.blueprint_name in rendered_images)
            }
        }
        
        # Save statistics
        stats_file = self.output_dir / "statistics.json"
        with open(stats_file, 'w') as f:
            json.dump(statistics, f, indent=2)
        
        return statistics


async def main():
    """Main function for running the pipeline from command line."""
    parser = argparse.ArgumentParser(description="Generate Factorio blueprint VQA dataset")
    
    parser.add_argument(
        "--blueprints-dir", 
        default="fle/agents/data/blueprints_to_policies/blueprints",
        help="Directory containing blueprint JSON files"
    )
    parser.add_argument(
        "--output-dir", 
        default="vqa_dataset/output",
        help="Output directory for generated dataset"
    )
    parser.add_argument(
        "--max-blueprints", 
        type=int, 
        default=50,
        help="Maximum number of blueprints to process"
    )
    parser.add_argument(
        "--min-entities", 
        type=int, 
        default=1,
        help="Minimum entities per blueprint"
    )
    parser.add_argument(
        "--max-entities", 
        type=int, 
        default=200,
        help="Maximum entities per blueprint"
    )
    parser.add_argument(
        "--questions-per-blueprint", 
        type=int, 
        default=8,
        help="Number of questions to generate per blueprint"
    )
    parser.add_argument(
        "--no-render", 
        action="store_true",
        help="Skip rendering images (faster for testing)"
    )
    parser.add_argument(
        "--blueprint-subdirs", 
        nargs="+",
        default=["example", "other"],
        help="Blueprint subdirectories to process"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = VQADatasetPipeline(
        blueprints_dir=args.blueprints_dir,
        output_dir=args.output_dir
    )
    
    try:
        results = await pipeline.run_pipeline(
            blueprint_subdirs=args.blueprint_subdirs,
            max_blueprints=args.max_blueprints,
            min_entities=args.min_entities,
            max_entities=args.max_entities,
            questions_per_blueprint=args.questions_per_blueprint,
            render_images=not args.no_render
        )
        
        print("\n" + "="*50)
        print("PIPELINE SUMMARY")
        print("="*50)
        print(f"Blueprints processed: {results['blueprints_count']}")
        print(f"Questions generated: {results['questions_count']}")
        print(f"Images rendered: {results['rendered_images_count']}")
        print(f"Output directory: {results['output_directory']}")
        print("\nDataset files created:")
        for key, value in results['dataset_info'].items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))