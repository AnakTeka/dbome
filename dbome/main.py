#!/usr/bin/env python3
"""
Main script for managing BigQuery views from SQL files
"""

import os
import re
import sys
import glob
import yaml
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from sqlglot import parse_one, ParseError
from sqlglot import expressions as exp
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .auth import AuthManager
from .exceptions import (
    DbomeError, ConfigError, AuthenticationError, 
    DeploymentError, ValidationError, FileSystemError, GitError
)
from .template_compiler import SQLTemplateCompiler
from .types import ViewInfo, DeploymentResult, ViewRegistration
from .project_init import init_project
from .deployment import DeploymentManager
from .config import Config, load_and_validate_config

console = Console()

class BigQueryViewManager:
    """Manages BigQuery views from SQL files using CREATE OR REPLACE VIEW syntax"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.auth_manager = AuthManager(self.config)
        self.client = self._get_client() if not self.config['deployment']['dry_run'] else None
        self.template_compiler = SQLTemplateCompiler(self.config)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from YAML file"""
        config = load_and_validate_config(config_path)
        # Convert Pydantic model to dict for backward compatibility
        return config.model_dump()
    
    def _get_client(self) -> bigquery.Client:
        """Get BigQuery client from auth manager."""
        try:
            return self.auth_manager.get_client()
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize BigQuery client: {e}")
    
    def find_sql_files(self, specific_files: Optional[List[str]] = None) -> List[Path]:
        """Find SQL view files based on configuration or specific file list"""
        if specific_files:
            # Process only the specified files
            sql_files = []
            views_directory = Path(self.config['sql']['views_directory'])
            
            for file_input in specific_files:
                found = False
                
                # Try different resolution strategies
                candidates = []
                
                # 1. Exact path as given
                candidates.append(Path(file_input))
                
                # 2. If it's just a name (no path separators), try in views directory
                if '/' not in file_input and '\\' not in file_input:
                    # Add .sql extension if missing
                    if not file_input.endswith('.sql'):
                        candidates.append(views_directory / f"{file_input}.sql")
                    candidates.append(views_directory / file_input)
                
                # 3. If it has .sql but no path, try in views directory
                elif file_input.endswith('.sql') and '/' not in file_input and '\\' not in file_input:
                    candidates.append(views_directory / file_input)
                
                # Try each candidate
                for candidate in candidates:
                    if candidate.exists() and candidate.suffix.lower() == '.sql':
                        # Check if file is in views directory or subdirectory
                        try:
                            candidate.relative_to(views_directory)
                            sql_files.append(candidate)
                            found = True
                            break
                        except ValueError:
                            # File exists but not in views directory, try full path
                            if candidate == Path(file_input):
                                sql_files.append(candidate)
                                found = True
                                break
                
                if not found:
                    console.print(f"[yellow]Warning: Could not find SQL file for '{file_input}', skipping[/yellow]")
                    console.print(f"[dim]  Tried: {[str(c) for c in candidates]}[/dim]")
            
            return sorted(sql_files)
        
        # Default behavior: find all SQL files
        views_directory = self.config['sql']['views_directory']
        
        if not os.path.exists(views_directory):
            raise FileSystemError(f"Views directory {views_directory} does not exist!")
        
        sql_files = []
        for pattern in self.config['sql']['include_patterns']:
            search_pattern = os.path.join(views_directory, "**", pattern)
            files = glob.glob(search_pattern, recursive=True)
            sql_files.extend([Path(f) for f in files])
        
        # Filter out excluded patterns
        for exclude_pattern in self.config['sql']['exclude_patterns']:
            sql_files = [f for f in sql_files if not f.match(exclude_pattern)]
        
        return sorted(sql_files)
    
    def _register_all_views(self, sql_files: List[Path]) -> None:
        """Register all views in the template compiler for ref() resolution"""
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    raw_content = f.read()
                
                view_name = file_path.stem
                
                # Check if SQL contains CREATE OR REPLACE VIEW
                has_create_view = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+', raw_content, re.IGNORECASE)
                
                if has_create_view:
                    # Extract view name from CREATE statement
                    create_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([`\'"]?[^`\'"]+[`\'"]?)', raw_content, re.IGNORECASE)
                    if create_match:
                        full_name = create_match.group(1)
                        self.template_compiler.register_view(view_name, full_name)
                else:
                    # Plain SELECT statement - use default naming
                    project_id = self.config['bigquery']['project_id']
                    dataset_id = self.config['bigquery']['dataset_id']
                    full_name = f"`{project_id}.{dataset_id}.{view_name}`"
                    self.template_compiler.register_view(view_name, full_name)
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Could not register view from {file_path}: {e}[/yellow]")
    
    def parse_sql_file(self, file_path: Path) -> Optional[ViewInfo]:
        """Parse SQL file using SQLGlot and extract view information"""
        try:
            with open(file_path, 'r') as f:
                raw_content = f.read()
            
            # Compile template (handles ref() functions and auto-wrapping)
            try:
                compiled_content = self.template_compiler.compile_sql(raw_content, file_path.stem, file_path, auto_wrap=True)
            except Exception as e:
                console.print(f"[red]Template compilation error in {file_path}: {e}[/red]")
                return None
            
            # Parse with SQLGlot BigQuery dialect
            try:
                parsed = parse_one(compiled_content, dialect="bigquery")
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
            
            # Register view in template compiler
            self.template_compiler.register_view(view_name, full_name)
            
            return {
                'name': view_name,
                'full_name': full_name,
                'project_id': project_id,
                'dataset_id': dataset_id,
                'path': file_path,
                'raw_content': raw_content.strip(),
                'compiled_content': compiled_content.strip(),
                'parsed_ast': parsed
            }
            
        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")
            return None
    
    def execute_view_sql(self, sql_info: ViewInfo) -> bool:
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
            
            # Execute the SQL directly (use compiled content)
            job = self.client.query(sql_info['compiled_content'])
            job.result()  # Wait for the job to complete
            
            console.print(f"[green]✓[/green] Created/updated view: {sql_info['name']}")
            return True
                    
        except Exception as e:
            console.print(f"[red]Failed to execute SQL for view {sql_info['name']}: {e}[/red]")
            if not self.config['deployment']['dry_run']:
                raise DeploymentError(f"Failed to execute SQL for view {sql_info['name']}: {e}")
            return False
    
    def deploy_views(self, specific_files: Optional[List[str]] = None) -> None:
        """Deploy SQL view files to BigQuery.
        
        Args:
            specific_files: Optional list of specific files to deploy
        """
        deployment_manager = DeploymentManager(self)
        deployment_manager.deploy_views(specific_files)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🏠 dbome (dbt at home) - BigQuery View Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dbome init                         Initialize project in current directory
  dbome init my-project              Initialize a new project directory
  dbome run                          Deploy all views
  dbome run --dry                    Preview what would be deployed
  dbome run user_metrics             Deploy specific view by name
  dbome run user_metrics.sql         Deploy specific view by filename
  dbome run user_metrics user_actions Deploy multiple views
  dbome run --select view1.sql       Deploy using --select flag
  dbome compile                      Compile templates to compiled/ directory
  dbome deps                         Show dependency graph
  dbome validate                     Validate all ref() references

For more help, visit: https://github.com/AnakTeka/dbome
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init subcommand
    init_parser = subparsers.add_parser('init', help='Initialize a new dbome project')
    init_parser.add_argument('project_name', nargs='?', help='Name of the project directory to create (optional - defaults to current directory)')
    init_parser.add_argument('--quiet', action='store_true', help='Suppress auto-deployment warnings (useful for scripted installations)')
    
    # Run subcommand
    run_parser = subparsers.add_parser('run', help='Deploy SQL views to BigQuery')
    run_parser.add_argument(
        "views", 
        nargs="*", 
        help="View names or files to deploy (e.g., user_metrics, user_metrics.sql)",
        metavar="VIEW"
    )
    run_parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to config file (default: config.yaml)",
        metavar="FILE"
    )
    run_parser.add_argument(
        "--dry", 
        action="store_true", 
        help="Show what would be done without executing (safe preview mode)"
    )
    run_parser.add_argument(
        "--select", 
        nargs="+", 
        help="Specific SQL files to process (alternative to positional args)",
        metavar="FILE"
    )
    
    # Compile subcommand
    compile_parser = subparsers.add_parser('compile', help='Compile SQL templates without deploying')
    compile_parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to config file (default: config.yaml)",
        metavar="FILE"
    )
    compile_parser.add_argument(
        "--select", 
        nargs="+", 
        help="Specific SQL files to compile (default: all files in views directory)",
        metavar="FILE"
    )
    
    # Deps subcommand
    deps_parser = subparsers.add_parser('deps', help='Show dependency graph and deployment order')
    deps_parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to config file (default: config.yaml)",
        metavar="FILE"
    )
    deps_parser.add_argument(
        "--select", 
        nargs="+", 
        help="Specific SQL files to analyze (default: all files in views directory)",
        metavar="FILE"
    )
    
    # Validate subcommand
    validate_parser = subparsers.add_parser('validate', help='Validate all ref() references')
    validate_parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to config file (default: config.yaml)",
        metavar="FILE"
    )
    validate_parser.add_argument(
        "--select", 
        nargs="+", 
        help="Specific SQL files to validate (default: all files in views directory)",
        metavar="FILE"
    )
    
    # Global arguments
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"dbome (dbt at home) {__version__}"
    )
    
    args = parser.parse_args()
    
    # If no command provided, show help
    if not args.command:
        parser.print_help()
        return
    
    # Handle init command
    if args.command == 'init':
        try:
            init_project(args.project_name, args.quiet)
        except (FileSystemError, GitError) as e:
            console.print(f"[red]Initialization error: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error during initialization: {e}[/red]")
            sys.exit(1)
        return
    
    # All other commands need a config file
    config_path = args.config
    temp_config = None
    
    # Handle dry run for run command
    if args.command == 'run' and args.dry:
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
        
        # Get selected files (combine positional args and --select)
        selected_files = getattr(args, 'select', None) or []
        if args.command == 'run' and hasattr(args, 'views') and args.views:
            selected_files = selected_files + args.views if selected_files else args.views
        
        if args.command == 'run':
            manager.deploy_views(selected_files if selected_files else None)
        
        elif args.command == 'compile':
            sql_files = manager.find_sql_files(selected_files)
            if not sql_files:
                console.print("[yellow]No SQL files found to compile[/yellow]")
                return
            
            console.print(f"\n[bold blue]📄 Compiling SQL Templates[/bold blue]\n")
            
            # Temporarily enable compiled output
            original_save_compiled = manager.config.get('deployment', {}).get('save_compiled', False)
            manager.config.setdefault('deployment', {})['save_compiled'] = True
            
            try:
                compiled_sqls = manager.template_compiler.compile_and_save_all(sql_files)
                
                if compiled_sqls:
                    console.print(f"[green]✅ Compiled {len(compiled_sqls)} SQL files[/green]")
                    compiled_dir = manager.config.get('sql', {}).get('compiled_directory', 'compiled/views')
                    console.print(f"[dim]  Output directory: {compiled_dir}[/dim]")
                else:
                    console.print("[yellow]No SQL files were compiled[/yellow]")
                    
            finally:
                # Restore original setting
                manager.config['deployment']['save_compiled'] = original_save_compiled
        
        elif args.command == 'deps':
            sql_files = manager.find_sql_files(selected_files)
            if not sql_files:
                console.print("[yellow]No SQL files found to analyze[/yellow]")
                return
            
            # For dependency analysis, consider all files for full graph but highlight selected ones
            all_sql_files = manager.find_sql_files() if selected_files else sql_files
            graph = manager.template_compiler.build_dependency_graph(all_sql_files)
            order = manager.template_compiler.get_deployment_order(sql_files, all_sql_files)
            
            # Show only the selected views in the graph if --select was used
            target_views = {f.stem for f in sql_files}
            
            console.print("[bold blue]Dependency Graph:[/bold blue]")
            for view, deps in graph.items():
                if view in target_views:  # Only show selected views
                    if deps:
                        console.print(f"  {view} → {', '.join(deps)}")
                    else:
                        console.print(f"  {view} (no dependencies)")
            
            console.print(f"\n[bold green]Deployment Order:[/bold green]")
            for i, view in enumerate(order, 1):
                console.print(f"  {i}. {view}")
        
        elif args.command == 'validate':
            sql_files = manager.find_sql_files(selected_files)
            if not sql_files:
                console.print("[yellow]No SQL files found to validate[/yellow]")
                return
            
            # For validation, always check against all available views
            all_sql_files = manager.find_sql_files() if selected_files else sql_files
            errors = manager.template_compiler.validate_references(sql_files, all_sql_files)
            if errors:
                console.print("[red]Validation errors found:[/red]")
                for error in errors:
                    console.print(f"  ❌ {error}")
                sys.exit(1)
            else:
                console.print("[green]✅ All references are valid[/green]")
    
    except ConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except AuthenticationError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        sys.exit(1)
    except ValidationError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        sys.exit(1)
    except DeploymentError as e:
        console.print(f"[red]Deployment failed: {e}[/red]")
        sys.exit(1)
    except DbomeError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if "--debug" in sys.argv:
            console.print_exception()
        sys.exit(1)
    finally:
        # Clean up temporary config file if created
        if temp_config:
            os.unlink(temp_config)


if __name__ == "__main__":
    main() 