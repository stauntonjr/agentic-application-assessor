"""Product errors safe to show at the CLI boundary."""


class AssessmentError(RuntimeError):
    """Raised when an assessment cannot be completed safely or deterministically."""
