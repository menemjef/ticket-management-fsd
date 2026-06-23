import mysql.connector
from utils import db

def init_database():
    try:
        # Connect to the database using the credentials from utils.py
        conn = mysql.connector.connect(**db)
        cursor = conn.cursor()

        print("Connected to database. Starting migration...")

        # 1. Create Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            firebase_uid VARCHAR(255) UNIQUE,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            role VARCHAR(50) DEFAULT 'user'
        )
        """)
        print("- Users table ensured.")

        # 2. Create Tickets Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'Open',
            user_id INT,
            attachment_name VARCHAR(255),
            attachment_path VARCHAR(500),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("- Tickets table ensured.")

        # 3. Create TicketHistory Table (No auto-increment on ID, it mirrors tickets)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickethistory (
            id INT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'Open',
            user_id INT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)
        print("- TicketHistory table ensured.")

        # 4. Create Triggers safely (Drop first to avoid 'already exists' errors if schema changes)
        cursor.execute("DROP TRIGGER IF EXISTS after_ticket_insert")
        cursor.execute("""
        CREATE TRIGGER after_ticket_insert
        AFTER INSERT ON tickets
        FOR EACH ROW
        BEGIN
            INSERT IGNORE INTO tickethistory (id, title, description, status, user_id)
            VALUES (NEW.id, NEW.title, NEW.description, NEW.status, NEW.user_id);
        END
        """)

        cursor.execute("DROP TRIGGER IF EXISTS after_ticket_update")
        cursor.execute("""
        CREATE TRIGGER after_ticket_update
        AFTER UPDATE ON tickets
        FOR EACH ROW
        BEGIN
            UPDATE tickethistory SET status = NEW.status WHERE id = NEW.id;
        END
        """)
        print("- Triggers ensured.")

        # 5. Data Seeding
        # Seed an admin user if it doesn't exist
        admin_email = "admin@example.com"
        cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        admin_user = cursor.fetchone()

        if not admin_user:
            cursor.execute(
                "INSERT INTO users (firebase_uid, username, email, role) VALUES (%s, %s, %s, %s)",
                ("seeded_admin_uid_123", "System Admin", admin_email, "admin")
            )
            admin_id = cursor.lastrowid
            print(f"- Seeded Admin user with ID: {admin_id}")
            
            # Seed dummy tickets for the new admin
            dummy_tickets = [
                ("Login page bug", "The login button does not respond on mobile devices.", "Open", admin_id),
                ("Dashboard slow", "Dashboard takes 10+ seconds to load ticket list.", "Open", admin_id),
                ("Password reset broken", "Password reset email never arrives.", "In Progress", admin_id),
                ("Add dark mode", "Users are requesting a dark mode toggle.", "Open", admin_id),
                ("Export to CSV", "Admin needs to export ticket data to CSV format.", "Open", admin_id)
            ]
            
            cursor.executemany(
                "INSERT INTO tickets (title, description, status, user_id) VALUES (%s, %s, %s, %s)",
                dummy_tickets
            )
            print("- Seeded 5 dummy tickets.")
        else:
            print("- Admin user already exists. Skipping seeding to preserve existing data.")

        conn.commit()
        print("Database migration and seeding completed successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    init_database()
