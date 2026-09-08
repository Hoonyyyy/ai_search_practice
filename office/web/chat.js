// 팀 채팅 패널 — 회의 발언·요약 로그.
window.Chat = (() => {
  const el = document.getElementById("chat");

  function add(speaker, text, kind) {
    const d = document.createElement("div");
    d.className = "msg" + (kind ? " " + kind : "");
    const b = document.createElement("b");
    b.textContent = speaker + " ";
    d.appendChild(b);
    d.appendChild(document.createTextNode(text));
    el.appendChild(d);
    el.scrollTop = el.scrollHeight;
  }

  function clear() { el.innerHTML = ""; }

  return { add, clear };
})();
