-- Create forum_threads table
CREATE TABLE forum_threads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Announcements', 'General Discussion', 'Help & Support', 'Feedback & Suggestions', 'Introductions', 'Off-Topic / Lounge', 'Bug Reports')),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    likes INTEGER DEFAULT 0 NOT NULL,
    comments INTEGER DEFAULT 0 NOT NULL,
    is_pinned BOOLEAN DEFAULT false NOT NULL,
    is_locked BOOLEAN DEFAULT false NOT NULL
);

-- Create forum_comments table
CREATE TABLE forum_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    parent_id UUID REFERENCES forum_comments(id) ON DELETE CASCADE,
    likes INTEGER DEFAULT 0 NOT NULL
);

-- Create forum_likes table
CREATE TABLE forum_likes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES forum_threads(id) ON DELETE CASCADE,
    comment_id UUID REFERENCES forum_comments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT check_like_target CHECK (
        (thread_id IS NOT NULL AND comment_id IS NULL) OR
        (thread_id IS NULL AND comment_id IS NOT NULL)
    ),
    CONSTRAINT unique_user_like UNIQUE (user_id, thread_id, comment_id)
);

-- Create indexes for better query performance
CREATE INDEX idx_forum_threads_user_id ON forum_threads(user_id);
CREATE INDEX idx_forum_threads_category ON forum_threads(category);
CREATE INDEX idx_forum_threads_created_at ON forum_threads(created_at);
CREATE INDEX idx_forum_comments_thread_id ON forum_comments(thread_id);
CREATE INDEX idx_forum_comments_user_id ON forum_comments(user_id);
CREATE INDEX idx_forum_comments_parent_id ON forum_comments(parent_id);
CREATE INDEX idx_forum_likes_user_id ON forum_likes(user_id);
CREATE INDEX idx_forum_likes_thread_id ON forum_likes(thread_id);
CREATE INDEX idx_forum_likes_comment_id ON forum_likes(comment_id);

-- Create function to update thread comment count
CREATE OR REPLACE FUNCTION update_thread_comment_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE forum_threads
        SET comments = comments + 1,
            updated_at = now()
        WHERE id = NEW.thread_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE forum_threads
        SET comments = comments - 1,
            updated_at = now()
        WHERE id = OLD.thread_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for comment count
CREATE TRIGGER update_thread_comment_count
AFTER INSERT OR DELETE ON forum_comments
FOR EACH ROW
EXECUTE FUNCTION update_thread_comment_count();

-- Create function to update thread/comment like count
CREATE OR REPLACE FUNCTION update_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.thread_id IS NOT NULL THEN
            UPDATE forum_threads
            SET likes = likes + 1,
                updated_at = now()
            WHERE id = NEW.thread_id;
        ELSIF NEW.comment_id IS NOT NULL THEN
            UPDATE forum_comments
            SET likes = likes + 1,
                updated_at = now()
            WHERE id = NEW.comment_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        IF OLD.thread_id IS NOT NULL THEN
            UPDATE forum_threads
            SET likes = likes - 1,
                updated_at = now()
            WHERE id = OLD.thread_id;
        ELSIF OLD.comment_id IS NOT NULL THEN
            UPDATE forum_comments
            SET likes = likes - 1,
                updated_at = now()
            WHERE id = OLD.comment_id;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for like count
CREATE TRIGGER update_like_count
AFTER INSERT OR DELETE ON forum_likes
FOR EACH ROW
EXECUTE FUNCTION update_like_count();

-- Create RLS policies
ALTER TABLE forum_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_likes ENABLE ROW LEVEL SECURITY;

-- Forum threads policies
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

-- Forum comments policies
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

-- Forum likes policies
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