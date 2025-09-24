from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from . import tools
from .config import Config
from .playlist import Playlist


def _download_playlist_only(cfg: Config) -> None:
    for i, v in enumerate(cfg.urls):
        pl = cfg.get_playlist(v, i)
        if pl.is_nil():
            continue
        try:
            m3u8_filename = pl.filename + ".m3u8"
            with open(m3u8_filename, "wb") as f:
                f.write(pl.m3u8)
            # Clean up the m3u8 file immediately after writing
            try:
                from pathlib import Path
                m3u8_path = Path(m3u8_filename)
                if m3u8_path.exists():
                    m3u8_path.unlink()
                    print(f"Cleaned up m3u8 file: {m3u8_filename}")
            except Exception as cleanup_ex:
                print(f"Failed to cleanup m3u8 {m3u8_filename}: {cleanup_ex}", file=sys.stderr)
        except Exception as ex:
            print(pl.m3u8.decode(errors="ignore"))
            print(f"Failed to write playlist data: {ex}", file=sys.stderr)
            continue
        print(f"Completed: {pl.filename}:{v}")


def _download_content_from_path(cfg: Config) -> None:
    playlist_path = tools.argparser(3)
    try:
        with open(playlist_path, "rb") as f:
            data = f.read()
    except Exception as ex:
        print(f"Failed to read playlist: {ex}", file=sys.stderr)
        return
    filename = os.path.basename(playlist_path)
    if filename.endswith(".m3u8"):
        filename = filename[:-5]
    pl = Playlist.new_from_filename(data, filename, 0)
    cfg.get_video(pl)


def _parallel_service(cfg: Config, delay_between: float = 1.0) -> None:
    playlists: List[Playlist] = []
    for i, link in enumerate(cfg.urls):
        playlists.append(cfg.get_playlist(link, i))
    with ThreadPoolExecutor(max_workers=min(4, len(playlists) or 1)) as ex:
        futs = []
        for pl in playlists:
            if pl.is_nil():
                continue
            def task(pl=pl):
                err = cfg.get_video(pl)
                if err is None:
                    try:
                        m3u8_filename = pl.filename + ".m3u8"
                        with open(m3u8_filename, "wb") as f:
                            f.write(pl.m3u8)
                        # Clean up the m3u8 file immediately after writing
                        try:
                            from pathlib import Path
                            m3u8_path = Path(m3u8_filename)
                            if m3u8_path.exists():
                                m3u8_path.unlink()
                                print(f"Cleaned up m3u8 file: {m3u8_filename}")
                        except Exception as cleanup_ex:
                            print(f"Failed to cleanup m3u8 {m3u8_filename}: {cleanup_ex}", file=sys.stderr)
                    except Exception as ex:
                        print(pl.m3u8.decode(errors="ignore"))
                        print(f"Failed to write playlist data: {ex}", file=sys.stderr)
                return err
            futs.append(ex.submit(task))
            time.sleep(delay_between)
        for _ in as_completed(futs):
            pass


def _serial_service(cfg: Config) -> None:
    playlists: List[Playlist] = []
    for i, link in enumerate(cfg.urls):
        playlists.append(cfg.get_playlist(link, i))
    for i, pl in enumerate(playlists):
        if pl.is_nil():
            continue
        print(f"{i+1}/{len(playlists)}:")
        if cfg.get_video(pl) is not None:
            continue
        try:
            m3u8_filename = pl.filename + ".m3u8"
            with open(m3u8_filename, "wb") as f:
                f.write(pl.m3u8)
            # Clean up the m3u8 file immediately after writing
            try:
                from pathlib import Path
                m3u8_path = Path(m3u8_filename)
                if m3u8_path.exists():
                    m3u8_path.unlink()
                    print(f"Cleaned up m3u8 file: {m3u8_filename}")
            except Exception as cleanup_ex:
                print(f"Failed to cleanup m3u8 {m3u8_filename}: {cleanup_ex}", file=sys.stderr)
        except Exception as ex:
            print(pl.m3u8.decode(errors="ignore"))
            print(f"Failed to write playlist data: {ex}", file=sys.stderr)


