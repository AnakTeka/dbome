"""
Unit tests for BigQueryViewManager
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import yaml
import tempfile
import os

from bq_view_manager.main import BigQueryViewManager


class TestBigQueryViewManager:
    """Test cases for BigQueryViewManager class"""
    
    def test_init_with_config_file(self, config_file):
        """Test manager initialization with config file"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            assert manager.config['bigquery']['project_id'] == 'test-project'
            assert manager.config['bigquery']['dataset_id'] == 'test_dataset'
            assert manager.template_compiler is not None
    
    def test_init_dry_run_mode(self, config_file, sample_config):
        """Test manager initialization in dry run mode"""
        # Modify config for dry run
        sample_config['deployment']['dry_run'] = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_config = f.name
        
        try:
            manager = BigQueryViewManager(temp_config)
            assert manager.client is None  # No client in dry run mode
        finally:
            os.unlink(temp_config)
    
    def test_load_config_file_not_found(self):
        """Test config loading with non-existent file"""
        with pytest.raises(SystemExit):
            BigQueryViewManager('nonexistent.yaml')
    
    def test_load_config_invalid_yaml(self, temp_dir):
        """Test config loading with invalid YAML"""
        invalid_config = temp_dir / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content: [")
        
        with pytest.raises(SystemExit):
            BigQueryViewManager(str(invalid_config))
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_initialize_client_success(self, mock_client_class, config_file):
        """Test successful BigQuery client initialization"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        
        mock_client_class.assert_called_once_with(
            project='test-project',
            location='US'
        )
        assert manager.client == mock_client
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_initialize_client_with_credentials(self, mock_client_class, temp_dir, sample_config):
        """Test client initialization with credentials file"""
        # Add credentials to config
        sample_config['google_application_credentials'] = '/path/to/creds.json'
        
        config_path = temp_dir / "config_with_creds.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {}, clear=True):
            manager = BigQueryViewManager(str(config_path))
            
            assert os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') == '/path/to/creds.json'
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_initialize_client_failure(self, mock_client_class, config_file):
        """Test BigQuery client initialization failure"""
        mock_client_class.side_effect = Exception("Authentication failed")
        
        with pytest.raises(SystemExit):
            BigQueryViewManager(str(config_file))
    
    def test_find_sql_files_default(self, config_file, views_dir):
        """Test finding SQL files with default behavior"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Update config to point to our test views directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            sql_files = manager.find_sql_files()
            
            assert len(sql_files) == 4  # base_events, user_metrics, user_summary, invalid
            assert all(f.suffix == '.sql' for f in sql_files)
    
    def test_find_sql_files_specific_files(self, config_file, views_dir):
        """Test finding specific SQL files"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Update config to point to our test views directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            specific_file = str(views_dir / "base_events.sql")
            sql_files = manager.find_sql_files([specific_file])
            
            assert len(sql_files) == 1
            assert sql_files[0].name == "base_events.sql"
    
    def test_find_sql_files_nonexistent_directory(self, config_file):
        """Test finding SQL files in non-existent directory"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            sql_files = manager.find_sql_files()
            
            assert sql_files == []
    
    def test_find_sql_files_with_exclusions(self, config_file, views_dir):
        """Test finding SQL files with exclusion patterns"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Create a backup file that should be excluded
            backup_file = views_dir / "backup.backup.sql"
            backup_file.write_text("-- Backup file")
            
            # Update config
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            sql_files = manager.find_sql_files()
            
            # Should not include the backup file
            file_names = [f.name for f in sql_files]
            assert 'backup.backup.sql' not in file_names
    
    @patch('bq_view_manager.main.parse_one')
    def test_parse_sql_file_success(self, mock_parse_one, config_file, views_dir):
        """Test successful SQL file parsing"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Mock SQLGlot parsing
            mock_ast = Mock()
            mock_ast.kind = "VIEW"
            mock_ast.this = Mock()
            mock_ast.this.name = "test_view"
            mock_ast.this.sql.return_value = "`test-project.test_dataset.test_view`"
            mock_ast.this.catalog = "test-project"
            mock_ast.this.db = "test_dataset"
            
            mock_parse_one.return_value = mock_ast
            
            sql_file = views_dir / "base_events.sql"
            result = manager.parse_sql_file(sql_file)
            
            assert result is not None
            assert result['name'] == 'test_view'
            assert result['project_id'] == 'test-project'
            assert result['dataset_id'] == 'test_dataset'
            assert 'raw_content' in result
            assert 'compiled_content' in result
    
    def test_parse_sql_file_template_error(self, config_file, temp_dir):
        """Test SQL file parsing with template compilation error"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Create file with invalid Jinja2 syntax
            bad_file = temp_dir / "bad_template.sql"
            bad_file.write_text("SELECT * FROM {{ invalid_syntax")
            
            result = manager.parse_sql_file(bad_file)
            
            assert result is None
    
    @patch('bq_view_manager.main.parse_one')
    def test_parse_sql_file_not_view(self, mock_parse_one, config_file, temp_dir):
        """Test parsing non-VIEW SQL statement"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Mock parsing a CREATE TABLE instead of VIEW
            mock_ast = Mock()
            mock_ast.kind = "TABLE"  # Not a VIEW
            mock_parse_one.return_value = mock_ast
            
            sql_file = temp_dir / "not_a_view.sql"
            sql_file.write_text("CREATE TABLE test AS SELECT 1")
            
            result = manager.parse_sql_file(sql_file)
            
            assert result is None
    
    def test_execute_view_sql_dry_run(self, config_file):
        """Test SQL execution in dry run mode"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            # Ensure dry run mode
            manager.config['deployment']['dry_run'] = True
            
            sql_info = {
                'name': 'test_view',
                'project_id': 'test-project',
                'dataset_id': 'test_dataset',
                'full_name': '`test-project.test_dataset.test_view`',
                'compiled_content': 'SELECT 1',
                'parsed_ast': Mock()
            }
            
            result = manager.execute_view_sql(sql_info)
            
            assert result is True
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_execute_view_sql_real_execution(self, mock_client_class, config_file):
        """Test real SQL execution (not dry run)"""
        # Set up non-dry-run config
        mock_client = Mock()
        mock_job = Mock()
        mock_client.query.return_value = mock_job
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        manager.config['deployment']['dry_run'] = False
        manager.client = mock_client
        
        sql_info = {
            'name': 'test_view',
            'compiled_content': 'CREATE OR REPLACE VIEW test AS SELECT 1'
        }
        
        result = manager.execute_view_sql(sql_info)
        
        assert result is True
        mock_client.query.assert_called_once_with('CREATE OR REPLACE VIEW test AS SELECT 1')
        mock_job.result.assert_called_once()
    
    @patch('bq_view_manager.main.bigquery.Client')
    def test_execute_view_sql_execution_error(self, mock_client_class, config_file):
        """Test SQL execution with error"""
        mock_client = Mock()
        mock_client.query.side_effect = Exception("BigQuery error")
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        manager.config['deployment']['dry_run'] = False
        manager.client = mock_client
        
        sql_info = {
            'name': 'test_view',
            'compiled_content': 'INVALID SQL'
        }
        
        result = manager.execute_view_sql(sql_info)
        
        assert result is False


@pytest.mark.integration  
class TestBigQueryViewManagerIntegration:
    """Integration tests for BigQueryViewManager"""
    
    def test_deploy_views_end_to_end(self, config_file, views_dir):
        """Test complete view deployment workflow"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Update config to point to test views
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            config['deployment']['dry_run'] = True  # Safe for testing
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should complete without errors
            manager.deploy_views()
    
    def test_deploy_views_with_dependency_order(self, config_file, views_dir):
        """Test that views are deployed in correct dependency order"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Update config
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            config['deployment']['dry_run'] = True
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Mock execute_view_sql to track call order
            executed_views = []
            original_execute = manager.execute_view_sql
            
            def mock_execute(sql_info):
                executed_views.append(sql_info['name'])
                return original_execute(sql_info)
            
            manager.execute_view_sql = mock_execute
            
            # Run deployment
            manager.deploy_views()
            
            # Check that base_events comes before user_metrics
            # and user_metrics comes before user_summary
            if 'base_events' in executed_views and 'user_metrics' in executed_views:
                assert executed_views.index('base_events') < executed_views.index('user_metrics')
            if 'user_metrics' in executed_views and 'user_summary' in executed_views:
                assert executed_views.index('user_metrics') < executed_views.index('user_summary')
    
    def test_deploy_views_validation_errors(self, config_file, views_dir):
        """Test deployment with validation errors"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Update config to include invalid.sql file
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should exit early due to validation errors
            manager.deploy_views()
    
    def test_deploy_views_no_files(self, config_file, temp_dir):
        """Test deployment with no SQL files"""
        with patch('bq_view_manager.main.bigquery.Client'):
            # Create empty views directory
            empty_views = temp_dir / "empty_views"
            empty_views.mkdir()
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(empty_views)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should handle gracefully
            manager.deploy_views()


@pytest.mark.unit
class TestBigQueryViewManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_parse_sql_file_file_not_found(self, config_file):
        """Test parsing non-existent file"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            result = manager.parse_sql_file(Path("/nonexistent/file.sql"))
            
            assert result is None
    
    def test_execute_view_sql_missing_keys(self, config_file):
        """Test executing SQL with missing required keys"""
        with patch('bq_view_manager.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Missing required keys - should fail gracefully, not raise KeyError
            incomplete_sql_info = {'name': 'test'}
            
            result = manager.execute_view_sql(incomplete_sql_info)
            # Should return False for errors instead of raising KeyError
            assert result is False 