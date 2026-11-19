// AI DLP Guard - 팝업
// 서버 통신은 직접 하지 않고 background.js에 맡깁니다.
// 그래야 EC2 주소가 한 군데에만 있습니다.

const DEFAULTS = { enabled: true };

const views = {
  login: document.getElementById("loginView"),
  signup: document.getElementById("signupView"),
  main: document.getElementById("mainView"),
};

const enabledBox = document.getElementById("enabled");
const stateText = document.getElementById("state");

/* ---------------- 화면 전환 ---------------- */

function show(name) {
  for (const [key, el] of Object.entries(views)) {
    el.hidden = key !== name;
  }
}

function showLogin() {
  show("login");
  document.getElementById("username").focus();
}

function showSignup() {
  show("signup");
  document.getElementById("suUsername").focus();
}

function showMain(auth) {
  show("main");

  document.getElementById("whoName").textContent = auth.username;
  document.getElementById("whoOrg").textContent = auth.org || "";

  const roleTag = document.getElementById("whoRole");
  roleTag.textContent = auth.role === "admin" ? "관리자" : "일반";
  roleTag.classList.toggle("admin", auth.role === "admin");
}

function paint(on) {
  document.body.classList.toggle("off", !on);
  stateText.textContent = on
    ? "전송 전에 6종을 검사합니다."
    : "검사하지 않습니다. 개인정보가 그대로 전송됩니다.";
}

function setMsg(el, text, kind) {
  el.textContent = text;
  el.className = "msg " + (kind || "error");
  el.hidden = !text;
}

/* ---------------- 처음 열릴 때 ---------------- */

chrome.storage.local.get({ ...DEFAULTS, auth: null }).then((data) => {
  enabledBox.checked = data.enabled;
  paint(data.enabled);

  if (data.auth && data.auth.token) {
    showMain(data.auth);
  } else {
    showLogin();
  }
});

/* ---------------- 로그인 ---------------- */

const loginBtn = document.getElementById("loginBtn");
const loginMsg = document.getElementById("loginMsg");

async function doLogin(username, password) {
  const res = await chrome.runtime.sendMessage({
    type: "LOGIN",
    username,
    password,
  });
  return res;
}

loginBtn.addEventListener("click", async () => {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!username || !password) {
    setMsg(loginMsg, "아이디와 비밀번호를 입력하세요");
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = "로그인 중...";
  setMsg(loginMsg, "");

  const res = await doLogin(username, password);

  loginBtn.disabled = false;
  loginBtn.textContent = "로그인";

  if (!res || !res.ok) {
    setMsg(loginMsg, (res && res.error) || "로그인에 실패했습니다");
    return;
  }

  document.getElementById("password").value = "";
  showMain(res.auth);
});

document.getElementById("password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loginBtn.click();
});

/* ---------------- 회원가입 ---------------- */

const signupBtn = document.getElementById("signupBtn");
const signupMsg = document.getElementById("signupMsg");

signupBtn.addEventListener("click", async () => {
  const username = document.getElementById("suUsername").value.trim();
  const password = document.getElementById("suPassword").value;
  const joinCode = document.getElementById("suCode").value.trim().toUpperCase();

  if (!username || !password || !joinCode) {
    setMsg(signupMsg, "모든 칸을 채워주세요");
    return;
  }
  if (username.length < 3) {
    setMsg(signupMsg, "아이디는 3자 이상이어야 합니다");
    return;
  }
  if (password.length < 8) {
    setMsg(signupMsg, "비밀번호는 8자 이상이어야 합니다");
    return;
  }

  signupBtn.disabled = true;
  signupBtn.textContent = "가입 중...";
  setMsg(signupMsg, "");

  const res = await chrome.runtime.sendMessage({
    type: "SIGNUP",
    username,
    password,
    joinCode,
  });

  if (!res || !res.ok) {
    signupBtn.disabled = false;
    signupBtn.textContent = "가입하기";
    setMsg(signupMsg, (res && res.error) || "가입에 실패했습니다");
    return;
  }

  // 가입에 성공하면 바로 로그인시켜 줍니다
  setMsg(signupMsg, "가입 완료. 로그인 중...", "ok");
  const loginRes = await doLogin(username, password);

  signupBtn.disabled = false;
  signupBtn.textContent = "가입하기";

  document.getElementById("suPassword").value = "";
  document.getElementById("suCode").value = "";

  if (loginRes && loginRes.ok) {
    showMain(loginRes.auth);
  } else {
    setMsg(signupMsg, "가입은 됐습니다. 로그인 화면에서 다시 시도해 주세요.", "ok");
  }
});

document.getElementById("suCode").addEventListener("keydown", (e) => {
  if (e.key === "Enter") signupBtn.click();
});

/* ---------------- 화면 전환 버튼 ---------------- */

document.getElementById("toSignup").addEventListener("click", () => {
  setMsg(loginMsg, "");
  setMsg(signupMsg, "");
  showSignup();
});

document.getElementById("toLogin").addEventListener("click", () => {
  setMsg(loginMsg, "");
  setMsg(signupMsg, "");
  showLogin();
});

/* ---------------- 로그아웃 ---------------- */

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "LOGOUT" });
  document.getElementById("username").value = "";
  document.getElementById("password").value = "";
  showLogin();
});

/* ---------------- 보호 켜기/끄기 ---------------- */

enabledBox.addEventListener("change", () => {
  const on = enabledBox.checked;
  paint(on);
  chrome.storage.local.set({ enabled: on });
});

/* ---------------- 오늘 탐지 건수 ---------------- */

function localToday() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

chrome.storage.local.get("stats").then(({ stats }) => {
  const fresh = stats && stats.date === localToday() ? stats : null;

  document.getElementById("statHigh").textContent = fresh ? fresh.HIGH : 0;
  document.getElementById("statMedium").textContent = fresh ? fresh.MEDIUM : 0;
  document.getElementById("statLow").textContent = fresh ? fresh.LOW : 0;
});
