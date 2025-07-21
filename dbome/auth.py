"""Authentication management for BigQuery connections."""

import os
import base64
import json
from typing import Optional, Dict, Any

import boto3
from google.cloud import bigquery
from google.oauth2 import service_account
from rich.console import Console

console = Console()


class AuthManager:
    """Manages authentication for BigQuery connections.
    
    Supports multiple authentication methods:
    - Default application credentials (gcloud auth)
    - Service account JSON file
    - AWS SSM Parameter Store
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the auth manager with configuration.
        
        Args:
            config: Configuration dictionary containing auth settings
        """
        self.config = config
    
    def get_client(self) -> bigquery.Client:
        """Get authenticated BigQuery client based on configuration.
        
        Returns:
            Authenticated BigQuery client
            
        Raises:
            Exception: If authentication fails
        """
        project_id = self.config['bigquery']['project_id']
        location = self.config['bigquery'].get('location')
        
        try:
            # AWS SSM Parameter Store
            if self.config.get('aws_ssm_credentials_parameter'):
                console.print("[cyan]Using AWS SSM Parameter Store for credentials[/cyan]")
                return self._get_ssm_client(project_id, location)
            
            # Local service account file
            elif self.config.get('google_application_credentials'):
                console.print("[cyan]Using local service account file for credentials[/cyan]")
                return self._get_service_account_client(project_id, location)
            
            # Default application credentials
            else:
                console.print("[cyan]Using default application credentials[/cyan]")
                return self._get_default_client(project_id, location)
                
        except Exception as e:
            console.print(f"[red]Failed to initialize BigQuery client: {e}[/red]")
            raise
    
    def _get_ssm_client(self, project_id: str, location: Optional[str]) -> bigquery.Client:
        """Get BigQuery client using AWS SSM Parameter Store credentials.
        
        Args:
            project_id: GCP project ID
            location: BigQuery location
            
        Returns:
            Authenticated BigQuery client
        """
        parameter_name = self.config['aws_ssm_credentials_parameter']
        credentials_json = self._retrieve_ssm_credentials(parameter_name)
        credentials = service_account.Credentials.from_service_account_info(credentials_json)
        
        client = bigquery.Client(
            project=project_id,
            location=location,
            credentials=credentials
        )
        console.print(f"[green]✓[/green] Connected to BigQuery project: {project_id}")
        return client
    
    def _get_service_account_client(self, project_id: str, location: Optional[str]) -> bigquery.Client:
        """Get BigQuery client using service account file.
        
        Args:
            project_id: GCP project ID
            location: BigQuery location
            
        Returns:
            Authenticated BigQuery client
        """
        credentials_path = self.config['google_application_credentials']
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        client = bigquery.Client(project=project_id, location=location)
        console.print(f"[green]✓[/green] Connected to BigQuery project: {project_id}")
        return client
    
    def _get_default_client(self, project_id: str, location: Optional[str]) -> bigquery.Client:
        """Get BigQuery client using default application credentials.
        
        Args:
            project_id: GCP project ID
            location: BigQuery location
            
        Returns:
            Authenticated BigQuery client
        """
        client = bigquery.Client(project=project_id, location=location)
        console.print(f"[green]✓[/green] Connected to BigQuery project: {project_id}")
        return client
    
    def _retrieve_ssm_credentials(self, parameter_name: str) -> Dict[str, Any]:
        """Retrieve Google service account credentials from AWS SSM Parameter Store.
        
        Args:
            parameter_name: SSM parameter name
            
        Returns:
            Service account credentials as dictionary
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            console.print(f"[cyan]Retrieving credentials from AWS SSM parameter: {parameter_name}[/cyan]")
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            encoded_value = response['Parameter']['Value']
            decoded_value = base64.b64decode(encoded_value).decode('ascii')
            credentials_json = json.loads(decoded_value)
            console.print("[green]✓[/green] Successfully retrieved credentials from AWS SSM")
            return credentials_json
        except Exception as e:
            console.print(f"[red]Failed to retrieve credentials from AWS SSM parameter '{parameter_name}': {e}[/red]")
            raise