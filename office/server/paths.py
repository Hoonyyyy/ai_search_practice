import json
import re
from typing import Any

from config import settings

_NAME_RE = re.compile(r"^[a-z_]+\.json$")


def _target(name: str):
    if not _NAME_RE.match(name):
        raise ValueError(f"bad data file name: {name!r}")
    return settings.data_dir / name


def read_json(name: str, default: Any) -> Any:
    p = _target(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(name: str, obj: Any) -> None:
    p = _target(name)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
