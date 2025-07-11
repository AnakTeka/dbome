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
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from sqlglot import parse_one, ParseError
from sqlglot import expressions as exp
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .template_compiler import SQLTemplateCompiler

console = Console()

class BigQueryViewManager:
    """Manages BigQuery views from SQL files using CREATE OR REPLACE VIEW syntax"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.client = self._initialize_client() if not self.config['deployment']['dry_run'] else None
        self.template_compiler = SQLTemplateCompiler(self.config)
        
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
            
            # Execute the SQL directly (use compiled content)
            job = self.client.query(sql_info['compiled_content'])
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
        
        # Get deployment order based on dependencies
        deployment_order = self.template_compiler.get_deployment_order(sql_files)
        
        # Validate all references
        validation_errors = self.template_compiler.validate_references(sql_files)
        if validation_errors:
            console.print("[red]Template validation errors found:[/red]")
            for error in validation_errors:
                console.print(f"  ❌ {error}")
            return
        
        # Create a table to show files found
        table = Table(title="SQL View Files to Process")
        table.add_column("File", style="cyan")
        table.add_column("View Name", style="green")
        table.add_column("Full Name", style="magenta")
        table.add_column("Status", style="yellow")
        
        # First pass: Parse all files and register views (without compilation)
        file_map = {f.stem: f for f in sql_files}
        all_sql_info = {}
        
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    raw_content = f.read()
                
                # Check if this is a template file (contains {{ }})
                has_template_syntax = '{{' in raw_content and '}}' in raw_content
                
                # Check if SQL contains CREATE OR REPLACE VIEW
                has_create_view = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+', raw_content, re.IGNORECASE)
                
                if has_create_view:
                    # SQL already has CREATE OR REPLACE VIEW - extract view name from it
                    create_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([`\'"]?[^`\'"]+[`\'"]?)', raw_content, re.IGNORECASE)
                    if create_match:
                        full_name = create_match.group(1).strip('`\'"')
                        view_name = file_path.stem  # Use filename as view name
                        
                        # Register view for ref() resolution (use full name from CREATE statement)
                        self.template_compiler.register_view(view_name, create_match.group(1))
                        
                        all_sql_info[view_name] = {
                            'path': file_path,
                            'raw_content': raw_content,
                            'view_name': view_name,
                            'full_name': create_match.group(1),
                            'project_id': None,  # Will be extracted during compilation
                            'dataset_id': None,  # Will be extracted during compilation
                        }
                else:
                    # Plain SELECT statement - use filename as view name
                    view_name = file_path.stem
                    project_id = self.config['bigquery']['project_id']
                    dataset_id = self.config['bigquery']['dataset_id']
                    full_name = f"`{project_id}.{dataset_id}.{view_name}`"
                    
                    # Register view for ref() resolution
                    self.template_compiler.register_view(view_name, full_name)
                    
                    all_sql_info[view_name] = {
                        'path': file_path,
                        'raw_content': raw_content,
                        'view_name': view_name,
                        'full_name': full_name,
                        'project_id': project_id,
                        'dataset_id': dataset_id,
                    }
                    
            except Exception as e:
                console.print(f"[red]Error reading {file_path}: {e}[/red]")
        
        # Second pass: Process files in dependency order with compilation
        processed_files = []
        
        for view_name in deployment_order:
            if view_name in all_sql_info:
                info = all_sql_info[view_name]
                sql_info = self.parse_sql_file(info['path'])
                if sql_info:
                    processed_files.append(sql_info)
                    table.add_row(
                        str(info['path']), 
                        sql_info['name'], 
                        sql_info['full_name'],
                        "✓ Ready"
                    )
                else:
                    table.add_row(
                        str(info['path']), 
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


def init_project(project_name: str) -> None:
    """Initialize a new dbome project"""
    project_path = Path(project_name)
    
    if project_path.exists():
        console.print(f"[red]Error: Directory '{project_name}' already exists![/red]")
        sys.exit(1)
    
    console.print(f"[bold blue]🏠 Initializing dbome (dbt at home) project: {project_name}[/bold blue]\n")
    
    try:
        # Create project directory
        project_path.mkdir(parents=True)
        console.print(f"[green]📁 Created directory: {project_path}[/green]")
        
        # Get templates directory
        templates_dir = Path(__file__).parent / "templates"
        
        if not templates_dir.exists():
            console.print(f"[red]Error: Templates directory not found at {templates_dir}[/red]")
            sys.exit(1)
        
        # Copy template files
        files_to_copy = [
            ("config.yaml.template", "config.yaml.template"),
            ("setup.sh", "setup.sh"),
            ("Makefile", "Makefile"),
            (".gitignore.template", ".gitignore"),
            ("post-commit", ".git/hooks/post-commit"),
        ]
        
        for src_name, dst_name in files_to_copy:
            src_path = templates_dir / src_name
            dst_path = project_path / dst_name
            
            if src_path.exists():
                # Create parent directory if needed (e.g., .git/hooks/)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                
                # Make post-commit hook executable
                if dst_name.endswith("post-commit"):
                    os.chmod(dst_path, 0o755)
                    console.print(f"[green]🔗 Installed git hook: {dst_name}[/green]")
                else:
                    console.print(f"[green]📄 Created: {dst_name}[/green]")
        
        # Copy SQL directory structure
        sql_src = templates_dir / "sql"
        sql_dst = project_path / "sql"
        if sql_src.exists():
            shutil.copytree(sql_src, sql_dst)
            console.print(f"[green]📁 Created SQL directory with examples[/green]")
        
        # Create README from template
        readme_template = templates_dir / "README.md.template"
        readme_dst = project_path / "README.md"
        if readme_template.exists():
            with open(readme_template, 'r') as f:
                content = f.read()
            # Replace project name placeholder
            content = content.replace("{PROJECT_NAME}", project_name)
            with open(readme_dst, 'w') as f:
                f.write(content)
            console.print(f"[green]📚 Created README.md[/green]")
        
        # Initialize git repository
        os.chdir(project_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        console.print(f"[green]🔄 Initialized git repository[/green]")
        
        # Configure git user if not set (for initial commit)
        try:
            subprocess.run(["git", "config", "user.name"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "config", "user.name", "dbome"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "dbome@example.com"], check=True, capture_output=True)
        
        # Create initial commit
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit: dbome (dbt at home) project"], 
                      check=True, capture_output=True)
        console.print(f"[green]✅ Created initial commit[/green]")
        
        console.print(f"\n[bold green]🎉 Project '{project_name}' initialized successfully![/bold green]")
        console.print(f"\n[bold blue]Next steps:[/bold blue]")
        console.print(f"1. [cyan]cd {project_name}[/cyan]")
        console.print(f"2. [cyan]cp config.yaml.template config.yaml[/cyan]")
        console.print(f"3. Edit config.yaml with your BigQuery project details")
        console.print(f"4. [cyan]gcloud auth application-default login[/cyan]")
        console.print(f"5. [cyan]bq-view-deploy --dry-run[/cyan]")
        console.print(f"\n[dim]For more help, see README.md in your new project![/dim]")
        console.print(f"\n[bold blue]Welcome to dbome - dbt at home! 🏠[/bold blue]")
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running git command: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error initializing project: {e}[/red]")
        # Clean up on error
        if project_path.exists():
            shutil.rmtree(project_path)
        sys.exit(1)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🏠 dbome (dbt at home) - BigQuery View Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dbome init my-project              Initialize a new project
  bq-view-deploy                     Deploy all views
  bq-view-deploy --dry-run           Preview what would be deployed
  bq-view-deploy --files view1.sql   Deploy specific files only
  bq-view-deploy --validate-refs     Validate all ref() references
  bq-view-deploy --show-deps         Show dependency graph
  bq-view-deploy --compile-only      Compile templates to compiled/ directory
  bq-view-deploy --config prod.yaml  Use different config file

For more help, visit: https://github.com/your-repo/dbome
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init subcommand
    init_parser = subparsers.add_parser('init', help='Initialize a new dbome project')
    init_parser.add_argument('project_name', help='Name of the project directory to create')
    
    # If no subcommand provided, treat as deployment command (backwards compatibility)
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"dbome (dbt at home) {__version__}"
    )
    parser.add_argument(
        "--config", 
        default="config.yaml", 
        help="Path to config file (default: config.yaml)",
        metavar="FILE"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without executing (safe preview mode)"
    )
    parser.add_argument(
        "--files", 
        nargs="+", 
        help="Specific SQL files to process (default: all files in views directory)",
        metavar="FILE"
    )
    parser.add_argument(
        "--validate-refs", 
        action="store_true", 
        help="Validate all ref() references and exit"
    )
    parser.add_argument(
        "--show-deps", 
        action="store_true", 
        help="Show dependency graph and deployment order"
    )
    parser.add_argument(
        "--compile-only", 
        action="store_true", 
        help="Compile SQL templates without deploying (saves to compiled directory)"
    )
    
    args = parser.parse_args()
    
    # Handle init command
    if args.command == 'init':
        init_project(args.project_name)
        return
    
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
        
        # Handle validation, dependency, and compilation options
        if args.validate_refs or args.show_deps or args.compile_only:
            sql_files = manager.find_sql_files(args.files)
            if not sql_files:
                console.print("[yellow]No SQL files found to analyze[/yellow]")
                return
            
            if args.validate_refs:
                errors = manager.template_compiler.validate_references(sql_files)
                if errors:
                    console.print("[red]Validation errors found:[/red]")
                    for error in errors:
                        console.print(f"  ❌ {error}")
                    sys.exit(1)
                else:
                    console.print("[green]✅ All references are valid[/green]")
            
            if args.show_deps:
                graph = manager.template_compiler.build_dependency_graph(sql_files)
                order = manager.template_compiler.get_deployment_order(sql_files)
                
                console.print("[bold blue]Dependency Graph:[/bold blue]")
                for view, deps in graph.items():
                    if deps:
                        console.print(f"  {view} → {', '.join(deps)}")
                    else:
                        console.print(f"  {view} (no dependencies)")
                
                console.print(f"\n[bold green]Deployment Order:[/bold green]")
                for i, view in enumerate(order, 1):
                    console.print(f"  {i}. {view}")
            
            if args.compile_only:
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
            
            return
        
        # Normal deployment
        manager.deploy_views(args.files)
    finally:
        # Clean up temporary config file if created
        if temp_config:
            os.unlink(temp_config)


if __name__ == "__main__":
    main() 