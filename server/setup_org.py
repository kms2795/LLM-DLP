import secrets
import database

conn = database.get_connection()
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        join_code VARCHAR(20) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id)")
cur.execute("ALTER TABLE detection_logs ADD COLUMN IF NOT EXISTS org_id INTEGER REFERENCES organizations(id)")
conn.commit()
print("테이블 준비 완료")


def make_code(n=8):
    # 헷갈리는 글자(O, 0, I, 1)는 뺐습니다. secrets는 추측하기 어려운 난수를 씁니다.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


cur.execute("SELECT COUNT(*) FROM organizations")
if cur.fetchone()[0] == 0:
    name = input("조직 이름: ").strip() or "기본 조직"
    code = make_code()

    cur.execute(
        "INSERT INTO organizations (name, join_code) VALUES (%s, %s) RETURNING id",
        (name, code),
    )
    org_id = cur.fetchone()[0]

    # 기존 사용자와 로그를 이 조직으로 옮깁니다
    cur.execute("UPDATE users SET org_id = %s WHERE org_id IS NULL", (org_id,))
    cur.execute("UPDATE detection_logs SET org_id = %s WHERE org_id IS NULL", (org_id,))
    conn.commit()

    print(f"\n조직 '{name}' 생성")
    print(f"가입 코드: {code}")
    print("기존 사용자와 로그를 이 조직으로 옮겼습니다.")

cur.execute("""
    SELECT o.id, o.name, o.join_code, COUNT(u.id)
    FROM organizations o
    LEFT JOIN users u ON u.org_id = o.id
    GROUP BY o.id, o.name, o.join_code
    ORDER BY o.id
""")
print("\n조직 목록")
for oid, name, code, n in cur.fetchall():
    print(f"  [{oid}] {name} · 가입코드 {code} · 사용자 {n}명")

cur.close()
conn.close()
