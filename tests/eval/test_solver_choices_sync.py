"""Keep the fle inspect-eval --solver CLI choices in sync with SOLVER_MAP.

Parses both files with ast rather than importing them, so the test needs
neither a running Factorio server nor the eval dependency stack.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_PY = REPO_ROOT / "fle" / "run.py"
EVAL_SET_PY = REPO_ROOT / "fle" / "eval" / "inspect" / "integration" / "eval_set.py"


def _solver_map_keys() -> set[str]:
    """Extract the string keys of the SOLVER_MAP dict literal in eval_set.py."""
    tree = ast.parse(EVAL_SET_PY.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "SOLVER_MAP" in targets and isinstance(node.value, ast.Dict):
                return {
                    key.value
                    for key in node.value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
    raise AssertionError("SOLVER_MAP dict literal not found in eval_set.py")


def _cli_solver_choices() -> set[str]:
    """Extract the choices list of the --solver argument in run.py."""
    tree = ast.parse(RUN_PY.read_text())
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "add_argument"
        ):
            continue
        args = [a.value for a in node.args if isinstance(a, ast.Constant)]
        if "--solver" not in args:
            continue
        for kw in node.keywords:
            if kw.arg == "choices" and isinstance(kw.value, ast.List):
                return {
                    elt.value
                    for elt in kw.value.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                }
    raise AssertionError(
        "--solver add_argument with a choices list not found in run.py"
    )


def test_cli_solver_choices_match_solver_map() -> None:
    solver_map = _solver_map_keys()
    cli_choices = _cli_solver_choices()
    missing_from_cli = solver_map - cli_choices
    unknown_to_solver_map = cli_choices - solver_map
    assert not missing_from_cli, (
        f"Solvers defined in SOLVER_MAP but not selectable via --solver: {sorted(missing_from_cli)}"
    )
    assert not unknown_to_solver_map, (
        f"--solver choices with no SOLVER_MAP entry: {sorted(unknown_to_solver_map)}"
    )
