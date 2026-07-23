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
