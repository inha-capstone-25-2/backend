from __future__ import annotations
import time

def _fmt_bytes(n: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"

def _fmt_eta(bytes_done: int, total: int, elapsed: float) -> str:
    if bytes_done <= 0 or total <= 0:
        return "unknown"
    speed = bytes_done / max(elapsed, 1e-6)
    remain = max(total - bytes_done, 0)
    sec = int(remain / max(speed, 1e-6))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_current_time() -> float:
    return time.time()