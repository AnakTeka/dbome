-- User metrics view using ref() syntax (MODIFIED)
-- This demonstrates dbt-like functionality

CREATE OR REPLACE VIEW `your-project.your_dataset.user_metrics` AS
SELECT 
    user_id,
    COUNT(*) as total_actions,
    COUNT(DISTINCT DATE(action_timestamp)) as active_days,
    COUNT(DISTINCT session_id) as total_sessions,
    MAX(action_timestamp) as last_action_date,
    MIN(action_timestamp) as first_action_date,
    DATETIME_DIFF(MAX(action_timestamp), MIN(action_timestamp), DAY) as activity_span_days,
    COUNT(DISTINCT action_date) as unique_action_dates  -- ADDED: using new column from A
FROM {{ ref('user_actions') }}
GROUP BY user_id
HAVING total_actions >= 5  -- Only include users with meaningful activity 