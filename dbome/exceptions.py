"""Custom exceptions for dbome."""


class DbomeError(Exception):
    """Base exception for all dbome errors."""
    pass


class ConfigError(DbomeError):
    """Configuration-related errors.
    
    Raised when:
    - Config file is missing
    - Config file has invalid YAML
    - Required configuration keys are missing
    - Configuration values are invalid
    """
    pass


class AuthenticationError(DbomeError):
    """Authentication and authorization failures.
    
    Raised when:
    - Google Cloud credentials are invalid
    - Service account lacks required permissions
    - AWS SSM parameter cannot be accessed
    - BigQuery client initialization fails
    """
    pass


class DeploymentError(DbomeError):
    """Deployment and execution failures.
    
    Raised when:
    - SQL execution fails
    - BigQuery dataset doesn't exist
    - View creation/update fails
    - Network errors during deployment
    """
    pass


class ValidationError(DbomeError):
    """SQL and template validation errors.
    
    Raised when:
    - SQL syntax is invalid
    - ref() references non-existent views
    - Circular dependencies are detected
    - Template compilation fails
    """
    pass


class FileSystemError(DbomeError):
    """File system operation errors.
    
    Raised when:
    - SQL files cannot be read
    - Template files are missing
    - Directory creation fails
    - File permissions are insufficient
    """
    pass


class GitError(DbomeError):
    """Git operation errors.
    
    Raised when:
    - Git initialization fails
    - Git commands fail
    - Repository state is invalid
    """
    pass