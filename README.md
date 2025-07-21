# dbome - dbt at home 🏠

> *"Mom, can we have dbt?"* • *"We have dbt at home."* • **dbt at home:** 🏠

A **dbt-like tool** for BigQuery with simplified SQL syntax, automatic dependency resolution, and git-based workflows.

## ✨ **Why dbome?**

- **📝 Write clean SQL** - No CREATE OR REPLACE VIEW boilerplate
- **🔄 Use `{{ ref('view_name') }}`** - Just like dbt
- **📊 Automatic deployment order** - Dependencies resolved automatically  
- **🚀 One-command deployment** - `dbome run` deploys everything
- **⚡ Git-based workflow** - Auto-deploy on commit
- **🎯 Perfect for SageMaker** - Works great in hosted environments

## 🚀 **Quick Start**

### 1. Install (One Command)
```bash
# Create your project directory
mkdir my-analytics-project && cd my-analytics-project

# Install dbome (handles everything automatically)
curl -sSL https://raw.githubusercontent.com/AnakTeka/dbome/main/install.sh | bash
```

### 2. Configure BigQuery
```bash
# Copy template and edit with your details
cp config.yaml.template config.yaml
```

Edit `config.yaml`:
```yaml
bigquery:
  project_id: "your-gcp-project-id"
  dataset_id: "analytics"
  location: "US"

# Choose ONE authentication method:

# Option A: Default credentials (recommended for local)
# gcloud auth application-default login

# Option B: Service account file
# google_application_credentials: "/path/to/service-account.json"

# Option C: AWS SSM Parameter Store (perfect for SageMaker!)
# aws_ssm_credentials_parameter: "/your/ssm/parameter/name"
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

### 4. Deploy
```bash
# Test first (safe)
uv run dbome run --dry

# Deploy to BigQuery  
uv run dbome run
```

**That's it!** 🎉 Your view is now live in BigQuery.

## 📖 **Core Concepts**

### **Before & After**

**❌ Traditional BigQuery:**
```sql
CREATE OR REPLACE VIEW `project.dataset.user_metrics` AS
SELECT user_id, COUNT(*) as events
FROM `project.dataset.user_events`  
GROUP BY user_id;
```

**✅ With dbome:**
```sql
-- File: sql/views/user_metrics.sql
SELECT user_id, COUNT(*) as events  
FROM {{ ref('user_events') }}
GROUP BY user_id
```

### **Automatic Dependencies**
dbome figures out the order automatically:

```sql
-- sql/views/events.sql (deployed first)
SELECT * FROM `project.raw.events`

-- sql/views/users.sql (deployed second)
SELECT user_id, COUNT(*) as event_count
FROM {{ ref('events') }}
GROUP BY user_id

-- sql/views/summary.sql (deployed third)  
SELECT user_type, COUNT(*) as user_count
FROM {{ ref('users') }}
GROUP BY user_type
```

**Deployment order**: `events` → `users` → `summary` ✅

### **Git Integration**
Auto-deploy when you commit:
```bash
git add sql/views/new_view.sql
git commit -m "Add new view"
# 🚀 Automatically deployed to BigQuery!
```

## 🔧 **Commands**

| Command | Description |
|---------|-------------|
| `uv run dbome run` | Deploy all views |
| `uv run dbome run --dry` | Preview what would be deployed |
| `uv run dbome run view_name` | Deploy specific view |
| `uv run dbome validate` | Check all references are valid |
| `uv run dbome deps` | Show dependency graph |
| `uv run dbome compile` | Generate compiled SQL files |

## 📁 **Project Structure**

```
my-project/
├── sql/views/              # Your SQL view files
│   ├── user_events.sql
│   └── user_metrics.sql
├── config.yaml            # Your configuration  
├── config.yaml.template   # Template with examples
├── compiled/views/         # Generated SQL (auto-created)
└── .git/hooks/post-commit # Auto-deployment hook
```

## 🎯 **Perfect for SageMaker Users**

AWS SSM Parameter Store integration makes this ideal for SageMaker:

1. **Store your service account JSON** in AWS SSM Parameter Store (base64 encoded)
2. **Configure dbome**:
   ```yaml
   aws_ssm_credentials_parameter: "/sagemaker/production/GOOGLE_CREDS"
   ```
3. **Deploy with confidence** - credentials retrieved securely from SSM

## 🆘 **Troubleshooting**

### Installation Issues
```bash
# If uv command not found after install:
source $HOME/.local/bin/env

# Manual installation alternative:
pip install git+https://github.com/AnakTeka/dbome.git
dbome init
```

### Authentication Issues  
```bash
# Test your connection:
uv run dbome run --dry

# For gcloud auth:
gcloud auth application-default login

# Check your config:
cat config.yaml
```

## 📋 **Alternative Installation**

If you prefer manual setup:
```bash
# Via pip
pip install git+https://github.com/AnakTeka/dbome.git
dbome init

# Via uv  
uv add git+https://github.com/AnakTeka/dbome.git
uv run dbome init
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch  
3. Add tests for your changes
4. Submit a pull request

## 📜 **License**

MIT License - see LICENSE file for details.

---

**Made with ❤️ for the BigQuery community** | Inspired by dbt, optimized for simplicity 