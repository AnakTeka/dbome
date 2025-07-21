"""Type definitions for dbome."""

from typing import TypedDict, Optional, List, Dict, Any
from pathlib import Path


class BigQueryConfig(TypedDict):
    """BigQuery configuration."""
    project_id: str
    dataset_id: str
    location: Optional[str]


class SqlConfig(TypedDict):
    """SQL file configuration."""
    views_directory: str
    compiled_directory: str
    include_patterns: List[str]
    exclude_patterns: List[str]


class DeploymentConfig(TypedDict):
    """Deployment configuration."""
    dry_run: bool
    verbose: bool
    save_compiled: bool


class Config(TypedDict):
    """Complete configuration structure."""
    bigquery: BigQueryConfig
    sql: SqlConfig
    deployment: DeploymentConfig
    google_application_credentials: Optional[str]
    aws_ssm_credentials_parameter: Optional[str]


class ViewInfo(TypedDict):
    """Parsed SQL view information."""
    name: str
    full_name: str
    project_id: Optional[str]
    dataset_id: Optional[str]
    path: Path
    raw_content: str
    compiled_content: str
    parsed_ast: Any  # sqlglot.expressions.Expression


class DeploymentResult(TypedDict):
    """Result of a single view deployment."""
    view_name: str
    full_name: str
    success: bool
    error: Optional[str]


class ViewRegistration(TypedDict):
    """View registration information for dependency tracking."""
    path: Path
    raw_content: str
    view_name: str
    full_name: str
    project_id: Optional[str]
    dataset_id: Optional[str]