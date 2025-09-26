# Core model classes
from fle.agents.models import TaskResponse, Response, CompletionReason, CompletionResult

# Import TimingMetrics from commons to maintain backward compatibility
from fle.commons.models.timing_metrics import TimingMetrics

# Agent base classes - conditional import for optional a2a dependency
try:
    from fle.agents.agent_abc import AgentABC, create_default_agent_card
except ImportError:
    # a2a-sdk not installed, create placeholder classes
    class AgentABC:
        """Placeholder AgentABC when a2a-sdk is not installed."""

        def __init__(self):
            raise ImportError(
                "AgentABC requires a2a-sdk. Install with: pip install factorio-learning-environment[eval]"
            )

    def create_default_agent_card():
        """Placeholder function when a2a-sdk is not installed."""
        raise ImportError(
            "create_default_agent_card requires a2a-sdk. Install with: pip install factorio-learning-environment[eval]"
        )


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
