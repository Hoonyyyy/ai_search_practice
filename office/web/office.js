// 톱다운 아늑한 픽셀 사무실 (동물의숲 톤). 서버 /office/state 격자(24x16)를 픽셀로.
window.Office = (() => {
  const TILE = 32;
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const COLS = canvas.width / TILE;   // 24
  const ROWS = canvas.height / TILE;  // 16

  const PEOPLE = {
    Victoria: { body: "#e6b45a", hair: "#6b4326" },
    Sophia: { body: "#5ac9a0", hair: "#33323c" },
    Michelle: { body: "#e08ad6", hair: "#8a5620" },
    Chloe: { body: "#b6d766", hair: "#d79a3e" },
    후니: { body: "#7bb0f2", hair: "#2b2f3a" },
  };
  const STATUS_LABEL = {
    desk: "", thinking: "생각 중…", talking: "말하는 중",
    meeting: "회의 중", warn: "⚠",
  };

  let actors = {};
  let bubbles = [];
  let desks = {};
  let running = false;
  const t0 = performance.now();

  function render(state) {
    for (const [nick, a] of Object.entries(state.actors)) {
      const prev = actors[nick];
      actors[nick] = {
        x: a.x, y: a.y, status: a.status,
        cx: prev ? prev.cx : a.x,
        cy: prev ? prev.cy : a.y,
      };
    }
    if (!Object.keys(desks).length) {
      for (const [nick, a] of Object.entries(state.actors)) desks[nick] = { x: a.x, y: a.y };
    }
    if (!running) { running = true; requestAnimationFrame(loop); }
  }

  function say(nick, text) {
    const clean = text.replace(/```[\s\S]*?```/g, " (코드) ").replace(/\s+/g, " ").trim();
    bubbles = bubbles.filter((b) => b.nick !== nick);
    bubbles.push({ nick, lines: wrap(clean, 28).slice(0, 3), until: performance.now() + 6500 });
    if (actors[nick]) actors[nick].status = "talking";
  }

  function wrap(s, n) {
    const out = [];
    let line = "";
    for (const w of s.split(" ")) {
      if ((line + " " + w).trim().length > n) { out.push(line.trim()); line = w; }
      else line += " " + w;
    }
    if (line.trim()) out.push(line.trim());
    return out;
  }

  // ── 배경 ────────────────────────────────────────────────
  function drawRoom(now) {
    // 바닥: 따뜻한 나무 널
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        const s = (x * 7 + y * 13) % 4;
        ctx.fillStyle = ["#b98a5a", "#c09262", "#bd8d5d", "#b58658"][s];
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
        ctx.strokeStyle = "rgba(120,85,50,0.25)";
        ctx.strokeRect(x * TILE, y * TILE, TILE, TILE);
      }
    }

    // 회의실 카펫 (오른쪽)
    ctx.fillStyle = "#7fae86";
    rr(14 * TILE, TILE, 9 * TILE, 8 * TILE, 4); ctx.fill();

    // 라운지 러그 (아래 가운데)
    ctx.fillStyle = "#c98b7a";
    rr(3 * TILE, 12 * TILE, 8 * TILE, 3 * TILE, 12); ctx.fill();
    ctx.fillStyle = "#dda593";
    rr(3.4 * TILE, 12.4 * TILE, 7.2 * TILE, 2.2 * TILE, 8); ctx.fill();

    // 벽 (따뜻한 크림색)
    ctx.fillStyle = "#e8dcc4";
    ctx.fillRect(0, 0, canvas.width, TILE * 0.9);
    ctx.fillRect(0, 0, TILE * 0.5, canvas.height);
    ctx.fillRect(canvas.width - TILE * 0.5, 0, TILE * 0.5, canvas.height);
    ctx.fillRect(0, canvas.height - TILE * 0.5, canvas.width, TILE * 0.5);
    // 걸레받이
    ctx.strokeStyle = "#c9b78f"; ctx.lineWidth = 2;
    ctx.strokeRect(TILE * 0.5, TILE * 0.9, canvas.width - TILE, canvas.height - TILE * 1.4);
    ctx.lineWidth = 1;

    // 창문 (위 벽) — 하늘색 + 화분
    for (let i = 2; i < COLS - 3; i += 4) {
      ctx.fillStyle = "#a9d8ef";
      ctx.fillRect(i * TILE, 3, TILE * 2, TILE * 0.7);
      ctx.strokeStyle = "#b79a6b";
      ctx.strokeRect(i * TILE, 3, TILE * 2, TILE * 0.7);
      ctx.fillStyle = "#5aa06a";
      ctx.fillRect(i * TILE + TILE - 4, TILE * 0.55, 8, 6);
    }

    // 회의실 유리 파티션
    ctx.strokeStyle = "rgba(150,200,255,0.5)";
    ctx.lineWidth = 3;
    ctx.strokeRect(14 * TILE, TILE, 9 * TILE, 8 * TILE);
    ctx.lineWidth = 1;
    ctx.fillStyle = "#6f7f66";
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "left";
    ctx.fillText("MEETING ROOM", 14 * TILE + 10, TILE + 16);
    // 회의 테이블 (둥근 나무)
    ctx.fillStyle = "#8a5a34";
    rr(16.4 * TILE, 3.3 * TILE, 4.2 * TILE, 3.4 * TILE, 16); ctx.fill();
    ctx.fillStyle = "#9c6a40";
    rr(16.7 * TILE, 3.6 * TILE, 3.6 * TILE, 2.8 * TILE, 12); ctx.fill();

    // 화이트보드 (좌벽)
    ctx.fillStyle = "#f4f1e8";
    ctx.fillRect(TILE * 0.5, 4.5 * TILE, 8, 3 * TILE);
    // 화분들
    plant(1.2 * TILE, 1.2 * TILE);
    plant(12.3 * TILE, 1.3 * TILE);
    plant((COLS - 2) * TILE, (ROWS - 2.2) * TILE);
    // 책장 (아래 좌)
    ctx.fillStyle = "#6f4a2c";
    ctx.fillRect(1.7 * TILE, 13.2 * TILE, TILE * 2.4, TILE * 1.4);
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = ["#c76", "#7a9", "#dc8", "#89b", "#c99", "#8a7"][i];
      ctx.fillRect(1.8 * TILE + i * 11, 13.35 * TILE, 8, TILE * 1.1);
    }
    // 커피 코너 (라운지)
    ctx.fillStyle = "#3a3f4a";
    ctx.fillRect(9.3 * TILE, 12.2 * TILE, TILE * 0.9, TILE);
    ctx.fillStyle = "#c0392b";
    ctx.fillRect(9.45 * TILE, 12.35 * TILE, 6, 6);
    ctx.fillStyle = "#6cb6e6";
    ctx.fillRect(10.4 * TILE, 12.1 * TILE, TILE * 0.7, TILE * 1.1);
    // 소파
    ctx.fillStyle = "#6b6f8a";
    rr(4 * TILE, 12.9 * TILE, 3.2 * TILE, TILE * 1.1, 10); ctx.fill();
    ctx.fillStyle = "#7d82a0";
    rr(4.2 * TILE, 13.1 * TILE, 2.8 * TILE, TILE * 0.7, 6); ctx.fill();

    // 따뜻한 조명 비네트
    const g = ctx.createRadialGradient(
      canvas.width * 0.42, canvas.height * 0.4, 60,
      canvas.width * 0.42, canvas.height * 0.4, canvas.width * 0.75);
    g.addColorStop(0, "rgba(255,240,200,0.10)");
    g.addColorStop(1, "rgba(20,10,0,0.28)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function plant(x, y) {
    ctx.fillStyle = "#b5713e";
    ctx.fillRect(x, y + 16, 18, 12);
    ctx.fillStyle = "#4e9e57";
    ctx.beginPath(); ctx.arc(x + 9, y + 10, 13, 0, 7); ctx.fill();
    ctx.fillStyle = "#5fb268";
    ctx.beginPath(); ctx.arc(x + 4, y + 6, 7, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 14, y + 7, 7, 0, 7); ctx.fill();
  }

  function drawDesk(nick, d) {
    const px = d.x * TILE, py = d.y * TILE;
    // 책상 상판 (둥근 나무)
    ctx.fillStyle = "#9a6b40";
    rr(px - 16, py - 12, TILE + 26, TILE + 2, 7); ctx.fill();
    ctx.fillStyle = "#ac7c4d";
    rr(px - 13, py - 9, TILE + 20, TILE - 4, 5); ctx.fill();
    // 모니터
    ctx.fillStyle = "#20242e";
    rr(px - 3, py - 24, 24, 15, 3); ctx.fill();
    ctx.fillStyle = PEOPLE[nick] ? PEOPLE[nick].body : "#9aa";
    ctx.fillRect(px, py - 21, 18, 9);
    // 머그
    ctx.fillStyle = "#e07a4a";
    ctx.beginPath(); ctx.arc(px + 24, py, 4, 0, 7); ctx.fill();
  }

  // ── 아바타 (큰 머리, 둥글둥글) ───────────────────────────
  function drawAvatar(nick, a, now) {
    const walking = Math.abs(a.x - a.cx) + Math.abs(a.y - a.cy) > 0.05;
    const bob = walking ? Math.sin((now - t0) / 100) * 2.5 : 0;
    const px = a.cx * TILE + TILE / 2;
    const py = a.cy * TILE + TILE / 2 + bob;
    const p = PEOPLE[nick] || { body: "#9aa0b0", hair: "#333" };

    // 그림자
    ctx.fillStyle = "rgba(0,0,0,0.22)";
    ctx.beginPath(); ctx.ellipse(px, py + 15, 11, 4, 0, 0, 7); ctx.fill();
    // 몸 (작게)
    ctx.fillStyle = p.body;
    rr(px - 8, py + 1, 16, 14, 6); ctx.fill();
    // 머리 (크게 — 동물의숲 비율)
    ctx.beginPath(); ctx.arc(px, py - 7, 10, 0, 7);
    ctx.fillStyle = "#f5d9b8"; ctx.fill();
    // 머리카락
    ctx.fillStyle = p.hair;
    ctx.beginPath(); ctx.arc(px, py - 9, 10, Math.PI * 0.95, Math.PI * 2.05); ctx.fill();
    ctx.fillRect(px - 10, py - 10, 20, 4);
    // 눈
    ctx.fillStyle = "#2a2530";
    ctx.beginPath(); ctx.arc(px - 3.5, py - 6, 1.6, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(px + 3.5, py - 6, 1.6, 0, 7); ctx.fill();

    // 이름표
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(40,26,14,0.82)";
    rr(px - 22, py + 17, 44, 13, 4); ctx.fill();
    ctx.fillStyle = "#fdf3e2";
    ctx.fillText(nick, px, py + 26);

    const label = STATUS_LABEL[a.status];
    if (label) {
      ctx.fillStyle = a.status === "warn" ? "#e5484d" : "#5a4632";
      ctx.font = "9px monospace";
      ctx.fillText(label, px, py - 22);
    }
  }

  function drawBubble(b, now) {
    const a = actors[b.nick];
    if (!a) return;
    const px = a.cx * TILE + TILE / 2;
    const py = a.cy * TILE + TILE / 2;
    ctx.font = "11px -apple-system, 'Malgun Gothic', sans-serif";
    const w = Math.max(90, ...b.lines.map((l) => ctx.measureText(l).width)) + 18;
    const h = 10 + b.lines.length * 14;
    let bx = Math.min(Math.max(px - w / 2, 4), canvas.width - w - 4);
    const by = Math.max(py - 44 - h, 4);
    const fade = Math.min(1, (b.until - now) / 800);
    ctx.globalAlpha = fade;
    ctx.fillStyle = "#fffaf0";
    rr(bx, by, w, h, 9); ctx.fill();
    ctx.strokeStyle = "rgba(120,90,50,0.3)"; ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(px - 6, by + h - 1); ctx.lineTo(px + 6, by + h - 1); ctx.lineTo(px, by + h + 7);
    ctx.fillStyle = "#fffaf0"; ctx.fill();
    ctx.fillStyle = "#2a2016";
    ctx.textAlign = "left";
    b.lines.forEach((l, i) => ctx.fillText(l, bx + 9, by + 16 + i * 14));
    ctx.globalAlpha = 1;
  }

  function loop() {
    const now = performance.now();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawRoom(now);
    for (const [nick, d] of Object.entries(desks)) drawDesk(nick, d);
    bubbles = bubbles.filter((b) => b.until > now);
    for (const a of Object.values(actors)) {
      a.cx += (a.x - a.cx) * 0.12;
      a.cy += (a.y - a.cy) * 0.12;
    }
    Object.entries(actors)
      .sort((p, q) => p[1].cy - q[1].cy)
      .forEach(([nick, a]) => drawAvatar(nick, a, now));
    for (const b of bubbles) drawBubble(b, now);
    requestAnimationFrame(loop);
  }

  function rr(x, y, w, h, r) {
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
