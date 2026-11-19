// AI DLP Guard - content script
// 위험도 분기 + HIGH 확인 모달 + 팝업 설정 반영

console.log("[DLP Guard] 로드됨:", location.hostname);

const COLOR = {
  navy: "#13203A",
  light: "#F6F5F1",
  paper: "#FDFCF9",
  accent: "#A8500E",
  accentSoft: "#FBEFE4",
  line: "#DCDFE5",
  muted: "#5B6577",
  text: "#3F4A5C",
};

const FONT = "system-ui, -apple-system, 'Malgun Gothic', sans-serif";
const MONO = "ui-monospace, 'D2Coding', Consolas, monospace";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------------- 설정 ---------------- */
// 이벤트 처리 중에 비동기로 읽을 수 없어서 메모리에 들고 있다가,
// 팝업에서 바뀌면 알림을 받아 갱신합니다.

const DEFAULTS = { enabled: true };

let settings = { ...DEFAULTS };

chrome.storage.local.get(DEFAULTS).then((s) => {
  settings = s;
  console.log("[DLP Guard] 설정:", settings);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  for (const [key, change] of Object.entries(changes)) {
    if (key in DEFAULTS) settings[key] = change.newValue;
  }
  console.log("[DLP Guard] 설정 변경됨:", settings);
});

/* ---------------- 알림 ---------------- */

function showToast(message, ms = 3000) {
  const box = document.createElement("div");
  box.textContent = message;

  Object.assign(box.style, {
    position: "fixed",
    right: "20px",
    bottom: "20px",
    zIndex: "2147483647",
    maxWidth: "420px",
    background: COLOR.navy,
    color: COLOR.light,
    padding: "12px 18px",
    borderRadius: "10px",
    font: `14px/1.4 ${FONT}`,
    boxShadow: "0 4px 16px rgba(0, 0, 0, 0.3)",
    pointerEvents: "none",
  });

  document.body.appendChild(box);
  setTimeout(() => box.remove(), ms);
  return box;
}

/* ---------------- HIGH 확인 모달 ---------------- */
// "가리고 보내기" 또는 "취소"만 고를 수 있습니다.
// 원문 그대로 보내는 선택지는 일부러 두지 않았습니다.

