"""Project initialization utilities for dbome."""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

from .exceptions import FileSystemError, GitError

console = Console()


def init_project(project_name: Optional[str] = None, quiet: bool = False) -> None:
    """Initialize a new dbome project.
    
    Args:
        project_name: Name of the project directory to create (optional)
        quiet: Suppress auto-deployment warnings
    """
    project_path = _setup_project_directory(project_name)
    
    try:
        templates_dir = _get_templates_directory()
        
        # Check if we're in an existing git repository
        is_existing_git_repo = _is_git_repository(project_path)
        
        _copy_template_files(templates_dir, project_path, skip_git_hook=is_existing_git_repo)
        _copy_sql_examples(templates_dir, project_path)
        _create_readme(templates_dir, project_path, project_name or project_path.name)
        
        # Initialize git repository if not already in one
        if not is_existing_git_repo:
            _initialize_git_repository(project_path)
        
        console.print(f"\n[bold green]🎉 Project '{project_name or project_path.name}' initialized successfully![/bold green]")
        
        if not quiet:
            _show_auto_deployment_warning(skip_git_hook=is_existing_git_repo)
            _show_next_steps(project_path)
    
    except Exception as e:
        _cleanup_on_error(project_path, e)


def _setup_project_directory(project_name: Optional[str]) -> Path:
    """Set up the project directory (new or current).
    
    Args:
        project_name: Name of the project directory
        
    Returns:
        Path to the project directory
        
    Raises:
        FileSystemError: If directory already exists or current dir is already a project
    """
    if project_name:
        # Initialize in a new directory
        project_path = Path(project_name)
        
        if project_path.exists():
            raise FileSystemError(f"Directory '{project_name}' already exists!")
        
        console.print(f"[bold blue]🏠 Initializing dbome (dbt at home) project: {project_name}[/bold blue]\n")
        
        # Create project directory
        project_path.mkdir(parents=True)
        console.print(f"[green]📁 Created directory: {project_path}[/green]")
    else:
        # Initialize in current directory
        project_path = Path.cwd()
        project_name = project_path.name
        
        # Check if current directory already has dbome files
        if (project_path / "config.yaml").exists() or (project_path / "config.yaml.template").exists():
            raise FileSystemError("Current directory already appears to be a dbome project!")
        
        console.print(f"[bold blue]🏠 Initializing dbome (dbt at home) project in current directory: {project_name}[/bold blue]\n")
    
    return project_path


def _get_templates_directory() -> Path:
    """Get the templates directory path.
    
    Returns:
        Path to templates directory
        
    Raises:
        FileSystemError: If templates directory not found
    """
    templates_dir = Path(__file__).parent / "templates"
    
    if not templates_dir.exists():
        raise FileSystemError(f"Templates directory not found at {templates_dir}")
    
    return templates_dir


