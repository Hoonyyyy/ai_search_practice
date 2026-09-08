"""공유 브리핑 조립. 레포에 대해 읽기 전용 — git log 와 디렉토리 나열만 한다."""
import subprocess
from pathlib import Path

from config import settings

_SKIP = {
    ".git", "venv", "node_modules", "__pycache__", "office",
    "target", "build", ".idea", ".vscode", "logs", "data",
}
_BRIEF = Path(__file__).resolve().parent.parent / "context" / "brief.md"


def _git_log() -> str:
    try:
        out = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=settings.repo_root_path,
            capture_output=True, timeout=5,
            encoding="utf-8", errors="replace",  # 한국어 커밋 메시지: 로케일(cp949) 디코딩 금지
        )
        return (out.stdout or "").strip() or "(git log 없음)"
    except (OSError, subprocess.SubprocessError):
        return "(git log 조회 실패)"


def _tree(root: Path, depth: int = 2) -> str:
    lines: list[str] = []

    def walk(d: Path, prefix: str, level: int) -> None:
        if level > depth:
            return
        try:
            children = sorted(d.iterdir())
        except OSError:
            return
        for child in children:
            if child.name in _SKIP or child.name.startswith("."):
                continue
            lines.append(f"{prefix}{child.name}{'/' if child.is_dir() else ''}")
            if child.is_dir():
                walk(child, prefix + "  ", level + 1)

    walk(root, "", 1)
    return "\n".join(lines) or "(구조 없음)"


def assemble_brief() -> str:
    brief_md = _BRIEF.read_text(encoding="utf-8") if _BRIEF.exists() else ""
    full = (
        f"{brief_md}\n\n"
        f"## 최근 커밋\n{_git_log()}\n\n"
        f"## 레포 구조 (상위)\n{_tree(settings.repo_root_path, depth=1)}"
    )
    # 토큰 절약 — 회의 프롬프트에 매 턴 들어가므로 상한을 둔다
    return full[:2400]
