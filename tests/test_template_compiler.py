"""
Unit tests for SQLTemplateCompiler
"""

import pytest
from pathlib import Path
from bq_view_manager.template_compiler import SQLTemplateCompiler


class TestSQLTemplateCompiler:
    """Test cases for SQLTemplateCompiler class"""
    
    def test_init(self, sample_config):
        """Test compiler initialization"""
        compiler = SQLTemplateCompiler(sample_config)
        
        assert compiler.config == sample_config
        assert compiler.view_registry == {}
        assert compiler.dependency_graph == {}
        assert 'ref' in compiler.jinja_env.globals
    
    def test_ref_function_with_registry(self, sample_config):
        """Test ref() function when view exists in registry"""
        compiler = SQLTemplateCompiler(sample_config)
        compiler.register_view('test_view', '`project.dataset.test_view`')
        
        result = compiler._ref_function('test_view')
        assert result == '`project.dataset.test_view`'
    
    def test_ref_function_with_project_override(self, sample_config):
        """Test ref() function with explicit project parameter"""
        compiler = SQLTemplateCompiler(sample_config)
        
        result = compiler._ref_function('test_view', project='other-project')
        assert result == '`other-project.test_dataset.test_view`'
    
    def test_ref_function_default_resolution(self, sample_config):
        """Test ref() function falling back to default resolution"""
        compiler = SQLTemplateCompiler(sample_config)
        
        result = compiler._ref_function('unknown_view')
        assert result == '`test-project.test_dataset.unknown_view`'
    
    def test_register_view(self, sample_config):
        """Test view registration"""
        compiler = SQLTemplateCompiler(sample_config)
        
        compiler.register_view('my_view', '`project.dataset.my_view`')
        
        assert 'my_view' in compiler.view_registry
        assert compiler.view_registry['my_view'] == '`project.dataset.my_view`'
    
    def test_extract_references_single(self, sample_config):
        """Test extracting single ref() call"""
        compiler = SQLTemplateCompiler(sample_config)
        sql = "SELECT * FROM {{ ref('user_events') }} WHERE date > '2024-01-01'"
        
        refs = compiler.extract_references(sql)
        
        assert refs == ['user_events']
    
    def test_extract_references_multiple(self, sample_config):
        """Test extracting multiple ref() calls"""
        compiler = SQLTemplateCompiler(sample_config)
        sql = """
        SELECT u.*, e.event_count 
        FROM {{ ref('users') }} u
        JOIN {{ ref('event_counts') }} e ON u.id = e.user_id
        """
        
        refs = compiler.extract_references(sql)
        
        assert set(refs) == {'users', 'event_counts'}
    
    def test_extract_references_none(self, sample_config):
        """Test extracting refs when none exist"""
        compiler = SQLTemplateCompiler(sample_config)
        sql = "SELECT * FROM `project.dataset.table` WHERE id = 1"
        
        refs = compiler.extract_references(sql)
        
        assert refs == []
    
    def test_extract_references_various_quotes(self, sample_config):
        """Test extracting refs with different quote styles"""
        compiler = SQLTemplateCompiler(sample_config)
        sql = """
        SELECT * FROM {{ ref('single_quotes') }}
        UNION ALL
        SELECT * FROM {{ ref("double_quotes") }}
        """
        
        refs = compiler.extract_references(sql)
        
        assert set(refs) == {'single_quotes', 'double_quotes'}
    
    def test_compile_sql_simple(self, sample_config):
        """Test simple SQL compilation"""
        compiler = SQLTemplateCompiler(sample_config)
        compiler.register_view('events', '`test-project.test_dataset.events`')
        
        sql = "SELECT * FROM {{ ref('events') }}"
        
        compiled = compiler.compile_sql(sql, 'test_view')
        
        assert compiled == "SELECT * FROM `test-project.test_dataset.events`"
    
    def test_compile_sql_complex(self, sample_config):
        """Test complex SQL compilation with multiple refs"""
        compiler = SQLTemplateCompiler(sample_config)
        compiler.register_view('users', '`test-project.test_dataset.users`')
        compiler.register_view('events', '`test-project.test_dataset.events`')
        
        sql = """
        SELECT 
            u.user_id,
            COUNT(*) as event_count
        FROM {{ ref('users') }} u
        JOIN {{ ref('events') }} e ON u.user_id = e.user_id
        GROUP BY u.user_id
        """
        
        compiled = compiler.compile_sql(sql, 'test_view')
        
        assert '`test-project.test_dataset.users`' in compiled
        assert '`test-project.test_dataset.events`' in compiled
        assert '{{ ref(' not in compiled  # All refs should be compiled
    
    def test_compile_sql_template_error(self, sample_config):
        """Test SQL compilation with template syntax error"""
        compiler = SQLTemplateCompiler(sample_config)
        
        # Invalid Jinja2 syntax
        sql = "SELECT * FROM {{ ref('events') "  # Missing closing }}
        
        with pytest.raises(Exception):
            compiler.compile_sql(sql, 'test_view')
    
    def test_build_dependency_graph(self, sample_config, views_dir):
        """Test building dependency graph from SQL files"""
        compiler = SQLTemplateCompiler(sample_config)
        sql_files = list(views_dir.glob("*.sql"))
        
        graph = compiler.build_dependency_graph(sql_files)
        
        expected_graph = {
            'base_events': [],
            'user_metrics': ['base_events'],
            'user_summary': ['user_metrics'],
            'invalid': ['nonexistent_view']
        }
        
        assert graph == expected_graph
        assert compiler.dependency_graph == expected_graph
    
    def test_topological_sort_simple(self, sample_config):
        """Test topological sort with simple dependency chain"""
        compiler = SQLTemplateCompiler(sample_config)
        
        graph = {
            'a': [],
            'b': ['a'],
            'c': ['b']
        }
        
        result = compiler.topological_sort(graph)
        
        # Should be in dependency order: dependencies first
        assert result.index('a') < result.index('b')
        assert result.index('b') < result.index('c')
        assert set(result) == {'a', 'b', 'c'}
    
    def test_topological_sort_complex(self, sample_config):
        """Test topological sort with complex dependencies"""
        compiler = SQLTemplateCompiler(sample_config)
        
        graph = {
            'a': [],
            'b': [],
            'c': ['a', 'b'],
            'd': ['c'],
            'e': ['a']
        }
        
        result = compiler.topological_sort(graph)
        
        # Check dependency constraints
        assert result.index('a') < result.index('c')
        assert result.index('b') < result.index('c')
        assert result.index('c') < result.index('d')
        assert result.index('a') < result.index('e')
        assert set(result) == {'a', 'b', 'c', 'd', 'e'}
    
    def test_topological_sort_circular_dependency(self, sample_config):
        """Test topological sort with circular dependency"""
        compiler = SQLTemplateCompiler(sample_config)
        
        graph = {
            'a': ['b'],
            'b': ['c'],
            'c': ['a']  # Circular dependency
        }
        
        with pytest.raises(ValueError, match="Circular dependencies detected"):
            compiler.topological_sort(graph)
    
    def test_get_deployment_order(self, sample_config, views_dir):
        """Test getting deployment order from SQL files"""
        compiler = SQLTemplateCompiler(sample_config)
        sql_files = [f for f in views_dir.glob("*.sql") if f.name != 'invalid.sql']
        
        order = compiler.get_deployment_order(sql_files)
        
        # Should deploy in dependency order
        assert order.index('base_events') < order.index('user_metrics')
        assert order.index('user_metrics') < order.index('user_summary')
    
    def test_get_deployment_order_with_circular_dependency(self, sample_config, temp_dir):
        """Test deployment order with circular dependency (should fallback)"""
        compiler = SQLTemplateCompiler(sample_config)
        
        # Create files with circular dependency
        views_path = temp_dir / "views"
        views_path.mkdir()
        
        (views_path / "a.sql").write_text("SELECT * FROM {{ ref('b') }}")
        (views_path / "b.sql").write_text("SELECT * FROM {{ ref('a') }}")
        
        sql_files = list(views_path.glob("*.sql"))
        
        # Should fallback to original order without error
        order = compiler.get_deployment_order(sql_files)
        assert len(order) == 2
        assert set(order) == {'a', 'b'}
    
    def test_validate_references_valid(self, sample_config, views_dir):
        """Test reference validation with valid references"""
        compiler = SQLTemplateCompiler(sample_config)
        sql_files = [f for f in views_dir.glob("*.sql") if f.name != 'invalid.sql']
        
        errors = compiler.validate_references(sql_files)
        
        assert errors == []
    
    def test_validate_references_invalid(self, sample_config, views_dir):
        """Test reference validation with invalid references"""
        compiler = SQLTemplateCompiler(sample_config)
        sql_files = list(views_dir.glob("*.sql"))  # Include invalid.sql
        
        errors = compiler.validate_references(sql_files)
        
        assert len(errors) > 0
        assert any('nonexistent_view' in error for error in errors)
    
    def test_validate_references_missing_file(self, sample_config, temp_dir):
        """Test reference validation with missing file"""
        compiler = SQLTemplateCompiler(sample_config)
        
        # Create a non-existent file path
        fake_file = temp_dir / "nonexistent.sql"
        sql_files = [fake_file]
        
        errors = compiler.validate_references(sql_files)
        
        assert len(errors) > 0
        assert any('Error reading' in error for error in errors)


