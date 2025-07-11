-- Base view: user_actions (MODIFIED AGAIN - A)
-- This view will be referenced by multiple views (B and C) using ref() syntax

SELECT 
    user_id,
    action_type,
    action_timestamp,
    session_id,
    page_url,
    user_agent,
    DATE(action_timestamp) as action_date  -- ADDED: new column
FROM `your-project.raw_data.events`
WHERE action_type IS NOT NULL
    AND user_id IS NOT NULL
    AND DATE(action_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) 