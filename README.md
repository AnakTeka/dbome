# BigQuery View Manager

A dbt-like BigQuery View Manager with simplified SQL syntax, dependency resolution, and git-based workflows

> *"Mom, can we have dbt?"*  
> *"We have dbt at home."*  
> **dbt at home:** 🏠

## ✨ Features

- **📝 Simplified SQL syntax** - No more CREATE OR REPLACE VIEW boilerplate!
- **🔄 dbt-like `ref()` syntax** - Use `{{ ref('view_name') }}` in your SQL
- **📊 Automatic dependency resolution** - Deploy views in correct order
- **🎯 Template compilation** - Jinja2-powered SQL templates
- **🚀 One-command deployment** - Deploy all views with proper dependencies
- **🔍 Validation & debugging** - Validate references and visualize dependencies
- **📁 Compiled SQL output** - See resolved SQL files for debugging
- **⚡ Git-based workflow** - Automatic deployment on commit
- **🧪 Comprehensive testing** - 89% test coverage with pytest

## 🚀 Installation

### Install the Package

```bash
pip install bq-view-manager
```

### Initialize a New Project

```bash
# Create a new BigQuery view management project
bq-view-manager init my-dwh-project

# Navigate to your project
cd my-dwh-project

# Configure your project
cp config.yaml.template config.yaml
# Edit config.yaml with your BigQuery project details
```

### Setup Authentication

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Test your setup
bq-view-deploy --dry-run
```

## 📝 Quick Start

### 1. Initialize Your Project
```bash
bq-view-manager init analytics-views
cd analytics-views
```

### 2. Configure BigQuery
Edit `config.yaml`:
```yaml
bigquery:
  project_id: "your-gcp-project-id"
  dataset_id: "analytics"
  location: "US"
```

### 3. Write Your First View
Create `sql/views/user_events.sql`:
```sql
SELECT 
    user_id,
    event_type,
    event_timestamp,
    page_url
FROM `your-project.raw_data.events`
WHERE event_timestamp >= CURRENT_DATE()
```

### 4. Deploy Your Views
```bash
# Test deployment
bq-view-deploy --dry-run

# Deploy to BigQuery
bq-view-deploy

# Or use git (auto-deployment)
git add sql/views/user_events.sql
git commit -m "Add user events view"
# 🚀 Automatically deployed via git hook!
```

## 🎯 Key Concepts

### Simplified SQL Syntax
Write clean SQL without boilerplate:

**❌ Old way (traditional):**
```sql
CREATE OR REPLACE VIEW `project.dataset.user_metrics` AS
SELECT user_id, COUNT(*) as events
FROM `project.dataset.user_events`
GROUP BY user_id;
```

**✅ New way (bq-view-manager):**
```sql
-- File: sql/views/user_metrics.sql
SELECT user_id, COUNT(*) as events  
FROM {{ ref('user_events') }}
GROUP BY user_id
```

### Automatic Dependencies
Views are deployed in the correct order automatically:

```sql
-- sql/views/events.sql (deployed first)
SELECT * FROM `project.raw.events`

-- sql/views/users.sql (deployed second) 
SELECT user_id, COUNT(*) as event_count
FROM {{ ref('events') }}
GROUP BY user_id

-- sql/views/summary.sql (deployed third)
SELECT 
    CASE WHEN event_count > 100 THEN 'active' ELSE 'inactive' END as user_type,
    COUNT(*) as user_count
FROM {{ ref('users') }}
GROUP BY user_type
```

**Deployment Order**: `events` → `users` → `summary`

### Git-Based Workflow
Changes are automatically deployed when you commit:

```bash
git add sql/views/
git commit -m "Update analytics views"  
# 🚀 Views automatically deployed to BigQuery!
```

## 🔧 Commands

### Package Commands

| Command | Description |
|---------|-------------|
| `bq-view-manager init PROJECT` | Initialize a new project |
| `bq-view-manager --help` | Show help |

### Project Commands (inside your project)

| Command | Description |
|---------|-------------|
| `bq-view-deploy` | Deploy all views |
| `bq-view-deploy --dry-run` | Preview deployments |
| `bq-view-deploy --files FILE1 FILE2` | Deploy specific files only |
| `bq-view-deploy --validate-refs` | Validate all ref() references |
| `bq-view-deploy --show-deps` | Show dependency graph and deployment order |
| `bq-view-deploy --compile-only` | Compile templates to compiled/ directory |
| `bq-view-deploy --config FILE` | Use custom config file |

### Make Commands (inside your project)

| Command | Description |
|---------|-------------|
| `make deploy` | Deploy all views |
| `make dry-run` | Preview deployments |
| `make check` | Validate SQL syntax |
| `make compile` | Compile SQL templates to compiled/ directory |
| `make setup` | Run setup script |
| `make clean` | Clean build artifacts |

## 📁 Project Structure

When you run `bq-view-manager init my-project`, you get:

```
my-project/
├── sql/views/              # Your SQL view files
│   ├── example_view.sql    # Example view
│   └── user_metrics.sql    # Example with ref()
├── config.yaml.template   # Configuration template
├── config.yaml           # Your configuration (created from template)
├── Makefile              # Helpful commands
├── README.md             # Project-specific documentation  
├── .gitignore            # Excludes compiled/ and config files
├── .git/hooks/
│   └── post-commit       # Auto-deployment git hook
└── compiled/views/       # Auto-generated compiled SQL (gitignored)
```

## 🔍 Advanced Features

### Compiled SQL Output

See exactly what SQL is executed:

```bash
bq-view-deploy --compile-only
```

Files are saved to `compiled/views/` with resolved `ref()` calls:

```sql
-- compiled/views/user_metrics.sql
-- Compiled SQL from: sql/views/user_metrics.sql
-- Generated by BigQuery View Manager
-- DO NOT EDIT: This file is auto-generated

CREATE OR REPLACE VIEW `your-project.analytics.user_metrics` AS
SELECT user_id, COUNT(*) as events  
FROM `your-project.analytics.user_events`  -- ref() resolved!
GROUP BY user_id
```

### Dependency Visualization

```bash
bq-view-deploy --show-deps
```

Output:
```
Dependency Graph:
  user_events (no dependencies)
  user_metrics → user_events
  user_summary → user_metrics

Deployment Order:
  1. user_events
  2. user_metrics  
  3. user_summary
```

### Reference Validation

```bash
bq-view-deploy --validate-refs
```

Validates all `{{ ref('view_name') }}` calls before deployment.

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📜 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Inspired by dbt's approach to data transformation, adapted for BigQuery view management with git-based workflows.

---

**Made with ❤️ for the BigQuery community**
