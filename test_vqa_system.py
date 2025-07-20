#!/usr/bin/env python3
"""
Test script for the Factorio Blueprint VQA system.
"""

import asyncio
import sys
from pathlib import Path
import pytest
# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from vqa_dataset import (
    BlueprintLoader, 
    QuestionGenerator, 
    VQADatasetPipeline,
    FactorioBlueprintAnalyzer
)

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "small-electric-pole": 20,
        "iron-plate": 10,
        "assembling-machine-1": 1,
        "pipe-to-ground": 10,
        "pipe": 30,
        "transport-belt": 50,
        "underground-belt": 30,
        'splitter': 1,
        'lab': 1
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


async def test_blueprint_loading():
    """Test blueprint loading functionality."""
    print("Testing blueprint loading...")
    
    blueprints_dir = "fle/agents/data/blueprints_to_policies/blueprints"
    loader = BlueprintLoader(blueprints_dir)
    
    # Load blueprints from example directory
    blueprints = loader.load_all_blueprints(['example'])
    print(f"Loaded {len(blueprints)} blueprints from example directory")
    
    if blueprints:
        # Test one blueprint
        blueprint_name, blueprint = list(blueprints.items())[0]
        print(f"Sample blueprint: {blueprint_name}")
        print(f"  Total entities: {blueprint.get_total_entity_count()}")
        print(f"  Entity types: {blueprint.get_unique_entity_types()}")
        print(f"  Dimensions: {blueprint.get_dimensions()}")
        
        # Test statistics
        stats = loader.get_blueprint_statistics(blueprints)
        print(f"Blueprint statistics: {stats}")
        
        return True
    else:
        print("No blueprints loaded!")
        return False


def test_question_generation():
    """Test question generation functionality."""
    print("\nTesting question generation...")
    
    blueprints_dir = "fle/agents/data/blueprints_to_policies/blueprints"
    loader = BlueprintLoader(blueprints_dir)
    generator = QuestionGenerator()
    
    # Load a few blueprints
    blueprints = loader.load_all_blueprints(['example'])
    blueprints = loader.filter_blueprints_by_complexity(blueprints, max_entities=50)
    
    if not blueprints:
        print("No blueprints available for testing!")
        return False
    
    # Generate questions
    questions = generator.generate_questions_batch(
        blueprints, 
        num_questions_per_blueprint=3
    )
    
    print(f"Generated {len(questions)} questions")
    
    # Show sample questions
    print("Sample questions:")
    for i, q in enumerate(questions[:5]):
        print(f"{i+1}. Q: {q.question}")
        print(f"   A: {q.answer}")
        print(f"   Type: {q.question_type}")
        print()
    
    # Test statistics
    stats = generator.get_question_statistics(questions)
    print(f"Question statistics: {stats}")
    
    return True


def test_blueprint_analyzer():
    """Test the blueprint analyzer functionality."""
    print("\nTesting blueprint analyzer...")
    
    analyzer = FactorioBlueprintAnalyzer()
    
    try:
        results = analyzer.run_evaluation(
            "fle/agents/data/blueprints_to_policies/blueprints",
            output_file="test_analysis_results.json",
            max_blueprints=3
        )
        
        print(f"Analysis completed for {results['total_blueprints']} blueprints")
        
        if results['blueprints']:
            sample = results['blueprints'][0]
            print(f"Sample analysis for '{sample['blueprint_name']}':")
            print(f"  Total entities: {sample['total_entities']}")
            print(f"  Entity types: {len(sample['unique_entity_types'])}")
            print(f"  Questions generated: {len(sample['questions_and_answers'])}")
        
        return True
        
    except Exception as e:
        print(f"Analyzer test failed: {e}")
        return False


async def test_pipeline_without_rendering():
    """Test the complete pipeline without rendering (faster)."""
    print("\nTesting complete pipeline (without rendering)...")
    
    try:
        pipeline = VQADatasetPipeline(
            blueprints_dir="fle/agents/data/blueprints_to_policies/blueprints",
            output_dir="test_output"
        )
        
        results = await pipeline.run_pipeline(
            blueprint_subdirs=['example'],
            max_blueprints=5,
            max_entities=100,
            questions_per_blueprint=4,
            render_images=False  # Skip rendering for faster testing
        )
        
        print("Pipeline test completed successfully!")
        print(f"Processed {results['blueprints_count']} blueprints")
        print(f"Generated {results['questions_count']} questions")
        print(f"Output directory: {results['output_directory']}")
        
        return True
        
    except Exception as e:
        print(f"Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_small_pipeline_with_rendering():
    """Test pipeline with rendering on a very small dataset."""
    print("\nTesting pipeline with rendering (small dataset)...")
    
    try:
        pipeline = VQADatasetPipeline(
            blueprints_dir="fle/agents/data/blueprints_to_policies/blueprints",
            output_dir="test_output_with_images"
        )
        
        results = await pipeline.run_pipeline(
            blueprint_subdirs=['example'],
            max_blueprints=2,  # Very small for testing
            max_entities=50,   # Small blueprints only
            questions_per_blueprint=2,
            render_images=True
        )
        
        print("Pipeline with rendering completed successfully!")
        print(f"Processed {results['blueprints_count']} blueprints")
        print(f"Generated {results['questions_count']} questions") 
        print(f"Rendered {results['rendered_images_count']} images")
        
        return True
        
    except Exception as e:
        print(f"Pipeline with rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("Starting VQA System Tests")
    print("=" * 50)
    
    tests = [
        ("Blueprint Loading", test_blueprint_loading()),
        ("Question Generation", test_question_generation()),
        ("Blueprint Analyzer", test_blueprint_analyzer()),
        ("Pipeline (No Rendering)", test_pipeline_without_rendering()),
        ("Pipeline (With Rendering)", test_small_pipeline_with_rendering()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, result))
            print(f"✓ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"✗ {test_name}: FAILED with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The VQA system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))