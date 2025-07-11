# BigQuery View Manager

Git-based BigQuery View Management Tool

<!-- Last updated: 2025-01-11 for testing selective post-commit hook -->

A Git-based repository that automatically deploys BigQuery views using native `CREATE OR REPLACE VIEW` SQL syntax and post-commit hooks. Store your view definitions in standard SQL files that can be executed directly in BigQuery, track changes with Git, and keep your BigQuery views in sync automatically.

## 🚀 Features

- **Git-based SQL Management**: Store and version control your SQL view files
- **Automatic Deployment**: Post-commit hooks automatically update BigQuery views
- **Native SQL Syntax**: Uses `CREATE OR REPLACE VIEW` statements directly
- **dbt-like ref() Syntax**: Reference other views using `{{ ref('view_name') }}` syntax
- **Dependency Resolution**: Automatically deploys views in the correct order based on dependencies
- **Template Compilation**: Jinja2-powered template engine for dynamic SQL generation
- **Configuration-driven**: YAML configuration for flexible deployment settings
- **Dry Run Mode**: Test deployments without making changes
- **Rich CLI Output**: Beautiful console output with progress indicators
- **Error Handling**: Graceful handling of deployment errors with detailed logging

## 📁 Directory Structure

```
bq-view-manager/
├── sql/
│   └── views/          # SQL views with CREATE OR REPLACE VIEW syntax
├── bq_view_manager/    # Python package
│   ├── __init__.py
│   └── main.py         # Main deployment script
├── .git/hooks/
│   └── post-commit     # Git hook for auto-deployment
├── config.yaml         # BigQuery configuration
├── pyproject.toml      # Python dependencies
└── README.md
```

## 🛠️ Setup

### 1. Prerequisites

