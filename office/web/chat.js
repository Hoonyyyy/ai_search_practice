// 팀 채팅 패널 — 회의 발언·요약 로그. 코드블록은 monospace 로.
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
    row.appendChild(who);

    // ```code``` 블록 분리
    const parts = String(text).split(/```(?:\w+)?\n?/);
    parts.forEach((part, i) => {
      if (!part) return;
      if (i % 2 === 1) {
        const pre = document.createElement("pre");
        pre.textContent = part.replace(/\n$/, "");
        row.appendChild(pre);
      } else {
        const body = document.createElement("span");
        body.className = "body";
        body.textContent = part.replace(/\*\*|__|`/g, "").trim();
        row.appendChild(body);
      }
    });
    el.appendChild(row);
    el.scrollTop = el.scrollHeight;
  }

  function clear() { showEmpty(); }

  showEmpty();
  return { add, clear };
})();
