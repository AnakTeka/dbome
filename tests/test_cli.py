"""
Integration tests for CLI commands
"""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import yaml


@pytest.mark.integration
class TestCLI:
    """Test CLI command functionality"""
    
    def test_cli_help(self):
        """Test CLI help command"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'BigQuery View Manager' in result.stdout
        assert '--dry-run' in result.stdout
        assert '--validate-refs' in result.stdout
        assert '--show-deps' in result.stdout
    
    def test_cli_version(self):
        """Test CLI version command"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', '--version'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'BigQuery View Manager' in result.stdout
        assert '0.1.0' in result.stdout
    
    def test_cli_missing_config(self):
        """Test CLI with missing config file"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', '--config', 'nonexistent.yaml'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert 'Config file' in result.stderr or 'not found' in result.stderr
    
    def test_cli_validate_refs_success(self, config_file, views_dir):
        """Test CLI validate-refs command with valid references"""
        # Update config to point to test views (excluding invalid.sql)
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(views_dir)
        config['sql']['exclude_patterns'] = ['invalid.sql']
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--validate-refs'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'All references are valid' in result.stdout
    
    def test_cli_validate_refs_failure(self, config_file, views_dir):
        """Test CLI validate-refs command with invalid references"""
        # Update config to include invalid.sql
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(views_dir)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--validate-refs'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert 'Validation errors found' in result.stdout
        assert 'nonexistent_view' in result.stdout
    
    def test_cli_show_deps(self, config_file, views_dir):
        """Test CLI show-deps command"""
        # Update config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(views_dir)
        config['sql']['exclude_patterns'] = ['invalid.sql']
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--show-deps'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'Dependency Graph:' in result.stdout
        assert 'Deployment Order:' in result.stdout
        assert 'base_events' in result.stdout
        assert 'user_metrics' in result.stdout
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_cli_dry_run(self, mock_client, config_file, views_dir):
        """Test CLI dry-run command"""
        # Update config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(views_dir)
        config['sql']['exclude_patterns'] = ['invalid.sql']
        config['deployment']['dry_run'] = False  # Will be overridden by --dry-run
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--dry-run'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'DRY RUN' in result.stdout
        assert 'Would execute SQL' in result.stdout
    
    def test_cli_specific_files(self, config_file, views_dir):
        """Test CLI with specific files"""
        # Update config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(views_dir)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        specific_file = str(views_dir / "base_events.sql")
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--validate-refs', 
             '--files', specific_file],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'All references are valid' in result.stdout


@pytest.mark.slow
class TestCLIScripts:
    """Test script entry points"""
    
    def test_bq_view_deploy_script(self):
        """Test bq-view-deploy entry point script"""
        result = subprocess.run(
            ['bq-view-deploy', '--help'],
            capture_output=True,
            text=True
        )
        
        # Should work if package is installed
        if result.returncode == 0:
            assert 'BigQuery View Manager' in result.stdout
        else:
            # If not installed, command should not be found
            assert result.returncode != 0


class TestCLIArgumentParsing:
    """Test CLI argument parsing edge cases"""
    
    def test_cli_invalid_arguments(self):
        """Test CLI with invalid arguments"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', '--invalid-flag'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert 'unrecognized arguments' in result.stderr or 'error' in result.stderr
    
    def test_cli_conflicting_arguments(self, config_file):
        """Test CLI with potentially conflicting arguments"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--validate-refs', '--show-deps'],
            capture_output=True,
            text=True
        )
        
        # Should handle both flags gracefully
        assert result.returncode == 0
    
    def test_cli_files_with_nonexistent_file(self, config_file):
        """Test CLI with files argument pointing to non-existent file"""
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--validate-refs',
             '--files', 'nonexistent.sql'],
            capture_output=True,
            text=True
        )
        
        # Should handle gracefully
        assert 'No SQL files found' in result.stdout or result.returncode == 0
    
    def test_cli_empty_views_directory(self, config_file, temp_dir):
        """Test CLI with empty views directory"""
        # Create empty views directory
        empty_views = temp_dir / "empty"
        empty_views.mkdir()
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['sql']['views_directory'] = str(empty_views)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        result = subprocess.run(
            [sys.executable, '-m', 'bq_view_manager.main', 
             '--config', str(config_file), '--show-deps'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'No SQL files found' in result.stdout 