- Python 3.11.x or higher
- [uv](https://docs.astral.sh/uv/) for fast package management (**required**)
- Google Cloud SDK installed and authenticated
- BigQuery dataset created in your GCP project

**Note:** The setup script will attempt to install `uv` automatically if not found, but will fail if installation is unsuccessful.

### 2. Install Dependencies

We use [uv](https://docs.astral.sh/uv/) for fast package management:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (automatically creates venv and installs dependencies)
uv sync
```

Or use the automated setup script (will auto-install uv if needed):
```bash
./setup.sh
```

### 3. Configure BigQuery

Copy the configuration template and update with your settings:

```bash
cp config.yaml.template config.yaml
```

Edit `config.yaml` with your BigQuery project details:

```yaml
bigquery:
  project_id: "your-gcp-project-id"
  dataset_id: "your_dataset_name"
  location: "US"
```

### 4. Authentication

Choose one of these authentication methods:

#### Option A: Application Default Credentials (Recommended)
```bash
gcloud auth application-default login
```

#### Option B: Service Account Key
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Update `config.yaml`:
   ```yaml
   google_application_credentials: "/path/to/service-account-key.json"
   ```

The post-commit hook is now active and will deploy views automatically!

## 📝 Usage

### Adding SQL Views

1. Create SQL files in the `sql/views/` directory using `CREATE OR REPLACE VIEW` syntax:

**Basic view (no dependencies):**
```sql
-- sql/views/user_actions.sql
CREATE OR REPLACE VIEW `your-project.your_dataset.user_actions` AS
SELECT 
    user_id,
    action_type,
    action_timestamp,
    session_id
FROM `your-project.raw_data.events`
WHERE action_type IS NOT NULL;
```

**View with dependencies using ref() syntax:**
```sql
-- sql/views/user_metrics.sql
CREATE OR REPLACE VIEW `your-project.your_dataset.user_metrics` AS
SELECT 
    user_id,
    COUNT(*) as total_actions,
    MAX(action_timestamp) as last_action_date,
    COUNT(DISTINCT session_id) as total_sessions
FROM {{ ref('user_actions') }}
GROUP BY user_id;
```

**Multi-level dependency chain:**
```sql
-- sql/views/user_summary.sql
CREATE OR REPLACE VIEW `your-project.your_dataset.user_summary` AS
SELECT 
    CASE 
        WHEN total_actions >= 100 THEN 'High Activity'
        WHEN total_actions >= 20 THEN 'Medium Activity'
        ELSE 'Low Activity'
    END as activity_level,
    COUNT(*) as user_count,
    AVG(total_actions) as avg_actions_per_user
FROM {{ ref('user_metrics') }}
GROUP BY activity_level;
```

2. Commit your changes:

```bash
git add sql/views/
git commit -m "Add user views with dependencies"
```

3. The post-commit hook automatically deploys views in the correct order!

### Manual Deployment

You can also run deployments manually:

```bash
# Deploy all views
bq-view-deploy

# Dry run (see what would be deployed)
bq-view-deploy --dry-run

# Deploy specific files only
bq-view-deploy --files sql/views/user_metrics.sql sql/views/sales.sql

# Use different config file
bq-view-deploy --config custom-config.yaml

```

### Testing Changes

Use dry run mode to test your SQL without deploying:

```bash
bq-view-deploy --dry-run
```

## ⚙️ Configuration

### config.yaml Options

```yaml
bigquery:
  project_id: "your-gcp-project-id"    # Required
  dataset_id: "your_dataset_name"       # Required (for reference)
  location: "US"                        # Optional, default: US

sql:
  views_directory: "sql/views"          # Directory to scan for view files
  
  include_patterns:                     # File patterns to include
    - "*.sql"
  
  exclude_patterns:                     # File patterns to exclude
    - "*.backup.sql"

deployment:
  dry_run: false                       # Dry run mode
  verbose: true                        # Verbose logging
```

### Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key
- `GOOGLE_CLOUD_PROJECT`: Default GCP project ID

## 🔗 dbt-like ref() Functionality

### Using ref() Syntax

Reference other views using Jinja2 template syntax:

```sql
-- Instead of hardcoding table references:
SELECT * FROM `project.dataset.other_view`

-- Use ref() for dynamic resolution:
SELECT * FROM {{ ref('other_view') }}
```

### Benefits

- **Automatic dependency resolution**: Views are deployed in the correct order
- **Environment flexibility**: References adapt to different projects/datasets
- **Maintainability**: Change table names in one place (the CREATE statement)
- **Validation**: Detect broken references before deployment

### Reference Resolution

The `ref()` function resolves view names using this logic:

1. **Exact match**: If the referenced view exists in your views directory
2. **Config defaults**: Uses `project_id` and `dataset_id` from `config.yaml`
3. **Cross-project**: Explicitly specify project: `{{ ref('view_name', project='other-project') }}`

### Dependency Validation

```bash
# Validate all references are correct
bq-view-deploy --validate-refs

# Show dependency graph and deployment order
bq-view-deploy --show-deps
```

### Example Dependency Chain

```sql
-- Base view (no dependencies)
-- sql/views/events.sql
CREATE OR REPLACE VIEW `project.dataset.events` AS
SELECT * FROM `project.raw.events_table`;

-- Depends on events
-- sql/views/user_sessions.sql  
CREATE OR REPLACE VIEW `project.dataset.user_sessions` AS
SELECT 
    user_id,
    COUNT(*) as session_count
FROM {{ ref('events') }}
GROUP BY user_id;

-- Depends on user_sessions
-- sql/views/user_summary.sql
CREATE OR REPLACE VIEW `project.dataset.user_summary` AS
SELECT 
    CASE WHEN session_count >= 10 THEN 'Active' ELSE 'Inactive' END as user_type,
    COUNT(*) as user_count
FROM {{ ref('user_sessions') }}
GROUP BY user_type;
```

**Deployment Order**: `events` → `user_sessions` → `user_summary`

## 🔧 Commands

### CLI Commands
| Command | Description |
|---------|-------------|
| `bq-view-deploy` | Deploy all SQL views |
| `bq-view-deploy --dry-run` | Preview deployments without executing |
| `bq-view-deploy --files FILE1 FILE2` | Deploy specific files only |
| `bq-view-deploy --validate-refs` | Validate all ref() references |
| `bq-view-deploy --show-deps` | Show dependency graph and deployment order |
| `bq-view-deploy --version` | Show version information |
| `bq-view-deploy --config FILE` | Use custom config file |
| `bq-view-deploy --help` | Show detailed help with examples |

### Make Commands
| Command | Description |
|---------|-------------|
| `make` or `make help` | Show available commands |
| `make deploy` | Deploy all views |
| `make dry-run` | Preview deployments |
| `make check` | Validate SQL syntax |
| `make setup` | Run setup script |
| `make clean` | Clean build artifacts |


## 🎯 Workflow Examples

### Adding a New View

```bash
# 1. Create SQL file
cat > sql/views/sales_summary.sql << EOF
CREATE OR REPLACE VIEW \`project.dataset.sales_summary\` AS
SELECT 
    DATE(order_date) as sale_date,
    SUM(amount) as total_sales,
    COUNT(*) as order_count
FROM \`project.dataset.orders\`
GROUP BY DATE(order_date);
EOF

# 2. Commit and auto-deploy
git add sql/views/sales_summary.sql
git commit -m "Add sales summary view"
# ✅ View automatically deployed to BigQuery!
```

### Updating an Existing View

```bash
# 1. Edit the SQL file
vim sql/views/user_summary.sql

# 2. Commit changes
git add sql/views/user_summary.sql
git commit -m "Update user summary view with new metrics"
# ✅ View automatically updated in BigQuery!
```

## 🚨 Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Re-authenticate with gcloud
gcloud auth application-default login

# Or check service account key path
echo $GOOGLE_APPLICATION_CREDENTIALS
```

#### Permission Errors
Ensure your account has these BigQuery permissions:
- `bigquery.datasets.get`
- `bigquery.tables.create`
- `bigquery.tables.update`
- `bigquery.tables.get`

#### Git Hook Not Running
```bash
# Check if hook is executable
ls -la .git/hooks/post-commit

# Make executable if needed
chmod +x .git/hooks/post-commit
```

#### View Deployment Failures
```bash
# Run with verbose output
uv run python -m bq_view_manager.main

# Check SQL syntax in BigQuery console
# Verify table references exist
```

### Debugging

Enable verbose logging in `config.yaml`:
```yaml
deployment:
  verbose: true
```

Or run with dry run to see what would be executed:
```bash
uv run python -m bq_view_manager.main --dry-run
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Commit your changes: `git commit -m 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy SQL coding! 🎉**
