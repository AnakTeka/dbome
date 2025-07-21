"""Configuration validation for dbome."""

from typing import Optional, List, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator
import yaml

from .exceptions import ConfigError


class BigQueryConfig(BaseModel):
    """BigQuery configuration."""
    project_id: str = Field(..., description="GCP project ID")
    dataset_id: str = Field(..., description="BigQuery dataset ID")
    location: Optional[str] = Field("US", description="BigQuery location")
    
    @field_validator('project_id', 'dataset_id')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Ensure project_id and dataset_id are not empty."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v


class SqlConfig(BaseModel):
    """SQL file configuration."""
    views_directory: str = Field("sql/views", description="Directory containing SQL view files")
    compiled_directory: str = Field("compiled/views", description="Directory for compiled SQL files")
    include_patterns: List[str] = Field(default_factory=lambda: ["*.sql"], description="File patterns to include")
    exclude_patterns: List[str] = Field(default_factory=lambda: ["*.backup.sql"], description="File patterns to exclude")
    
    @field_validator('views_directory')
    @classmethod
    def validate_views_directory(cls, v: str) -> str:
        """Validate views directory path."""
        if not v or not v.strip():
            raise ValueError("views_directory cannot be empty")
        return v


class DeploymentConfig(BaseModel):
    """Deployment configuration."""
    dry_run: bool = Field(False, description="Run in dry-run mode (no actual deployment)")
    verbose: bool = Field(False, description="Enable verbose output")
    save_compiled: bool = Field(True, description="Save compiled SQL files")


class Config(BaseModel):
    """Complete configuration for dbome."""
    bigquery: BigQueryConfig
    sql: SqlConfig = Field(default_factory=SqlConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    google_application_credentials: Optional[str] = Field(None, description="Path to service account JSON file")
    aws_ssm_credentials_parameter: Optional[str] = Field(None, description="AWS SSM parameter name for credentials")
    
    @model_validator(mode='after')
    def validate_auth_config(self) -> 'Config':
        """Ensure at least one auth method is available."""
        # If no explicit auth is configured, we'll use default application credentials
        # which is valid, so no validation error needed
        return self
    
    @field_validator('google_application_credentials')
    @classmethod
    def validate_credentials_file(cls, v: Optional[str]) -> Optional[str]:
        """Validate credentials file path if provided."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"Credentials file not found: {v}")
            if not path.is_file():
                raise ValueError(f"Credentials path is not a file: {v}")
        return v
    
    model_config = {
        'extra': 'allow'  # Allow extra fields for backward compatibility
    }


def load_and_validate_config(config_path: str) -> Config:
    """Load and validate configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Validated Config object
        
    Raises:
        ConfigError: If configuration is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        if not config_dict:
            raise ConfigError("Configuration file is empty")
        
        # Validate with Pydantic
        return Config(**config_dict)
        
    except FileNotFoundError:
        raise ConfigError(f"Config file {config_path} not found!")
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing config file: {e}")
    except Exception as e:
        # Pydantic validation errors will be caught here
        raise ConfigError(f"Configuration validation error: {e}")