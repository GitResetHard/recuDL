from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from . import tools
from .playlist import Playlist
from . import recu
from . import post_process
from . import state
from .console import console, info, warn, error, success


class Config:
    def __init__(
        self,
        urls: List[Any],
        header: Dict[str, str],
        post_process_cfg: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
        persist_state: bool = False,
    ):
        self.urls: List[Any] = urls
        self.header: Dict[str, str] = header
        self.post_process: Dict[str, Any] = post_process_cfg or {}
        # Remember where to persist configuration
        self._config_path: str = config_path or "config.json"
        # If False, we will not modify config.json (user-owned). State persists only in-memory.
        self.persist_state: bool = persist_state
        self._mtx = threading.Lock()

    # region URL helpers
    def _modify_url(self, idx: int, last_index: Any) -> None:
        url = self.urls[idx]
        if isinstance(url, str):
            self.urls[idx] = [url, last_index]
        elif isinstance(url, list):
            t = list(url)
            if len(t) == 1:
                t.append(last_index)
            elif len(t) == 2:
                t[1] = last_index
            elif len(t) == 4:
                t.append(last_index)
            elif len(t) == 5:
                t[4] = last_index
            self.urls[idx] = t

    def _parse_url(self, url: Any) -> Tuple[str, List[float], int, Optional[Exception], bool]:
        try:
            url_string = ""
            duration: List[float] | None = None
            start_index = 0
            complete = False
            if isinstance(url, str):
                url_string = url
            elif isinstance(url, list):
                if len(url) == 1:
                    url_string = str(url[0])
                elif len(url) == 2:
                    url_string = str(url[0])
                    if isinstance(url[1], str):
                        if url[1] == "COMPLETE":
                            complete = True
                    else:
                        start_index = int(float(url[1]))
                elif len(url) == 4:
                    url_string = str(url[0])
                    duration = tools.percent_parse(url[1:])
                elif len(url) == 5:
                    url_string = str(url[0])
                    duration = tools.percent_parse(url[1:4])
                    if isinstance(url[4], str):
                        if url[4] == "COMPLETE":
                            complete = True
                    else:
                        start_index = int(float(url[4]))
                else:
                    return "", [0, 100], 0, ValueError("incorrect length of url array"), False
            else:
                return "", [0, 100], 0, ValueError("url is incorrect type"), False
            if duration is None:
                duration = [0, 100]
            return url_string, duration, start_index, None, complete
        except Exception as ex:
            return "", [0, 100], 0, ValueError(f"GetVideo: urls are in wrong format, error: {ex}"), False

    # endregion

    def get_playlist(self, url_any: Any, json_loc: int) -> Playlist:
        url, _, _, err, complete = self._parse_url(url_any)
        if err is not None:
            error(f"GetPlaylist: urls are in wrong format, error: {err}")
        if complete:
            return Playlist.new_from_filename(b"", "", json_loc)
        play_list, status, err = recu.parse(url, self.header, json_loc)
        if status == "cloudflare":
            error(f"{getattr(err, 'args', [''])[0]}\nCloudflare Blocked: Failed on url: {url}")
        elif status == "cookie":
            error(f"Please Log in: Failed on url: {url}")
        elif status == "wait":
            warn(f"Daily View Used: Failed on url: {url}")
        elif status == "panic":
            error(f"Error: {err}\nFailed on url: {url}")
        return play_list

    def get_video(self, play_list: Playlist) -> Optional[Exception]:
        url, duration, start_index, err, _ = self._parse_url(self.urls[play_list.json_loc])
        if err is not None:
            error(str(err))
            return err
        last_index, err2 = recu.mux(play_list, tools.formated_header(self.header, "", 0), start_index, duration)
        console.print()
        if err2 is None:
            success(f"Completed: {play_list.filename}:{url}")
            # Post-download pipeline (best-effort)
            try:
                post_process.run(self.post_process, play_list.filename, url)
            except Exception as ex:
                error(f"Post-process failed: {ex}")
            # Record progress externally
            try:
                state.record(url, play_list.filename, status="COMPLETE", last_index=None, json_loc=play_list.json_loc)
            except Exception:
                pass
        else:
            error(str(err2))
            error(f"Download Failed at line: {last_index}")
            try:
                state.record(url, play_list.filename, status="FAILED", last_index=last_index, json_loc=play_list.json_loc)
            except Exception:
                pass
        return err2

    def save(self) -> Optional[Exception]:
        """Save configuration to JSON file."""
        try:
            config_data = {
                "urls": self.urls,
                "header": self.header,
                "post_process": self.post_process
            }
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
            return None
        except Exception as ex:
            return ex

    def empty(self) -> bool:
        return (len(self.urls) < 1 or self.urls[0] == "" or not self.header.get("Cookie") or not self.header.get("User-Agent"))

    def parse_html(self, url: str) -> Optional[Exception]:
        info("Downloading HTML ...")
        resp, code, err = tools.request(url, 10, tools.formated_header(self.header, "", 1), None, "GET")
        if code != 200 or err is not None:
            if err is None:
                err = RuntimeError(f"response: {resp.decode(errors='ignore')}, status code: {code}, cloudflare blocked")
            return err
        info("Searching for links ...")
        url_split = url.split("/")
        name = url_split[4]
        prefix = "/".join(url_split[:3])
        urls = list(self.urls)
        lines = resp.decode(errors="ignore").split("\n")
        for v in lines:
            try:
                code_str, e = tools.search_string(v, f'href="/{name}/video/', '/play"')
                if e is not None:
                    continue
                urls.append(f"{prefix}/{name}/video/{code_str}/play")
            except Exception:
                continue
        self.urls = urls
        return self.save()

    @staticmethod
    def default() -> "Config":
        return Config(
            urls=[""],
            header={"Cookie": "", "User-Agent": ""},
            post_process_cfg={
                "remux_to_mp4": True,
                "generate_thumbnail": True,
                "organize_output": True,
                "open_in_explorer": False,
                "write_report": True,
                "output_dir": "downloads",
                "reports_dir": "reports",
                "thumbnails_dir": "thumbnails",
            },
            config_path="config.json",
            persist_state=False,
        )

    @staticmethod
    def load_from_file(path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config(
            urls=data.get("urls", []),
            header=data.get("header", {}),
            post_process_cfg=data.get("post_process", {}),
            config_path=path,
            persist_state=False,
        )
