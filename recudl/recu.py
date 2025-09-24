from __future__ import annotations

import os
import sys
import time
from typing import Tuple, Optional

from . import tools
from .playlist import Playlist
from .console import console, info, warn, error, success, make_progress


def _download_loop(url: str, timeout: int, header: dict[str, str], max_retries: int = 5) -> Tuple[bytes, Optional[Exception]]:
    retry = 0
    while True:
        data, status, err = tools.request(url, timeout, header, None, "GET")
        if err is None and status == 200:
            return data, None
        console.print("[warn]Failed, retrying...[/warn]", end="\r")
        if retry > max_retries:
            if err is None:
                err = RuntimeError(f"{data.decode(errors='ignore')}, status code: {status}")
            return b"", err
        retry += 1
        timeout += 30
        time.sleep(0.2)


def parse(site_url: str, header: dict[str, str], json_loc: int) -> Tuple[Playlist, str, Optional[Exception]]:
    # getting webpage
    info("📥 Downloading HTML ...")
    htmldata, err = _download_loop(site_url, 10, tools.formated_header(header, "", 1))
    if err is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "cloudflare", err
    html = htmldata.decode(errors="ignore")
    success("✅ Downloading HTML: Complete")
    # determine unique page token
    token, e = tools.search_string(html, 'data-token="', '"')
    if e is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", e
    # determine video token
    start = html.find(token)
    id_, e = tools.search_string(html[start:], 'data-video-id="', '"')
    if e is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", e
    # parse api url
    api_url = "/".join(site_url.split("/")[:3]) + "/api/video/" + id_ + "?token=" + token
    # request api
    info("🔗 Getting link to playlist ...")
    apidata, err = _download_loop(api_url, 10, tools.formated_header(header, api_url, 2))
    if err is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", err
    api = apidata.decode(errors="ignore")
    success("✅ Getting link to playlist: Complete")
    # continue based on response from api
    if api == "shall_subscribe":
        return Playlist.new_from_filename(b"", "", json_loc), "wait", None
    if api == "shall_signin":
        return Playlist.new_from_filename(b"", "", json_loc), "cookie", None
    if api == "wrong_token":
        return Playlist.new_from_filename(b"", "", json_loc), "panic", RuntimeError("wrong token")
    # search for m3u8 link from api response
    playlist_url, e = tools.search_string(api, '<source src="', '"')
    if e is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", e
    playlist_url = playlist_url.replace("amp;", "")
    info("📥 Downloading playlists ...")
    # get m3u8 playlist
    playlist_data, err = _download_loop(playlist_url, 10, tools.formated_header(header, "", 0))
    if err is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", err
    playlist_ref = playlist_data.decode(errors="ignore")
    playlist_lines = playlist_ref.split("\n")
    success("✅ Downloading playlists: Complete")
    # determine url prefix for playlist entries
    prefix = playlist_url[: playlist_url.rfind("/") + 1]
    # if playlist contains resolution selection
    if "EXT-X-STREAM-INF" in playlist_ref:
        for i in range(0, len(playlist_lines) - 1):
            if "NAME=max" in playlist_lines[i]:
                playlist_url2 = playlist_lines[i + 1]
                if prefix not in playlist_url2:
                    playlist_url2 = prefix + playlist_url2
                playlist_url = playlist_url2
        info("📥 Downloading playlist ...")
        playlist_data, err = _download_loop(playlist_url, 10, tools.formated_header(header, "", 0))
        if err is not None:
            return Playlist.new_from_filename(b"", "", json_loc), "panic", err
        playlist_lines = playlist_data.decode(errors="ignore").split("\n")
        success("✅ Downloading playlist: Complete")
    # add prefix to playlist
    for i, line in enumerate(playlist_lines):
        if len(line) < 2 or line.startswith("#"):
            continue
        if prefix not in line:
            playlist_lines[i] = prefix + line
    pl_data = "\n".join(playlist_lines).encode()
    pl, perr = None, None
    try:
        pl = Playlist.new(pl_data, playlist_url, json_loc)
    except Exception as ex:
        perr = ex
    if perr is not None:
        return Playlist.new_from_filename(b"", "", json_loc), "panic", perr
    return pl, "", None