def _hybrid_service(cfg: Config) -> None:
    # group playlists by origin domain
    playlists: List[Playlist] = []
    for i, link in enumerate(cfg.urls):
        playlists.append(cfg.get_playlist(link, i))
    servers: dict[str, List[Playlist]] = {}
    for pl in playlists:
        try:
            domain = pl.playlist_origin()
        except Exception as ex:
            print(ex, file=sys.stderr)
            continue
        servers.setdefault(domain, []).append(pl)
    with ThreadPoolExecutor(max_workers=len(servers) or 1) as ex:
        futs = []
        for domain, pls in servers.items():
            def worker(pls=pls):
                for pl in pls:
                    if pl.is_nil():
                        continue
                    if cfg.get_video(pl) is None:
                        try:
                            m3u8_filename = pl.filename + ".m3u8"
                            with open(m3u8_filename, "wb") as f:
                                f.write(pl.m3u8)
                            # Clean up the m3u8 file immediately after writing
                            try:
                                from pathlib import Path
                                m3u8_path = Path(m3u8_filename)
                                if m3u8_path.exists():
                                    m3u8_path.unlink()
                                    print(f"Cleaned up m3u8 file: {m3u8_filename}")
                            except Exception as cleanup_ex:
                                print(f"Failed to cleanup m3u8 {m3u8_filename}: {cleanup_ex}", file=sys.stderr)
                        except Exception as ex:
                            print(pl.m3u8.decode(errors="ignore"))
                            print(f"Failed to write playlist data: {ex}", file=sys.stderr)
            futs.append(ex.submit(worker))
        for _ in as_completed(futs):
            pass


def _readme(exe_name: str) -> str:
    string1 = (
        "Recurbate:\n"
        "If ran for the first time, json configuration will be generated\n"
        "\tin the working directory\n"
        "Fill in the json's URL, Cookie and User-Agent to allow the\n"
        "\tprogram to run\n\n"
        "Usage: "
    )
    string2 = (
        " <json location> playlist|series|hybrid <playlist.m3u8>\n"
        " --web-ui [host] [port]  Start web interface (default: 127.0.0.1:8080)\n\n"
        "if \"playlist\" is used, only the .m3u8 playlist file will be\n"
        "\tdownloaded, specifiying the playlist location will\n"
        "\tdownload the contents of the playlist\n"
        "if \"series\" is used, the program will download all the videos\n"
        "\tin series\n"
        "if \"hybrid is used, the program will download sequentially from\n"
        "\teach server but in parallel from different servers\n\n"
        "Web UI: Access the web interface at http://localhost:8080 for\n"
        "\tremote management, configuration editing, and download monitoring"
    )
    return string1 + exe_name + string2


def main() -> None:
    tag = ""
    print(f"Recu {tag}")
    tools.check_update(tag)
    if tools.argparser(1) == "--help":
        path = tools.argparser(0)
        name = os.path.basename(path)
        print(_readme(name))
        return
    if tools.argparser(1) == "--web-ui":
        from .web_server import start_web_server
        host = tools.argparser(2) or "127.0.0.1"
        port = int(tools.argparser(3) or "8080")
        start_web_server("config.json", host, port, debug=False)
        return
    json_location = "config.json"
    if tools.argparser(1):
        json_location = tools.argparser(1)
    if not os.path.exists(json_location):
        default = Config.default()
        # Save default
        default.save()
        print(f"{json_location} created in working directory\nPlease fill in the {json_location} with the \n\tURLs to Download\n\tCookies\n\tUser-Agent")
        return
    try:
        with open(json_location, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = Config(urls=data.get("urls", []), header=data.get("header", {}))
    except Exception as ex:
        print(ex)
        sys.exit(4)
    if cfg.empty():
        print("please modify config.json")
        if tools.argparser(2) != "parse":
            return
    cmd = tools.argparser(2)
    if cmd == "playlist":
        if tools.argparser(3):
            if not os.path.exists(tools.argparser(3)):
                print(f"{tools.argparser(3)} not found", file=sys.stderr)
                sys.exit(4)
            _download_content_from_path(cfg)
        else:
            _download_playlist_only(cfg)
    elif cmd == "series":
        _serial_service(cfg)
    elif cmd == "hybrid":
        _hybrid_service(cfg)
    elif cmd == "parse":
        err = cfg.parse_html(tools.argparser(3))
        if err is not None:
            print(err)
        else:
            print("Parsed HTML Successfully")
    else:
        _parallel_service(cfg)


if __name__ == "__main__":
    main()
