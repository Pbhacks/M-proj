# init_db.py
import sqlite3

conn = sqlite3.connect('rbc_results.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS rbc_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    raw_count INTEGER,
    rbc_per_uL INTEGER,
    comment TEXT,
    timestamp TEXT
)''')

conn.commit()
conn.close()

print("[✓] Database initialized successfully.")