def mux(play_list: Playlist, header: dict[str, str], start_index: int, duration_percent: list[float]) -> tuple[int, Optional[Exception]]:
    file = None
    avgdur = tools.AvgBuffer(data=[])
    avgsize = tools.AvgBuffer(data=[])
    if start_index < 0:
        start_index = 0
    if tools.Abort:
        return start_index, RuntimeError("aborting")
    if duration_percent[0] > 100 or duration_percent[1] <= duration_percent[0]:
        return start_index, RuntimeError("duration format error")
    if duration_percent[0] < 0:
        duration_percent[0] = 0
    if duration_percent[1] > 100:
        duration_percent[1] = 100
    # continuation
    try:
        if start_index != 0:
            file = open(play_list.filename + ".ts", "ab")
    except Exception as ex:
        console.print(f"[warn]original file not found, creating new one: {ex}[/warn]", style="bold yellow")
        file = None
    # create file
    if file is None:
        # collision check
        if os.path.exists(play_list.filename + ".ts"):
            i = 1
            while True:
                new = f"{play_list.filename}({i})"
                if not os.path.exists(new + ".ts"):
                    play_list.filename = new
                    break
                i += 1
        try:
            file = open(play_list.filename + ".ts", "ab")
        except Exception as ex:
            return start_index, RuntimeError(f"can not create file: {ex}")
    assert file is not None
    try:
        # mux loop
        if start_index == 0:
            start_index = int(float(play_list.len()) * duration_percent[0] / 100)
        end_index = int(float(play_list.len()) * duration_percent[1] / 100)
        total_segments = max(0, end_index - start_index)
        if total_segments == 0:
            return start_index, RuntimeError("no segments to download")
        with make_progress(transient=True) as progress:
            task_id = progress.add_task(f"Downloading {play_list.filename}.ts", total=total_segments)
            for idx, ts_link in enumerate(play_list.lst[start_index:end_index]):
                i = idx + start_index
                if tools.Abort:
                    return i, RuntimeError("aborting")
                start_time = time.time()
                chunk, err = _download_loop_ts(ts_link, header, 10, 5)
                if err is not None or chunk is None:
                    per = (i / float(play_list.len())) * 100 if play_list.len() else 0
                    return i, RuntimeError(f"error: {str(err)}\nFailed at {per:.2f}%")
                try:
                    file.write(chunk)
                except Exception as ex:
                    return i, RuntimeError(f"can not write file: {ex}")
                # UI stats (update progress each chunk)
                end_dur = (time.time() - start_time) / 60.0
                avgsize.add(float(len(chunk)))
                avgdur.add(end_dur)
                getavgdur = avgdur.average()
                speed_secs = avgsize.average() / (getavgdur * 60) if getavgdur else 0.0
                # Optionally show speed in task description
                progress.update(
                    task_id,
                    advance=1,
                    description=f"Downloading {play_list.filename}.ts [{tools.format_bytes_per_second(speed_secs)}]",
                )
        return 0, None
    finally:
        file.close()

def _download_loop_ts(url: str, header: dict[str, str], timeout: int, max_retry: int) -> tuple[Optional[bytes], Optional[Exception]]:
    # Helper adapted to mirror Go's downloadLoop signature/behavior
    retry = 0
    while True:
        data, status, err = tools.request(url, timeout, header, None, "GET")
        if err is None and status == 200:
            return data, None
        if status == 429:
            time.sleep(0.1)
            continue
        if status == 410:
            error("Download Expired")
            retry = max_retry
        retry += 1
        if err is None:
            err = RuntimeError(f"status Code: {status}, {data.decode(errors='ignore')} ")
        else:
            timeout += 30
        if retry > max_retry:
            return None, err
        short = tools.shorten_string(err, 40)
        error(f"Error: {short}, Retrying...")
        time.sleep(1)
