# Core model classes
from fle.agents.models import TaskResponse, Response, CompletionReason, CompletionResult

# Import TimingMetrics from commons to maintain backward compatibility
from fle.commons.models.timing_metrics import TimingMetrics

# Agent base classes
from fle.agents.agent_abc import AgentABC, create_default_agent_card


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
    # Lazy-loaded classes
    "Policy",
    "PolicyMeta",
]
