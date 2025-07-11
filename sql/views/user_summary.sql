-- User summary view with dependency chain
-- This references user_metrics, which references user_actions

CREATE OR REPLACE VIEW `your-project.your_dataset.user_summary` AS
SELECT 
    CASE 
        WHEN total_actions >= 100 THEN 'High Activity'
        WHEN total_actions >= 20 THEN 'Medium Activity'
        ELSE 'Low Activity'
    END as activity_level,
    COUNT(*) as user_count,
    AVG(total_actions) as avg_actions_per_user,
    AVG(active_days) as avg_active_days,
    AVG(total_sessions) as avg_sessions_per_user,
    AVG(activity_span_days) as avg_activity_span_days
FROM {{ ref('user_metrics') }}
GROUP BY activity_level
ORDER BY 
    CASE activity_level
        WHEN 'High Activity' THEN 1
        WHEN 'Medium Activity' THEN 2
        ELSE 3
    END; 