@pytest.mark.unit
class TestSQLTemplateCompilerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_ref_function_empty_name(self, sample_config):
        """Test ref() function with empty view name"""
        compiler = SQLTemplateCompiler(sample_config)
        
        result = compiler._ref_function('')
        
        # Should handle empty name gracefully with project and dataset
        assert result == '`test-project.test_dataset.`'
    
    def test_extract_references_malformed_syntax(self, sample_config):
        """Test extracting refs with malformed syntax"""
        compiler = SQLTemplateCompiler(sample_config)
        
        # Various malformed ref() calls
        sql = """
        SELECT * FROM {{ ref('valid_view') }}
        SELECT * FROM {{ ref() }}
        SELECT * FROM {{ ref(missing_quotes) }}
        SELECT * FROM {{ ref('unclosed_quote) }}
        """
        
        refs = compiler.extract_references(sql)
        
        # Should only extract the valid one
        assert refs == ['valid_view']
    
    def test_compile_sql_with_jinja_features(self, sample_config):
        """Test SQL compilation with other Jinja2 features"""
        compiler = SQLTemplateCompiler(sample_config)
        compiler.register_view('events', '`test.dataset.events`')
        
        sql = """
        SELECT 
            user_id,
            {% if True %}
            event_type,
            {% endif %}
            timestamp
        FROM {{ ref('events') }}
        """
        
        compiled = compiler.compile_sql(sql, 'test_view')
        
        assert '`test.dataset.events`' in compiled
        assert 'event_type' in compiled
        assert '{%' not in compiled  # Jinja syntax should be gone
    
    def test_build_dependency_graph_empty_files(self, sample_config, temp_dir):
        """Test building dependency graph with empty file list"""
        compiler = SQLTemplateCompiler(sample_config)
        
        graph = compiler.build_dependency_graph([])
        
        assert graph == {}
    
    def test_topological_sort_single_node(self, sample_config):
        """Test topological sort with single node"""
        compiler = SQLTemplateCompiler(sample_config)
        
        graph = {'single': []}
        result = compiler.topological_sort(graph)
        
        assert result == ['single']
    
    def test_topological_sort_empty_graph(self, sample_config):
        """Test topological sort with empty graph"""
        compiler = SQLTemplateCompiler(sample_config)
        
        result = compiler.topological_sort({})
        
        assert result == [] 