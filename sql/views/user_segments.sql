-- User segments view (MODIFIED - C) - also depends on A  
-- This demonstrates multiple views depending on the same base view

CREATE OR REPLACE VIEW `your-project.your_dataset.user_segments` AS
SELECT 
    user_id,
    CASE 
        WHEN COUNT(*) >= 50 THEN 'Power User'
        WHEN COUNT(*) >= 10 THEN 'Active User'
        ELSE 'Casual User'
    END as user_segment,
    COUNT(*) as total_actions,
    COUNT(DISTINCT action_type) as unique_action_types,
    MIN(action_date) as first_seen_date,
    MAX(action_date) as last_seen_date
FROM {{ ref('user_actions') }}
GROUP BY user_id; 