-- Example view to demonstrate auto-deployment
-- This is a simple view for testing purposes

SELECT 
    id,
    name,
    CURRENT_TIMESTAMP() as created_at,
    'example' as source_table
FROM `your-project.your_dataset.example_table`
WHERE id IS NOT NULL