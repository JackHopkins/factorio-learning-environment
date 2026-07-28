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


class RuntimeBackendError(EnvironmentServiceError):
    """An environment-runtime control-plane or data-plane request failed."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
