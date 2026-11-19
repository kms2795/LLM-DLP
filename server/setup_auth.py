import os
import secrets
import getpass
import bcrypt
import database

HERE = os.path.dirname(os.path.abspath(__file__))
SECRET_PATH = os.path.join(HERE, ".jwt_secret")

# 1. JWT 비밀키 — 코드에 박지 않고 파일로 따로 둡니다
if not os.path.exists(SECRET_PATH):
    with open(SECRET_PATH, "w") as f:
        f.write(secrets.token_urlsafe(48))
    os.chmod(SECRET_PATH, 0o600)
    print("JWT 비밀키 생성 완료 (.jwt_secret)")
else:
    print("JWT 비밀키가 이미 있습니다")

conn = database.get_connection()
cur = conn.cursor()

# 2. 사용자 테이블
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 3. 탐지 로그에 "누가" 를 추가
cur.execute("""
    ALTER TABLE detection_logs
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
""")
conn.commit()
print("테이블 준비 완료")

# 4. 관리자 계정
cur.execute("SELECT COUNT(*) FROM users")
if cur.fetchone()[0] == 0:
    print("\n관리자 계정을 만듭니다.")
    username = input("아이디: ").strip()
    password = getpass.getpass("비밀번호 (화면에 안 보입니다): ")

    if len(password) < 8:
        print("비밀번호는 8자 이상이어야 합니다. 다시 실행해 주세요.")
    else:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'admin')",
            (username, pw_hash),
        )
        conn.commit()
        print(f"관리자 계정 '{username}' 생성 완료")
else:
    cur.execute("SELECT username, role FROM users ORDER BY id")
    print("\n기존 사용자:")
    for u, r in cur.fetchall():
        print(f"  {u} ({r})")

cur.close()
conn.close()
