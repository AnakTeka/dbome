-- Example BigQuery view for testing
-- This demonstrates the view management system
CREATE OR REPLACE VIEW `your-project-id.views.example_view` AS

SELECT
  user_id,
  event_type,
  timestamp
FROM
  `your-project-id.source_dataset.events_table`
WHERE
  date(timestamp) >= '2024-01-01'