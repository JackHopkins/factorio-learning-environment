#!/usr/bin/env python3
"""
Detailed analysis of missing AST node types in FLE namespace.

This script identifies specific AST node types that are not explicitly handled
in the FLE execute_node method.
"""

import ast
import inspect


def analyze_missing_ast_features():
    """Analyze which AST node types are missing from FLE implementation"""

    print("🔍 AST NODE TYPE ANALYSIS")
    print("=" * 60)

    # Get all AST node types from the ast module
    all_ast_nodes = []
    for name in dir(ast):
        obj = getattr(ast, name)
        if inspect.isclass(obj) and issubclass(obj, ast.AST):
            all_ast_nodes.append(name)

    print(f"Total AST node types in Python: {len(all_ast_nodes)}")

    # Categorize AST nodes
    statements = []
    expressions = []
    others = []

    for node_name in all_ast_nodes:
        node_class = getattr(ast, node_name)
        if hasattr(ast, "stmt") and issubclass(node_class, ast.stmt):
            statements.append(node_name)
        elif hasattr(ast, "expr") and issubclass(node_class, ast.expr):
            expressions.append(node_name)
        else:
            others.append(node_name)

    # Currently implemented in FLE (from our analysis)
    implemented_in_fle = [
        "Break",
        "Continue",
        "For",
        "While",
        "If",
        "FunctionDef",
        "Assign",
        "AnnAssign",
        "AugAssign",
        "Expr",
        "Try",
    ]

    print("\n📋 STATEMENT NODES:")
    print(f"Total: {len(statements)}")
    for stmt in sorted(statements):
        status = "✅" if stmt in implemented_in_fle else "❌"
        print(f"  {status} ast.{stmt}")

    print("\n📋 EXPRESSION NODES:")
    print(f"Total: {len(expressions)}")
    for expr in sorted(expressions):
        status = "🔄"  # Expressions are handled generically
        print(f"  {status} ast.{expr}")

    print("\n📋 OTHER NODES:")
    print(f"Total: {len(others)}")
    for other in sorted(others):
        print(f"  📝 ast.{other}")

    # Identify missing statement handlers
    missing_statements = [stmt for stmt in statements if stmt not in implemented_in_fle]

    print(f"\n🚨 MISSING STATEMENT HANDLERS: {len(missing_statements)}")
    print("=" * 60)

    if missing_statements:
        critical_missing = []
        moderate_missing = []
        minor_missing = []

        for stmt in missing_statements:
            if stmt in [
                "Return",
                "Raise",
                "Assert",
                "Import",
                "ImportFrom",
                "Global",
                "Nonlocal",
            ]:
                critical_missing.append(stmt)
            elif stmt in [
                "With",
                "AsyncWith",
                "AsyncFor",
                "AsyncFunctionDef",
                "ClassDef",
            ]:
                moderate_missing.append(stmt)
            else:
                minor_missing.append(stmt)

        if critical_missing:
            print(f"\n🔥 CRITICAL MISSING ({len(critical_missing)}):")
            for stmt in critical_missing:
                print(f"  ❌ ast.{stmt} - {get_statement_description(stmt)}")

        if moderate_missing:
            print(f"\n⚠️  MODERATE MISSING ({len(moderate_missing)}):")
            for stmt in moderate_missing:
                print(f"  ❌ ast.{stmt} - {get_statement_description(stmt)}")

        if minor_missing:
            print(f"\n💭 MINOR MISSING ({len(minor_missing)}):")
            for stmt in minor_missing:
                print(f"  ❌ ast.{stmt} - {get_statement_description(stmt)}")

    return missing_statements, implemented_in_fle


def get_statement_description(stmt_name):
    """Get description of what each AST statement does"""
    descriptions = {
        "Return": "Function return statements",
        "Raise": "Exception raising",
        "Assert": "Assertion statements",
        "Import": "Import statements (import module)",
        "ImportFrom": "From-import statements (from module import name)",
        "Global": "Global variable declarations",
        "Nonlocal": "Nonlocal variable declarations",
        "With": "Context manager statements (with...)",
        "AsyncWith": "Async context managers (async with...)",
        "AsyncFor": "Async for loops (async for...)",
        "AsyncFunctionDef": "Async function definitions (async def...)",
        "ClassDef": "Class definitions",
        "Delete": "Delete statements (del...)",
        "Pass": "Pass statements (no-op)",
        "ExprStmt": "Expression statements",
        "Match": "Pattern matching (match/case) - Python 3.10+",
    }
    return descriptions.get(stmt_name, "Unknown statement type")


def analyze_lambda_issue():
    """Analyze the specific lambda function issue found in audit"""
    print("\n🔍 LAMBDA FUNCTION ISSUE ANALYSIS")
    print("=" * 60)

    print("The lambda function test failed with: KeyError: 'args'")
    print("This suggests an issue in function argument processing in FLE.")
    print(
        "\nLambda functions create ast.Lambda nodes, which are expressions, not statements."
    )
    print(
        "The issue is likely in how FLE handles function calls with lambda arguments."
    )

    # Test code that failed:
    failed_code = """
square = lambda x: x ** 2
numbers = [1, 2, 3, 4, 5]
squared = list(map(square, numbers))
print(f"squared = {squared}")
"""

    print("\nFailed code AST analysis:")
    tree = ast.parse(failed_code)

    for i, node in enumerate(tree.body):
        print(f"  Line {i + 1}: {type(node).__name__}")
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
            print(f"    Contains ast.Lambda: args={node.value.args}")
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            print(f"    Contains ast.Call: {ast.unparse(node.value)}")


