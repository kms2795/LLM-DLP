import getpass
import bcrypt
import database

username = input("아이디: ").strip()
password = getpass.getpass("비밀번호 (화면에 안 보입니다): ")
role = input("역할 [member]: ").strip() or "member"

if len(password) < 8:
    print("비밀번호는 8자 이상이어야 합니다.")
elif role not in ("admin", "member"):
    print("역할은 admin 또는 member만 됩니다.")
else:
    conn = database.get_connection()
    cur = conn.cursor()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (username, pw_hash, role),
        )
        conn.commit()
        print(f"'{username}' ({role}) 생성 완료")
    except Exception as e:
        print("실패:", e)
    cur.close()
    conn.close()
