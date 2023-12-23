class TiktokException(BaseException):
    """Base class for Tiktok-related exceptions."""

    def __init__(self, message: str):
        """Initialize the exception with a custom error message."""
        self.message = message

    def __str__(self):
        """Return a string representation of the exception."""
        return self.message


class AccountNotFoundError(TiktokException):
    """Raised when a Tiktok account does not exist or is private."""


class InvalidUrlError(TiktokException):
    """Raised when an invalid Tiktok URL type is encountered."""


class ScriptTagNotFoundError(TiktokException):
    """Raised when the script tag is not found in the Tiktok content."""


class UrlLimitError(TiktokException):
    """Raised when an invalid limiter input is provided for a Tiktok URL."""
