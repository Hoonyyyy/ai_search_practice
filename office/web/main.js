// 부트스트랩 — 상태 폴링 + 회의 SSE 구동 + 중단.
const $ = (id) => document.getElementById(id);
let currentMeetingId = null;
let aborter = null;
let totalTurns = 8;

function setStatus(t) { $("status").textContent = t; }

let localMeeting = false;   // 이 탭이 회의를 돌리는 중인가

async function poll() {
  try {
    const s = await fetch("/office/state").then((r) => r.json());
    Office.render(s);
    // 다른 곳(새로고침 전 탭 등)에서 시작된 회의가 남아있는 경우
    if (!localMeeting) {
      if (s.meeting_id) {
        setStatus("이전 회의 정리 중… 잠시 후 다시 시도하세요");
        $("summon").disabled = true;
      } else if ($("summon").disabled && $("endmtg").hidden) {
        $("summon").disabled = false;
        setStatus("");
      }
    }
  } catch { /* 서버 재시작 중 등 */ }
}

function meetingUI(on) {
  $("summon").hidden = on;
  $("endmtg").hidden = !on;
  $("topic").disabled = on;
  $("rounds").disabled = on;
}

async function runMeeting() {
  const topic = $("topic").value.trim();
  if (!topic) { setStatus("주제를 입력하세요"); return; }
  const rounds = Number($("rounds").value);
  totalTurns = rounds * 4;

  localMeeting = true;
  meetingUI(true);
  setStatus("소집 중…");
  Chat.clear();
  await fetch("/office/summon", { method: "POST" });
  await poll();

  aborter = new AbortController();
  let resp;
  try {
    resp = await fetch("/meeting", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ topic, rounds }),
      signal: aborter.signal,
    });
  } catch {
    setStatus("서버 연결 실패");
    endMeetingUI();
    return;
  }
  if (resp.status === 409) { setStatus("이미 회의가 진행 중입니다"); endMeetingUI(); return; }
  if (!resp.ok) { setStatus("회의 시작 실패 (" + resp.status + ")"); endMeetingUI(); return; }

  setStatus("회의 중…");
  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  try {
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
  } catch { /* aborted */ }

  await poll();
  if (currentMeetingId) setStatus("회의 종료");
  endMeetingUI();
}

function handleEvent(ev) {
  if (ev.type === "start") {
    currentMeetingId = ev.meeting_id;
  } else if (ev.type === "turn") {
    Chat.add(ev.speaker, ev.text);
    Office.say(ev.speaker, ev.text);
    setStatus(`회의 중… ${ev.seq}/${totalTurns} 발언`);
  } else if (ev.type === "summary") {
    setStatus("의견 정리 중…");
    Chat.add("📋 요약", ev.text, "system");
  } else if (ev.type === "cards") {
    Chat.add("🗂 보드", `액션 아이템 ${ev.cards.length}개를 카드로 만들었어요.`, "system");
    Board.refresh();
  } else if (ev.type === "cancelled") {
    Chat.add("⏹ 중단", ev.message, "system");
    setStatus("회의 중단됨");
  } else if (ev.type === "error") {
    Chat.add("⚠ 오류", ev.message, "system");
    setStatus("오류: " + ev.message);
  }
}

async function endMeeting() {
  setStatus("중단 중…");
  if (currentMeetingId) {
    await fetch(`/meeting/${currentMeetingId}/cancel`, { method: "POST" }).catch(() => {});
  } else {
    await fetch("/office/dismiss", { method: "POST" }).catch(() => {});
  }
  if (aborter) aborter.abort();
}

function endMeetingUI() {
  meetingUI(false);
  currentMeetingId = null;
  aborter = null;
  localMeeting = false;
}

$("summon").addEventListener("click", runMeeting);
$("endmtg").addEventListener("click", endMeeting);
$("clearchat").addEventListener("click", () => Chat.clear());
$("topic").addEventListener("keydown", (e) => { if (e.key === "Enter" && !$("topic").disabled) runMeeting(); });

poll();
Board.refresh();
setInterval(poll, 1500);
