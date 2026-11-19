import os
import datetime

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_connection

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, ".jwt_secret")) as f:
    _SECRET = f.read().strip()

ALGORITHM = "HS256"
TOKEN_HOURS = 24
COOKIE_NAME = "dlp_token"

_bearer = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def authenticate(username: str, password: str):
    """아이디와 비밀번호가 맞으면 사용자 정보를, 아니면 None을 반환"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id, u.username, u.password_hash, u.role, u.org_id, o.name
        FROM users u
        LEFT JOIN organizations o ON o.id = u.org_id
        WHERE u.username = %s
        """,
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    user_id, uname, pw_hash, role, org_id, org_name = row

    # 저장된 건 해시뿐이라, 입력값을 같은 방식으로 해싱해서 비교만 합니다
    if not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        return None

    return {
        "id": user_id,
        "username": uname,
        "role": role,
        "org_id": org_id,
        "org_name": org_name,
    }


def create_token(user: dict) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "org_id": user["org_id"],
        "org_name": user["org_name"],
        "iat": now,
        "exp": now + datetime.timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, _SECRET, algorithm=ALGORITHM)


def _unpack(payload: dict) -> dict:
    return {
        "id": int(payload["sub"]),
        "username": payload["username"],
        "role": payload["role"],
        "org_id": payload.get("org_id"),
        "org_name": payload.get("org_name"),
    }


def _read_token(request: Request, cred: HTTPAuthorizationCredentials):
    """익스텐션은 헤더로, 대시보드는 쿠키로 토큰을 보냅니다"""
    if cred is not None:
        return cred.credentials
    return request.cookies.get(COOKIE_NAME)


def current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """토큰을 검사해 사용자 정보를 돌려줍니다. 없거나 틀리면 401."""
    token = _read_token(request, cred)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다")

    try:
        payload = jwt.decode(token, _SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "토큰이 만료되었습니다")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "토큰이 올바르지 않습니다")

    return _unpack(payload)


def user_from_cookie(request: Request):
    """쿠키의 토큰으로 사용자를 찾습니다. 없거나 틀리면 None.

    current_user는 401을 던지는데, 대시보드는 에러 대신
    로그인 페이지로 돌려보내야 해서 따로 만들었습니다.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    return _unpack(payload)


def admin_only(user: dict = Depends(current_user)) -> dict:
    """관리자만 통과. 일반 사용자는 403."""
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자만 접근할 수 있습니다")
    return user
