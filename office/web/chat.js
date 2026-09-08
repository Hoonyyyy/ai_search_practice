// 팀 채팅 패널 — 회의 발언·요약 로그.
window.Chat = (() => {
  const el = document.getElementById("chat");
  let empty = true;

  function showEmpty() {
    el.innerHTML = '<div class="empty">회의를 소집하면 여기에 대화가 쌓여요.</div>';
    empty = true;
  }

  function add(speaker, text, kind) {
    if (empty) { el.innerHTML = ""; empty = false; }
    const row = document.createElement("div");
    row.className = "msg" + (kind ? " " + kind : "");
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = speaker;
    const body = document.createElement("span");
    body.className = "body";
    body.textContent = text;
    row.append(who, body);
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
  }

  function clear() { showEmpty(); }

  showEmpty();
  return { add, clear };
})();
