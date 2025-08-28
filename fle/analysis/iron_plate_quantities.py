#!/usr/bin/env python3
"""
Debug script to investigate the iron plate extraction discrepancy in v4168, agent0, iter18.

The program shows extracted plates (40+30+30=100) in print statements, but total_plates ends up as 0.
This script recreates the exact scenario from the database to debug what happened.
"""

import asyncio
import sys
from typing import Optional
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append("/Users/neel/Desktop/Work/factorio-learning-environment")

from fle.commons.db_client import create_db_client, PostgresDBClient
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance
from fle.env.game_types import Prototype

# Load environment variables
load_dotenv()


class IronPlateDebugger:
    """Debug class to investigate iron plate extraction issue"""

    def __init__(self):
        self.db_client = None
        self.game_instance = None
        self.version = 4168
        self.agent_idx = 0
        self.iteration = 18

    async def setup_db_client(self):
        """Initialize database client"""
        print("Setting up database client...")
        try:
            self.db_client = await create_db_client()
            print(f"✓ Database client initialized: {type(self.db_client).__name__}")
        except Exception as e:
            print(f"✗ Failed to initialize database: {e}")
            raise

    async def get_game_state_from_db(self) -> Optional[GameState]:
        """Retrieve the game state for the specific iteration from database"""
        print(
            f"Retrieving game state for version={self.version}, agent={self.agent_idx}, iteration={self.iteration}"
        )

        try:
            if isinstance(self.db_client, PostgresDBClient):
                hack_query = """
                SELECT state_json, code, response, achievements_json FROM programs WHERE id = 577121 LIMIT 1
                """
                query = """
                SELECT state_json, code, response, achievements_json FROM programs 
                WHERE version = %s AND instance = %s AND depth = %s
                AND state_json IS NOT NULL
                LIMIT 1
                """
                with self.db_client.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            hack_query, (self.version, self.agent_idx, self.iteration)
                        )
                        result = cur.fetchone()
            else:  # SQLite
                query = """
                SELECT state_json, code, response, achievements_json FROM programs 
                WHERE version = ? AND instance = ? AND depth = ?
                AND state_json IS NOT NULL
                LIMIT 1
                """
                with self.db_client.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(query, (self.version, self.agent_idx, self.iteration))
                    result = cur.fetchone()

            if not result:
                print(
                    f"✗ No program found for version={self.version}, agent={self.agent_idx}, iteration={self.iteration}"
                )
                return None

            # Parse the JSON state
            game_state = GameState.parse(result[0])

            print("✓ Retrieved game state from database")
            # print(f"  - Game tick: {game_state.game_tick}")
            # print(f"  - Score: {game_state.score}")
            print(f"  - Program code length: {len(result[1])} chars")
            print(f"  - Response length: {len(result[2])} chars")

            return game_state

        except Exception as e:
            print(f"✗ Error retrieving game state: {e}")
            raise

    def setup_factorio_instance(self):
        """Initialize Factorio instance for debugging"""
        print("Setting up Factorio instance...")
        try:
            # Use localhost setup (assuming docker container is running)
            self.game_instance = FactorioInstance(
                address="localhost",
                tcp_port=27000,  # Default port for first container
                num_agents=1,
                fast=True,
                cache_scripts=True,
                inventory={},
                all_technologies_researched=True,
                bounding_box=200,
            )

            # Speed up the game for debugging
            self.game_instance.set_speed_and_unpause(10)
            print("✓ Factorio instance initialized")

        except Exception as e:
            print(f"✗ Failed to initialize Factorio instance: {e}")
            print("Make sure a Factorio docker container is running on port 27000")
            raise

    def load_game_state(self, game_state: GameState):
        """Load the specific game state into the Factorio instance"""
        print("Loading game state into Factorio instance...")
        try:
            self.game_instance.reset(game_state)
            print("✓ Game state loaded successfully")
            import time

            time.sleep(0.4)

            # Verify the state was loaded correctly
            current_score, _ = self.game_instance.namespaces[0].score()
            print(f"  - Current score: {current_score}")
            # print(f"  - Expected score: {game_state.score}")

        except Exception as e:
            print(f"✗ Failed to load game state: {e}")
            raise

    def debug_program_execution(self, original_game_state):
        """Execute the program step by step with debugging"""
        print("\n" + "=" * 60)
        print("DEBUGGING PROGRAM EXECUTION")
        print("=" * 60)

        try:
            # Get the namespace for API calls
            namespace = self.game_instance.namespaces[0]

            print("\n1. Getting all stone furnaces...")
            furnaces = namespace.get_entities({Prototype.StoneFurnace})
            print(f"   Found {len(furnaces)} stone furnaces:")
            for i, furnace in enumerate(furnaces):
                print(f"   - Furnace {i + 1}: {furnace.position}")

            print("\n2. Inspecting furnace inventories...")
            total_plates_before = 0
            furnace_inventories = []

            for i, furnace in enumerate(furnaces):
                inventory = namespace.inspect_inventory(furnace)
                plates = inventory.get(Prototype.IronPlate, 0)
                total_plates_before += plates
                furnace_inventories.append((furnace, plates))
                print(
                    f"   - Furnace {i + 1} at {furnace.position}: {plates} iron plates"
                )

            print(f"\n   Total iron plates in all furnaces: {total_plates_before}")

            print("\n3. Extracting iron plates...")
            total_plates_extracted = 0
            extraction_results = []

            for i, (furnace, plates_available) in enumerate(furnace_inventories):
                if plates_available > 0:
                    print(
                        f"\n   Extracting from furnace {i + 1} at {furnace.position}:"
                    )
                    print(f"   - Plates available: {plates_available}")

                    try:
                        # This is the exact line from the program
                        extracted = namespace.extract_item(
                            Prototype.IronPlate, furnace, quantity=plates_available
                        )
                        print(f"   - Plates extracted: {extracted}")
                        total_plates_extracted += extracted
                        extraction_results.append(
                            (furnace, plates_available, extracted)
                        )

                    except Exception as e:
                        print(f"   - ✗ Extraction failed: {e}")
                        extraction_results.append((furnace, plates_available, 0))
                else:
                    print(f"   - Furnace {i + 1}: No plates to extract")

            print("\n4. RESULTS SUMMARY:")
            print(f"   - Total plates before extraction: {total_plates_before}")
            print(f"   - Total plates extracted: {total_plates_extracted}")
            print(f"   - Discrepancy: {total_plates_before - total_plates_extracted}")

            print("\n5. DETAILED EXTRACTION RESULTS:")
            for i, (furnace, available, extracted) in enumerate(extraction_results):
                print(
                    f"   - Furnace {i + 1} at {furnace.position}: {available} available → {extracted} extracted"
                )

            # Check player inventory
            print("\n6. PLAYER INVENTORY CHECK:")
            player_inventory = namespace.inspect_inventory()
            player_iron_plates = player_inventory.get(Prototype.IronPlate, 0)
            print(f"   - Iron plates in player inventory: {player_iron_plates}")

            # Re-check furnace inventories after extraction
            print("\n7. POST-EXTRACTION FURNACE INVENTORIES:")
            total_plates_after = 0
            for i, furnace in enumerate(furnaces):
                inventory = namespace.inspect_inventory(furnace)
                plates = inventory.get(Prototype.IronPlate, 0)
                total_plates_after += plates
                print(
                    f"   - Furnace {i + 1} at {furnace.position}: {plates} iron plates remaining"
                )

            print(f"   - Total plates remaining in furnaces: {total_plates_after}")

            # Simulate the original program's total_plates variable
            print("\n8. SIMULATING ORIGINAL PROGRAM LOGIC:")
            print("   Original code:")
            print("   total_plates = 0")
            print("   for furnace in furnaces:")
            print("       plates = inspect_inventory(furnace)[Prototype.IronPlate]")
            print("       if plates > 0:")
            print(
                "           extracted = extract_item(Prototype.IronPlate, furnace, quantity=plates)"
            )
            print("           total_plates += extracted")
            print(
                "           print(f'Extracted {extracted} iron plates from furnace at {furnace.position}')"
            )
            print("")
            print("   Simulation:")

            simulated_total = 0
            for i, (furnace, available, extracted) in enumerate(extraction_results):
                if available > 0:
                    simulated_total += extracted
                    print(
                        f"   total_plates += {extracted}  # (now total_plates = {simulated_total})"
                    )

            print(f"\n   Final simulated total_plates: {simulated_total}")

            # Test the exact accumulation logic that's failing
            print("\n9. TESTING EXACT ACCUMULATION LOGIC:")
            print("   Testing the exact += operation that seems to be failing...")

            test_total_plates = 0
            print(f"   Initial total_plates: {test_total_plates}")

            for i, (furnace, plates_available, extracted) in enumerate(
                extraction_results
            ):
                if plates_available > 0:
                    print(
                        f"   Before += operation: total_plates = {test_total_plates}, extracted = {extracted}"
                    )
                    print(f"   Executing: total_plates += {extracted}")

                    # Store previous value to detect any issues
                    prev_total = test_total_plates
                    test_total_plates += extracted

                    print(f"   After += operation: total_plates = {test_total_plates}")

                    # Verify the operation worked correctly
                    expected = prev_total + extracted
                    if test_total_plates != expected:
                        print(
                            f"   ⚠️  ACCUMULATION FAILURE: Expected {expected}, got {test_total_plates}"
                        )
                    else:
                        print("   ✓ Accumulation successful")
                    print()

            print(f"   Final test total_plates: {test_total_plates}")

            # Reset game state before testing FLE execution environment
            print("\n9.5. RESETTING GAME STATE FOR FLE TESTING:")
            print("   Reloading original game state to restore iron plates...")
            try:
                # Use the original game state that was passed in
                if original_game_state:
                    self.load_game_state(original_game_state)
                    print("   ✓ Game state reset successfully")

                    # Verify the reset worked
                    namespace = self.game_instance.namespaces[0]
                    furnaces = namespace.get_entities({Prototype.StoneFurnace})
                    total_plates_after_reset = 0
                    for i, furnace in enumerate(furnaces):
                        inventory = namespace.inspect_inventory(furnace)
                        plates = inventory.get(Prototype.IronPlate, 0)
                        total_plates_after_reset += plates
                        print(
                            f"   - Furnace {i + 1} at {furnace.position}: {plates} iron plates"
                        )
                    print(f"   - Total plates after reset: {total_plates_after_reset}")
                else:
                    print("   ✗ No original game state available")
            except Exception as e:
                print(f"   ✗ Failed to reset game state: {e}")

            # Test using the actual FLE execution environment
            print("\n10. TESTING IN ACTUAL FLE EXECUTION ENVIRONMENT:")
            print(
                "   Running the exact original program code using instance.eval_with_error()..."
            )

            # The exact original program code
            original_program = """
# Extract iron plates from all furnaces
total_plates = 0
furnaces = get_entities({Prototype.StoneFurnace})
for furnace in furnaces:
    plates = inspect_inventory(furnace)[Prototype.IronPlate]
    if plates > 0:
        extracted = extract_item(Prototype.IronPlate, furnace, quantity=plates)
        total_plates += extracted
        print(f"Extracted {extracted} iron plates from furnace at {furnace.position}")

print(f"Total iron plates extracted: {total_plates}")
total_plates  # Return the final value
"""

            print("   Executing original program in FLE environment...")
            try:
                result = self.game_instance.eval_with_error(
                    original_program, agent_idx=0, timeout=60
                )
                print(f"   FLE execution result: {result}")

                # result should be (return_code, stdout, stderr)
                if len(result) >= 3:
                    return_code, stdout, stderr = result[0], result[1], result[2]
                    print(f"   Return code: {return_code}")
                    print(f"   Stdout: {stdout}")
                    print(f"   Stderr: {stderr}")

                    # The final value of total_plates should be in the result
                    print(f"   Final total_plates from FLE execution: {result}")

            except Exception as e:
                print(f"   ✗ FLE execution failed: {e}")
                import traceback

                traceback.print_exc()

            # Test step-by-step execution in FLE - FOCUSED ON += BUG
            print("\n11. FOCUSED += OPERATION TEST IN FLE:")
            print("   Testing if += operations work correctly in FLE...")

            try:
                # Test simple accumulation first
                print("\n   A. Simple accumulation test:")
                simple_test = self.game_instance.eval_with_error(
                    """
total = 0
print(f"Initial total: {total}")
total += 40
print(f"After adding 40: {total}")
total += 30  
print(f"After adding 30: {total}")
total += 30
print(f"After adding 30 again: {total}")
print(f"Final total: {total}")
total
""",
                    agent_idx=0,
                )
                print(f"   Simple accumulation result: {simple_test}")

                # Test with function calls
                print("\n   B. Accumulation with extract_item calls:")
                extract_test = self.game_instance.eval_with_error(
                    """
total_plates = 0
furnaces = get_entities({Prototype.StoneFurnace})
print(f"Found {len(furnaces)} furnaces")

for i, furnace in enumerate(furnaces):
    plates_available = inspect_inventory(furnace)[Prototype.IronPlate]
    print(f"Furnace {i+1} has {plates_available} plates")
    
    if plates_available > 0:
        print(f"Before extraction - total_plates: {total_plates}")
        extracted = extract_item(Prototype.IronPlate, furnace, quantity=plates_available)
        print(f"Extracted: {extracted}")
        
        print(f"Before += operation - total_plates: {total_plates}, extracted: {extracted}")
        total_plates += extracted
        print(f"After += operation - total_plates: {total_plates}")
    
    print(f"End of iteration {i+1} - total_plates: {total_plates}")

print(f"FINAL RESULT - total_plates: {total_plates}")
total_plates
""",
                    agent_idx=0,
                )
                print(f"   Extract accumulation result: {extract_test}")

                # Test variable persistence across calls
                print("\n   C. Testing variable persistence:")
                persist1 = self.game_instance.eval_with_error(
                    "test_var = 42", agent_idx=0
                )
                print(f"   Set test_var = 42: {persist1}")

                persist2 = self.game_instance.eval_with_error("test_var", agent_idx=0)
                print(f"   Check test_var: {persist2}")

                persist3 = self.game_instance.eval_with_error(
                    "test_var += 8", agent_idx=0
                )
                print(f"   test_var += 8: {persist3}")

                persist4 = self.game_instance.eval_with_error("test_var", agent_idx=0)
                print(f"   Check test_var again: {persist4}")

            except Exception as e:
                print(f"   ✗ Focused += test failed: {e}")
                import traceback

                traceback.print_exc()

            # Test the fix!
            print("\n12. TESTING THE FIX - POST-PATCH VERIFICATION:")
            print("   Re-running the original program to see if += now works...")

            try:
                # Reset game state one more time
                if original_game_state:
                    self.load_game_state(original_game_state)
                    print("   ✓ Game state reset for fix verification")

                # Run the original program again
                fixed_result = self.game_instance.eval_with_error(
                    original_program, agent_idx=0, timeout=60
                )
                print(f"   Fixed program result: {fixed_result}")

                # Parse the output to see if total_plates is now correct
                stderr_output = fixed_result[2] if len(fixed_result) > 2 else ""

                print("\n   Analyzing fixed output:")
                if "Total iron plates extracted: 0" in stderr_output:
                    print("   ❌ BUG STILL EXISTS - total_plates is still 0")
                elif "Total iron plates extracted:" in stderr_output:
                    # Extract the actual number
                    lines = stderr_output.split("\n")
                    for line in lines:
                        if "Total iron plates extracted:" in line:
                            print(f"   ✅ SUCCESS! Found: {line}")
                            break
                else:
                    print("   ⚠️  Could not find total_plates output")

                print("   Full stderr output:")
                for line in stderr_output.split("\n"):
                    if line.strip():
                        print(f"     {line}")

            except Exception as e:
                print(f"   ✗ Fix verification failed: {e}")
                import traceback

                traceback.print_exc()

            return {
                "total_plates_before": total_plates_before,
                "total_plates_extracted": total_plates_extracted,
                "player_iron_plates": player_iron_plates,
                "total_plates_after": total_plates_after,
                "simulated_total": simulated_total,
                "extraction_results": extraction_results,
            }

        except Exception as e:
            print(f"✗ Error during program execution: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def run_analysis(self):
        """Main analysis function"""
        print("=" * 60)
        print("IRON PLATE EXTRACTION DEBUG ANALYSIS")
        print("=" * 60)
        print(
            f"Target: Version {self.version}, Agent {self.agent_idx}, Iteration {self.iteration}"
        )
        print("")

        try:
            # Setup
            await self.setup_db_client()
            game_state = await self.get_game_state_from_db()

            if not game_state:
                print("Cannot proceed without game state")
                return

            self.setup_factorio_instance()
            self.load_game_state(game_state)

            # Debug the program execution
            results = self.debug_program_execution(game_state)

            print("\n" + "=" * 60)
            print("ANALYSIS CONCLUSION")
            print("=" * 60)

            # Compare with the original output
            print("Original program output from observation file:")
            print("- 'Extracted 40 iron plates from furnace at x=16.0 y=74.0'")
            print("- 'Extracted 30 iron plates from furnace at x=19.0 y=74.0'")
            print("- 'Extracted 30 iron plates from furnace at x=22.0 y=74.0'")
            print("- 'Total iron plates extracted: 0'")
            print("")

            print("Our debugging results:")
            print(f"- Total plates extracted: {results['total_plates_extracted']}")
            print(f"- Simulated total_plates variable: {results['simulated_total']}")
            print(f"- Player inventory iron plates: {results['player_iron_plates']}")

            if (
                results["simulated_total"] == 0
                and results["total_plates_extracted"] > 0
            ):
                print("\n🔍 LIKELY ISSUE IDENTIFIED:")
                print(
                    "The extraction operations are succeeding individually, but there may be:"
                )
                print("1. A variable scoping issue in the program execution")
                print(
                    "2. An exception occurring after extraction but before the total is printed"
                )
                print("3. The total_plates variable being reset somewhere")
                print("4. An issue with the program execution environment")
            elif (
                results["simulated_total"] == 0
                and results["total_plates_extracted"] == 0
            ):
                print("\n🔍 ISSUE IDENTIFIED:")
                print(
                    "The extract_item calls are failing, despite the print statements suggesting success"
                )
                print("This indicates a problem with:")
                print("1. The extract_item function implementation")
                print("2. The game state not matching what was expected")
                print("3. The furnace positions or states being different")

        except Exception as e:
            print(f"✗ Analysis failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup
            if self.game_instance:
                self.game_instance.cleanup()
            if self.db_client:
                await self.db_client.cleanup()


async def main():
    """Main function to run the debug analysis"""
    debugger = IronPlateDebugger()
    await debugger.run_analysis()


if __name__ == "__main__":
    print("Starting iron plate extraction debug analysis...")
    print("Make sure you have:")
    print("1. A Factorio docker container running on port 27000")
    print("2. Database credentials set in environment variables")
    print("3. Virtual environment activated")
    print("")

    asyncio.run(main())