function showHighRiskModal({ original, masked, types }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    Object.assign(overlay.style, {
      position: "fixed",
      inset: "0",
      zIndex: "2147483647",
      background: "rgba(10, 16, 30, 0.55)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      font: `15px/1.5 ${FONT}`,
    });

    const card = document.createElement("div");
    Object.assign(card.style, {
      width: "min(620px, 92vw)",
      maxHeight: "82vh",
      overflowY: "auto",
      background: COLOR.paper,
      color: COLOR.text,
      borderRadius: "16px",
      padding: "32px 36px",
      boxShadow: "0 18px 50px rgba(0, 0, 0, 0.35)",
    });

    const label = document.createElement("p");
    label.textContent = "위험도 HIGH";
    Object.assign(label.style, {
      margin: "0 0 8px",
      font: `600 13px/1 ${FONT}`,
      letterSpacing: "1.5px",
      color: COLOR.accent,
    });

    const title = document.createElement("h2");
    title.textContent = "민감한 개인정보가 들어 있습니다";
    Object.assign(title.style, {
      margin: "0 0 10px",
      font: `600 25px/1.3 ${FONT}`,
      color: COLOR.navy,
    });

    const lead = document.createElement("p");
    lead.textContent = `${types.join(" · ")} — 법적으로 저장·전송이 제한되는 항목이라 가린 뒤에만 보낼 수 있습니다.`;
    Object.assign(lead.style, { margin: "0 0 22px", color: COLOR.muted });

    const makeBlock = (caption, body, highlight) => {
      const wrap = document.createElement("div");
      Object.assign(wrap.style, {
        border: `1px solid ${highlight ? COLOR.accent : COLOR.line}`,
        background: highlight ? COLOR.accentSoft : "#fff",
        borderRadius: "10px",
        padding: "14px 16px",
        marginBottom: "12px",
      });

      const head = document.createElement("p");
      head.textContent = caption;
      Object.assign(head.style, {
        margin: "0 0 6px",
        font: `600 12px/1 ${FONT}`,
        letterSpacing: "1px",
        color: highlight ? COLOR.accent : COLOR.muted,
      });

      const pre = document.createElement("p");
      pre.textContent = body;
      Object.assign(pre.style, {
        margin: "0",
        font: `14px/1.5 ${MONO}`,
        color: COLOR.navy,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      });

      wrap.append(head, pre);
      return wrap;
    };

    const buttons = document.createElement("div");
    Object.assign(buttons.style, {
      display: "flex",
      gap: "10px",
      justifyContent: "flex-end",
      marginTop: "22px",
    });

    const makeButton = (text, primary) => {
      const b = document.createElement("button");
      b.textContent = text;
      Object.assign(b.style, {
        font: `600 15px/1 ${FONT}`,
        padding: "12px 22px",
        borderRadius: "9px",
        cursor: "pointer",
        border: primary ? "none" : `1px solid ${COLOR.line}`,
        background: primary ? COLOR.navy : "#fff",
        color: primary ? COLOR.light : COLOR.text,
      });
      return b;
    };

    const cancelBtn = makeButton("취소하고 수정", false);
    const sendBtn = makeButton("가리고 보내기", true);

    const finish = (choice) => {
      document.removeEventListener("keydown", onKey, true);
      overlay.remove();
      resolve(choice);
    };

    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        finish("cancel");
      }
    };

    cancelBtn.addEventListener("click", () => finish("cancel"));
    sendBtn.addEventListener("click", () => finish("send"));
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) finish("cancel");
    });
    document.addEventListener("keydown", onKey, true);

    buttons.append(cancelBtn, sendBtn);
    card.append(
      label,
      title,
      lead,
      makeBlock("지금 입력한 내용", original, false),
      makeBlock("실제로 보낼 내용", masked, true),
      buttons
    );
    overlay.append(card);
    document.body.append(overlay);

    sendBtn.focus();
  });
}

/* ---------------- 입력창 ---------------- */

const EDITOR_SELECTORS = [
  "#prompt-textarea",
  "div.ProseMirror[contenteditable='true']",
  "div[contenteditable='true']",
  "textarea",
];

const SEND_BUTTON_SELECTORS = [
  "button[data-testid='send-button']",
  "button[aria-label*='Send']",
  "button[aria-label*='보내기']",
  "form button[type='submit']",
].join(",");

function findEditor() {
  for (const selector of EDITOR_SELECTORS) {
    const el = document.querySelector(selector);
    if (el) return { el, selector };
  }
  return null;
}

function readText(el) {
  return typeof el.value === "string" ? el.value : el.innerText;
}

// el.value = "..." 로 바꾸면 React가 모릅니다.
// 화면만 바뀌고 원래 글이 그대로 전송됩니다.
function writeText(el, text) {
  el.focus();

  if (typeof el.value === "string") {
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value"
    ).set;
    setter.call(el, text);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }

  const range = document.createRange();
  range.selectNodeContents(el);

  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);

  document.execCommand("insertText", false, text);
}

/* ---------------- 다시 전송 ---------------- */

let bypass = false;

async function resend() {
  bypass = true;
  try {
    let button = null;
    for (let i = 0; i < 10; i++) {
      await sleep(50);
      button = document.querySelector(SEND_BUTTON_SELECTORS);
      if (button && !button.disabled) break;
    }

    if (button && !button.disabled) {
      button.click();
      return true;
    }

    const found = findEditor();
    if (!found) return false;

    found.el.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        keyCode: 13,
        bubbles: true,
        cancelable: true,
      })
    );
    return true;
  } finally {
    await sleep(300);
    bypass = false;
  }
}

