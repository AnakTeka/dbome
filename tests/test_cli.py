"""
Command line interface tests for BigQuery view manager
"""

import pytest
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
import yaml


class TestCLI:
    """Test command line interface functionality"""
    
    def test_help_command(self):
        """Test --help command"""
        result = subprocess.run(
            [sys.executable, '-m', 'dbome.main', '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'BigQuery View Management' in result.stdout
        assert 'init' in result.stdout
        assert 'run' in result.stdout
        assert 'compile' in result.stdout
        assert 'deps' in result.stdout
        assert 'validate' in result.stdout
    
    def test_version_command(self):
        """Test --version command"""
        result = subprocess.run(
            [sys.executable, '-m', 'dbome.main', '--version'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'dbome (dbt at home)' in result.stdout
    
    def test_config_file_not_found(self):
        """Test behavior when config file doesn't exist"""
        result = subprocess.run(
            [sys.executable, '-m', 'dbome.main', 'run', '--config', 'nonexistent.yaml'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert 'Configuration error' in result.stdout or 'not found' in result.stdout
    
    def test_dry_run_mode(self, sample_config, temp_dir):
        """Test dry run mode"""
        # Create views directory
        views_dir = temp_dir / "sql" / "views"
        views_dir.mkdir(parents=True)
        
        # Create a test SQL file
        sql_file = views_dir / "test_view.sql"
        sql_file.write_text("SELECT 1 as col1")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(views_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'run', '--config', config_file,
                 '--dry'],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert 'DRY RUN' in result.stdout or 'dry run' in result.stdout.lower()
        finally:
            os.unlink(config_file)
    
    def test_validate_refs_mode(self, sample_config, temp_dir):
        """Test reference validation mode"""
        # Create views directory
        views_dir = temp_dir / "sql" / "views"
        views_dir.mkdir(parents=True)
        
        # Create a test SQL file
        sql_file = views_dir / "test_view.sql"
        sql_file.write_text("SELECT 1 as col1")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(views_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'validate', '--config', config_file],
                capture_output=True,
                text=True
            )
            
            # Should complete (may have validation errors but shouldn't crash)
            assert result.returncode in [0, 1]  # 0 for success, 1 for validation failures
        finally:
            os.unlink(config_file)
    
    def test_show_deps_mode(self, sample_config, temp_dir):
        """Test dependency graph display mode"""
        # Create views directory
        views_dir = temp_dir / "sql" / "views"
        views_dir.mkdir(parents=True)
        
        # Create a test SQL file
        sql_file = views_dir / "test_view.sql"
        sql_file.write_text("SELECT 1 as col1")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(views_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'deps', '--config', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            # Should show some dependency information
            assert 'dependency' in result.stdout.lower() or 'order' in result.stdout.lower()
        finally:
            os.unlink(config_file)
    
    @patch('dbome.main.bigquery.Client')
    def test_specific_files_mode(self, mock_client_class, sample_config, temp_dir):
        """Test deploying specific files"""
        # Create test SQL files
        sql_file1 = temp_dir / "view1.sql"
        sql_file2 = temp_dir / "view2.sql"
        sql_file1.write_text("SELECT 1 as col1")
        sql_file2.write_text("SELECT 2 as col2")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(temp_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'run', '--config', config_file,
                 str(sql_file1)],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert 'view1' in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_compile_only_mode(self, sample_config, temp_dir):
        """Test compile-only mode"""
        # Create test SQL file
        sql_file = temp_dir / "test_view.sql"
        sql_file.write_text("SELECT 1 as col1")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(temp_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'compile', '--config', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert 'compiled' in result.stdout.lower()
        finally:
            os.unlink(config_file)
    
    def test_invalid_argument(self):
        """Test behavior with invalid command line arguments"""
        result = subprocess.run(
            [sys.executable, '-m', 'dbome.main', '--invalid-flag'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert 'error' in result.stderr.lower() or 'unrecognized' in result.stderr.lower()
    
    def test_config_file_with_invalid_yaml(self):
        """Test behavior with invalid YAML config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'run', '--config', config_file],
                capture_output=True,
                text=True
            )
            
            assert result.returncode != 0
            assert 'Configuration error' in result.stdout or 'Error parsing config' in result.stdout
        finally:
            os.unlink(config_file)
    
    def test_multiple_modes_combination(self, sample_config, temp_dir):
        """Test combining multiple CLI modes"""
        # Create views directory
        views_dir = temp_dir / "sql" / "views"
        views_dir.mkdir(parents=True)
        
        # Create a test SQL file
        sql_file = views_dir / "test_view.sql"
        sql_file.write_text("SELECT 1 as col1")
        
        # Update config to point to temp directory
        sample_config['sql']['views_directory'] = str(views_dir)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            config_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'dbome.main',
                 'run', '--config', config_file,
                 '--dry'],
                capture_output=True,
                text=True
            )
            
            # Should handle multiple modes gracefully
            assert result.returncode in [0, 1]
        finally:
            os.unlink(config_file) 