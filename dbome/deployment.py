"""Deployment logic for BigQuery views."""

from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.table import Table

from .exceptions import ValidationError, DeploymentError
from .types import ViewInfo, DeploymentResult, ViewRegistration

console = Console()


class DeploymentManager:
    """Manages the deployment of SQL views to BigQuery."""
    
    def __init__(self, view_manager):
        """Initialize deployment manager.
        
        Args:
            view_manager: Instance of BigQueryViewManager
        """
        self.view_manager = view_manager
        self.config = view_manager.config
        self.template_compiler = view_manager.template_compiler
    
    def deploy_views(self, specific_files: Optional[List[str]] = None) -> None:
        """Deploy SQL view files to BigQuery.
        
        Args:
            specific_files: Optional list of specific files to deploy
        """
        sql_files = self._prepare_deployment(specific_files)
        if not sql_files:
            return
        
        # Pre-register views for dependency resolution
        self._register_all_views(sql_files, specific_files)
        
        # Validate and get deployment plan
        deployment_plan = self._create_deployment_plan(sql_files, specific_files)
        if not deployment_plan:
            return
        
        # Execute deployment
        results = self._execute_deployment(deployment_plan)
        
        # Report results
        self._report_results(results, len(deployment_plan))
    
    def _prepare_deployment(self, specific_files: Optional[List[str]] = None) -> List[Path]:
        """Prepare for deployment by finding SQL files.
        
        Args:
            specific_files: Optional list of specific files
            
        Returns:
            List of SQL file paths
        """
        mode_text = "🔍 DRY RUN -" if self.config['deployment']['dry_run'] else "🚀"
        file_source = f"({len(specific_files)} specific files)" if specific_files else "(all files)"
        
        console.print(f"\n[bold blue]{mode_text} Starting BigQuery View Deployment {file_source}[/bold blue]\n")
        
        sql_files = self.view_manager.find_sql_files(specific_files)
        
        if not sql_files:
            if specific_files:
                console.print("[yellow]No valid SQL view files found in the specified file list[/yellow]")
            else:
                console.print("[yellow]No SQL view files found to deploy[/yellow]")
            return []
        
        return sql_files
    
    def _register_all_views(self, sql_files: List[Path], specific_files: Optional[List[str]]) -> None:
        """Register all views for dependency resolution.
        
        Args:
            sql_files: List of SQL files to deploy
            specific_files: Whether specific files were requested
        """
        # For selected files, we need to register ALL views for ref() resolution
        if specific_files:
            all_sql_files = self.view_manager.find_sql_files()
            self.view_manager._register_all_views(all_sql_files)
        else:
            self.view_manager._register_all_views(sql_files)
    
    def _create_deployment_plan(self, sql_files: List[Path], specific_files: Optional[List[str]]) -> List[ViewInfo]:
        """Create deployment plan with dependency resolution.
        
        Args:
            sql_files: List of SQL files to deploy
            specific_files: Whether specific files were requested
            
        Returns:
            List of ViewInfo objects in deployment order
        """
        # Get deployment order
        if specific_files:
            all_sql_files = self.view_manager.find_sql_files()
            deployment_order = self.template_compiler.get_deployment_order(sql_files, all_sql_files)
        else:
            deployment_order = self.template_compiler.get_deployment_order(sql_files)
            all_sql_files = sql_files
        
        # Validate references
        validation_errors = self.template_compiler.validate_references(sql_files, all_sql_files)
        if validation_errors:
            console.print("[red]Template validation errors found:[/red]")
            for error in validation_errors:
                console.print(f"  ❌ {error}")
            return []
        
        # Parse and prepare views
        processed_files = self._parse_sql_files(sql_files, deployment_order)
        
        if not processed_files:
            console.print("[yellow]No valid view files found (must contain CREATE OR REPLACE VIEW)[/yellow]")
            return []
        
        return processed_files
    
    def _parse_sql_files(self, sql_files: List[Path], deployment_order: List[str]) -> List[ViewInfo]:
        """Parse SQL files and create deployment plan.
        
        Args:
            sql_files: List of SQL files
            deployment_order: Order of deployment
            
        Returns:
            List of parsed ViewInfo objects
        """
        # First pass: Register all views
        file_map = {f.stem: f for f in sql_files}
        all_sql_info = self._collect_view_info(sql_files)
        
        # Second pass: Process files in dependency order
        processed_files = []
        
        # Create table to show files found
        table = Table(title="SQL View Files to Process")
        table.add_column("File", style="cyan")
        table.add_column("View Name", style="green") 
        table.add_column("Full Name", style="magenta")
        table.add_column("Status", style="yellow")
        
        for view_name in deployment_order:
            if view_name in all_sql_info:
                info = all_sql_info[view_name]
                sql_info = self.view_manager.parse_sql_file(info['path'])
                if sql_info:
                    processed_files.append(sql_info)
                    table.add_row(
                        str(info['path']), 
                        sql_info['name'], 
                        sql_info['full_name'],
                        "✓ Valid"
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
        
        return processed_files
    
    def _collect_view_info(self, sql_files: List[Path]) -> Dict[str, ViewRegistration]:
        """Collect basic view information from SQL files.
        
        Args:
            sql_files: List of SQL files
            
        Returns:
            Dictionary mapping view names to registration info
        """
        import re
        
        all_sql_info = {}
        
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    raw_content = f.read()
                
                # Check if SQL contains CREATE OR REPLACE VIEW
                has_create_view = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+', raw_content, re.IGNORECASE)
                
                if has_create_view:
                    # Extract view name from CREATE statement
                    create_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([`\'"]?[^`\'"]+[`\'"]?)', raw_content, re.IGNORECASE)
                    if create_match:
                        full_name = create_match.group(1).strip('`\'"')
                        view_name = file_path.stem
                        
                        # Register view for ref() resolution
                        self.template_compiler.register_view(view_name, create_match.group(1))
                        
                        all_sql_info[view_name] = {
                            'path': file_path,
                            'raw_content': raw_content,
                            'view_name': view_name,
                            'full_name': create_match.group(1),
                            'project_id': None,
                            'dataset_id': None,
                        }
                else:
                    # Plain SELECT statement
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
        
        return all_sql_info
    
    def _execute_deployment(self, deployment_plan: List[ViewInfo]) -> List[DeploymentResult]:
        """Execute the deployment plan.
        
        Args:
            deployment_plan: List of views to deploy
            
        Returns:
            List of deployment results
        """
        deployment_results = []
        success_count = 0
        
        for i, sql_info in enumerate(deployment_plan, 1):
            action = "Dry-run checking" if self.config['deployment']['dry_run'] else "Deploying"
            
            # Show progress message first
            console.print(f"[{i}/{len(deployment_plan)}] {action} {sql_info['name']}...")
            
            # Then execute (any errors will appear after the progress message)
            success = self.view_manager.execute_view_sql(sql_info)
            if success:
                success_count += 1
            
            # Track result for results table
            deployment_results.append({
                'view_name': sql_info['name'],
                'full_name': sql_info['full_name'],
                'success': success
            })
        
        return deployment_results
    
    def _report_results(self, results: List[DeploymentResult], total_files: int) -> None:
        """Report deployment results to user.
        
        Args:
            results: List of deployment results
            total_files: Total number of files processed
        """
        # Create results table
        results_table = Table(title="Deployment Results")
        results_table.add_column("View Name", style="green")
        results_table.add_column("Full Name", style="magenta")
        results_table.add_column("Result", style="bold")
        
        success_count = 0
        for result in results:
            if result['success']:
                success_count += 1
            status = "✅ Success" if result['success'] else "❌ Failed"
            status_style = "green" if result['success'] else "red"
            results_table.add_row(
                result['view_name'],
                result['full_name'],
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        console.print()
        console.print(results_table)
        
        result_text = "validated" if self.config['deployment']['dry_run'] else "deployed"
        
        # Status-aware completion messages based on success rate
        if success_count == total_files:
            # All succeeded
            console.print(f"\n[bold green]✅ Processing completed successfully![/bold green]")
            console.print(f"[green]Successfully {result_text} all {total_files} views[/green]")
        elif success_count > 0:
            # Partial success
            console.print(f"\n[bold yellow]⚠️  Processing completed with errors[/bold yellow]")
            console.print(f"[yellow]Successfully {result_text} {success_count}/{total_files} views[/yellow]")
            console.print(f"[red]{total_files - success_count} views failed[/red]")
        else:
            # All failed
            console.print(f"\n[bold red]❌ Processing failed[/bold red]")
            console.print(f"[red]Failed to {result_text.rstrip('d')} any views ({success_count}/{total_files})[/red]")
            console.print(f"[dim]Check the error messages above for details[/dim]")
            
            # Exit with error code when all views fail (unless dry run)
            if not self.config['deployment']['dry_run']:
                raise DeploymentError(f"All views failed to deploy")