#!/usr/bin/env python3
"""Count the Korean signals of machine prose in a chapter, as places to go and read.

    python signals.py 본문/1화.md [본문/2화.md ...]

The signals point at text to judge in context; a hit is not a fault, and no hits is not a pass.
Standard library only.
"""

import re
import sys
from pathlib import Path

# name, pattern, hits per 1,000 characters from which the kind is worth a look (0: always).
SIGNALS: list[tuple[str, re.Pattern, float]] = [
    (
        "부정 후 뒤집기",
        re.compile(
            r"[가-힣]+(이|가) 아니라 [^.\n]{1,30}(였다|이었다|였어|이다)|단순한 [^.\n]{1,16}아니었다"
        ),
        0,
    ),
    ("부정 나열", re.compile(r"[가-힣]+도,? ?[가-힣]+도 없었다|오직 [^.\n]{1,16}뿐"), 0),
    (
        "음량 반전",
        re.compile(
            r"(낮|작|크지 않|조용하)[^.\n]{0,8}지만[^.\n]{0,16}(거역|단호|선명|또렷|묵직|분명)"
        ),
        0,
    ),
    (
        "예고와 총결",
        re.compile(
            r"(알지 못했다|이제 막 시작|운명의 톱니|아무도 잠들지 못|되돌릴 수 없|"
            r"새로운 페이지|인생이란|전에 없던)"
        ),
        0,
    ),
    ("대시", re.compile(r"—|――"), 0),
    (
        "상투 신체 반응",
        re.compile(
            r"입꼬리가|눈동자가 (흔들|떨)|숨을 (삼|죽)|손끝이|입술을 (깨물|달싹)|눈시울|"
            r"목울대|가슴이 (쿵|철렁|내려앉)|심장이 (쿵|철렁|내려앉)"
        ),
        1.5,
    ),
    (
        "미세 동작",
        re.compile(r"(잠깐|잠시|살짝|가볍게|한 번) (멈칫|웃|끄덕|고개를|눈을|어깨를)"),
        2.0,
    ),
    ("비유와 추측", re.compile(r"마치 |듯했다|듯한|것 같았다|처럼 "), 6.0),
    (
        "상투어",
        re.compile(r"한 줄기|희미하게|천천히|깊게 숨|깊은 숨|스쳤다|스치고|차가운 기운|묘한"),
        3.0,
    ),
    (
        "서술자의 결론",
        re.compile(r"깨달았다|이는 곧|다시 말해|누가 봐도|아우라|라는 뜻이었다|라는 걸 알았다"),
        0.5,
    ),
    (
        "속마음 풀이",
        re.compile(
            r"(어색했는지|알아챈 듯|실수였다는 듯|라기보다|에 가깝다|듯이 말했다|듯 웃었다)"
        ),
        0.5,
    ),
    ("군중 반응", re.compile(r"모두가 (경악|놀라|숨을)|귀를 의심|일제히"), 0),
    ("공정 용어", re.compile(r"복선|세부개요|독자|이번 화|다음 화|본 화|플롯"), 0),
]
SENTENCE = re.compile(r"[^.!?…\n]+[.!?…]+")


def stutters(text: str) -> list[str]:
    """Three or more very short sentences in a row, outside dialogue."""
    found = []
    for line in text.splitlines():
        if line.lstrip().startswith(('"', "“", "[", "「")):
            continue
        sentences = [item.strip() for item in SENTENCE.findall(line)]
        for index in range(len(sentences) - 2):
            trio = sentences[index : index + 3]
            if all(len(item) <= 8 for item in trio):
                found.append(" ".join(trio))
                break
    return found


def opens_with_weather(text: str) -> str | None:
    first = next(
        (line.strip() for line in text.splitlines() if line.strip() and line[0] != "#"), ""
    )
    if re.match(r"(햇살|햇빛|먹구름|빗방울|비가|바람이|창밖|아침 햇|노을|달빛)", first):
        return first[:40]
    return None


def report(path: Path) -> None:
    text = path.read_text("utf-8")
    chars = len(re.sub(r"\s", "", text)) or 1
    print(f"\n{path} (공백 포함 {len(text):,}자, 공백 제외 {chars:,}자)")
    weather = opens_with_weather(text)
    if weather:
        print(f"  날씨로 시작: {weather}")
    short = stutters(text)
    if short:
        print(f"  끊긴 문장 연타 {len(short)}곳: {short[0][:40]}")
    for name, pattern, limit in SIGNALS:
        hits = list(pattern.finditer(text))
        if not hits:
            continue
        rate = len(hits) / chars * 1000
        if rate < limit:
            continue
        shown = [text[max(0, hit.start() - 10) : hit.end() + 10].replace("\n", " ") for hit in hits]
        print(f"  {name} {len(hits)}건 ({rate:.1f}/1000자)")
        for sample in shown[:3]:
            print(f"    …{sample}…")
    print("  신호는 읽어 볼 곳입니다. 0건이 합격은 아닙니다.")


def main() -> int:
    if len(sys.argv) < 2:
        print("쓰는 법: python signals.py 본문/1화.md")
        return 2
    for name in sys.argv[1:]:
        report(Path(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
