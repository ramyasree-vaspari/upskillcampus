import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            voter_id TEXT UNIQUE NOT NULL,
            face_encoding TEXT NOT NULL,
            has_voted BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    # Create Candidates table
    c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            party TEXT NOT NULL,
            vote_count INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # Insert initial candidates if empty
    c.execute('SELECT COUNT(*) FROM candidates')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO candidates (name, party) VALUES ('Revanth Reddy', 'Congress')")
        c.execute("INSERT INTO candidates (name, party) VALUES ('KCR', 'BRS')")
        c.execute("INSERT INTO candidates (name, party) VALUES ('Sanjay', 'BJP')")
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
