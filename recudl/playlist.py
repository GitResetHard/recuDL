from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Playlist:
    json_loc: int
    m3u8: bytes
    lst: List[str]
    filename: str

    @classmethod
    def new(cls, raw_m3u8: bytes, url: str, json_loc: int) -> "Playlist":
        filename = parse_playlist_url(url)
        return cls.new_from_filename(raw_m3u8, filename, json_loc)

    @classmethod
    def new_from_filename(cls, raw_m3u8: bytes, filename: str, json_loc: int) -> "Playlist":
        lines = (raw_m3u8.decode(errors="ignore")).split("\n")
        items: List[str] = []
        for line in lines:
            if len(line) < 2 or line.startswith("#"):
                continue
            items.append(line)
        if len(items) > 0:
            items = items[1:-1]
        return cls(json_loc=json_loc, m3u8=raw_m3u8, lst=items, filename=filename)

    def len(self) -> int:
        return len(self.lst)

    def is_nil(self) -> bool:
        return self.m3u8 is None or len(self.m3u8) == 0

    def playlist_origin(self) -> str:
        if not self.lst:
            raise ValueError("playlist contains no data")
        first = self.lst[0]
        # Extract domain after scheme (e.g., https://domain/...)
        parts = first.split("/")
        if len(parts) < 3:
            raise ValueError("playlist doesn't contain urls")
        # parts: ['https:', '', 'domain', 'path', ...]
        return parts[2]


def parse_playlist_url(url: str) -> str:
    parts = url.split("/")
    if len(parts) < 6:
        raise ValueError("wrong url format")
    username = parts[4]
    date = parts[5].replace(",", "-")
    date_split = date.split("-")
    if len(date_split) < 5:
        raise ValueError("wrong date format")
    if len(date_split[0]) == 4:
        date_split[0] = date_split[0][2:]
    return f"CB_{username}_{date_split[0]}-{date_split[1]}-{date_split[2]}_{date_split[3]}-{date_split[4]}"
