// 톱다운 아늑한 픽셀 사무실 (동물의숲 톤). 서버 /office/state 격자(28x18)를 픽셀로.
window.Office = (() => {
  const TILE = 32;
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const COLS = W / TILE;   // 28
  const ROWS = H / TILE;   // 18

  const PEOPLE = {
    Victoria: { body: "#e6b45a", hair: "#6b4326" },
    Sophia: { body: "#5ac9a0", hair: "#33323c" },
    Michelle: { body: "#e08ad6", hair: "#8a5620" },
    Chloe: { body: "#b6d766", hair: "#d79a3e" },
    후니: { body: "#7bb0f2", hair: "#2b2f3a" },
  };
  const STATUS_LABEL = {
    desk: "", thinking: "생각 중…", talking: "말하는 중",
    meeting: "회의 중", warn: "⚠", break: "☕",
  };

  // 책상이 바라보는 방향 (아바타/의자 배치용)
  const DESK_FACE = {
    Victoria: "down", Sophia: "up", Michelle: "down", Chloe: "up", 후니: "down",
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
        cx: prev ? prev.cx : a.x, cy: prev ? prev.cy : a.y,
      };
    }
    // 책상은 서버가 준 고정 좌표. 캐릭터가 어디 있든 항상 제자리.
    if (state.desks) {
      for (const [nick, xy] of Object.entries(state.desks)) desks[nick] = { x: xy[0], y: xy[1] };
    }
    if (!running) { running = true; requestAnimationFrame(loop); }
  }

  function say(nick, text) {
    const clean = text
      .replace(/```[\s\S]*?```/g, " (코드 제안) ")
      .replace(/[*_`#>]/g, "")
      .replace(/\s+/g, " ").trim();
    bubbles = bubbles.filter((b) => b.nick !== nick);
    bubbles.push({ nick, lines: wrap(clean, 30).slice(0, 3), until: performance.now() + 6500 });
    if (bubbles.length > 2) bubbles = bubbles.slice(-2);   // 최근 발언 2개만
    if (actors[nick]) actors[nick].status = "talking";
  }

  function wrap(s, n) {
    const out = []; let line = "";
    for (const w of s.split(" ")) {
      if ((line + " " + w).trim().length > n) { out.push(line.trim()); line = w; }
      else line += " " + w;
    }
    if (line.trim()) out.push(line.trim());
    return out;
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
  const px = (n) => n * TILE;

  // ── 바닥 ────────────────────────────────────────────────
  function drawFloors() {
    // 개발실 + 라운지: 나무 널
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        let col;
        if (x >= 15 && y <= 9) {                     // 회의실: 초록 카펫
          col = ((x + y) % 2) ? "#84b18a" : "#7fae86";
        } else if (x >= 15 && y >= 10) {             // 탕비실: 체크 타일
          col = ((x + y) % 2) ? "#d9d2c4" : "#e7e1d3";
        } else {                                     // 나무
          col = ["#b98a5a", "#c09262", "#bd8d5d", "#b58658"][(x * 7 + y * 13) % 4];
        }
        ctx.fillStyle = col;
        ctx.fillRect(px(x), px(y), TILE, TILE);
      }
    }
    // 나무 널 이음선
    ctx.strokeStyle = "rgba(120,85,50,0.18)";
    for (let y = 0; y < ROWS; y++) for (let x = 0; x < 15; x++) ctx.strokeRect(px(x), px(y), TILE, TILE);

    // 라운지 러그
    ctx.fillStyle = "#c98b7a"; rr(px(1.5), px(12.5), px(6.5), px(4), 14); ctx.fill();
    ctx.fillStyle = "#dda593"; rr(px(1.9), px(12.9), px(5.7), px(3.2), 10); ctx.fill();
  }

  // ── 벽 / 파티션 ─────────────────────────────────────────
  function drawWalls() {
    ctx.fillStyle = "#e8dcc4";
    ctx.fillRect(0, 0, W, px(0.85));
    ctx.fillRect(0, 0, px(0.4), H);
    ctx.fillRect(W - px(0.4), 0, px(0.4), H);
    ctx.fillRect(0, H - px(0.4), W, px(0.4));
    ctx.strokeStyle = "#cbb98f"; ctx.lineWidth = 2;
    ctx.strokeRect(px(0.4), px(0.85), W - px(0.8), H - px(1.25));
    ctx.lineWidth = 1;

    // 창문 (위 벽) — 하늘 그라데이션 + 창틀
    for (let i = 1.5; i < 13; i += 3.5) {
      const sky = ctx.createLinearGradient(0, 0, 0, px(0.8));
      sky.addColorStop(0, "#bfe3f2"); sky.addColorStop(1, "#9fd0e8");
      ctx.fillStyle = sky; ctx.fillRect(px(i), 3, px(2.6), px(0.74));
      ctx.strokeStyle = "#c8ab77"; ctx.lineWidth = 2;
      ctx.strokeRect(px(i), 3, px(2.6), px(0.74));
      ctx.beginPath(); ctx.moveTo(px(i) + px(1.3), 3); ctx.lineTo(px(i) + px(1.3), px(0.77) + 3);
      ctx.moveTo(px(i), 3 + px(0.37)); ctx.lineTo(px(i) + px(2.6), 3 + px(0.37)); ctx.stroke();
      ctx.lineWidth = 1;
      // 화분
      ctx.fillStyle = "#5aa06a"; ctx.fillRect(px(i) + px(1.05), px(0.55), 10, 7);
    }
    // 벽시계
    ctx.fillStyle = "#fdfaf2"; ctx.beginPath(); ctx.arc(px(13.5), px(0.42), 9, 0, 7); ctx.fill();
    ctx.strokeStyle = "#3a3f4f"; ctx.beginPath(); ctx.arc(px(13.5), px(0.42), 9, 0, 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(px(13.5), px(0.42)); ctx.lineTo(px(13.5), px(0.42) - 6);
    ctx.moveTo(px(13.5), px(0.42)); ctx.lineTo(px(13.5) + 4, px(0.42)); ctx.stroke();

    // 회의실 유리 파티션 (x=15 세로, y=9 가로)
    ctx.strokeStyle = "rgba(150,200,255,0.55)"; ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(px(15), px(0.85)); ctx.lineTo(px(15), px(9));
    ctx.lineTo(W - px(0.4), px(9));
    ctx.stroke();
    // 유리 하이라이트
    ctx.strokeStyle = "rgba(255,255,255,0.15)"; ctx.lineWidth = 1;
    for (let y = 1; y < 9; y += 1.2) { ctx.beginPath(); ctx.moveTo(px(15) + 3, px(y)); ctx.lineTo(px(15) + 3, px(y + 0.7)); ctx.stroke(); }
    ctx.lineWidth = 1;
    // 회의실 문 틈
    ctx.strokeStyle = "#7fae86"; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(px(15), px(6.4)); ctx.lineTo(px(15), px(7.6)); ctx.stroke();
    ctx.lineWidth = 1;

    // 탕비실 상단 캐비닛 라인 (벽면)
    ctx.fillStyle = "#c9a36b";
    ctx.fillRect(px(15.2), px(9.2), px(11.4), px(0.7));
    for (let i = 0; i < 9; i++) ctx.strokeRect(px(15.4) + i * px(1.25), px(9.25), px(1.1), px(0.6));

    // 라벨
    ctx.fillStyle = "#6f7f66"; ctx.font = "bold 10px monospace"; ctx.textAlign = "left";
    ctx.fillText("MEETING ROOM", px(15.4), px(0.72));
    ctx.fillStyle = "#8a7a5f";
    ctx.fillText("PANTRY", px(15.4), px(10.05));
  }

  // ── 개별 가구 ───────────────────────────────────────────
  function chair(cx, cy, dir, tone = "#556") {
    // 등받이
    ctx.fillStyle = tone;
    if (dir === "up") rr(cx - 10, cy - 13, 20, 7, 4);
    else if (dir === "down") rr(cx - 10, cy + 6, 20, 7, 4);
    else if (dir === "left") rr(cx - 13, cy - 10, 7, 20, 4);
    else rr(cx + 6, cy - 10, 7, 20, 4);
    ctx.fill();
    // 시트
    ctx.fillStyle = "#6a7188";
    rr(cx - 9, cy - 9, 18, 18, 6); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.10)";
    rr(cx - 7, cy - 7, 14, 6, 3); ctx.fill();
  }

  // 데스크: 의자는 아바타 자리(x,y)에, 책상+모니터는 face 방향으로 offset.
  function deskSetup(nick, d) {
    const x = px(d.x) + TILE / 2, y = px(d.y) + TILE / 2;
    const face = DESK_FACE[nick] || "down";     // "down" = 아래를 향해 앉음 → 책상은 아래
    const dir = face === "down" ? 1 : -1;
    const ty = y + dir * 30;                     // 책상 중심

    // 작은 러그
    ctx.fillStyle = "rgba(120,90,150,0.14)";
    ctx.beginPath(); ctx.ellipse(x, y + dir * 12, 44, 34, 0, 0, 7); ctx.fill();
    // 의자 (아바타 아래에 깔림)
    chair(x, y, face);
    // 책상 상판
    ctx.fillStyle = "#7a5233"; rr(x - 36, ty - 13, 72, 24, 7); ctx.fill();
    ctx.fillStyle = "#986641"; rr(x - 33, ty - 10, 66, 18, 5); ctx.fill();
    // 듀얼 모니터 (책상 먼 가장자리)
    const my = ty + dir * 12;
    ctx.fillStyle = "#20242e";
    rr(x - 27, my - 8, 24, 15, 3); ctx.fill();
    rr(x + 3, my - 8, 24, 15, 3); ctx.fill();
    ctx.fillStyle = (PEOPLE[nick] || {}).body || "#9aa";
    ctx.fillRect(x - 24, my - 5, 18, 9);
    ctx.fillStyle = "#8fd3e6";
    ctx.fillRect(x + 6, my - 5, 18, 9);
    // 키보드 + 머그 + 서류
    ctx.fillStyle = "#3a3f52"; rr(x - 13, ty - 2, 28, 8, 2); ctx.fill();
    ctx.fillStyle = "#e07a4a"; ctx.beginPath(); ctx.arc(x + 24, ty + 1, 4, 0, 7); ctx.fill();
    ctx.fillStyle = "#f2ede0"; ctx.fillRect(x - 32, ty - 3, 10, 12);
  }

  function meetingRoom() {
    const tx = px(21), ty = px(4.6);
    // 의자 6개 (테이블 아래에 깔림)
    for (const [ax, ay, dr] of [[17.2, 4, "right"], [17.2, 6, "right"],
      [21, 2.6, "down"], [21, 7, "up"], [24.8, 4, "left"], [24.8, 6, "left"]])
      chair(px(ax), px(ay), dr);
    // 큰 원탁 + 나이테
    ctx.fillStyle = "#7a4f2e";
    ctx.beginPath(); ctx.ellipse(tx, ty, px(2.7), px(1.95), 0, 0, 7); ctx.fill();
    ctx.fillStyle = "#95643f";
    ctx.beginPath(); ctx.ellipse(tx, ty, px(2.4), px(1.68), 0, 0, 7); ctx.fill();
    ctx.strokeStyle = "rgba(90,60,35,0.35)";
    for (const r of [0.55, 0.78]) { ctx.beginPath(); ctx.ellipse(tx, ty, px(2.4) * r, px(1.68) * r, 0, 0, 7); ctx.stroke(); }
    // 노트북 + 커피 + 문서
    ctx.fillStyle = "#2a2f3c"; rr(tx - 34, ty - 7, 18, 12, 2); ctx.fill();
    ctx.fillStyle = "#7fd0e6"; ctx.fillRect(tx - 32, ty - 5, 14, 8);
    ctx.fillStyle = "#e07a4a"; ctx.beginPath(); ctx.arc(tx + 20, ty - 6, 4, 0, 7); ctx.fill();
    ctx.fillStyle = "#f2ede0"; ctx.fillRect(tx + 10, ty + 6, 12, 15);
    // 벽면 TV (프레젠테이션 화면)
    ctx.fillStyle = "#15181f"; rr(px(19.3), px(1.0), px(3.4), px(1.7), 4); ctx.fill();
    const gr = ctx.createLinearGradient(px(19.5), 0, px(22.5), 0);
    gr.addColorStop(0, "#2f6f8f"); gr.addColorStop(1, "#3f8f7f");
    ctx.fillStyle = gr; ctx.fillRect(px(19.5), px(1.15), px(3), px(1.35));
    ctx.fillStyle = "rgba(255,255,255,0.25)"; ctx.fillRect(px(19.8), px(1.4), px(1.6), 4); ctx.fillRect(px(19.8), px(1.8), px(2.2), 4);
    // 화이트보드 (측벽)
    ctx.fillStyle = "#f7f4ec"; rr(px(25.9), px(2.3), px(0.55), px(3.2), 2); ctx.fill();
    ctx.strokeStyle = "#c74"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(px(26), px(3)); ctx.lineTo(px(26.35), px(4)); ctx.lineTo(px(26.05), px(4.6)); ctx.stroke();
    ctx.lineWidth = 1;
    plant(px(15.6), px(7.3));
    plant(px(25.4), px(7.3));
  }

  function pantry() {
    const top = px(9.9);
    // 조리대
    ctx.fillStyle = "#cdd3da"; ctx.fillRect(px(15.2), top, px(11.4), px(1));
    ctx.fillStyle = "#b8bec6"; ctx.fillRect(px(15.2), top, px(11.4), 5);
    // 싱크
    ctx.fillStyle = "#8b939c"; rr(px(16), top + 6, px(1.4), px(0.7), 3); ctx.fill();
    ctx.strokeStyle = "#6f767e"; ctx.beginPath(); ctx.moveTo(px(16.7), top + 2); ctx.lineTo(px(16.7), top + 6); ctx.stroke();
    // 커피 머신
    ctx.fillStyle = "#3a3f4a"; ctx.fillRect(px(18.2), top - px(0.5), px(0.9), px(1.3));
    ctx.fillStyle = "#c0392b"; ctx.fillRect(px(18.35), top - px(0.2), 7, 7);
    // 전자레인지
    ctx.fillStyle = "#2b2f38"; ctx.fillRect(px(19.6), top - px(0.4), px(1.3), px(0.9));
    ctx.fillStyle = "#5b8fb0"; ctx.fillRect(px(19.75), top - px(0.25), px(0.8), px(0.6));
    // 스낵 선반
    ctx.fillStyle = "#8a6a44"; ctx.fillRect(px(21.4), top - px(0.35), px(2), px(0.5));
    for (let i = 0; i < 5; i++) { ctx.fillStyle = ["#e6b45a", "#e08ad6", "#b6d766", "#7bb0f2", "#e07a4a"][i]; ctx.fillRect(px(21.5) + i * 11, top - px(0.3), 8, 10); }
    // 냉장고
    ctx.fillStyle = "#dfe3e8"; rr(px(24.4), top - px(0.4), px(1.6), px(2.6), 5); ctx.fill();
    ctx.strokeStyle = "#b7bcc4"; ctx.beginPath(); ctx.moveTo(px(24.4), top + px(0.9)); ctx.lineTo(px(26), top + px(0.9)); ctx.stroke();
    ctx.fillStyle = "#9aa0aa"; ctx.fillRect(px(25.6), top + px(0.2), 4, 10);
    ctx.fillStyle = "#9aa0aa"; ctx.fillRect(px(25.6), top + px(1.1), 4, 10);

    // 커피 코너 간판
    ctx.fillStyle = "#5b3f28"; rr(px(17.6), px(10.4), px(2.4), px(0.7), 3); ctx.fill();
    ctx.fillStyle = "#f0e2c4"; ctx.font = "bold 11px monospace"; ctx.textAlign = "center";
    ctx.fillText("☕ COFFEE", px(18.8), px(10.9));

    // 바 스툴 (조리대 앞)
    for (const bx of [16, 17.3, 18.6]) {
      ctx.fillStyle = "#6f5842"; ctx.beginPath(); ctx.arc(px(bx), px(11.4), 8, 0, 7); ctx.fill();
      ctx.fillStyle = "#8a6a44"; ctx.beginPath(); ctx.arc(px(bx), px(11.4), 4, 0, 7); ctx.fill();
    }

    // 원형 식탁 + 의자 3
    const dx = px(21.5), dy = px(13.8);
    ctx.fillStyle = "#7a4f2e"; ctx.beginPath(); ctx.arc(dx, dy, 30, 0, 7); ctx.fill();
    ctx.fillStyle = "#95643f"; ctx.beginPath(); ctx.arc(dx, dy, 25, 0, 7); ctx.fill();
    ctx.strokeStyle = "rgba(90,60,35,0.3)"; ctx.beginPath(); ctx.arc(dx, dy, 15, 0, 7); ctx.stroke();
    for (const [sx, sy, dr] of [[dx - 40, dy, "right"], [dx + 40, dy, "left"], [dx, dy + 40, "up"]])
      chair(sx, sy, dr, "#6a5240");
    ctx.fillStyle = "#e07a4a"; ctx.beginPath(); ctx.arc(dx - 6, dy - 4, 4, 0, 7); ctx.fill();
    ctx.fillStyle = "#7fd0e6"; ctx.beginPath(); ctx.arc(dx + 8, dy + 4, 4, 0, 7); ctx.fill();

    // 자판기
    ctx.fillStyle = "#c0392b"; rr(px(25.7), px(10.2), px(1.1), px(2), 4); ctx.fill();
    ctx.fillStyle = "#1a1d24"; ctx.fillRect(px(25.85), px(10.4), px(0.55), px(1.1));
    ctx.fillStyle = "#f0c040"; ctx.fillRect(px(25.85), px(11.7), px(0.8), 6);

    plant(px(15.5), px(15.2));
    plant(px(25.4), px(14.8));
  }

  function lounge() {
    // ㄴ자 소파
    ctx.fillStyle = "#6b6f8a";
    rr(px(1.6), px(12.8), px(3.6), px(1.1), 10); ctx.fill();
    rr(px(1.6), px(12.8), px(1.1), px(3.4), 10); ctx.fill();
    ctx.fillStyle = "#7d82a0";
    rr(px(1.85), px(13.05), px(3.1), px(0.7), 6); ctx.fill();
    rr(px(1.85), px(13.05), px(0.7), px(2.9), 6); ctx.fill();
    // 쿠션
    ctx.fillStyle = "#e6b45a"; rr(px(3.1), px(13.0), px(0.8), px(0.7), 4); ctx.fill();
    ctx.fillStyle = "#b6d766"; rr(px(1.9), px(14.4), px(0.7), px(0.8), 4); ctx.fill();
    // 커피 테이블
    ctx.fillStyle = "#7a5636"; rr(px(3.4), px(14.2), px(2), px(1.2), 6); ctx.fill();
    ctx.fillStyle = "#8a6a44"; rr(px(3.55), px(14.35), px(1.7), px(0.9), 4); ctx.fill();
    ctx.fillStyle = "#c94"; ctx.fillRect(px(4), px(14.55), 8, 5);
    // 책장
    ctx.fillStyle = "#6f4a2c"; ctx.fillRect(px(6.4), px(12.7), px(2.6), px(1.5));
    for (let i = 0; i < 7; i++) { ctx.fillStyle = ["#c76", "#7a9", "#dc8", "#89b", "#c99", "#8a7", "#b98"][i]; ctx.fillRect(px(6.55) + i * 10, px(12.8), 7, px(1.3)); }
    // 플로어 램프
    ctx.strokeStyle = "#8a8a8a"; ctx.beginPath(); ctx.moveTo(px(9.6), px(13.2)); ctx.lineTo(px(9.6), px(14.6)); ctx.stroke();
    ctx.fillStyle = "#ffe6a8"; ctx.beginPath(); ctx.moveTo(px(9.3), px(13.2)); ctx.lineTo(px(9.9), px(13.2)); ctx.lineTo(px(9.75), px(12.7)); ctx.lineTo(px(9.45), px(12.7)); ctx.fill();
    // 큰 화분
    plant(px(11), px(13.4));
    // 정수기
    ctx.fillStyle = "#dfe3e8"; ctx.fillRect(px(12.5), px(13.0), px(0.8), px(1.4));
    ctx.fillStyle = "#6cb6e6"; ctx.fillRect(px(12.55), px(12.6), px(0.7), px(0.7));
  }

  // 개발실 아래 빈 공간 채우기 — 복합기 / 코트걸이 / 화분
  function centralProps() {
    // 복합기(프린터) 스테이션
    const cx = px(11.5), cy = px(11);
    ctx.fillStyle = "#3b4150"; rr(cx - 20, cy - 16, 40, 34, 5); ctx.fill();
    ctx.fillStyle = "#4c5364"; rr(cx - 17, cy - 13, 34, 14, 3); ctx.fill();
    ctx.fillStyle = "#e9edf2"; ctx.fillRect(cx - 12, cy + 2, 24, 8);   // 배출된 종이
    ctx.fillStyle = "#5aa06a"; ctx.fillRect(cx - 14, cy - 9, 5, 4);
    ctx.fillStyle = "#e0b45a"; ctx.fillRect(cx - 6, cy - 9, 5, 4);
    // 코트 걸이
    const rxp = px(13.6), ryp = px(9.6);
    ctx.strokeStyle = "#7a5a3a"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(rxp, ryp); ctx.lineTo(rxp, ryp + 26); ctx.stroke();
    ctx.lineWidth = 1;
    ctx.fillStyle = "#c0524a"; rr(rxp + 2, ryp + 4, 10, 14, 3); ctx.fill();
    ctx.fillStyle = "#4d6a94"; rr(rxp - 12, ryp + 4, 10, 14, 3); ctx.fill();
    // 러그 + 화분
    ctx.fillStyle = "rgba(120,140,110,0.14)";
    ctx.beginPath(); ctx.ellipse(px(11.5), px(12.6), 52, 34, 0, 0, 7); ctx.fill();
    plant(px(9.4), px(11.2));
  }

  function plant(x, y) {
    ctx.fillStyle = "#b5713e"; ctx.fillRect(x, y + 16, 18, 12);
    ctx.fillStyle = "#4e9e57"; ctx.beginPath(); ctx.arc(x + 9, y + 10, 13, 0, 7); ctx.fill();
    ctx.fillStyle = "#5fb268";
    ctx.beginPath(); ctx.arc(x + 4, y + 6, 7, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 14, y + 7, 7, 0, 7); ctx.fill();
  }

  function ceilingGlow() {
    for (const [gx, gy] of [[6, 5], [11, 9], [21, 4.5], [21, 13.5], [4, 14]]) {
      const g = ctx.createRadialGradient(px(gx), px(gy), 6, px(gx), px(gy), px(4));
      g.addColorStop(0, "rgba(255,244,214,0.13)");
      g.addColorStop(1, "rgba(255,244,214,0)");
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    // 전체 비네트 (약하게)
    const v = ctx.createRadialGradient(W * 0.45, H * 0.42, 120, W * 0.45, H * 0.42, W * 0.85);
    v.addColorStop(0, "rgba(0,0,0,0)");
    v.addColorStop(1, "rgba(20,12,0,0.16)");
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }

  // ── 아바타 ─────────────────────────────────────────────
  function drawAvatar(nick, a, now) {
    const walking = Math.abs(a.x - a.cx) + Math.abs(a.y - a.cy) > 0.05;
    const bob = walking ? Math.sin((now - t0) / 100) * 2.5 : 0;
    const X = a.cx * TILE + TILE / 2;
    const Y = a.cy * TILE + TILE / 2 + bob;
    const p = PEOPLE[nick] || { body: "#9aa0b0", hair: "#333" };

    ctx.fillStyle = "rgba(0,0,0,0.22)";
    ctx.beginPath(); ctx.ellipse(X, Y + 15, 11, 4, 0, 0, 7); ctx.fill();
    ctx.fillStyle = p.body; rr(X - 8, Y + 1, 16, 14, 6); ctx.fill();
    ctx.beginPath(); ctx.arc(X, Y - 7, 10, 0, 7); ctx.fillStyle = "#f5d9b8"; ctx.fill();
    ctx.fillStyle = p.hair;
    ctx.beginPath(); ctx.arc(X, Y - 9, 10, Math.PI * 0.95, Math.PI * 2.05); ctx.fill();
    ctx.fillRect(X - 10, Y - 10, 20, 4);
    ctx.fillStyle = "#2a2530";
    ctx.beginPath(); ctx.arc(X - 3.5, Y - 6, 1.6, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(X + 3.5, Y - 6, 1.6, 0, 7); ctx.fill();

    ctx.font = "bold 10px monospace"; ctx.textAlign = "center";
    ctx.fillStyle = "rgba(40,26,14,0.82)"; rr(X - 22, Y + 17, 44, 13, 4); ctx.fill();
    ctx.fillStyle = "#fdf3e2"; ctx.fillText(nick, X, Y + 26);

    if (a.status === "break") {
      // 머리 위 커피컵
      ctx.fillStyle = "#f2ede0"; rr(X + 8, Y - 20, 8, 7, 1); ctx.fill();
      ctx.strokeStyle = "#c98b5a"; ctx.strokeRect(X + 8, Y - 20, 8, 7);
      ctx.fillStyle = "#7a4a2a"; ctx.fillRect(X + 9, Y - 19, 6, 2);
    } else {
      const label = STATUS_LABEL[a.status];
      if (label) {
        ctx.fillStyle = a.status === "warn" ? "#e5484d" : "#5a4632";
        ctx.font = "9px monospace"; ctx.fillText(label, X, Y - 22);
      }
    }
  }

  function drawBubble(b, now) {
    const a = actors[b.nick]; if (!a) return;
    const X = a.cx * TILE + TILE / 2;
    const Y = a.cy * TILE + TILE / 2;
    ctx.font = "11px -apple-system, 'Malgun Gothic', sans-serif";
    const w = Math.max(90, ...b.lines.map((l) => ctx.measureText(l).width)) + 18;
    const h = 10 + b.lines.length * 14;
    const bx = Math.min(Math.max(X - w / 2, 4), W - w - 4);
    const by = Math.max(Y - 44 - h, 4);
    const fade = Math.min(1, (b.until - now) / 800);
    ctx.globalAlpha = fade;
    ctx.fillStyle = "#fffaf0"; rr(bx, by, w, h, 9); ctx.fill();
    ctx.strokeStyle = "rgba(120,90,50,0.3)"; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(X - 6, by + h - 1); ctx.lineTo(X + 6, by + h - 1); ctx.lineTo(X, by + h + 7);
    ctx.fillStyle = "#fffaf0"; ctx.fill();
    ctx.fillStyle = "#2a2016"; ctx.textAlign = "left";
    b.lines.forEach((l, i) => ctx.fillText(l, bx + 9, by + 16 + i * 14));
    ctx.globalAlpha = 1;
  }

  function loop() {
    const now = performance.now();
    ctx.clearRect(0, 0, W, H);
    drawFloors();
    lounge();
    centralProps();
    pantry();
    meetingRoom();
    drawWalls();
    for (const [nick, d] of Object.entries(desks)) deskSetup(nick, d);

    bubbles = bubbles.filter((b) => b.until > now);
    for (const a of Object.values(actors)) {
      a.cx += (a.x - a.cx) * 0.055;
      a.cy += (a.y - a.cy) * 0.055;
    }
    Object.entries(actors).sort((p, q) => p[1].cy - q[1].cy)
      .forEach(([nick, a]) => drawAvatar(nick, a, now));
    for (const b of bubbles) drawBubble(b, now);

    ceilingGlow();
    requestAnimationFrame(loop);
  }

  return { render, say };
})();
