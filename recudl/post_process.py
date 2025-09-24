from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .console import info, warn, error, success, console


@dataclass
class PostProcessConfig:
    remux_to_mp4: bool = True
    generate_thumbnail: bool = True
    organize_output: bool = True
    open_in_explorer: bool = False
    write_report: bool = True
    output_dir: str = "downloads"
    reports_dir: str = "reports"
    thumbnails_dir: str = "thumbnails"


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run_ffmpeg(args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run([
            "ffmpeg",
            *args,
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", "ffmpeg not found"



def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _remux_ts_to_mp4(ts_path: Path, mp4_path: Path) -> bool:
    # Copy streams without re-encoding; fast and lossless
    rc, _, err = _run_ffmpeg(["-y", "-i", str(ts_path), "-c", "copy", str(mp4_path)])
    if rc != 0:
        warn(f"ffmpeg remux failed ({rc}): {err.splitlines()[-1] if err else ''}")
        return False
    return True


def _thumbnail(ts_or_mp4: Path, thumb_path: Path) -> bool:
    # Grab a frame at 25% of duration. If that fails, fallback to 00:00:01
    # First probe duration
    # ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input
    try:
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(ts_or_mp4),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        dur = 0.0
        if probe.returncode == 0:
            try:
                dur = float(probe.stdout.strip())
            except Exception:
                dur = 0.0
        ts = max(1.0, dur * 0.25)
        timestamp = time.strftime("%H:%M:%S", time.gmtime(ts))
        rc, _, err = _run_ffmpeg([
            "-y",
            "-ss",
            timestamp,
            "-i",
            str(ts_or_mp4),
            "-frames:v",
            "1",
            str(thumb_path),
        ])
        if rc != 0:
            warn(f"ffmpeg thumbnail failed ({rc}): {err.splitlines()[-1] if err else ''}")
            return False
        return True
    except FileNotFoundError:
        warn("ffprobe not found; skipping thumbnail generation")
        return False


def _open_in_explorer(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            # Select file in Explorer
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
    except Exception as ex:
        warn(f"Failed to open in file manager: {ex}")


def run(cfg: Dict[str, Any], base_filename: str, source_url: str) -> Dict[str, Any]:
    """Execute post-download steps.

    cfg: dictionary with toggles (see PostProcessConfig)
    base_filename: file name without extension (e.g., CB_user_YY-MM-DD_HH-MM)
    source_url: original URL used to download
    Returns a summary dict (also persisted if write_report=True)
    """
    # Normalize and apply defaults
    raw = cfg or {}
    norm: Dict[str, Any] = {}
    for k, v in raw.items():
        key = str(k).replace("-", "_")
        if isinstance(v, str) and v.lower() in ("true", "false"):
            v = v.lower() == "true"
        norm[key] = v
    p = PostProcessConfig(**{**PostProcessConfig().__dict__, **norm})

    ts_path = Path(f"{base_filename}.ts").resolve()
    # Prepare directories
    out_dir = Path(p.output_dir).resolve()
    rep_dir = Path(p.reports_dir).resolve()
    thm_dir = Path(p.thumbnails_dir).resolve()
    _ensure_dir(out_dir)
    _ensure_dir(rep_dir)
    _ensure_dir(thm_dir)

    final_path = ts_path
    steps: list[str] = []
    started_at = time.time()

    # 1) Remux
    remuxed = False
    if p.remux_to_mp4 and ts_path.exists():
        mp4_path = out_dir / f"{base_filename}.mp4"
        if _which("ffmpeg"):
            info("Post: Remuxing to MP4 ...")
            remuxed = _remux_ts_to_mp4(ts_path, mp4_path)
            if remuxed:
                final_path = mp4_path
                steps.append("remux_to_mp4")
                try:
                    ts_path.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            warn("ffmpeg not found; skipping remux")

    # 2) Organize output (ensure in output_dir)
    if p.organize_output:
        info("Post: Organizing output ...")
        target = out_dir / final_path.name
        if final_path != target:
            try:
                shutil.move(str(final_path), str(target))
                final_path = target
                steps.append("organize_output")
            except Exception as ex:
                warn(f"Failed to move output: {ex}")
                final_path = target if target.exists() else final_path

    # 3) Thumbnail
    thumb_path = None
    if p.generate_thumbnail and final_path.exists():
        if _which("ffmpeg") and _which("ffprobe"):
            info("Post: Generating thumbnail ...")
            thumb_path = thm_dir / f"{base_filename}.jpg"
            if _thumbnail(final_path, thumb_path):
                steps.append("thumbnail")
        else:
            warn("ffmpeg/ffprobe not found; skipping thumbnail")

    # 4) Report
    elapsed = time.time() - started_at
    summary = {
        "file": str(final_path),
        "source_url": source_url,
        "steps": steps,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": int(time.time()),
    }
    if p.write_report:
        try:
            _ensure_dir(rep_dir)
            report_path = rep_dir / f"{base_filename}.json"
            report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            steps.append("report")
        except Exception as ex:
            warn(f"Failed to write report: {ex}")

    # 6) Open in Explorer
    if p.open_in_explorer and final_path.exists():
        _open_in_explorer(final_path)

    success(f"Post-process complete: {final_path.name}")
    return summary
