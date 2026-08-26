class EnvironmentServiceError(RuntimeError):
    """Base error for the Factorio environment service."""


class CapacityExhausted(EnvironmentServiceError):
    pass


class LeaseNotFound(EnvironmentServiceError):
    pass


class LeaseExpired(EnvironmentServiceError):
    pass


class InterventionLimitReached(EnvironmentServiceError):
    pass


class LeaseFinalized(EnvironmentServiceError):
    pass


class IdempotencyConflict(EnvironmentServiceError):
    """A request ID was reused for a different mutation payload."""


class ContractEpochError(EnvironmentServiceError):
    """Base error for adaptive contract epoch lifecycle violations."""


class EpochAlreadyActive(ContractEpochError):
    """A second open order was requested while one is active."""


class NoActiveEpoch(ContractEpochError):
    """Finalization attempted without an open epoch."""


class EpochMismatch(ContractEpochError):
    """Epoch index or session identity does not match the lease state."""


class CommitmentMismatch(ContractEpochError):
    """Finalization commitment hash differs from the committed spec."""


class RuntimeBackendError(EnvironmentServiceError):
    """An environment-runtime control-plane or data-plane request failed."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
