# dbome - dbt at home 🏠

A dbt-like tool with simplified SQL syntax, dependency resolution, and git-based workflows

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

### 🎯 One-Line Install (Recommended)

The easiest way to get started - **perfect for SageMaker users** and quick setup:

> **💡 Why this approach?** Data scientists working in SageMaker, Colab, or other hosted environments need a quick, reliable way to set up tools without worrying about Python package management. This installer handles everything for you - just create a directory and run one command!

```bash
# Simply run this in the directory where you want your dbome project
curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash
```

This will:
- ✅ Install `uv` (if not already installed)
- ✅ Create a Python project with `dbome` as dependency
- ✅ Initialize dbome project with templates
- ✅ Set up git repository with auto-deployment hooks
- ✅ Provide example SQL files to get you started

**Perfect for SageMaker, Colab, or any Linux/macOS environment!**

### 🚀 SageMaker Quick Start

For your DS friend using SageMaker:

1. **Open SageMaker terminal** 
2. **Create directory**: `mkdir my-bq-project && cd my-bq-project`
3. **Install dbome**: `curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash`
4. **Configure BigQuery**: Edit `config.yaml` with your project details
5. **Deploy views**: `uv run dbome run --dry` (test) then `uv run dbome run` (deploy)

Zero Python environment management needed! 🎉

### 📦 Manual Installation

If you prefer to install manually:

```bash
# Option 1: Install via pip
mkdir my-dwh-project
cd my-dwh-project
pip install dbome
dbome init

# Option 2: Install via uv (recommended for Python projects)
mkdir my-dwh-project
cd my-dwh-project
uv init
uv add dbome
uv run dbome init
```

### 🔑 Setup Authentication

```bash
# Authenticate with Google Cloud
gcloud auth application-default login

# Test your setup
uv run dbome run --dry  # if using uv
# or
dbome run --dry         # if using pip
```

## 📝 Quick Start

### 1. One-Line Install (Perfect for SageMaker! 🔬)
```bash
# In SageMaker terminal or any Linux environment:
mkdir my-analytics-project
cd my-analytics-project
curl -sSL https://raw.githubusercontent.com/your-repo/dbome/main/install.sh | bash
```

**That's it!** ✨ Everything is set up and ready to go.

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
uv run dbome run --dry

# Deploy to BigQuery
uv run dbome run

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

**✅ New way (dbome):**
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
| `dbome` | Show help |
| `dbome init` | Initialize a new project in current directory |
| `dbome run` | Deploy all views |
| `dbome compile` | Compile templates |
| `dbome deps` | Show dependencies |
| `dbome validate` | Validate references |

### Project Commands (inside your project)

| Command | Description |
|---------|-------------|
| `uv run dbome` | Show help |
| `uv run dbome run` | Deploy all views |
| `uv run dbome run --dry` | Preview deployments |
| `uv run dbome run --select FILE1 FILE2` | Deploy specific files only |
| `uv run dbome validate` | Validate all ref() references |
| `uv run dbome deps` | Show dependency graph and deployment order |
| `uv run dbome compile` | Compile templates to compiled/ directory |
| `uv run dbome COMMAND --config FILE` | Use custom config file |

> **Note**: If you installed via pip, replace `uv run dbome` with just `dbome`

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

When you run `dbome init`, you get:

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
dbome --compile-only
```

Files are saved to `compiled/views/` with resolved `ref()` calls:

```sql
-- compiled/views/user_metrics.sql
-- Compiled SQL from: sql/views/user_metrics.sql
-- Generated by dbome (dbt at home)
-- DO NOT EDIT: This file is auto-generated

CREATE OR REPLACE VIEW `your-project.analytics.user_metrics` AS
SELECT user_id, COUNT(*) as events  
FROM `your-project.analytics.user_events`  -- ref() resolved!
GROUP BY user_id
```

### Dependency Visualization

```bash
dbome deps
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
dbome validate
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
