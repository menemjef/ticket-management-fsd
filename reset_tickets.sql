-- ============================================================
-- Reset tickets & tickethistory with matching IDs
-- and add triggers so they ALWAYS stay in sync.
-- Run this in MySQL Workbench or the mysql CLI.
-- ============================================================

-- 1. Drop old tables
DROP TABLE IF EXISTS tickethistory;
DROP TABLE IF EXISTS tickets;

-- 2. Recreate tickets table
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'Open',
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 3. Recreate tickethistory table (id is NOT auto_increment — it mirrors tickets.id)
CREATE TABLE tickethistory (
    id INT PRIMARY KEY,           -- NO auto_increment! We copy from tickets.
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'Open',
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. Create trigger: when a ticket is INSERTED into tickets,
--    automatically copy it into tickethistory with the SAME id.
--    This means your Python code's second INSERT into tickethistory
--    will be a duplicate — so we use INSERT IGNORE to silently skip it.
DELIMITER //

CREATE TRIGGER after_ticket_insert
AFTER INSERT ON tickets
FOR EACH ROW
BEGIN
    INSERT IGNORE INTO tickethistory (id, title, description, status, user_id)
    VALUES (NEW.id, NEW.title, NEW.description, NEW.status, NEW.user_id);
END//

-- 5. Create trigger: when a ticket's status is UPDATED in tickets,
--    automatically update it in tickethistory too.
CREATE TRIGGER after_ticket_update
AFTER UPDATE ON tickets
FOR EACH ROW
BEGIN
    UPDATE tickethistory SET status = NEW.status WHERE id = NEW.id;
END//

DELIMITER ;

-- 6. Insert sample data (tickethistory will be auto-populated by the trigger!)
--    Replace user_id values with actual user IDs from your users table.
--    Check your user IDs first:  SELECT id, username FROM users;

INSERT INTO tickets (title, description, status, user_id) VALUES
('Login page bug', 'The login button does not respond on mobile devices.', 'Open', 1),
('Dashboard slow', 'Dashboard takes 10+ seconds to load ticket list.', 'Open', 1),
('Password reset broken', 'Password reset email never arrives.', 'In Progress', 1),
('Add dark mode', 'Users are requesting a dark mode toggle.', 'Open', 1),
('Export to CSV', 'Admin needs to export ticket data to CSV format.', 'Open', 1);

-- 7. Verify both tables have matching IDs and statuses
SELECT 'tickets' AS source, id, title, status FROM tickets
UNION ALL
SELECT 'tickethistory' AS source, id, title, status FROM tickethistory
ORDER BY id, source;
