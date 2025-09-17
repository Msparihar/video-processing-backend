import sqlite3
from datetime import datetime

conn = sqlite3.connect("ddialog.db")
cursor = conn.cursor()

cursor.execute(
    "SELECT id, original_video_id, filename, timestamp FROM processed_videos ORDER BY timestamp DESC LIMIT 5"
)
rows = cursor.fetchall()

print("Recent processed videos:")
for row in rows:
    print(row)

conn.close()