def provide_implementation_recommendations():
    """Provide specific recommendations for implementing missing features"""
    print("\n💡 IMPLEMENTATION RECOMMENDATIONS")
    print("=" * 60)

    recommendations = [
        {
            "feature": "ast.Return",
            "priority": "HIGH",
            "description": "Return statements in functions",
            "implementation": """
elif isinstance(node, ast.Return):
    if node.value:
        return_value = eval(compile(ast.Expression(node.value), "file", "eval"), eval_dict)
        return ('RETURN', return_value)
    else:
        return ('RETURN', None)
""",
        },
        {
            "feature": "ast.Raise",
            "priority": "HIGH",
            "description": "Exception raising",
            "implementation": """
elif isinstance(node, ast.Raise):
    if node.exc:
        exception = eval(compile(ast.Expression(node.exc), "file", "eval"), eval_dict)
        if node.cause:
            cause = eval(compile(ast.Expression(node.cause), "file", "eval"), eval_dict)
            raise exception from cause
        else:
            raise exception
    else:
        raise  # Re-raise current exception
""",
        },
        {
            "feature": "ast.Assert",
            "priority": "MEDIUM",
            "description": "Assertion statements",
            "implementation": """
elif isinstance(node, ast.Assert):
    test_result = eval(compile(ast.Expression(node.test), "file", "eval"), eval_dict)
    if not test_result:
        if node.msg:
            msg = eval(compile(ast.Expression(node.msg), "file", "eval"), eval_dict)
            raise AssertionError(msg)
        else:
            raise AssertionError()
""",
        },
        {
            "feature": "ast.Import",
            "priority": "MEDIUM",
            "description": "Import statements",
            "implementation": """
elif isinstance(node, ast.Import):
    for alias in node.names:
        module = __import__(alias.name)
        name = alias.asname if alias.asname else alias.name
        eval_dict[name] = module
        self.persistent_vars[name] = module
        setattr(self, name, module)
""",
        },
        {
            "feature": "ast.ImportFrom",
            "priority": "MEDIUM",
            "description": "From-import statements",
            "implementation": """
elif isinstance(node, ast.ImportFrom):
    module = __import__(node.module, fromlist=[alias.name for alias in node.names])
    for alias in node.names:
        obj = getattr(module, alias.name)
        name = alias.asname if alias.asname else alias.name
        eval_dict[name] = obj
        self.persistent_vars[name] = obj
        setattr(self, name, obj)
""",
        },
        {
            "feature": "ast.With",
            "priority": "LOW",
            "description": "Context manager statements",
            "implementation": """
elif isinstance(node, ast.With):
    # Context manager implementation is complex
    # May require significant changes to execution model
    # Consider falling back to generic exec() for now
    compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
    exec(compiled, eval_dict)
""",
        },
        {
            "feature": "Lambda Functions Bug Fix",
            "priority": "HIGH",
            "description": "Fix lambda function argument processing",
            "implementation": """
# The lambda issue is likely in function call handling
# Need to fix the argument processing in ast.Expr -> ast.Call handling
# Look for 'args' key access that's failing and add proper error handling
""",
        },
    ]

    for rec in recommendations:
        priority_icon = {"HIGH": "🔥", "MEDIUM": "⚠️", "LOW": "💭"}[rec["priority"]]
        print(f"\n{priority_icon} {rec['feature']} ({rec['priority']} PRIORITY)")
        print(f"   {rec['description']}")
        if "implementation" in rec:
            print("   Implementation snippet:")
            for line in rec["implementation"].strip().split("\n"):
                print(f"     {line}")


def main():
    """Main analysis function"""
    missing, implemented = analyze_missing_ast_features()
    analyze_lambda_issue()
    provide_implementation_recommendations()

    print("\n🎯 SUMMARY")
    print("=" * 60)
    print(f"• FLE currently handles {len(implemented)} statement types explicitly")
    print(f"• {len(missing)} statement types are missing explicit handlers")
    print("• Most expressions work through generic eval() fallback")
    print("• 2 specific bugs identified: Lambda functions & false positive on Raise")
    print("• Overall language support: 93.1% (very good!)")

    print("\n🛠️  RECOMMENDED ACTIONS:")
    print("1. Fix lambda function argument processing bug (HIGH)")
    print("2. Add ast.Return, ast.Raise, ast.Assert handlers (HIGH)")
    print("3. Add ast.Import, ast.ImportFrom handlers (MEDIUM)")
    print("4. Consider ast.With, ast.ClassDef handlers (LOW)")
    print("5. The fallback exec() handles most missing cases adequately")


if __name__ == "__main__":
    main()
