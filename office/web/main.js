// 부트스트랩 — 상태 폴링 + 회의 SSE 구동.
const $ = (id) => document.getElementById(id);
let polling = true;

function setStatus(t) { $("status").textContent = t; }

async function poll() {
  try {
    const s = await fetch("/office/state").then((r) => r.json());
    Office.render(s);
  } catch { /* 서버 재시작 중 등 */ }
}

async function runMeeting() {
  const topic = $("topic").value.trim();
  if (!topic) { setStatus("주제를 입력하세요"); return; }
  const rounds = Number($("rounds").value);

  $("summon").disabled = true;
  setStatus("소집 중…");
  Chat.clear();
  await fetch("/office/summon", { method: "POST" });
  await poll();

  let resp;
  try {
    resp = await fetch("/meeting", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ topic, rounds }),
    });
  } catch {
    setStatus("서버 연결 실패");
    $("summon").disabled = false;
    return;
  }
  if (resp.status === 409) { setStatus("이미 회의가 진행 중입니다"); $("summon").disabled = false; return; }
  if (!resp.ok) { setStatus("회의 시작 실패 (" + resp.status + ")"); $("summon").disabled = false; return; }

  setStatus("회의 중…");
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, i).replace(/^data: /, "");
      buf = buf.slice(i + 2);
      if (!raw) continue;
      let ev;
      try { ev = JSON.parse(raw); } catch { continue; }
      handleEvent(ev);
    }
  }
  await poll();
  setStatus("회의 종료");
  $("summon").disabled = false;
}

function handleEvent(ev) {
  if (ev.type === "turn") {
    Chat.add(ev.speaker, ev.text);
    Office.say(ev.speaker, ev.text);
  } else if (ev.type === "summary") {
    Chat.add("📋 요약", ev.text, "system");
  } else if (ev.type === "cards") {
    Chat.add("🗂 보드", `카드 ${ev.cards.length}개 생성`, "system");
    Board.refresh();
  } else if (ev.type === "error") {
    Chat.add("⚠ 오류", ev.message, "system");
    setStatus("오류: " + ev.message);
  }
}

$("summon").addEventListener("click", runMeeting);
$("topic").addEventListener("keydown", (e) => { if (e.key === "Enter") runMeeting(); });

poll();
Board.refresh();
setInterval(() => { if (polling) poll(); }, 1500);
