"""Domain-specific errors. Callers (CLI, CI, notifiers) can branch on these
instead of parsing assertion messages."""


class UPassError(Exception):
    """Base class for every expected failure in the U-Pass workflow."""


class ConfigError(UPassError):
    """Credentials are missing or malformed."""


class InvalidCredentialsError(UPassError):
    """The SSO provider rejected the username/password."""


class MfaFailedError(UPassError):
    """MFA did not succeed within the allowed number of attempts."""


class NoPrivilegeError(UPassError):
    """Login worked, but the institution has not enabled U-Pass for this user."""


class NotEligibleError(UPassError):
    """The request button was present but disabled."""