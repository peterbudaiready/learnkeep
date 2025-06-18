-- Enable RLS on forum tables
ALTER TABLE forum_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_likes ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Anyone can view threads" ON forum_threads;
DROP POLICY IF EXISTS "Authenticated users can create threads" ON forum_threads;
DROP POLICY IF EXISTS "Users can update their own threads" ON forum_threads;
DROP POLICY IF EXISTS "Users can delete their own threads" ON forum_threads;

DROP POLICY IF EXISTS "Anyone can view comments" ON forum_comments;
DROP POLICY IF EXISTS "Authenticated users can create comments" ON forum_comments;
DROP POLICY IF EXISTS "Users can update their own comments" ON forum_comments;
DROP POLICY IF EXISTS "Users can delete their own comments" ON forum_comments;

DROP POLICY IF EXISTS "Anyone can view likes" ON forum_likes;
DROP POLICY IF EXISTS "Authenticated users can create likes" ON forum_likes;
DROP POLICY IF EXISTS "Users can delete their own likes" ON forum_likes;

-- Create new policies for forum_threads
CREATE POLICY "Anyone can view threads"
    ON forum_threads FOR SELECT
    USING (true);

CREATE POLICY "Authenticated users can create threads"
    ON forum_threads FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Users can update their own threads"
    ON forum_threads FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own threads"
    ON forum_threads FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Create policies for forum_comments
CREATE POLICY "Anyone can view comments"
    ON forum_comments FOR SELECT
    USING (true);

CREATE POLICY "Authenticated users can create comments"
    ON forum_comments FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Users can update their own comments"
    ON forum_comments FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own comments"
    ON forum_comments FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Create policies for forum_likes
CREATE POLICY "Anyone can view likes"
    ON forum_likes FOR SELECT
    USING (true);

CREATE POLICY "Authenticated users can create likes"
    ON forum_likes FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Users can delete their own likes"
    ON forum_likes FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id); 