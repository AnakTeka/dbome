-- User analytics view - MODIFIED - depends on MULTIPLE views (B and C)
-- This demonstrates a single view with multiple ref() references

CREATE OR REPLACE VIEW `your-project.your_dataset.user_analytics` AS
SELECT 
    m.user_id,
    m.total_actions,
    m.active_days,
    m.last_action_date,
    s.user_segment,
    s.unique_action_types,
    CASE 
        WHEN m.total_actions > 100 AND s.user_segment = 'Power User' THEN 'VIP'
        WHEN m.total_actions > 50 THEN 'Premium'
        ELSE 'Standard'
    END as user_tier,
    -- NEW: Add combined score using data from both dependencies
    (m.total_actions * 0.7 + s.unique_action_types * 10) as engagement_score
FROM {{ ref('user_metrics') }} m  -- Reference to user_metrics (B)
JOIN {{ ref('user_segments') }} s  -- Reference to user_segments (C)
    ON m.user_id = s.user_id
WHERE m.total_actions >= 5; 