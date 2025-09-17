import sqlite3
from datetime import datetime

# Connect to the SQLite database
conn = sqlite3.connect("ddialog.db")
cursor = conn.cursor()

# Add timestamp column to videos table without default
cursor.execute("ALTER TABLE videos ADD COLUMN timestamp DATETIME")

# Add timestamp column to processed_videos table without default
cursor.execute("ALTER TABLE processed_videos ADD COLUMN timestamp DATETIME")

# Backfill existing rows in videos table
cursor.execute("UPDATE videos SET timestamp = CURRENT_TIMESTAMP WHERE timestamp IS NULL")

# Backfill existing rows in processed_videos table
cursor.execute("UPDATE processed_videos SET timestamp = CURRENT_TIMESTAMP WHERE timestamp IS NULL")

# Commit the changes
conn.commit()

# Close the connection
conn.close()

print("Timestamp columns added to videos and processed_videos tables with backfill.")
