// 업무 보드 — 4열, 드래그로 열 이동. 동료 제안 코드는 접힌 채로 카드에 표시.
window.Board = (() => {
  const el = document.getElementById("board");
  const COLS = [
    ["todo", "할 일"], ["doing", "진행 중"],
    ["review", "리뷰 대기"], ["done", "완료"],
  ];

  async function refresh() {
    let cards = [];
    try {
      cards = await fetch("/board/cards").then((r) => r.json());
    } catch { return; }
    el.innerHTML = "";
    for (const [key, label] of COLS) {
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `<h4>${label} · ${cards.filter((c) => c.column === key).length}</h4>`;
      col.addEventListener("dragover", (e) => e.preventDefault());
      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        const id = e.dataTransfer.getData("id");
        if (!id) return;
        await fetch(`/board/cards/${id}`, {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ column: key }),
        });
        refresh();
      });
      for (const c of cards.filter((c) => c.column === key)) col.appendChild(cardEl(c));
      el.appendChild(col);
    }
  }

  function cardEl(c) {
    const card = document.createElement("div");
    card.className = "card";
    card.draggable = true;
    card.addEventListener("dragstart", (e) => e.dataTransfer.setData("id", c.id));

    const tag = document.createElement("span");
    tag.className = "tag " + c.tag;
    tag.textContent = c.tag;
    card.append(tag, document.createTextNode(" " + c.title));

    const who = document.createElement("span");
    who.className = "who";
    who.textContent = "담당 @" + c.assignee;
    card.appendChild(who);

    if (c.draft_snippet && c.draft_snippet.code) {
      const d = document.createElement("details");
      const s = document.createElement("summary");
      s.textContent = "💡 " + (c.draft_snippet.lang || "code") + " 제안 (파일엔 미반영)";
      const pre = document.createElement("pre");
      pre.textContent = c.draft_snippet.code;
      d.append(s, pre);
      card.appendChild(d);
    }
    return card;
  }

  return { refresh };
})();
