-- Create support_tickets table
CREATE TABLE support_tickets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Technical Issue', 'Course Problem', 'Account Issue', 'Billing', 'Other')),
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Urgent')),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    resolved_at TIMESTAMPTZ,
    assigned_to UUID REFERENCES auth.users(id),
    response TEXT,
    response_at TIMESTAMPTZ
);

-- Create support_ticket_attachments table
CREATE TABLE support_ticket_attachments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_data BYTEA NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create support_ticket_history table
CREATE TABLE support_ticket_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    description TEXT NOT NULL,
    performed_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    performed_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status);
CREATE INDEX idx_support_tickets_category ON support_tickets(category);
CREATE INDEX idx_support_tickets_created_at ON support_tickets(created_at);
CREATE INDEX idx_support_ticket_attachments_ticket_id ON support_ticket_attachments(ticket_id);
CREATE INDEX idx_support_ticket_history_ticket_id ON support_ticket_history(ticket_id);

-- Create function to update ticket history
CREATE OR REPLACE FUNCTION update_ticket_history()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO support_ticket_history (ticket_id, action, description, performed_by)
        VALUES (NEW.id, 'Created', 'Ticket created', NEW.user_id);
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status THEN
            INSERT INTO support_ticket_history (ticket_id, action, description, performed_by)
            VALUES (NEW.id, 'Status Changed', 'Status changed from ' || OLD.status || ' to ' || NEW.status, 
                   COALESCE(NEW.assigned_to, NEW.user_id));
        END IF;
        IF OLD.response IS NULL AND NEW.response IS NOT NULL THEN
            INSERT INTO support_ticket_history (ticket_id, action, description, performed_by)
            VALUES (NEW.id, 'Response Added', 'Response added to ticket', 
                   COALESCE(NEW.assigned_to, NEW.user_id));
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for ticket history
CREATE TRIGGER update_ticket_history
AFTER INSERT OR UPDATE ON support_tickets
FOR EACH ROW
EXECUTE FUNCTION update_ticket_history();

-- Enable Row Level Security
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_ticket_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_ticket_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for support_tickets
CREATE POLICY "Users can view their own tickets"
    ON support_tickets FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create tickets"
    ON support_tickets FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tickets"
    ON support_tickets FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Create RLS policies for support_ticket_attachments
CREATE POLICY "Users can view their own ticket attachments"
    ON support_ticket_attachments FOR SELECT
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM support_tickets
        WHERE support_tickets.id = support_ticket_attachments.ticket_id
        AND support_tickets.user_id = auth.uid()
    ));

CREATE POLICY "Users can add attachments to their tickets"
    ON support_ticket_attachments FOR INSERT
    TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM support_tickets
        WHERE support_tickets.id = support_ticket_attachments.ticket_id
        AND support_tickets.user_id = auth.uid()
    ));

-- Create RLS policies for support_ticket_history
CREATE POLICY "Users can view their own ticket history"
    ON support_ticket_history FOR SELECT
    TO authenticated
    USING (EXISTS (
        SELECT 1 FROM support_tickets
        WHERE support_tickets.id = support_ticket_history.ticket_id
        AND support_tickets.user_id = auth.uid()
    ));

-- Create admin role and policies
CREATE ROLE support_admin;

-- Grant admin access to all support tables
GRANT ALL ON support_tickets TO support_admin;
GRANT ALL ON support_ticket_attachments TO support_admin;
GRANT ALL ON support_ticket_history TO support_admin;

-- Create admin policies
CREATE POLICY "Admins can view all tickets"
    ON support_tickets FOR SELECT
    TO support_admin
    USING (true);

CREATE POLICY "Admins can update all tickets"
    ON support_tickets FOR UPDATE
    TO support_admin
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Admins can delete tickets"
    ON support_tickets FOR DELETE
    TO support_admin
    USING (true);

-- Create function to notify ticket updates
CREATE OR REPLACE FUNCTION notify_ticket_update()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status != OLD.status OR NEW.response IS NOT NULL THEN
        -- Here you can add notification logic (email, push notification, etc.)
        -- For now, we'll just update the updated_at timestamp
        NEW.updated_at = now();
        
        IF NEW.status = 'Resolved' AND OLD.status != 'Resolved' THEN
            NEW.resolved_at = now();
        END IF;
        
        IF NEW.response IS NOT NULL AND OLD.response IS NULL THEN
            NEW.response_at = now();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for ticket updates
CREATE TRIGGER notify_ticket_update
BEFORE UPDATE ON support_tickets
FOR EACH ROW
EXECUTE FUNCTION notify_ticket_update(); 