/* ---------------- 검사 요청 ---------------- */

async function detect(text) {
  const started = performance.now();
  const response = await chrome.runtime.sendMessage({ type: "DETECT", text });
  const elapsed = Math.round(performance.now() - started);
  return { response, elapsed };
}

/* ---------------- 본체 ---------------- */

async function intercept(event, how) {
  const found = findEditor();
  if (!found) {
    console.warn("[DLP Guard] 입력창을 못 찾았습니다");
    return;
  }

  const original = readText(found.el).trim();
  if (!original) return;

  // await 전에 동기로 실행되어야 전송이 멈춥니다
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();

  console.log(`[DLP Guard] 가로챔 (${how}) · selector = ${found.selector}`);

  const checking = showToast("검사 중...", 10000);

  let result;
  try {
    result = await detect(original);
  } catch (err) {
    checking.remove();
    console.error("[DLP Guard] 메시지 전달 실패:", err);
    showToast(`메시지 전달 실패: ${err}`, 8000);
    return;
  }

  checking.remove();
  const { response, elapsed } = result;

  // 검사를 못 했으면 보내지 않습니다 (fail-closed)
  if (!response || !response.ok) {
    const reason = response ? response.error : "응답 없음";
    console.error("[DLP Guard] 서버 호출 실패:", reason);

    if (response && response.needLogin) {
      showToast("로그인이 필요합니다 — 확장 아이콘을 눌러 로그인하세요", 8000);
    } else {
      showToast(`검사 실패로 전송을 막았습니다: ${reason}`, 8000);
    }
    return;
  }

  const { masked_text, detected_types, risk_level } = response.data;
  console.log(`[DLP Guard] ${risk_level} · ${elapsed}ms ·`, detected_types);

  // NONE — 아무 일도 일어나지 않습니다
  if (!detected_types.length) {
    await resend();
    return;
  }

  // HIGH — 멈추고 확인을 받습니다
  if (risk_level === "HIGH") {
    const choice = await showHighRiskModal({
      original,
      masked: masked_text,
      types: detected_types,
    });

    if (choice !== "send") {
      showToast("전송을 취소했습니다", 3000);
      return;
    }
  }

  // 공통 — 마스킹본으로 바꿔치기
  writeText(found.el, masked_text);
  await sleep(100);

  // 제대로 바뀌었는지 확인. 실패한 채로 보내면 원문이 나갑니다.
  const after = readText(found.el).trim();
  if (after !== masked_text.trim()) {
    console.error("[DLP Guard] 쓰기 실패");
    console.error("  기대:", masked_text);
    console.error("  실제:", after);
    showToast("마스킹에 실패해 전송을 막았습니다", 8000);
    return;
  }

  await resend();

  // LOW·MEDIUM만 알립니다. HIGH는 이미 모달로 확인했으니 조용히 넘어갑니다.
  if (risk_level !== "HIGH") {
    showToast(`${detected_types.join(", ")} 가림 · ${elapsed}ms`, 4000);
  }
}

/* ---------------- 이벤트 연결 ---------------- */

document.addEventListener(
  "keydown",
  (event) => {
    if (!settings.enabled || bypass) return;
    if (event.key !== "Enter" || event.shiftKey) return;

    // 한글 조합을 확정하는 엔터는 전송이 아닙니다
    if (event.isComposing || event.keyCode === 229) return;

    const found = findEditor();
    if (!found) return;

    const inEditor = found.el === event.target || found.el.contains(event.target);
    if (!inEditor) return;

    intercept(event, "엔터");
  },
  true
);

document.addEventListener(
  "click",
  (event) => {
    if (!settings.enabled || bypass) return;

    const button = event.target.closest(SEND_BUTTON_SELECTORS);
    if (!button) return;

    intercept(event, "버튼");
  },
  true
);

showToast("AI DLP Guard · 준비됨");
