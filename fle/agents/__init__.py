# Core model classes
from fle.agents.models import TaskResponse, Response, CompletionReason, CompletionResult

# Import TimingMetrics from commons to maintain backward compatibility
from fle.commons.models.timing_metrics import TimingMetrics

# Agent base classes
from fle.agents.agent_abc import AgentABC, create_default_agent_card

# Agent implementations
from fle.agents.basic_agent import BasicAgent
from fle.agents.gym_agent import GymAgent
from fle.agents.visual_agent import VisualAgent
from fle.agents.backtracking_agent import BacktrackingAgent
from fle.agents.backtracking_system import BacktrackingSystem

from fle.agents.llm.parsing import Policy, PolicyMeta


# Lazy imports to avoid circular dependencies
def _get_policy_classes():
    """Lazy import for Policy classes to avoid circular imports."""
    from fle.agents.llm.parsing import Policy, PolicyMeta

    return Policy, PolicyMeta


# Maintain backward compatibility with lazy loading
def __getattr__(name):
    if name in ("Policy", "PolicyMeta"):
        Policy, PolicyMeta = _get_policy_classes()
        globals()[name] = globals().get("Policy" if name == "Policy" else "PolicyMeta")
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Standard exports
__all__ = [
    # Models
    "TimingMetrics",
    "TaskResponse",
    "Response",
    "CompletionReason",
    "CompletionResult",
    # Agent classes
    "AgentABC",
    "create_default_agent_card",
    "BasicAgent",
    "GymAgent",
    "VisualAgent",
    "BacktrackingAgent",
    "BacktrackingSystem",
    # Lazy-loaded classes
    "Policy",
    "PolicyMeta",
]
