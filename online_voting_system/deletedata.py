"""
deletedata.py  -  Admin utility to reset voting data.
Clears all registered users and resets every candidate vote count to 0.
Run from the project root:  python deletedata.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def reset_data():
    if not os.path.exists(DB_PATH):
        print("ERROR: database.db not found. Run app.py first to initialise the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM users")
    users_deleted = c.rowcount

    c.execute("UPDATE candidates SET vote_count = 0")
    candidates_reset = c.rowcount

    conn.commit()
    conn.close()

    print(f"Deleted {users_deleted} registered voter(s).")
    print(f"Reset vote count to 0 for {candidates_reset} candidate(s).")
    print("Database is clean and ready for a fresh election.")

if __name__ == "__main__":
    confirm = input("This will DELETE all voters and reset all votes. Type yes to confirm: ").strip().lower()
    if confirm == "yes":
        reset_data()
    else:
        print("Aborted - no changes made.")
