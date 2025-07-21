"""
Unit tests for BigQueryViewManager
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import yaml
import tempfile
import os

from dbome.main import BigQueryViewManager


class TestBigQueryViewManager:
    """Test cases for BigQueryViewManager class"""
    
    def test_init_with_config_file(self, config_file):
        """Test manager initialization with config file"""
        with patch('dbome.main.bigquery.Client'):
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
        from dbome.exceptions import ConfigError
        with pytest.raises(ConfigError):
            BigQueryViewManager('nonexistent.yaml')
    
    def test_load_config_invalid_yaml(self, temp_dir):
        """Test config loading with invalid YAML"""
        from dbome.exceptions import ConfigError
        invalid_config = temp_dir / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ConfigError):
            BigQueryViewManager(str(invalid_config))
    
    @patch('dbome.main.bigquery.Client')
    def test_initialize_client_success(self, mock_client_class, config_file):
        """Test successful BigQuery client initialization"""
        # Set dry_run to False to trigger client initialization
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['deployment']['dry_run'] = False
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        
        mock_client_class.assert_called_once_with(
            project='test-project',
            location='US'
        )
        assert manager.client == mock_client
    
    @patch('dbome.main.bigquery.Client')
    def test_initialize_client_with_credentials(self, mock_client_class, temp_dir, sample_config):
        """Test client initialization with credentials file"""
        # Create a temporary credentials file
        creds_file = temp_dir / "creds.json"
        creds_file.write_text('{"type": "service_account"}')
        
        # Add credentials to config and set dry_run to False
        sample_config['google_application_credentials'] = str(creds_file)
        sample_config['deployment']['dry_run'] = False
        
        config_path = temp_dir / "config_with_creds.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f)
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {}, clear=True):
            manager = BigQueryViewManager(str(config_path))
            
            assert os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') == str(creds_file)
    
    @patch('dbome.main.bigquery.Client')
    def test_initialize_client_failure(self, mock_client_class, config_file):
        """Test BigQuery client initialization failure"""
        # Set dry_run to False to trigger client initialization
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['deployment']['dry_run'] = False
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_client_class.side_effect = Exception("Authentication failed")
        
        from dbome.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError):
            BigQueryViewManager(str(config_file))
    
    def test_find_sql_files_default(self, config_file, views_dir):
        """Test finding SQL files with default behavior"""
        with patch('dbome.main.bigquery.Client'):
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
        with patch('dbome.main.bigquery.Client'):
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
        with patch('dbome.main.bigquery.Client'):
            # Update config to point to nonexistent directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = '/nonexistent/directory'
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            from dbome.exceptions import FileSystemError
            with pytest.raises(FileSystemError):
                manager.find_sql_files()
    
    def test_find_sql_files_with_exclusions(self, config_file, views_dir):
        """Test finding SQL files with exclusion patterns"""
        with patch('dbome.main.bigquery.Client'):
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
    
    @patch('dbome.main.parse_one')
    def test_parse_sql_file_success(self, mock_parse_one, config_file, views_dir):
        """Test successful SQL file parsing"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Mock SQLGlot parsing with proper type
            from sqlglot import expressions as exp
            
            mock_ast = Mock(spec=exp.Create)
            mock_ast.kind = "VIEW"
            mock_ast.this = Mock(spec=exp.Table)
            mock_ast.this.name = "base_events"  # Match the actual file name
            mock_ast.this.sql.return_value = "`test-project.test_dataset.base_events`"
            mock_ast.this.catalog = "test-project"
            mock_ast.this.db = "test_dataset"
            
            mock_parse_one.return_value = mock_ast
            
            sql_file = views_dir / "base_events.sql"
            result = manager.parse_sql_file(sql_file)
            
            assert result is not None
            assert result['name'] == 'base_events'
            assert result['compiled_content'] is not None
    
    def test_parse_sql_file_template_error(self, config_file, temp_dir):
        """Test SQL file parsing with template compilation error"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Create a SQL file with invalid template syntax
            bad_sql = temp_dir / "bad_template.sql"
            bad_sql.write_text("SELECT * FROM {{ ref('events'")  # Missing closing }}
            
            result = manager.parse_sql_file(bad_sql)
            assert result is None  # Should return None on template error
    
    @patch('dbome.main.parse_one')
    def test_parse_sql_file_not_view(self, mock_parse_one, config_file, temp_dir):
        """Test SQL file parsing for non-view statements"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Mock SQLGlot parsing for non-view SQL
            from sqlglot import expressions as exp
            
            mock_ast = Mock(spec=exp.Select)  # Not a Create expression
            mock_parse_one.return_value = mock_ast
            
            sql_file = temp_dir / "not_a_view.sql"
            sql_file.write_text("SELECT * FROM table")
            
            result = manager.parse_sql_file(sql_file)
            
            assert result is None
    
    def test_execute_view_sql_dry_run(self, config_file):
        """Test view SQL execution in dry run mode"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            sql_info = {
                'name': 'test_view',
                'full_name': '`test-project.test_dataset.test_view`',
                'project_id': 'test-project',
                'dataset_id': 'test_dataset',
                'path': Path('/tmp/test.sql'),
                'raw_content': 'SELECT * FROM table',
                'compiled_content': 'CREATE OR REPLACE VIEW `test-project.test_dataset.test_view` AS SELECT * FROM table',
                'parsed_ast': Mock()
            }
            
            # Should return True in dry run mode
            result = manager.execute_view_sql(sql_info)
            assert result is True
    
    @patch('dbome.main.bigquery.Client')
    def test_execute_view_sql_real_execution(self, mock_client_class, config_file):
        """Test real view SQL execution"""
        # Set dry_run to False to trigger actual execution
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['deployment']['dry_run'] = False
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        
        sql_info = {
            'name': 'test_view',
            'full_name': '`test-project.test_dataset.test_view`',
            'project_id': 'test-project',
            'dataset_id': 'test_dataset',
            'path': Path('/tmp/test.sql'),
            'raw_content': 'SELECT * FROM table',
            'compiled_content': 'CREATE OR REPLACE VIEW `test-project.test_dataset.test_view` AS SELECT * FROM table',
            'parsed_ast': Mock()
        }
        
        result = manager.execute_view_sql(sql_info)
        assert result is True
        
        # Verify the query was executed
        mock_client.query.assert_called_once_with(sql_info['compiled_content'])
    
    @patch('dbome.main.bigquery.Client')
    def test_execute_view_sql_execution_error(self, mock_client_class, config_file):
        """Test view SQL execution with error handling"""
        # Set dry_run to False to trigger actual execution
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['deployment']['dry_run'] = False
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        mock_client = Mock()
        mock_client.query.side_effect = Exception("BigQuery error")
        mock_client_class.return_value = mock_client
        
        manager = BigQueryViewManager(str(config_file))
        
        sql_info = {
            'name': 'test_view',
            'full_name': '`test-project.test_dataset.test_view`',
            'project_id': 'test-project',
            'dataset_id': 'test_dataset',
            'path': Path('/tmp/test.sql'),
            'raw_content': 'SELECT * FROM table',
            'compiled_content': 'CREATE OR REPLACE VIEW `test-project.test_dataset.test_view` AS SELECT * FROM table',
            'parsed_ast': Mock()
        }
        
        from dbome.exceptions import DeploymentError
        with pytest.raises(DeploymentError):
            manager.execute_view_sql(sql_info)


@pytest.mark.integration  
class TestBigQueryViewManagerIntegration:
    """Integration tests for BigQueryViewManager"""
    
    def test_deploy_views_end_to_end(self, config_file, views_dir):
        """Test complete view deployment workflow"""
        with patch('dbome.main.bigquery.Client'):
            # Update config to point to our test views directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should complete without errors
            manager.deploy_views()
    
    def test_deploy_views_with_dependency_order(self, config_file, views_dir):
        """Test that views are deployed in correct dependency order"""
        with patch('dbome.main.bigquery.Client'):
            # Update config to point to our test views directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Track execution order
            executed_views = []
            
            def mock_execute(sql_info):
                executed_views.append(sql_info['name'])
                return True  # Return success
            
            manager.execute_view_sql = mock_execute
            
            # Remove the invalid.sql file that causes validation errors
            invalid_file = views_dir / "invalid.sql"
            if invalid_file.exists():
                invalid_file.unlink()
            
            manager.deploy_views()
            
            # Verify deployment order respects dependencies
            assert 'base_events' in executed_views
            assert 'user_metrics' in executed_views
            assert 'user_summary' in executed_views
            assert executed_views.index('base_events') < executed_views.index('user_metrics')
            assert executed_views.index('user_metrics') < executed_views.index('user_summary')
    
    def test_deploy_views_validation_errors(self, config_file, views_dir):
        """Test deploy_views with validation errors"""
        with patch('dbome.main.bigquery.Client'):
            # Update config to point to our test views directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(views_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should handle validation errors gracefully - validation happens automatically
            manager.deploy_views()
    
    def test_deploy_views_no_files(self, config_file, temp_dir):
        """Test deploy_views when no SQL files found"""
        with patch('dbome.main.bigquery.Client'):
            # Update config to point to empty directory
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            config['sql']['views_directory'] = str(temp_dir)
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            manager = BigQueryViewManager(str(config_file))
            
            # Should handle empty directory gracefully
            manager.deploy_views()


@pytest.mark.unit
class TestBigQueryViewManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_parse_sql_file_file_not_found(self, config_file):
        """Test parsing non-existent SQL file"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            from pathlib import Path
            nonexistent_file = Path("/tmp/nonexistent.sql")
            
            result = manager.parse_sql_file(nonexistent_file)
            assert result is None
    
    def test_execute_view_sql_missing_keys(self, config_file):
        """Test execute_view_sql with missing required keys"""
        with patch('dbome.main.bigquery.Client'):
            manager = BigQueryViewManager(str(config_file))
            
            # Missing required keys
            incomplete_sql_info = {
                'view_name': 'test_view'
                # Missing 'sql' and 'compiled_sql'
            }
            
            with pytest.raises(KeyError):
                manager.execute_view_sql(incomplete_sql_info) 