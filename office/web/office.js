// 톱다운 픽셀 사무실 렌더러. 서버 /office/state 의 격자 좌표를 픽셀로 그린다.
window.Office = (() => {
  const TILE = 32;
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const COLS = canvas.width / TILE;   // 20
  const ROWS = canvas.height / TILE;  // 13

  const PALETTE = {
    Victoria: "#e0a33a",
    Sophia: "#3fb98a",
    Michelle: "#c56bd6",
    Chloe: "#9ecb3a",
    후니: "#6ea8fe",
  };
  const STATUS_LABEL = {
    desk: "자리", thinking: "생각 중…", talking: "말하는 중",
    meeting: "회의 중", warn: "⚠",
  };

  let actors = {};        // nick -> {x,y,status, cx,cy}  (격자 목표 / 픽셀 현재)
  let bubbles = [];       // {nick, text, until}
  let deskCoords = {};    // 서버가 알려준 책상 위치 (state 최초 수신 시 기록)
  let started = false;

  function render(state) {
    for (const [nick, a] of Object.entries(state.actors)) {
      const prev = actors[nick];
      actors[nick] = {
        x: a.x, y: a.y, status: a.status,
        cx: prev ? prev.cx : a.x,
        cy: prev ? prev.cy : a.y,
      };
    }
    // 최초 상태 = 전원 자리 → 책상 좌표로 간주
    if (!Object.keys(deskCoords).length) {
      for (const [nick, a] of Object.entries(state.actors)) deskCoords[nick] = { x: a.x, y: a.y };
    }
    if (!started) { started = true; requestAnimationFrame(loop); }
  }

  function say(nick, text) {
    bubbles.push({ nick, text: text.replace(/\s+/g, " ").trim(), until: performance.now() + 4200 });
    if (actors[nick]) actors[nick].status = "talking";
  }

  function drawFloor() {
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        const edge = x === 0 || y === 0 || x === COLS - 1 || y === ROWS - 1;
        if (edge) { ctx.fillStyle = "#2b2f3d"; }
        else { ctx.fillStyle = (x + y) % 2 ? "#20232e" : "#1d2029"; }
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
      }
    }
    // 회의실 구역 음영 (오른쪽)
    ctx.fillStyle = "rgba(110,168,254,0.06)";
    ctx.fillRect(11 * TILE, 1 * TILE, 8 * TILE, 6 * TILE);
    ctx.strokeStyle = "#3a4160";
    ctx.strokeRect(11 * TILE + 1, 1 * TILE + 1, 8 * TILE - 2, 6 * TILE - 2);
    ctx.fillStyle = "#5a6280";
    ctx.font = "10px monospace";
    ctx.textAlign = "left";
    ctx.fillText("MEETING ROOM", 11 * TILE + 8, 1 * TILE + 14);
    // 회의 테이블
    ctx.fillStyle = "#3b3222";
    roundRect(12 * TILE, 2.4 * TILE, 3 * TILE, 3 * TILE, 8);
    ctx.fill();
  }

  function drawDesk(x, y, color) {
    const px = x * TILE, py = y * TILE;
    ctx.fillStyle = "#39301f";
    roundRect(px - 12, py - 8, TILE + 8, TILE - 2, 4);
    ctx.fill();
    // 모니터
    ctx.fillStyle = "#0d1017";
    ctx.fillRect(px - 6, py - 20, 20, 12);
    ctx.fillStyle = color;
    ctx.fillRect(px - 4, py - 18, 16, 8);
  }

  function drawAvatar(nick, a) {
    const px = a.cx * TILE + TILE / 2;
    const py = a.cy * TILE + TILE / 2;
    const color = PALETTE[nick] || "#8a90a6";
    // 몸
    ctx.fillStyle = color;
    roundRect(px - 9, py - 2, 18, 16, 5);
    ctx.fill();
    // 머리
    ctx.beginPath();
    ctx.arc(px, py - 8, 7, 0, Math.PI * 2);
    ctx.fillStyle = "#f1d3b0";
    ctx.fill();
    // 이름표
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.fillStyle = "#0d1017";
    ctx.fillRect(px - 22, py + 16, 44, 12);
    ctx.fillStyle = "#e7e9ef";
    ctx.fillText(nick, px, py + 25);
    // 상태 배지
    ctx.fillStyle = a.status === "warn" ? "#e5484d" : "#8a90a6";
    ctx.font = "9px monospace";
    ctx.fillText(STATUS_LABEL[a.status] || a.status, px, py - 20);
  }

  function drawBubble(b) {
    const a = actors[b.nick];
    if (!a) return;
    const px = a.cx * TILE + TILE / 2;
    const py = a.cy * TILE + TILE / 2;
    const text = b.text.length > 46 ? b.text.slice(0, 45) + "…" : b.text;
    ctx.font = "11px -apple-system, 'Malgun Gothic', sans-serif";
    const w = Math.max(60, ctx.measureText(text).width + 16);
    const bx = Math.min(Math.max(px - w / 2, 4), canvas.width - w - 4);
    const by = py - 52;
    ctx.fillStyle = "#f4f5f8";
    roundRect(bx, by, w, 24, 6);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(px - 5, by + 24); ctx.lineTo(px + 5, by + 24); ctx.lineTo(px, by + 30);
    ctx.fill();
    ctx.fillStyle = "#15171d";
    ctx.textAlign = "left";
    ctx.fillText(text, bx + 8, by + 16);
  }

  function loop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawFloor();
    for (const [nick, d] of Object.entries(deskCoords)) drawDesk(d.x, d.y, PALETTE[nick] || "#888");

    const now = performance.now();
    bubbles = bubbles.filter((b) => b.until > now);

    for (const [nick, a] of Object.entries(actors)) {
      a.cx += (a.x - a.cx) * 0.12;
      a.cy += (a.y - a.cy) * 0.12;
    }
    // y 정렬로 겹침 자연스럽게
    const order = Object.entries(actors).sort((p, q) => p[1].cy - q[1].cy);
    for (const [nick, a] of order) drawAvatar(nick, a);
    for (const b of bubbles) drawBubble(b);

    requestAnimationFrame(loop);
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  return { render, say };
})();
