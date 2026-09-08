// 업무 보드 + 회의 결과 모달. 카드는 클릭해서 펼치고, ◀▶ 로 열 이동.
window.Board = (() => {
  const el = document.getElementById("board");
  const modal = document.getElementById("modal");
  const modalBody = document.getElementById("modalBody");
  const COLS = [
    ["todo", "할 일"], ["doing", "진행 중"],
    ["review", "리뷰 대기"], ["done", "완료"],
  ];
  const COL_KEYS = COLS.map((c) => c[0]);

  async function refresh() {
    let cards = [];
    try {
      cards = await fetch("/board/cards").then((r) => r.json());
    } catch { return; }
    el.innerHTML = "";
    for (const [key, label] of COLS) {
      const inCol = cards.filter((c) => c.column === key);
      const col = document.createElement("div");
      col.className = "col";
      col.innerHTML = `<h4>${label} · ${inCol.length}</h4>`;
      for (const c of inCol) col.appendChild(cardEl(c));
      el.appendChild(col);
    }
  }

  function cardEl(c) {
    const card = document.createElement("div");
    card.className = "card";

    const head = document.createElement("div");
    head.className = "card-head";
    const tag = document.createElement("span");
    tag.className = "tag " + c.tag;
    tag.textContent = c.tag;
    head.append(tag, document.createTextNode(" " + c.title));
    card.appendChild(head);

    const body = document.createElement("div");
    body.className = "card-body";
    body.hidden = true;
    if (c.detail) {
      const d = document.createElement("p");
      d.textContent = c.detail;
      body.appendChild(d);
    }
    const who = document.createElement("div");
    who.className = "who";
    who.textContent = "담당 @" + c.assignee;
    body.appendChild(who);
    if (c.draft_snippet && c.draft_snippet.code) {
      const lbl = document.createElement("div");
      lbl.className = "snip-label";
      lbl.textContent = "💡 " + (c.draft_snippet.lang || "code") + " 제안 (파일엔 미반영)";
      const pre = document.createElement("pre");
      pre.textContent = c.draft_snippet.code;
      body.append(lbl, pre);
    }
    const move = document.createElement("div");
    move.className = "card-move";
    const idx = COL_KEYS.indexOf(c.column);
    if (idx > 0) move.appendChild(moveBtn("◀ " + COLS[idx - 1][1], c.id, COL_KEYS[idx - 1]));
    if (idx < COL_KEYS.length - 1) move.appendChild(moveBtn(COLS[idx + 1][1] + " ▶", c.id, COL_KEYS[idx + 1]));
    body.appendChild(move);
    card.appendChild(body);

    head.addEventListener("click", () => { body.hidden = !body.hidden; });
    return card;
  }

  function moveBtn(text, id, col) {
    const b = document.createElement("button");
    b.className = "mini";
    b.textContent = text;
    b.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch(`/board/cards/${id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ column: col }),
      });
      refresh();
    });
    return b;
  }

  // ── 회의 결과 모달 ─────────────────────────────────────
  function showResult(summary, cards) {
    modalBody.innerHTML = "";
    if (summary) {
      const s = document.createElement("p");
      s.className = "modal-summary";
      s.textContent = summary;
      modalBody.appendChild(s);
    }
    const h = document.createElement("div");
    h.className = "modal-sub";
    h.textContent = `할 일에 추가된 카드 ${cards.length}개`;
    modalBody.appendChild(h);
    for (const c of cards) {
      const card = cardEl(c);
      card.querySelector(".card-body").hidden = false;   // 모달에선 펼친 채로
      modalBody.appendChild(card);
    }
    modal.hidden = false;
  }

  document.getElementById("modalClose").addEventListener("click", () => { modal.hidden = true; });
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.hidden = true; });

  return { refresh, showResult };
})();
