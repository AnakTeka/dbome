#!/usr/bin/env python3
"""
Main script for managing BigQuery views from SQL files
"""

import os
import sys
import yaml
import glob
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.auth import default
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import sqlglot
from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

console = Console()

class BigQueryViewManager:
    """Manages BigQuery views from SQL files using CREATE OR REPLACE VIEW syntax"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.client = self._initialize_client() if not self.config['deployment']['dry_run'] else None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            console.print(f"[red]Config file {config_path} not found![/red]")
            sys.exit(1)
        except yaml.YAMLError as e:
            console.print(f"[red]Error parsing config file: {e}[/red]")
            sys.exit(1)
    
    def _initialize_client(self) -> bigquery.Client:
        """Initialize BigQuery client"""
        try:
            # Set credentials if specified in config
            if 'google_application_credentials' in self.config:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config['google_application_credentials']
            
            project_id = self.config['bigquery']['project_id']
            location = self.config['bigquery'].get('location')
            
            client = bigquery.Client(project=project_id, location=location)
            console.print(f"[green]✓[/green] Connected to BigQuery project: {project_id}")
            return client
            
        except Exception as e:
            console.print(f"[red]Failed to initialize BigQuery client: {e}[/red]")
            sys.exit(1)
    
    def find_sql_files(self, specific_files: Optional[List[str]] = None) -> List[Path]:
        """Find SQL view files based on configuration or specific file list"""
        if specific_files:
            # Process only the specified files
            sql_files = []
            for file_path in specific_files:
                path = Path(file_path)
                if path.exists() and path.suffix.lower() == '.sql':
                    # Check if file is in views directory
                    try:
                        path.relative_to(self.config['sql']['views_directory'])
                        sql_files.append(path)
                    except ValueError:
                        console.print(f"[yellow]Warning: {file_path} is not in views directory, skipping[/yellow]")
                else:
                    console.print(f"[yellow]Warning: {file_path} does not exist or is not a SQL file, skipping[/yellow]")
            return sorted(sql_files)
        
        # Default behavior: find all SQL files
        views_directory = self.config['sql']['views_directory']
        
        if not os.path.exists(views_directory):
            console.print(f"[red]Views directory {views_directory} does not exist![/red]")
            return []
        
        sql_files = []
        for pattern in self.config['sql']['include_patterns']:
            search_pattern = os.path.join(views_directory, "**", pattern)
            files = glob.glob(search_pattern, recursive=True)
            sql_files.extend([Path(f) for f in files])
        
        # Filter out excluded patterns
        for exclude_pattern in self.config['sql']['exclude_patterns']:
            sql_files = [f for f in sql_files if not f.match(exclude_pattern)]
        
        return sorted(sql_files)
    
    def parse_sql_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse SQL file using SQLGlot and extract view information"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse with SQLGlot BigQuery dialect
            try:
                parsed = parse_one(content, dialect="bigquery")
            except ParseError as e:
                console.print(f"[red]SQLGlot parse error in {file_path}: {e}[/red]")
                return None
            
            if not parsed:
                console.print(f"[yellow]Warning: Could not parse {file_path}[/yellow]")
                return None
            
            # Check if it's a CREATE OR REPLACE VIEW statement
            if not (isinstance(parsed, exp.Create) and parsed.kind == "VIEW"):
                console.print(f"[yellow]Warning: {file_path} does not contain a CREATE OR REPLACE VIEW statement[/yellow]")
                return None
            
            # Extract view information from AST
            if not (parsed.this and isinstance(parsed.this, exp.Table)):
                console.print(f"[yellow]Warning: Could not extract table information from {file_path}[/yellow]")
                return None
                
            table = parsed.this
            
            # Extract view name and full name
            view_name = table.name if table.name else "unknown"
            full_name = table.sql(dialect="bigquery")
            
            # Extract project and dataset
            project_id = table.catalog if table.catalog else None
            dataset_id = table.db if table.db else None
            
            return {
                'name': view_name,
                'full_name': full_name,
                'project_id': project_id,
                'dataset_id': dataset_id,
                'path': file_path,
                'content': content.strip(),
                'parsed_ast': parsed
            }
            
        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")
            return None
    
    def execute_view_sql(self, sql_info: Dict[str, Any]) -> bool:
        """Execute the CREATE OR REPLACE VIEW SQL statement"""
        try:
            if self.config['deployment']['dry_run']:
                console.print(f"[blue]🔍 DRY RUN:[/blue] Would execute SQL for view {sql_info['name']}")
                console.print(f"[dim]  Project: {sql_info['project_id'] or 'default'}[/dim]")
                console.print(f"[dim]  Dataset: {sql_info['dataset_id'] or 'default'}[/dim]")
                console.print(f"[dim]  Full name: {sql_info['full_name']}[/dim]")
                if self.config['deployment']['verbose']:
                    # Format the SQL nicely for dry run output
                    formatted_sql = sql_info['parsed_ast'].sql(dialect="bigquery", pretty=True)
                    console.print(f"[dim]SQL:[/dim]\n{formatted_sql}")
                return True
            
            # Execute the SQL directly
            job = self.client.query(sql_info['content'])
            job.result()  # Wait for the job to complete
            
            console.print(f"[green]✓[/green] Created/updated view: {sql_info['name']}")
            return True
                    
        except Exception as e:
            console.print(f"[red]Failed to execute SQL for view {sql_info['name']}: {e}[/red]")
            return False
    
    def deploy_views(self, specific_files: Optional[List[str]] = None) -> None:
        """Deploy SQL view files to BigQuery"""
        mode_text = "🔍 DRY RUN -" if self.config['deployment']['dry_run'] else "🚀"
        file_source = f"({len(specific_files)} specific files)" if specific_files else "(all files)"
        
        console.print(f"\n[bold blue]{mode_text} Starting BigQuery View Deployment {file_source}[/bold blue]\n")
        
        sql_files = self.find_sql_files(specific_files)
        
        if not sql_files:
            if specific_files:
                console.print("[yellow]No valid SQL view files found in the specified file list[/yellow]")
            else:
                console.print("[yellow]No SQL view files found to deploy[/yellow]")
            return
        
        # Create a table to show files found
        table = Table(title="SQL View Files to Process")
        table.add_column("File", style="cyan")
        table.add_column("View Name", style="green")
        table.add_column("Full Name", style="magenta")
        table.add_column("Status", style="yellow")
        
        processed_files = []
        for file_path in sql_files:
            sql_info = self.parse_sql_file(file_path)
            if sql_info:
                processed_files.append(sql_info)
                table.add_row(
                    str(file_path), 
                    sql_info['name'], 
                    sql_info['full_name'],
                    "✓ Ready"
                )
            else:
                table.add_row(
                    str(file_path), 
                    "N/A", 
                    "N/A",
                    "❌ Parse Error"
                )
        
        console.print(table)
        console.print()
        
        if not processed_files:
            console.print("[yellow]No valid view files found (must contain CREATE OR REPLACE VIEW)[/yellow]")
            return
        
        # Deploy views
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Processing views...", total=len(processed_files))
            
            success_count = 0
            for sql_info in processed_files:
                action = "Dry-run checking" if self.config['deployment']['dry_run'] else "Deploying"
                progress.update(task, description=f"{action} {sql_info['name']}...")
                if self.execute_view_sql(sql_info):
                    success_count += 1
                progress.advance(task)
        
        result_text = "validated" if self.config['deployment']['dry_run'] else "deployed"
        console.print(f"\n[bold green]✅ Processing completed![/bold green]")
        console.print(f"Successfully {result_text} {success_count}/{len(processed_files)} views")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy SQL view files to BigQuery")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--files", nargs="+", help="Specific SQL files to process (instead of all files)")
    
    args = parser.parse_args()
    
    # Load and potentially modify config
    config_path = args.config
    temp_config = None
    
    if args.dry_run:
        import tempfile
        
        # Load config and modify dry_run setting
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        config['deployment']['dry_run'] = True
        
        # Write to temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            temp_config = f.name
        config_path = temp_config
    
    try:
        manager = BigQueryViewManager(config_path)
        manager.deploy_views(args.files)
    finally:
        # Clean up temporary config file if created
        if temp_config:
            os.unlink(temp_config)


if __name__ == "__main__":
    main() 