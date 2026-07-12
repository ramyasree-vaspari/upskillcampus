import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM students WHERE has_voted=1")

conn.commit()
conn.close()

print("Voted records deleted successfully")