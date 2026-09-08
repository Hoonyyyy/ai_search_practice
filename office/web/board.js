// 업무 보드 — 4열, 드래그로 열 이동.
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
      col.dataset.col = key;
      col.innerHTML = `<h4>${label}</h4>`;
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
      for (const c of cards.filter((c) => c.column === key)) {
        col.appendChild(cardEl(c));
      }
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
    card.appendChild(tag);
    card.appendChild(document.createTextNode(" " + c.title));
    const who = document.createElement("small");
    who.textContent = "@" + c.assignee;
    card.appendChild(who);
    if (c.draft_snippet && c.draft_snippet.code) {
      const pre = document.createElement("pre");
      pre.textContent = c.draft_snippet.code;
      card.appendChild(pre);
    }
    return card;
  }

  return { refresh };
})();
