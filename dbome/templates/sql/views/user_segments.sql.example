-- User segments view (MODIFIED FINAL - C)
-- This demonstrates another view that depends on A

SELECT 
    user_id,
    COUNT(DISTINCT action_type) as unique_action_types,
    CASE 
        WHEN COUNT(DISTINCT action_type) >= 5 THEN 'Power User'
        WHEN COUNT(DISTINCT action_type) >= 3 THEN 'Regular User'
        ELSE 'Light User'
    END as user_segment,
    COUNT(DISTINCT page_url) as pages_visited,
    SUM(CASE WHEN action_type = 'purchase' THEN 1 ELSE 0 END) as purchase_count,
    MAX(action_timestamp) as last_segment_activity  -- NEW: segment-specific activity
FROM {{ ref('user_actions') }}
GROUP BY user_id
HAVING COUNT(*) >= 5 