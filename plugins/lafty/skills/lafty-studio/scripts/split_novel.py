#!/usr/bin/env python3
"""Cut a long text into pieces a model can read one at a time.

    python split_novel.py 소설.txt 조각/

Cuts at chapter headings when it finds them and at blank lines otherwise, so no piece is over
12,000 characters, and prints each piece with its first line. Reading piece by piece keeps a
long novel from filling the conversation.
"""

import re
import sys
from pathlib import Path

PIECE_CHARS = 12_000
HEADING = re.compile(
    r"^\s*(#{1,3}\s+.+|제?\s*\d+\s*[화장회부권편](\s.*)?|chapter\s+\d+.*|prologue|epilogue"
    r"|프롤로그.*|에필로그.*)\s*$",
    re.I | re.M,
)


def sections(text: str) -> list[str]:
    starts = [found.start() for found in HEADING.finditer(text)]
    if len(starts) < 2:
        return [text]
    bounds = [0, *starts] if starts[0] > 0 else starts
    return [text[a:b] for a, b in zip(bounds, [*bounds[1:], len(text)], strict=True)]


def pieces(text: str) -> list[str]:
    found: list[str] = []
    for section in sections(text):
        current = ""
        for block in re.split(r"(?<=\n)\s*\n", section):
            if current and len(current) + len(block) > PIECE_CHARS:
                found.append(current)
                current = ""
            while len(block) > PIECE_CHARS:
                found.append(block[:PIECE_CHARS])
                block = block[PIECE_CHARS:]
            current += block
        if current.strip():
            found.append(current)
    return found


def main() -> int:
    if len(sys.argv) != 3:
        print("쓰는 법: python split_novel.py 소설.txt 조각/")
        return 2
    text = Path(sys.argv[1]).read_text("utf-8")
    folder = Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    cut = pieces(text)
    print(f"전체 {len(text):,}자, 조각 {len(cut)}개")
    for index, piece in enumerate(cut, 1):
        name = f"{index:03d}.txt"
        (folder / name).write_text(piece, encoding="utf-8")
        head = next((line.strip() for line in piece.splitlines() if line.strip()), "")
        print(f"{name} {len(piece):>6,}자  {head[:40]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