def _is_git_repository(path: Path) -> bool:
    """Check if the given path is inside a git repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if inside a git repository, False otherwise
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(path)
        subprocess.run(["git", "rev-parse", "--git-dir"], check=True, capture_output=True)
        os.chdir(original_cwd)
        return True
    except subprocess.CalledProcessError:
        os.chdir(original_cwd)
        return False
    except Exception:
        return False


def _copy_template_files(templates_dir: Path, project_path: Path, skip_git_hook: bool = False) -> None:
    """Copy template files to the project directory.
    
    Args:
        templates_dir: Source templates directory
        project_path: Destination project directory
        skip_git_hook: Whether to skip installing the git hook
    """
    files_to_copy = [
        ("config.yaml.template", "config.yaml.template"),
        ("setup.sh", "setup.sh"),
        (".gitignore.template", ".gitignore"),
    ]
    
    # Add git hook only if not skipping
    if not skip_git_hook:
        files_to_copy.append(("post-commit", ".git/hooks/post-commit"))
    
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
    
    # If we skipped the git hook, inform the user
    if skip_git_hook:
        console.print(f"[yellow]⚠️  Existing git repository detected - skipping auto-deployment hook[/yellow]")
        console.print(f"[yellow]    To enable auto-deployment, manually copy the post-commit hook:[/yellow]")
        console.print(f"[dim]    cp {templates_dir}/post-commit .git/hooks/post-commit[/dim]")
        console.print(f"[dim]    chmod +x .git/hooks/post-commit[/dim]")


def _copy_sql_examples(templates_dir: Path, project_path: Path) -> None:
    """Copy SQL example files to the project.
    
    Args:
        templates_dir: Source templates directory
        project_path: Destination project directory
    """
    sql_src = templates_dir / "sql"
    sql_dst = project_path / "sql"
    
    if sql_src.exists():
        shutil.copytree(sql_src, sql_dst)
        console.print(f"[green]📁 Created SQL directory with examples[/green]")


def _create_readme(templates_dir: Path, project_path: Path, project_name: str) -> None:
    """Create README.md from template.
    
    Args:
        templates_dir: Source templates directory
        project_path: Destination project directory
        project_name: Name of the project
    """
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


def _initialize_git_repository(project_path: Path) -> None:
    """Initialize git repository with initial commit.
    
    Args:
        project_path: Project directory path
        
    Raises:
        GitError: If git operations fail
    """
    original_cwd = os.getcwd()
    try:
        if project_path != Path.cwd():
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
        
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: {e}")
    finally:
        os.chdir(original_cwd)


def _show_auto_deployment_warning(skip_git_hook: bool = False) -> None:
    """Show warning about auto-deployment feature.
    
    Args:
        skip_git_hook: Whether the git hook was skipped
    """
    if skip_git_hook:
        # Show message for existing git repositories
        console.print(f"\n[bold yellow]⚠️  Auto-Deployment Hook Not Installed[/bold yellow]")
        console.print("─" * 60)
        console.print(f"[yellow]Existing git repository detected - auto-deployment hook was skipped[/yellow]")
        console.print()
        console.print(f"[blue]💡 TO ENABLE AUTO-DEPLOYMENT:[/blue]")
        console.print(f"   Copy the post-commit hook manually:")
        console.print(f"   [cyan]cp templates/post-commit .git/hooks/post-commit[/cyan]")
        console.print(f"   [cyan]chmod +x .git/hooks/post-commit[/cyan]")
        console.print()
        console.print(f"[dim]This will enable automatic deployment to BigQuery after each commit[/dim]")
    else:
        # Show message for new git repositories
        console.print(f"\n[bold red]⚡ IMPORTANT: Auto-Deployment Feature Enabled![/bold red]")
        console.print("─" * 60)
        console.print(f"[yellow]🔗 Git Hook Installed:[/yellow] [bold].git/hooks/post-commit[/bold]")
        console.print()
        console.print(f"[green]✅ WHAT THIS MEANS:[/green]")
        console.print(f"   • When you commit SQL files, they will be [bold]automatically deployed[/bold] to BigQuery")
        console.print(f"   • This happens [bold]immediately after each commit[/bold] - no manual deployment needed!")
        console.print(f"   • Only changed SQL files in sql/views/ are deployed")
        console.print()
        console.print(f"[red]⚠️  SAFETY REMINDER:[/red]")
        console.print(f"   • Always test with [bold]dry run[/bold] before committing: [cyan]uv run dbome run --dry[/cyan]")
        console.print(f"   • Configure your BigQuery credentials in [bold]config.yaml[/bold] first")
        console.print(f"   • The hook respects your [bold]dry_run[/bold] config setting")
    console.print()


def _show_next_steps(project_path: Path) -> None:
    """Display next steps for the user.
    
    Args:
        project_path: Project directory path
    """
    console.print(f"[bold blue]🚀 Next steps:[/bold blue]")
    
    if project_path != Path.cwd():
        console.print(f"1. [cyan]cd {project_path.name}[/cyan]")
        console.print(f"2. [cyan]cp config.yaml.template config.yaml[/cyan]")
        step_offset = 2
    else:
        console.print(f"1. [cyan]cp config.yaml.template config.yaml[/cyan]")
        step_offset = 1
    
    console.print(f"{step_offset + 1}. Edit config.yaml with your BigQuery project details")
    console.print(f"{step_offset + 2}. Configure Google Cloud authentication (choose one):")
    console.print(f"   [bold]Option A (Recommended for local development):[/bold]")
    console.print(f"   [cyan]gcloud auth application-default login[/cyan]")
    console.print(f"   [bold]Option B (Service Account File):[/bold]")
    console.print(f"   • Download service account JSON key from Google Cloud Console")
    console.print(f"   • Update config.yaml with the path:")
    console.print(f"     [dim]google_application_credentials: \"/path/to/service-account-key.json\"[/dim]")
    console.print(f"   [bold]Option C (AWS SSM Parameter Store):[/bold]")
    console.print(f"   • Store your service account JSON in AWS SSM Parameter Store")
    console.print(f"   • Update config.yaml with the parameter name:")
    console.print(f"     [dim]aws_ssm_credentials_parameter: \"/your/ssm/parameter/name\"[/dim]")
    console.print(f"{step_offset + 3}. [cyan]uv run dbome run --dry[/cyan]")
    
    console.print(f"\n[dim]For more help, see README.md in your new project![/dim]")
    console.print(f"\n[bold blue]Welcome to dbome - dbt at home! 🏠[/bold blue]")


def _cleanup_on_error(project_path: Path, error: Exception) -> None:
    """Clean up on initialization error.
    
    Args:
        project_path: Project directory path
        error: The exception that occurred
    """
    console.print(f"[red]Error initializing project: {error}[/red]")
    # Clean up on error (only if we created a new directory)
    if project_path != Path.cwd() and project_path.exists():
        shutil.rmtree(project_path)
    raise error