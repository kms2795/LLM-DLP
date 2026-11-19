// AI DLP Guard - background service worker
// 서버 통신을 전부 여기서 합니다.
//   - SIGNUP : 가입 코드로 회원가입
//   - LOGIN  : 로그인하고 토큰을 저장
//   - LOGOUT : 토큰 삭제
//   - DETECT : 토큰을 붙여서 /detect 호출
//
// 왜 여기서 부르냐면: 페이지 안(content.js)에서 외부 서버를 직접 부르면
// 그 페이지의 CORS 규칙에 걸립니다. 백그라운드에서 부르면
// manifest의 host_permissions 권한으로 통과할 수 있습니다.

// ↓↓↓ 본인 EC2 주소로 바꾸세요 (끝에 / 붙이지 마세요) ↓↓↓
const API_BASE = "http://localhost:8000";

function today() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// 팝업에 보여줄 오늘자 집계. 탐지 "건수"만 세고 내용은 저장하지 않습니다.
async function bumpStats(riskLevel) {
  if (!["HIGH", "MEDIUM", "LOW"].includes(riskLevel)) return;

  const { stats } = await chrome.storage.local.get("stats");
  const base =
    stats && stats.date === today()
      ? stats
      : { date: today(), HIGH: 0, MEDIUM: 0, LOW: 0 };

  base[riskLevel] += 1;
  await chrome.storage.local.set({ stats: base });
}

// 서버가 보내는 오류 메시지를 꺼냅니다 (FastAPI는 detail에 담아 보냅니다)
async function errorOf(res, fallback) {
  try {
    const body = await res.json();
    if (body && body.detail) return body.detail;
  } catch (e) {
    /* 본문이 JSON이 아니면 기본 문구를 씁니다 */
  }
  return fallback || `서버 오류 (HTTP ${res.status})`;
}

/* ---------------- 회원가입 ---------------- */

async function signup(username, password, joinCode) {
  const res = await fetch(`${API_BASE}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      join_code: joinCode,
    }),
  });

  if (!res.ok) throw new Error(await errorOf(res));
  return res.json();
}

/* ---------------- 로그인 ---------------- */

async function login(username, password) {
  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    throw new Error(
      await errorOf(
        res,
        res.status === 401 ? "아이디 또는 비밀번호가 올바르지 않습니다" : null
      )
    );
  }

  const data = await res.json();
  const auth = {
    token: data.access_token,
    username: data.username,
    role: data.role,
    org: data.org,
  };

  await chrome.storage.local.set({ auth });
  return auth;
}

/* ---------------- 탐지 ---------------- */

async function detect(text) {
  const { auth } = await chrome.storage.local.get("auth");

  // 로그인하지 않았으면 서버에 묻지도 않습니다
  if (!auth || !auth.token) {
    return { ok: false, error: "로그인이 필요합니다", needLogin: true };
  }

  const res = await fetch(`${API_BASE}/detect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.token}`,
    },
    body: JSON.stringify({ text }),
  });

  // 토큰이 만료됐거나 잘못된 경우 — 저장된 토큰을 지웁니다
  if (res.status === 401) {
    await chrome.storage.local.remove("auth");
    return { ok: false, error: "로그인이 만료되었습니다", needLogin: true };
  }

  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const data = await res.json();
  bumpStats(data.risk_level);
  return { ok: true, data };
}

/* ---------------- 메시지 처리 ---------------- */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "DETECT") {
    detect(message.text)
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  if (message.type === "SIGNUP") {
    signup(message.username, message.password, message.joinCode)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "LOGIN") {
    login(message.username, message.password)
      .then((auth) => sendResponse({ ok: true, auth }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "LOGOUT") {
    chrome.storage.local.remove("auth").then(() => sendResponse({ ok: true }));
    return true;
  }

  // 응답을 나중에 보내겠다는 표시가 없으면 fetch가 끝나기 전에
  // 연결이 끊겨서 호출한 쪽이 undefined를 받습니다.
});
