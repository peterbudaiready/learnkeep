-- First, create a temporary column to store the new category
ALTER TABLE forum_threads ADD COLUMN new_category TEXT;

-- Update existing categories to new ones based on content
UPDATE forum_threads
SET new_category = CASE
    WHEN category = 'Updates' THEN 'Announcements'
    WHEN category = 'Course Generation' THEN 'General Discussion'
    WHEN category = 'Knowledge' THEN 'Help & Support'
    ELSE 'General Discussion'  -- Default for any other categories
END;

-- Drop the old category column
ALTER TABLE forum_threads DROP COLUMN category;

-- Rename the new column to category
ALTER TABLE forum_threads RENAME COLUMN new_category TO category;

-- Add the new check constraint
ALTER TABLE forum_threads ADD CONSTRAINT forum_threads_category_check 
    CHECK (category IN ('Announcements', 'General Discussion', 'Help & Support', 'Feedback & Suggestions', 'Introductions', 'Off-Topic / Lounge', 'Bug Reports'));

-- Make the category column NOT NULL
ALTER TABLE forum_threads ALTER COLUMN category SET NOT NULL;

-- Update the index on category
DROP INDEX IF EXISTS idx_forum_threads_category;
CREATE INDEX idx_forum_threads_category ON forum_threads(category); 