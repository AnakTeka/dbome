"""
SQL Template Compiler with Jinja2 support

Provides dbt-like ref() functionality for dbome
"""

import re
import os
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
from rich.console import Console

console = Console()

class SQLTemplateCompiler:
    """Compiles SQL templates with dbt-like ref() functionality"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.view_registry = {}  # view_name -> full_reference mapping
        self.dependency_graph = {}  # view_name -> [dependencies]
        self.jinja_env = Environment(loader=BaseLoader())
        
        # Set up custom functions for Jinja2
        self.jinja_env.globals['ref'] = self._ref_function
        
    def _ref_function(self, view_name: str, project: Optional[str] = None) -> str:
        """
        Jinja2 ref() function that resolves view references
        
        Args:
            view_name: Name of the view to reference
            project: Optional project override
            
        Returns:
            Full BigQuery reference string
        """
        # If explicit project provided, use it
        if project:
            dataset = self.config.get('bigquery', {}).get('dataset_id', 'analytics')
            return f"`{project}.{dataset}.{view_name}`"
        
        # Check if view exists in registry
        if view_name in self.view_registry:
            return self.view_registry[view_name]
        
        # Default resolution
        default_project = self.config.get('bigquery', {}).get('project_id', 'your-project')
        default_dataset = self.config.get('bigquery', {}).get('dataset_id', 'analytics')
        
        full_ref = f"`{default_project}.{default_dataset}.{view_name}`"
        console.print(f"[yellow]Warning: Referenced view '{view_name}' not found in registry, using default: {full_ref}[/yellow]")
        
        return full_ref
    
    def register_view(self, view_name: str, full_reference: str) -> None:
        """Register a view in the registry for ref() resolution"""
        self.view_registry[view_name] = full_reference
        
    def extract_references(self, sql_content: str) -> List[str]:
        """Extract all ref() calls from SQL content"""
        # Find all {{ ref('view_name') }} patterns
        ref_pattern = r'{{\s*ref\([\'"]([^\'\"]+)[\'"]\)\s*}}'
        matches = re.findall(ref_pattern, sql_content)
        return matches
    
    def compile_sql(self, sql_content: str, view_name: str, source_file: Optional[Path] = None, auto_wrap: bool = True) -> str:
        """
        Compile SQL template using Jinja2
        
        Args:
            sql_content: Raw SQL content with template syntax
            view_name: Name of the view being compiled (for error reporting)
            source_file: Path to source file (for saving compiled output)
            auto_wrap: Whether to auto-wrap with CREATE OR REPLACE VIEW if needed
            
        Returns:
            Compiled SQL content
        """
        try:
            template = self.jinja_env.from_string(sql_content)
            compiled_sql = template.render()
            
            # Check if auto-wrapping is needed
            if auto_wrap and not re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+', compiled_sql, re.IGNORECASE):
                # Auto-wrap with CREATE OR REPLACE VIEW using filename as view name
                project_id = self.config['bigquery']['project_id']
                dataset_id = self.config['bigquery']['dataset_id']
                
                # Create the full view name
                full_name = f"`{project_id}.{dataset_id}.{view_name}`"
                
                # Wrap the SQL with CREATE OR REPLACE VIEW
                compiled_sql = f"CREATE OR REPLACE VIEW {full_name} AS\n{compiled_sql}"
            
            # Save compiled SQL if enabled and source file provided
            if (source_file and 
                self.config.get('deployment', {}).get('save_compiled', False) and
                self.config.get('sql', {}).get('compiled_directory')):
                self._save_compiled_sql(compiled_sql, source_file)
            
            return compiled_sql
            
        except TemplateSyntaxError as e:
            console.print(f"[red]Template syntax error in {view_name}: {e}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Error compiling template for {view_name}: {e}[/red]")
            raise
    
    def _save_compiled_sql(self, compiled_sql: str, source_file: Path) -> None:
        """
        Save compiled SQL to the compiled directory
        
        Args:
            compiled_sql: The compiled SQL content
            source_file: The original source file path
        """
        try:
            compiled_dir = Path(self.config['sql']['compiled_directory'])
            views_dir = Path(self.config['sql']['views_directory'])
            
            # Calculate relative path from views directory
            try:
                relative_path = source_file.relative_to(views_dir)
            except ValueError:
                # If file is not in views directory, use just the filename
                relative_path = source_file.name
            
            # Create output path in compiled directory
            output_path = compiled_dir / relative_path
            
            # Create parent directories if they don't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add header comment to compiled file
            header = f"""-- Compiled SQL from: {source_file}
