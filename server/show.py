import database

c = database.get_connection().cursor()
c.execute("SELECT id, masked_text, evidence, risk_level FROM detection_logs ORDER BY id DESC LIMIT 3")
for row in c.fetchall():
    print(row)
    print("-" * 60)
PYEOFcat > show.py << 'PYEOF'
import database

c = database.get_connection().cursor()
c.execute("SELECT id, masked_text, evidence, risk_level FROM detection_logs ORDER BY id DESC LIMIT 3")
for row in c.fetchall():
    print(row)
    print("-" * 60)
