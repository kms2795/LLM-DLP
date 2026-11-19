import database

conn = database.get_connection()
cur = conn.cursor()

cur.execute("ALTER TABLE detection_logs ADD COLUMN IF NOT EXISTS evidence TEXT")
cur.execute("ALTER TABLE detection_logs ALTER COLUMN user_text DROP NOT NULL")
conn.commit()

cur.execute(
    "SELECT column_name, is_nullable FROM information_schema.columns "
    "WHERE table_name='detection_logs' ORDER BY ordinal_position"
)
print("--- 현재 컬럼 ---")
for name, nullable in cur.fetchall():
    print(f"{name:15} nullable={nullable}")

cur.close()
conn.close()
