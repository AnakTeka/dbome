"""
Pytest configuration and shared fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import yaml

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing"""
    return {
        'bigquery': {
            'project_id': 'test-project',
            'dataset_id': 'test_dataset',
            'location': 'US'
        },
        'sql': {
            'views_directory': 'sql/views',
            'include_patterns': ['*.sql'],
            'exclude_patterns': ['*.backup.sql']
        },
        'deployment': {
            'dry_run': True,
            'verbose': True
        }
    }

@pytest.fixture
def config_file(temp_dir, sample_config):
    """Create a temporary config file"""
    config_path = temp_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    return config_path

@pytest.fixture
def views_dir(temp_dir):
    """Create a views directory with sample SQL files"""
    views_path = temp_dir / "sql" / "views"
    views_path.mkdir(parents=True)
    
    # Base view (no dependencies)
    base_view = views_path / "base_events.sql"
    base_view.write_text('''
-- Base events view
CREATE OR REPLACE VIEW `test-project.test_dataset.base_events` AS
SELECT 
    user_id,
    event_type,
    timestamp
FROM `test-project.raw.events`
WHERE user_id IS NOT NULL;
    '''.strip())
    
    # View with dependency
    metrics_view = views_path / "user_metrics.sql"
    metrics_view.write_text('''
-- User metrics with ref() dependency
CREATE OR REPLACE VIEW `test-project.test_dataset.user_metrics` AS
SELECT 
    user_id,
    COUNT(*) as event_count,
    MAX(timestamp) as last_event
FROM {{ ref('base_events') }}
GROUP BY user_id;
    '''.strip())
    
    # View with multi-level dependency
    summary_view = views_path / "user_summary.sql"
    summary_view.write_text('''
-- User summary with dependency chain
CREATE OR REPLACE VIEW `test-project.test_dataset.user_summary` AS
SELECT 
    CASE 
        WHEN event_count >= 10 THEN 'Active'
        ELSE 'Inactive'
    END as user_type,
    COUNT(*) as user_count
FROM {{ ref('user_metrics') }}
GROUP BY user_type;
    '''.strip())
    
    # Invalid view (for error testing)
    invalid_view = views_path / "invalid.sql"
    invalid_view.write_text('''
-- Invalid SQL for testing
SELECT * FROM {{ ref('nonexistent_view') }};
    '''.strip())
    
    return views_path

@pytest.fixture
def sample_sql_files(views_dir):
    """Get list of sample SQL files"""
    return list(views_dir.glob("*.sql")) 