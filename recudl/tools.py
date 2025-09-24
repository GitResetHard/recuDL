from __future__ import annotations

import json
import sys
import time
import typing as t
from dataclasses import dataclass

# Rich console utilities
from .console import info, warn, error, console

import requests

Abort: bool = False


def check_update(current_tag: str) -> None:
    try:
        url = "https://api.github.com/repos/baconator696/Recu-Download/releases/latest"
        resp = requests.get(url, timeout=2)
        if resp.status_code != 200:
            return
        data = resp.json()
        if data.get("prerelease"):
            return
        new_tag = str(data.get("tag_name", "")).replace("v", "")
        new_nums = new_tag.split(".")
        cur_tag = current_tag.replace("v", "")
        cur_nums = cur_tag.split(".")
        for i, v in enumerate(new_nums):
            try:
                current = int(cur_nums[i])
                new = int(v)
            except Exception:
                continue
            if new > current:
                info(f"New Update Available: v{new_tag}")
                body = str(data.get('body', ''))
                console.print(f"[link={data.get('html_url')}]Release Notes[/link]\n[dim]{body}[/dim]")
                return
    except Exception:
        return


def request(url: str, timeout: int, header: dict[str, str] | None, body: bytes | None, method: str) -> tuple[bytes, int, t.Optional[Exception]]:
    try:
        method = method.upper()
        headers = header or {}
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            r = requests.post(url, headers=headers, data=body or b"", timeout=timeout)
        else:
            r = requests.request(method, url, headers=headers, data=body or b"", timeout=timeout)
        content = r.content
        return content, r.status_code, None
    except Exception as e:
        return b"", 0, e


def argparser(n: int) -> str:
    return sys.argv[n] if len(sys.argv) > n else ""


def search_string(s: str, start: str, end: str) -> tuple[str, t.Optional[Exception]]:
    if len(s) <= len(start) + len(end):
        return "", ValueError("search term longer than the given string")
    i1 = s.find(start)
    i2 = s.find(end, i1 + len(start)) if i1 != -1 else -1
    if i1 == -1 or i2 == -1:
        return "", ValueError(f"could not find {{{start}}} and/or {{{end}}} in {{{s}}}")
    return s[i1 + len(start): i2], None


def shorten_string(s: t.Any, ln: int) -> str:
    if ln < 0:
        ln = 0
    if isinstance(s, str):
        return s[:ln] if len(s) > ln else s
    if isinstance(s, BaseException):
        es = str(s)
        return es[:ln] if len(es) > ln else es
    return f"Type:{type(s)}"


def percent_parse(times: list[t.Any]) -> list[float] | None:
    start = end = 0.0
    secs = [0, 0, 0]
    for i, w in enumerate(times):
        if not isinstance(w, str):
            error(f"timestamps is in wrong format: {times}")
            return None
        parts = w.split(":")
        cons = 1
        for j in range(len(parts) - 1, -1, -1):
            try:
                val = int(parts[j])
            except Exception:
                error(f"timestamps is in wrong format: {times}")
                return None
            secs[i] += val * cons
            cons *= 60
    start = secs[0] / secs[2] * 100 if secs[2] else 0.0
    end = secs[1] / secs[2] * 100 if secs[2] else 100.0
    return [start, end]


@dataclass
class AvgBuffer:
    data: list[float]
    pos: int = 0
    size: int = 25

    def average(self) -> float:
        if not self.data:
            return 0.0
        return sum(self.data) / len(self.data)

    def add(self, add: float) -> None:
        if self.size <= 0:
            self.size = 25
        if self.pos < 0 or self.pos >= self.size:
            self.pos = 0
        while self.pos >= len(self.data):
            self.data.append(add)
        self.data[self.pos] = add
        self.pos += 1


def format_minutes(num: float) -> str:
    unit = "mins"
    if num < 1:
        num *= 60
        unit = "secs"
    elif num > 1440:
        num /= 1440
        unit = "days"
    elif num > 60:
        num /= 60
        unit = "hours"
    else:
        unit = "mins"
    return f"{num:.1f} {unit}"


def format_bytes_per_second(num: float) -> str:
    unit = "B/s"
    if num < 1000:
        unit = "B/s"
    elif num >= 1_000_000:
        num /= 1_000_000
        unit = "MB/s"
    elif num >= 1000:
        num /= 1000
        unit = "KB/s"
    return f"{num:.1f} {unit}"


def formated_header(ref_header: dict[str, str], video_url: str, i: int) -> dict[str, str]:
    header = dict(ref_header or {})
    header["Accept"] = "*/*"
    header["Accept-Language"] = "en-US,en;q=0.9"
    header["Origin"] = "https://recu.me"
    header["Priority"] = "u=1, i"
    header["Sec-Ch-Ua"] = '"Chromium";v="128", "Not;A=Brand";v="24"'
    header["Sec-Ch-Ua-Full-Version-List"] = '"Chromium";v="128.0.6613.120", "Not;A=Brand";v="24.0.0.0"'
    header["Sec-Ch-Ua-Mobile"] = "?0"
    header["Sec-Ch-Ua-Platform"] = '"Windows"'
    header["Sec-Fetch-Dest"] = "empty"
    header["Sec-Fetch-Mode"] = "cors"
    header["Sec-Ch-Ua-Arch"] = '"x86"'
    header["Sec-Ch-Ua-Bitness"] = '"64"'
    header["Sec-Ch-Ua-Full-Version"] = '"128.0.2739.67"'
    header["Sec-Ch-Ua-Model"] = '""'
    header["Sec-Ch-Ua-Platform-Version"] = '"15.0.0"'
    if i == 1:
        header["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        header["Referer"] = "https://recu.me/"
        header["Sec-Fetch-Dest"] = "document"
        header["Sec-Fetch-Mode"] = "navigate"
        header["Sec-Fetch-Site"] = "none"
        header["Sec-Fetch-User"] = "?1"
        header["Upgrade-Insecure-Requests"] = "1"
    elif i == 2:
        header["Referer"] = video_url
        header["Sec-Fetch-Site"] = "same-origin"
        header["X-Requested-With"] = "XMLHttpRequest"
    else:
        header["Sec-Fetch-Site"] = "cross-site"
        header.pop("Cookie", None)
        header.pop("Sec-Ch-Ua-Full-Version-List", None)
        header.pop("Sec-Ch-Ua-Arch", None)
        header.pop("Sec-Ch-Ua-Bitness", None)
        header.pop("Sec-Ch-Ua-Full-Version", None)
        header.pop("Sec-Ch-Ua-Model", None)
        header.pop("Sec-Ch-Ua-Platform-Version", None)
    return header