-- Generated by dbome (dbt at home)
-- DO NOT EDIT: This file is auto-generated

"""
            
            # Write compiled SQL
            with open(output_path, 'w') as f:
                f.write(header + compiled_sql)
            
            console.print(f"[dim]  📄 Saved compiled SQL: {output_path}[/dim]")
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save compiled SQL for {source_file}: {e}[/yellow]")
    
    def compile_and_save_all(self, sql_files: List[Path]) -> Dict[str, str]:
        """
        Compile all SQL files and optionally save compiled versions
        
        Args:
            sql_files: List of SQL file paths to compile
            
        Returns:
            Dictionary mapping view names to compiled SQL content
        """
        compiled_sqls = {}
        
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    raw_content = f.read()
                
                view_name = file_path.stem
                compiled_sql = self.compile_sql(raw_content, view_name, file_path)
                compiled_sqls[view_name] = compiled_sql
                
            except Exception as e:
                console.print(f"[red]Error compiling {file_path}: {e}[/red]")
                continue
        
        return compiled_sqls
    
    def build_dependency_graph(self, sql_files: List[Path]) -> Dict[str, List[str]]:
        """
        Build dependency graph from SQL files
        
        Args:
            sql_files: List of SQL file paths
            
        Returns:
            Dictionary mapping view names to their dependencies
        """
        graph = {}
        
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                view_name = file_path.stem
                dependencies = self.extract_references(content)
                graph[view_name] = dependencies
                
            except Exception as e:
                console.print(f"[red]Error reading {file_path}: {e}[/red]")
                continue
        
        self.dependency_graph = graph
        return graph
    
    def topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Perform topological sort to determine deployment order
        
        Args:
            graph: Dependency graph (node -> [dependencies])
            
        Returns:
            List of view names in deployment order
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        # For deployment order, we need to process nodes with no dependencies first
        # Create a copy of the graph to avoid modifying the original
        remaining = graph.copy()
        result = []
        
        while remaining:
            # Find nodes with no dependencies
            ready_nodes = [node for node, deps in remaining.items() if not deps]
            
            if not ready_nodes:
                # No nodes without dependencies - circular dependency
                raise ValueError(f"Circular dependencies detected involving: {list(remaining.keys())}")
            
            # Process nodes with no dependencies
            for node in ready_nodes:
                result.append(node)
                del remaining[node]
                
                # Remove this node from other nodes' dependencies
                for other_node in remaining:
                    if node in remaining[other_node]:
                        remaining[other_node].remove(node)
        
        return result
    
    def get_deployment_order(self, sql_files: List[Path]) -> List[str]:
        """
        Get the correct deployment order based on dependencies
        
        Args:
            sql_files: List of SQL file paths
            
        Returns:
            List of view names in deployment order
        """
        graph = self.build_dependency_graph(sql_files)
        
        if not graph:
            return [f.stem for f in sql_files]
        
        try:
            return self.topological_sort(graph)
        except ValueError as e:
            console.print(f"[red]Dependency error: {e}[/red]")
            # Fallback to original order
            return [f.stem for f in sql_files]
    
    def validate_references(self, sql_files: List[Path]) -> List[str]:
        """
        Validate that all ref() calls reference existing views
        
        Args:
            sql_files: List of SQL file paths
            
        Returns:
            List of validation errors
        """
        errors = []
        available_views = {f.stem for f in sql_files}
        
        for file_path in sql_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                view_name = file_path.stem
                references = self.extract_references(content)
                
                for ref in references:
                    if ref not in available_views:
                        errors.append(f"View '{view_name}' references unknown view '{ref}'")
                        
            except Exception as e:
                errors.append(f"Error reading {file_path}: {e}")
        
        return errors 