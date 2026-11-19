import os

from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import get_connection
from masking import mask_text
from auth import (
    authenticate,
    create_token,
    current_user,
    user_from_cookie,
    hash_password,
    COOKIE_NAME,
    TOKEN_HOURS,
)

app = FastAPI()

mask_text("워밍업 문장입니다")
print("[DLP] 모델 워밍업 완료")

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
)


class TextInput(BaseModel):
    text: str


class LoginInput(BaseModel):
    username: str
    password: str


class SignupInput(BaseModel):
    username: str
    password: str
    join_code: str


# ===== 인증 =====

@app.post("/signup")
def signup(input: SignupInput):
    username = input.username.strip()

    if len(username) < 3:
        raise HTTPException(400, "아이디는 3자 이상이어야 합니다")
    if len(input.password) < 8:
        raise HTTPException(400, "비밀번호는 8자 이상이어야 합니다")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name FROM organizations WHERE join_code = %s",
        (input.join_code.strip().upper(),),
    )
    org = cur.fetchone()
    if not org:
        cur.close()
        conn.close()
        raise HTTPException(400, "가입 코드가 올바르지 않습니다")

    org_id, org_name = org

    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(409, "이미 있는 아이디입니다")

    # 역할은 항상 member입니다. 관리자 승격은 서버에서만 할 수 있습니다.
    cur.execute(
        "INSERT INTO users (username, password_hash, role, org_id) VALUES (%s, %s, 'member', %s)",
        (username, hash_password(input.password), org_id),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"ok": True, "username": username, "org": org_name}


@app.post("/login")
def login(input: LoginInput, response: Response):
    user = authenticate(input.username, input.password)
    if not user:
        # 아이디가 없는 건지 비밀번호가 틀린 건지 알려주지 않습니다
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다")

    token = create_token(user)

    # 대시보드용 쿠키. httponly라 자바스크립트가 읽을 수 없습니다.
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", max_age=TOKEN_HOURS * 3600
    )

    return {
        "access_token": token,
        "username": user["username"],
        "role": user["role"],
        "org": user["org_name"],
    }


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


# ===== 탐지 =====

@app.post("/detect")
def detect(input: TextInput, user: dict = Depends(current_user)):
    masked_text, detected_types, risk_level, evidence = mask_text(input.text)
    detected_type_str = ",".join(detected_types) if detected_types else None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO detection_logs
            (masked_text, detected_type, risk_level, evidence, user_id, org_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (masked_text, detected_type_str, risk_level, evidence,
          user["id"], user["org_id"]))
    conn.commit()
    cur.close()
    conn.close()

    return {
        "masked_text": masked_text,
        "detected_types": detected_types,
        "risk_level": risk_level,
    }


# ===== 조회 =====
# 관리자는 자기 조직 전체, 일반 사용자는 본인 것만 봅니다.

def _scope(user: dict):
    if user["role"] == "admin":
        return "l.org_id = %s", (user["org_id"],), "org"
    return "l.user_id = %s", (user["id"],), "mine"


@app.get("/logs")
def logs(user: dict = Depends(current_user), limit: int = 50):
    cond, args, _ = _scope(user)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT l.id, l.detected_at, u.username,
               l.masked_text, l.detected_type, l.risk_level, l.evidence
        FROM detection_logs l
        LEFT JOIN users u ON u.id = l.user_id
        WHERE {cond}
        ORDER BY l.id DESC
        LIMIT %s
    """, args + (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "detected_at": r[1].isoformat() if r[1] else None,
            "username": r[2],
            "masked_text": r[3],
            "detected_type": r[4],
            "risk_level": r[5],
            "evidence": r[6],
        }
        for r in rows
    ]


@app.get("/stats")
def stats(user: dict = Depends(current_user)):
    cond, args, scope = _scope(user)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"SELECT risk_level, COUNT(*) FROM detection_logs l WHERE {cond} GROUP BY risk_level",
        args,
    )
    by_risk = {r[0]: r[1] for r in cur.fetchall()}

    # 쉼표로 묶인 탐지 유형을 펼쳐서 셉니다
    cur.execute(f"""
        SELECT TRIM(t) AS kind, COUNT(*)
        FROM detection_logs l,
             UNNEST(STRING_TO_ARRAY(l.detected_type, ',')) AS t
        WHERE {cond}
        GROUP BY kind
        ORDER BY COUNT(*) DESC
    """, args)
    by_type = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute(f"""
        SELECT DATE(l.detected_at) AS d, COUNT(*)
        FROM detection_logs l
        WHERE {cond} AND l.detected_at >= NOW() - INTERVAL '7 days'
        GROUP BY d ORDER BY d
    """, args)
    by_day = [{"date": r[0].isoformat(), "count": r[1]} for r in cur.fetchall()]

    cur.execute(f"SELECT COUNT(*) FROM detection_logs l WHERE {cond}", args)
    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "scope": scope,
        "org": user["org_name"],
        "total": total,
        "by_risk": by_risk,
        "by_type": by_type,
        "by_day": by_day,
    }


# ===== 대시보드 =====

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    user = user_from_cookie(request)
    if not user:
        return RedirectResponse("/dashboard/login", status_code=303)
    return _templates.TemplateResponse(request, "dashboard.html", {"user": user})


@app.get("/dashboard/login", response_class=HTMLResponse)
def dashboard_login_page(request: Request, error: str = ""):
    return _templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/dashboard/login")
def dashboard_login(username: str = Form(...), password: str = Form(...)):
    user = authenticate(username, password)
    if not user:
        return RedirectResponse("/dashboard/login?error=1", status_code=303)

    redirect = RedirectResponse("/dashboard", status_code=303)
    redirect.set_cookie(
        COOKIE_NAME,
        create_token(user),
        httponly=True,
        samesite="lax",
        max_age=TOKEN_HOURS * 3600,
    )
    return redirect


@app.get("/dashboard/logout")
def dashboard_logout():
    redirect = RedirectResponse("/dashboard/login", status_code=303)
    redirect.delete_cookie(COOKIE_NAME)
    return redirect
