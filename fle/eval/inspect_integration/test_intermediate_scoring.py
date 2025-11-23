#!/usr/bin/env python3
"""Test script to demonstrate intermediate scoring functionality."""

import asyncio
from inspect_ai import eval
from factorio_eval_set import iron_ore_throughput


async def test_intermediate_scoring():
    """Test the enhanced Factorio scoring with intermediate metrics."""

    print("🚀 Testing Enhanced Factorio Scoring with Intermediate Metrics")
    print("=" * 60)

    # Run evaluation with the enhanced scorer
    try:
        results = eval(
            tasks=[iron_ore_throughput()],
            model="openrouter/anthropic/claude-3.5-sonnet",
            epochs=1,
            log_dir="./test_intermediate_logs",
        )

        if results and len(results) > 0:
            result = results[0]
            print("\n📊 Evaluation Results:")
            print(f"Task: {result.eval.task}")
            print(f"Model: {result.eval.model}")

            # Check for intermediate scores in the result
            if hasattr(result, "samples") and result.samples:
                sample = result.samples[0]
                print(
                    f"\nSample scores count: {len(sample.scores) if sample.scores else 0}"
                )

                if sample.scores:
                    for scorer_name, score_obj in sample.scores.items():
                        print(f"\n{scorer_name}:")
                        print(f"  Value: {score_obj.value}")
                        print(f"  Answer: {score_obj.answer}")
                        print(f"  Explanation: {score_obj.explanation}")

                        if hasattr(score_obj, "metadata") and score_obj.metadata:
                            print(f"  Metadata keys: {list(score_obj.metadata.keys())}")

                            # Show key metrics
                            metadata = score_obj.metadata
                            if "throughput_proportion" in metadata:
                                print(
                                    f"    Throughput Proportion: {metadata['throughput_proportion']:.3f}"
                                )
                            if "production_score" in metadata:
                                print(
                                    f"    Production Score: {metadata['production_score']:.2f}"
                                )
                            if "last_step_change" in metadata:
                                print(
                                    f"    Last Step Change: {metadata['last_step_change']:+.3f}"
                                )

            print("\n✅ Test completed successfully!")

        else:
            print("❌ No results returned from evaluation")

    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main test function."""
    print("Testing intermediate scoring with enhanced Factorio metrics...")
    print("This will run a short evaluation to verify the scoring system works.")

    # Run the test
    asyncio.run(test_intermediate_scoring())


if __name__ == "__main__":
    main()
