#!/usr/bin/env python3
"""Read-only system and experiment summaries for the Discord control bot."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(
    os.environ.get("OPENCLAW_RESEARCH_WORKSPACE", Path(__file__).resolve().parents[1])
).resolve()
OUTPUTS = ROOT / "outputs"
EXPERIMENTS = ROOT / "experiments"
LOG_ROOTS = (ROOT / "logs", EXPERIMENTS, OUTPUTS, Path("/openclaw_runtime_logs"))
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
REDACT = re.compile(r"(?i)(token|secret|password|authorization|api[_-]?key)\s*[:=]\s*([^\s,;]+)")
FAILURE = re.compile(r"(?i)\b(error|failed|failure|traceback|exception|oom|out of memory)\b")


def human_bytes(value: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def redact(text: str) -> str:
    return REDACT.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)


def run_fixed(argv: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        return completed.returncode, redact(output)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"실행 실패: {type(exc).__name__}"


def gateway_ok() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=2):
            return True
    except OSError:
        return False


def ollama_models() -> tuple[bool, list[str]]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as response:
            payload = json.load(response)
        names = [str(item.get("name", "")) for item in payload.get("models", [])]
        return True, [name for name in names if name]
    except (OSError, ValueError, urllib.error.URLError):
        return False, []


def uptime_text() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "확인 불가"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    return f"{days}일 {hours}시간 {seconds // 60}분"


def status() -> str:
    ollama_ok, models = ollama_models()
    model_state = "로드 가능" if DEFAULT_MODEL in models else "목록에서 미확인"
    return "\n".join(
        [
            "연구 PC 상태",
            f"- OpenClaw Gateway: {'정상' if gateway_ok() else '연결 실패'} (loopback:18789)",
            f"- Ollama: {'정상' if ollama_ok else '연결 실패'} (loopback:11434)",
            f"- 현재 기본 모델: ollama/{DEFAULT_MODEL} ({model_state})",
            f"- 서버 uptime: {uptime_text()}",
        ]
    )


def gpu() -> str:
    code, output = run_fixed([
        "nvidia-smi",
        "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
        "--format=csv,noheader,nounits",
    ])
    if code != 0 or not output:
        return f"GPU 상태 확인 실패\n{output}".strip()
    return "\n".join(
        ["GPU 상태 (이름 | 온도°C | 사용률% | VRAM 사용/전체 MiB | 전력 W)"]
        + [f"- {line}" for line in output.splitlines()[:8]]
    )


def disk() -> str:
    lines = ["디스크 상태"]
    seen: set[int] = set()
    # The sandbox root itself is a tmpfs; report the real workspace/data filesystems.
    targets = (("작업공간", ROOT), ("원본 데이터(읽기 전용)", Path("/data_raw")))
    for label, path in targets:
        if not path.exists():
            continue
        try:
            device = path.stat().st_dev
            if device in seen and label != "원본 데이터(읽기 전용)":
                continue
            seen.add(device)
            usage = shutil.disk_usage(path)
            percent = usage.used / usage.total * 100 if usage.total else 0
            lines.append(
                f"- {label}: {human_bytes(usage.used)} / {human_bytes(usage.total)} 사용 "
                f"({percent:.1f}%), 여유 {human_bytes(usage.free)}"
            )
        except OSError:
            lines.append(f"- {label}: 확인 실패")
    return "\n".join(lines)


def mem() -> str:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return "메모리 상태 확인 실패"
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(0, total - available)
    swap_total = values.get("SwapTotal", 0)
    swap_used = max(0, swap_total - values.get("SwapFree", 0))
    percent = used / total * 100 if total else 0
    return "\n".join([
        "메모리 상태",
        f"- RAM: {human_bytes(used)} / {human_bytes(total)} 사용 ({percent:.1f}%), 가용 {human_bytes(available)}",
        f"- Swap: {human_bytes(swap_used)} / {human_bytes(swap_total)} 사용",
    ])


def candidate_logs() -> list[Path]:
    files: list[Path] = []
    for root in LOG_ROOTS:
        if not root.exists():
            continue
        try:
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".log", ".txt", ".out", ".err", ".jsonl"}:
                    files.append(path)
        except OSError:
            continue
    return sorted(files, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)


def tail_lines(paths: Iterable[Path], limit: int = 80) -> list[str]:
    collected: list[str] = []
    for path in paths:
        if len(collected) >= limit:
            break
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        take = min(limit - len(collected), len(lines))
        collected.append(f"[{str(path).replace(str(ROOT), '.')}]")
        collected.extend(redact(line)[:500] for line in lines[-max(0, take - 1):])
    return collected[-limit:]


def log_summary() -> str:
    paths = candidate_logs()
    if not paths:
        return "최근 OpenClaw/실험 로그를 찾지 못했습니다."
    lines = tail_lines(paths, 80)
    failures = [line for line in lines if FAILURE.search(line)]
    names = [str(path).replace(str(ROOT), ".") for path in paths[:5]]
    body = ["최근 로그 요약 (최대 80줄 검사)", f"- 검사 파일: {len(paths)}개", f"- 오류 관련 줄: {len(failures)}개"]
    body.extend(f"- {name}" for name in names)
    if failures:
        body.append("최근 오류 후보:")
        body.extend(f"  {line[:350]}" for line in failures[-10:])
    return "\n".join(body)


def modified_files_since(cutoff: datetime) -> list[Path]:
    result: list[Path] = []
    for root in (EXPERIMENTS, OUTPUTS, ROOT / "logs"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            try:
                if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
                    result.append(path)
            except OSError:
                continue
    return result


def report() -> str:
    recent = modified_files_since(datetime.now() - timedelta(hours=24))
    failures = recent_failures(limit=100)
    return "\n".join([
        "최근 24시간 연구 관제 보고",
        status(), gpu(), mem(), disk(),
        f"- 최근 변경된 실험/출력/로그 파일: {len(recent)}개",
        f"- 감지된 최근 실패 후보: {len(failures)}개",
        f"- 생성 시각: {datetime.now().astimezone().isoformat(timespec='seconds')}",
    ])


def is_float(value: object) -> bool:
    try:
        float(str(value))
        return True
    except (TypeError, ValueError):
        return False


def leaderboard() -> str:
    path = EXPERIMENTS / "leaderboard.csv"
    if not path.exists():
        return "experiments/leaderboard.csv가 없습니다."
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return "leaderboard.csv 읽기에 실패했습니다."
    if not rows:
        return "leaderboard.csv에 데이터 행이 없습니다."
    fields = list(rows[0])
    preferred = ("score", "accuracy", "f1", "map", "mAP", "val_accuracy", "loss", "val_loss", "rmse", "mae")
    metric = next((name for name in preferred if name in fields), None)
    if metric is None:
        metric = next((name for name in fields if all(is_float(row.get(name, "")) for row in rows)), None)
    if metric is None:
        return "정렬 가능한 숫자 성능 열을 찾지 못했습니다."
    valid = [row for row in rows if is_float(row.get(metric, ""))]
    ascending = any(token in metric.lower() for token in ("loss", "rmse", "mae", "error"))
    valid.sort(key=lambda row: float(row[metric]), reverse=not ascending)
    identity = next((name for name in ("experiment", "run", "name", "id") if name in fields), fields[0])
    lines = [f"최고 성능 실험 5개 (기준: {metric}, {'낮을수록 우수' if ascending else '높을수록 우수'})"]
    lines.extend(
        f"{index}. {row.get(identity, '(이름 없음)')} — {metric}={row.get(metric)}"
        for index, row in enumerate(valid[:5], 1)
    )
    return "\n".join(lines)


def recent_failures(limit: int = 5) -> list[str]:
    candidates: list[tuple[float, str]] = []
    failed_dir = EXPERIMENTS / "failed_runs"
    if failed_dir.exists():
        for path in failed_dir.rglob("*"):
            try:
                if path.is_file():
                    candidates.append((path.stat().st_mtime, f"실패 산출물: {path.relative_to(ROOT)}"))
            except OSError:
                continue
    for path in candidate_logs():
        try:
            for line in path.read_text(errors="replace").splitlines()[-500:]:
                if FAILURE.search(line):
                    candidates.append((path.stat().st_mtime, f"{path.name}: {redact(line)[:300]}"))
        except OSError:
            continue
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in candidates[:limit]]


def failed() -> str:
    items = recent_failures(5)
    if not items:
        return "최근 실패 실행 또는 실패 로그를 찾지 못했습니다."
    return "\n".join(["최근 실패 5개"] + [f"{index}. {item}" for index, item in enumerate(items, 1)])


COMMANDS = {
    "status": status,
    "gpu": gpu,
    "disk": disk,
    "mem": mem,
    "log": log_summary,
    "report": report,
    "top5": leaderboard,
    "failed": failed,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print("허용된 명령: " + ", ".join(COMMANDS), file=sys.stderr)
        return 2
    started = time.monotonic()
    try:
        result = COMMANDS[sys.argv[1]]()
    except Exception as exc:
        print(f"관제 수집 실패: {type(exc).__name__}")
        return 1
    print(f"{result}\n- 수집 시간: {time.monotonic() - started:.2f}초")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
