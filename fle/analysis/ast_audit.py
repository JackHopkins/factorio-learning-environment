#!/usr/bin/env python3
"""
Comprehensive AST audit script to identify missing Python language features in FLE.

This script systematically tests different Python language constructs to identify
what works and what doesn't in the FLE execution environment.
"""

import sys

sys.path.append("/Users/neel/Desktop/Work/factorio-learning-environment")

from fle.env import FactorioInstance


class ASTFeatureAuditor:
    """Audits Python AST feature support in FLE environment"""

    def __init__(self):
        self.results = {}
        self.instance = None

    def setup_instance(self):
        """Initialize Factorio instance for testing"""
        try:
            self.instance = FactorioInstance(
                address="localhost",
                tcp_port=27000,
                num_agents=1,
                fast=True,
                cache_scripts=True,
                inventory={},
                all_technologies_researched=True,
            )
            print("✓ Factorio instance initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize Factorio instance: {e}")
            return False

    def test_feature(
        self, feature_name: str, code: str, expected_behavior: str = "Should work"
    ):
        """Test a specific Python language feature"""
        print(f"\n📋 Testing: {feature_name}")
        print(f"   Code: {code.strip()}")
        print(f"   Expected: {expected_behavior}")

        try:
            result = self.instance.eval_with_error(code, agent_idx=0, timeout=10)
            score, goal, output = result

            # Check for common error indicators
            has_error = any(
                keyword in output.lower()
                for keyword in ["error", "exception", "traceback", "failed"]
            )

            if has_error:
                status = "❌ FAILED"
                details = f"Error in output: {output[:200]}..."
            else:
                status = "✅ PASSED"
                details = (
                    f"Output: {output[:100]}..." if output else "No output (success)"
                )

            print(f"   Result: {status}")
            print(f"   Details: {details}")

            self.results[feature_name] = {
                "status": "PASSED" if not has_error else "FAILED",
                "code": code,
                "result": result,
                "error": has_error,
            }

        except Exception as e:
            print("   Result: ❌ EXCEPTION")
            print(f"   Exception: {str(e)[:200]}...")
            self.results[feature_name] = {
                "status": "EXCEPTION",
                "code": code,
                "result": None,
                "error": str(e),
            }

    def run_comprehensive_audit(self):
        """Run comprehensive audit of Python language features"""

        print("🔍 COMPREHENSIVE PYTHON AST FEATURE AUDIT")
        print("=" * 60)

        # ===== BASIC STATEMENTS =====
        print("\n📂 BASIC STATEMENTS")

        self.test_feature(
            "Simple Assignment",
            """
x = 42
print(f"x = {x}")
""",
        )

        self.test_feature(
            "Multiple Assignment",
            """
a, b, c = 1, 2, 3
print(f"a={a}, b={b}, c={c}")
""",
        )

        self.test_feature(
            "Augmented Assignment (+=)",
            """
x = 10
x += 5
print(f"x = {x}")
""",
        )

        self.test_feature(
            "Augmented Assignment (-=, *=, /=)",
            """
a, b, c, d = 10, 6, 4, 8
a -= 3
b *= 2  
c /= 2
d //= 3
print(f"a={a}, b={b}, c={c}, d={d}")
""",
        )

        # ===== CONTROL FLOW =====
        print("\n📂 CONTROL FLOW")

        self.test_feature(
            "If/Elif/Else",
            """
x = 5
if x > 10:
    result = "big"
elif x > 0:
    result = "positive"
else:
    result = "non-positive"
print(f"result = {result}")
""",
        )

        self.test_feature(
            "For Loop",
            """
total = 0
for i in range(5):
    total += i
print(f"total = {total}")
""",
        )

        self.test_feature(
            "While Loop",
            """
i = 0
total = 0
while i < 5:
    total += i
    i += 1
print(f"total = {total}")
""",
        )

        self.test_feature(
            "Break/Continue",
            """
result = []
for i in range(10):
    if i % 2 == 0:
        continue
    if i > 7:
        break
    result.append(i)
print(f"result = {result}")
""",
        )

        # ===== FUNCTIONS =====
        print("\n📂 FUNCTIONS")

        self.test_feature(
            "Function Definition",
            """
def greet(name):
    return f"Hello, {name}!"

message = greet("World")
print(message)
""",
        )

        self.test_feature(
            "Function with Default Args",
            """
def power(base, exp=2):
    return base ** exp

result1 = power(3)
result2 = power(3, 4)
print(f"3^2 = {result1}, 3^4 = {result2}")
""",
        )

        self.test_feature(
            "Function with *args, **kwargs",
            """
def flexible_func(*args, **kwargs):
    return f"args: {args}, kwargs: {kwargs}"

result = flexible_func(1, 2, 3, name="test", value=42)
print(result)
""",
        )

        self.test_feature(
            "Lambda Functions",
            """
square = lambda x: x ** 2
numbers = [1, 2, 3, 4, 5]
squared = list(map(square, numbers))
print(f"squared = {squared}")
""",
        )

        # ===== CLASSES =====
        print("\n📂 CLASSES")

        self.test_feature(
            "Class Definition",
            """
class Counter:
    def __init__(self, start=0):
        self.value = start
    
    def increment(self):
        self.value += 1
        return self.value

counter = Counter(10)
result = counter.increment()
print(f"counter value = {result}")
""",
        )

        self.test_feature(
            "Class Inheritance",
            """
class Animal:
    def speak(self):
        return "Some sound"

class Dog(Animal):
    def speak(self):
        return "Woof!"

dog = Dog()
print(dog.speak())
""",
        )

        # ===== EXCEPTION HANDLING =====
        print("\n📂 EXCEPTION HANDLING")

        self.test_feature(
            "Try/Except",
            """
try:
    result = 10 / 2
    print(f"Division result: {result}")
except ZeroDivisionError:
    print("Cannot divide by zero!")
""",
        )

        self.test_feature(
            "Try/Except/Finally",
            """
try:
    x = int("42")
    print(f"Parsed: {x}")
except ValueError:
    print("Invalid number")
finally:
    print("Cleanup completed")
""",
        )

        self.test_feature(
            "Raise Exception",
            """
try:
    raise ValueError("Custom error message")
except ValueError as e:
    print(f"Caught: {e}")
""",
        )

        # ===== ADVANCED FEATURES =====
        print("\n📂 ADVANCED FEATURES")

        self.test_feature(
            "List Comprehension",
            """
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers if x % 2 == 1]
print(f"odd squares = {squares}")
""",
        )

        self.test_feature(
            "Dictionary Comprehension",
            """
numbers = [1, 2, 3, 4, 5]
square_dict = {x: x**2 for x in numbers}
print(f"square_dict = {square_dict}")
""",
        )

        self.test_feature(
            "Generator Expression",
            """
numbers = [1, 2, 3, 4, 5]
squares_gen = (x**2 for x in numbers)
squares_list = list(squares_gen)
print(f"squares = {squares_list}")
""",
        )

        self.test_feature(
            "With Statement",
            """
class TestContext:
    def __enter__(self):
        print("Entering context")
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting context")

with TestContext() as ctx:
    print("Inside context")
""",
        )

        self.test_feature(
            "Yield (Generator)",
            """
def count_up_to(max_count):
    count = 1
    while count <= max_count:
        yield count
        count += 1

result = list(count_up_to(3))
print(f"generated = {result}")
""",
        )

        # ===== IMPORTS =====
        print("\n📂 IMPORTS")

        self.test_feature(
            "Import Statement",
            """
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
""",
        )

        self.test_feature(
            "From Import",
            """
from math import pi, cos
result = cos(pi)
print(f"cos(pi) = {result}")
""",
        )

        # ===== ASYNC/AWAIT =====
        print("\n📂 ASYNC/AWAIT")

        self.test_feature(
            "Async Function Definition",
            """
async def async_greet(name):
    return f"Hello, {name}!"

# Note: This may not work without event loop
print("Async function defined")
""",
            "May fail without event loop",
        )

        # ===== MATCH STATEMENTS (Python 3.10+) =====
        print("\n📂 PATTERN MATCHING (Python 3.10+)")

        self.test_feature(
            "Match Statement",
            """
def describe_animal(animal):
    match animal:
        case "dog":
            return "loyal companion"
        case "cat":
            return "independent hunter"
        case _:
            return "unknown animal"

result = describe_animal("dog")
print(f"dog is a {result}")
""",
            "May fail in older Python versions",
        )

        # ===== TYPE ANNOTATIONS =====
        print("\n📂 TYPE ANNOTATIONS")

        self.test_feature(
            "Function Type Annotations",
            """
def add_numbers(a: int, b: int) -> int:
    return a + b

result = add_numbers(5, 3)
print(f"5 + 3 = {result}")
""",
        )

        self.test_feature(
            "Variable Type Annotations",
            """
name: str = "Alice"
age: int = 30
height: float = 5.6
print(f"{name} is {age} years old and {height} feet tall")
""",
        )

        # ===== OPERATOR OVERLOADING =====
        print("\n📂 OPERATOR OVERLOADING")

        self.test_feature(
            "Custom Operators",
            """
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y
    
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)
    
    def __str__(self):
        return f"Vector({self.x}, {self.y})"

v1 = Vector(1, 2)
v2 = Vector(3, 4)
v3 = v1 + v2
print(f"v1 + v2 = {v3}")
""",
        )

    def print_summary(self):
        """Print audit results summary"""
        print("\n" + "=" * 60)
        print("📊 AUDIT SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAILED")
        exceptions = sum(1 for r in self.results.values() if r["status"] == "EXCEPTION")
        total = len(self.results)

        print(f"Total Features Tested: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"💥 Exceptions: {exceptions}")
        print(f"Success Rate: {passed / total * 100:.1f}%")

        if failed > 0 or exceptions > 0:
            print("\n🚨 ISSUES FOUND:")
            for name, result in self.results.items():
                if result["status"] != "PASSED":
                    status_icon = "❌" if result["status"] == "FAILED" else "💥"
                    print(f"  {status_icon} {name}")
                    if isinstance(result["error"], str):
                        print(f"     Error: {result['error'][:100]}...")

    def cleanup(self):
        """Clean up resources"""
        if self.instance:
            self.instance.cleanup()


def main():
    """Main function to run the AST audit"""
    auditor = ASTFeatureAuditor()

    if not auditor.setup_instance():
        print("Cannot proceed without Factorio instance")
        return

    try:
        auditor.run_comprehensive_audit()
        auditor.print_summary()
    finally:
        auditor.cleanup()


if __name__ == "__main__":
    main()
