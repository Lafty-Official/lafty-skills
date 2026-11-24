#!/usr/bin/env python3
"""Check a lafty-work file the way the studio will, without anything but Python.

    python check.py 작품.lafty.json

Reads the schemas beside this skill (assets/). Runs anywhere the skill runs, so it uses the
standard library only; the studio's own check stays the final word. Prints one line per
problem, in Korean, with where it is. Exits 1 when an error remains, 0 otherwise; warnings do
not fail.
"""

import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
FORMAT = "lafty-work/v1"
# Other services' placeholders for the user; the guide's chapter 9 allows only ours.
FOREIGN = re.compile(r"\{\{user\}\}|\{\{char\}\}|\{player\}|<user>|<char>", re.I)
STARTS_AND_ENDS = re.compile(r"\S고, .*(끝난다|끝나고|정리된다|마무리된다|가라앉는다)")
GAUGE_WORDS = ("호감", "애정", "관계")
PLAYER_WIDGET = re.compile(r"^p\d+$")
# A clock time the app can read: 09:00 or 09:00:00, and never 24:00 or 99:99.
TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?")
SPEAKER = re.compile(r"^\[([^:\]]+):([^\]]+)\]", re.M)
# The app's faces for a supporting role that names none.
NPC_FACES = ["기본"]
# A section of the file only; the studio keeps it as two fields of the work's page.
DERIVATIVE = {
    "type": "object",
    "properties": {"is": {"type": "boolean"}, "source": {"type": "string"}},
    "additionalProperties": False,
}
WEEKDAYS = "월화수목금토일"
# Each step takes 2~4 turns in play. Works with 25~41 steps on the way sat in chapter 2 after
# 45 turns; a hand-made one with 17 had just reached its last chapter. Hand-made works: 17~21.
STEPS_IN_A_STORY = 22
STEPS_IN_AN_EVENT = 3
# Picture tags (references/picture-tags.md): each spot and the ratio the app shows it at.
SPOTS = {
    "profile": ("프로필", "1:1"),
    "portrait": ("초상", "3:4"),
    "background": ("배경", "16:9"),
    "cg": ("CG", "16:9"),
    "cover": ("표지", "3:4"),
}
LOOK_TAGS = (6, 16)
ADULT_LOOK = ("mature female", "mature male", "old woman", "old man")
# No place takes a photographic picture (guide 8-3).
REAL_TAGS = {"photorealistic", "realistic", "photo (medium)", "real life", "3d"}
# The skill writes tags anyone may see; a 19 picture is the author's own, in the photo tab.
NOT_FOR_ALL = {
    "nsfw",
    "explicit",
    "uncensored",
    "nude",
    "naked",
    "completely nude",
    "topless",
    "bottomless",
    "nipples",
    "areolae",
    "pussy",
    "penis",
    "testicles",
    "anus",
    "pubic hair",
    "sex",
    "cum",
    "after sex",
}
AGE = re.compile(r"\d+\s*(?:years? old|yo)\b|\b(?:aged?|age)\s*\d+", re.I)
HANGUL = re.compile(r"[ㄱ-ㆎ가-힣一-鿿]")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}" if where else message)

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}" if where else message)


def here(path: str, key: object) -> str:
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}.{key}" if path else str(key)


def resolve(node: dict, root: dict) -> dict:
    while "$ref" in node:
        target: object = root
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]  # type: ignore[index]
        node = target  # type: ignore[assignment]
    return node


def is_type(value: object, kind: str) -> bool:
    if kind == "null":
        return value is None
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "array":
        return isinstance(value, list)
    return isinstance(value, dict)


def is_datetime(text: str) -> bool:
    try:
        return datetime.fromisoformat(text).tzinfo is None
    except ValueError:
        return False


def problems(value: object, node: dict, root: dict, path: str) -> list[tuple[str, str]]:
    """What is wrong with `value` by the schema; empty when it fits."""
    node = resolve(node, root)
    if "anyOf" in node:
        options = [problems(value, option, root, path) for option in node["anyOf"]]
        return min(options, key=len) if all(options) else []
    found: list[tuple[str, str]] = []
    kind = node.get("type")
    if isinstance(kind, str) and not is_type(value, kind):
        names = {
            "string": "글을 넣으세요",
            "integer": "숫자를 넣으세요",
            "array": "목록이어야 해요",
            "object": "묶음이어야 해요",
            "boolean": "참이나 거짓이어야 해요",
        }
        return [(path, names.get(kind, f"{kind} 값이어야 해요"))]
    if "const" in node and value != node["const"]:
        found.append((path, f"{node['const']}이어야 해요"))
    if "enum" in node and value not in node["enum"]:
        found.append((path, f"고를 수 있는 값이 아니에요: {', '.join(map(str, node['enum']))}"))
    if isinstance(value, str):
        low, high = node.get("minLength"), node.get("maxLength")
        if low is not None and len(value) < low:
            found.append((path, "비어 있어요" if low == 1 else f"{low}자 이상 써야 해요"))
        if high is not None and len(value) > high:
            found.append((path, f"{high}자 이하로 줄이세요(지금 {len(value)}자)"))
        if "pattern" in node and not re.search(node["pattern"], value):
            found.append((path, "쓸 수 없는 글자가 있어요(대괄호, 콜론, 줄바꿈, 한글 ID 등)"))
        if node.get("format") == "time" and not TIME.fullmatch(value):
            found.append((path, "시각은 09:00 형식이에요"))
        if node.get("format") == "date-time" and not is_datetime(value):
            found.append((path, "시각은 2026-12-18T19:20:00 형식이에요(시간대 없이)"))
    if is_type(value, "number"):
        if "minimum" in node and value < node["minimum"]:
            found.append((path, f"{node['minimum']} 이상이어야 해요"))
        if "maximum" in node and value > node["maximum"]:
            found.append((path, f"{node['maximum']} 이하여야 해요"))
    if isinstance(value, list):
        low, high = node.get("minItems"), node.get("maxItems")
        if low is not None and len(value) < low:
            found.append((path, f"{low}개 이상 있어야 해요"))
        if high is not None and len(value) > high:
            found.append((path, f"{high}개까지만 넣을 수 있어요(지금 {len(value)}개)"))
        if "items" in node:
            for index, item in enumerate(value):
                found += problems(item, node["items"], root, here(path, index))
    if isinstance(value, dict):
        properties = node.get("properties", {})
        for name in node.get("required", []):
            if name not in value:
                found.append((here(path, name), "빠졌어요"))
        rest = node.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                found += problems(item, properties[name], root, here(path, name))
            elif rest is False:
                found.append((here(path, name), "규격에 없는 항목이에요"))
            elif isinstance(rest, dict):
                found += problems(item, rest, root, here(path, name))
        if "maxProperties" in node and len(value) > node["maxProperties"]:
            found.append((path, f"{node['maxProperties']}개까지만 넣을 수 있어요"))
    return found


def fits(report: Report, document: object, schema: dict, path: str) -> bool:
    found = problems(document, schema, schema, path)
    for where, message in found:
        report.error(where, message)
    return not found


def schema_of(assets: Path, name: str) -> dict:
    return json.loads((assets / name).read_text("utf-8"))


def faces_of(npc: dict) -> list[str]:
    return npc.get("expressions", NPC_FACES)


def unique(report: Report, path: str, label: str, ids: list) -> None:
    repeated = sorted({item for item in ids if ids.count(item) > 1})
    if repeated:
        report.error(path, f"같은 {label}이 두 번 있어요: {', '.join(map(str, repeated))}")


def minutes(text: str) -> int:
    hours, rest = text.split(":")[:2]
    return int(hours) * 60 + int(rest)


def covers(slot: dict, day: int, minute: int) -> bool:
    if slot.get("days") and day not in slot["days"]:
        return False
    start, end = minutes(slot["start"]), minutes(slot["end"])
    if start <= end:
        return start <= minute < end
    return minute >= start or minute < end


def check_routine(report: Report, routine: list[dict]) -> None:
    """The first slot that covers a moment wins, like the app's messenger status."""
    winners: set[int] = set()
    gaps: list[str] = []
    for day in range(7):
        open_from: int | None = None
        for minute in range(24 * 60 + 1):
            winner = next(
                (
                    i
                    for i, slot in enumerate(routine)
                    if minute < 1440 and covers(slot, day, minute)
                ),
                None,
            )
            if winner is not None:
                winners.add(winner)
            if winner is None and open_from is None and minute < 1440:
                open_from = minute
            elif (winner is not None or minute == 1440) and open_from is not None:
                gaps.append(f"{WEEKDAYS[day]} {open_from // 60:02}:{open_from % 60:02}부터")
                open_from = None
    if gaps:
        shown = ", ".join(gaps[:4]) + (" 등" if len(gaps) > 4 else "")
        report.warn("character.routine", f"일과가 비는 시간: {shown}")
    hidden = [str(i + 1) for i in range(len(routine)) if i not in winners]
    if hidden:
        report.warn(
            "character.routine",
            f"{', '.join(hidden)}번째 항목은 앞 항목에 가려 쓰이지 않아요. 짧은 항목을 위로 올리세요",
        )


def card_chars(card: dict) -> int:
    """How long the card is as the actor reads it in a DM, the length the studio counts."""
    name = card["identity"]["name"]
    age = f"{card['identity']['age']}살. " if card["identity"].get("age") else ""

    def bullets(items) -> str:
        return "\n".join(f"- {item}" for item in items)

    def example(item: dict) -> str:
        lines = [f"상황: {item['situation']}"]
        for line in item["lines"]:
            speaker = "상대" if line["speaker"] == "user" else name
            lines.append(f"{speaker}: {line['text']}")
        return "\n".join(lines)

    def routine(slot: dict) -> str:
        days = "".join(WEEKDAYS[day] for day in slot.get("days") or []) or "매일"
        return f"{days} {slot['start'][:5]}~{slot['end'][:5]}: {slot['doing']}"

    looks = f"\n\n외모: {card['appearance']}" if card.get("appearance") else ""
    drives, voice, canon = card["drives"], card["voice"], card["canon_policy"]
    sections = [
        f"# {name}\n{card['premise']}\n{age}{card['identity']['role']}. "
        f"{card['identity']['world']}.\n\n{card['background']}{looks}",
        "## 가치와 갈등\n"
        + bullets(f"{item['value']}: {item['behavior']}" for item in card["values"])
        + "\n"
        + bullets(card["value_conflicts"]),
        f"## 원하는 것과 두려운 것\n- 원하는 것: {drives['want']}\n"
        f"- 두려운 것: {drives['fear']}\n- 요즘 마음에 걸리는 것: {drives['current_concern']}",
        "## 행동으로 드러나는 결점\n" + bullets(card["flaws_in_behavior"]),
        "## 의견\n" + bullets(card["opinions"]),
        f"## 말투\n- 기본: {voice['speech_level']}\n- 리듬: {voice['rhythm']}\n"
        f"- 버릇: {', '.join(voice['habits'])}\n- 유머: {voice['humor']}\n"
        f"- 피하는 것: {', '.join(voice['avoid'])}",
        "## 정해진 사실\n" + bullets(card["facts"]),
        "## 하루\n" + bullets(routine(slot) for slot in card["routine"]),
        "## 아는 사람과 장소\n"
        + bullets(f"{entry['topic']}: {entry['content']}" for entry in card["lore"]),
        "## 관계가 깊어지는 단계\n"
        + bullets(f"{item['stage']}: {item['behavior']}" for item in card["relationship_stages"]),
        "## 지어내도 되는 것과 안 되는 것\n"
        f"- 바뀌지 않는 정본: {', '.join(canon['fixed'])}\n"
        f"- 지어내도 되지만 한 번 말하면 지키는 것: {', '.join(canon['improvisable'])}\n"
        f"- 대화에 있어야만 사실인 것: {', '.join(canon['evidence_required'])}",
        "## 목소리 예시 (실제로 있었던 일이 아니며 문장을 그대로 쓰지 않는다)\n"
        + "\n\n".join(example(item) for item in card["examples"]),
    ]
    return len("\n\n".join(sections))


def check_card(report: Report, card: dict, sizes: dict) -> None:
    if card["greeting"].rstrip().endswith("?"):
        report.error("character.greeting", "첫 인사는 물음표로 끝나면 안 돼요")
    if not card["relationship_stages"]:
        report.error("character.relationship_stages", "관계 단계를 하나 이상 넣으세요")
    stages = {item["stage"] for item in card["relationship_stages"]}
    openings = card.get("openings") or []
    unique(report, "character.openings", "만남 ID", [item["opening_id"] for item in openings])
    for index, opening in enumerate(openings):
        where = f"character.openings[{index}]"
        if opening["start_stage"] not in stages:
            report.error(f"{where}.start_stage", "관계 단계 목록에 있는 이름을 쓰세요")
        if (opening.get("greeting") or "").rstrip().endswith("?"):
            report.error(f"{where}.greeting", "첫 메시지는 물음표로 끝나면 안 돼요")
    check_routine(report, card["routine"])
    chars, (low, high) = card_chars(card), sizes["suggested"]
    if chars > sizes["chars"]:
        report.error(
            "character",
            f"카드가 너무 길어요(AI가 읽는 글 {chars:,}자). {sizes['chars']:,}자까지 쓸 수 있어요. "
            "작품마다 달라지는 설정은 작품의 '이 이야기에서의 역할'과 무대, 이벤트로 옮기세요",
        )
    elif chars > high:
        report.warn(
            "character",
            f"카드가 길어요(AI가 읽는 글 {chars:,}자). {high:,}자 이하를 권해요. "
            "작품마다 달라지는 설정은 작품 쪽에 쓰세요",
        )
    if chars < low:
        report.warn(
            "character", f"카드가 짧아요(AI가 읽는 글 {chars:,}자). {low:,}자 이상을 권해요"
        )


def check_world(report: Report, story: dict, suggested: int) -> None:
    if len(story["world"]) > suggested:
        report.warn(
            "story.world",
            f"무대가 길어요({len(story['world']):,}자). 답장마다 읽히는 글이라 {suggested:,}자 "
            "이하를 권해요. 이야기 중에 드러날 것은 이벤트 설정이나 엑스트라의 비밀에 쓰세요",
        )


def check_lessons(report: Report, story: dict, card: dict | None) -> None:
    """Warnings the studio does not give: what went wrong in the three test plays."""
    events = {item["event_id"]: item for item in story["events"]}
    chapters = story["chapters"]
    last = chapters[-1]
    if not any(events.get(item, {}).get("ending") for item in last["ends_with"]):
        report.warn("story.chapters", "마지막 챕터를 끝내는 이벤트에 엔딩이 없어요")
    for chapter in chapters:
        for event_id in chapter["ends_with"]:
            event = events.get(event_id)
            if event and event.get("trigger") == "player":
                report.warn(
                    f"story.events[{event_id}].trigger",
                    "챕터를 끝내는 이벤트가 사용자의 말로만 열립니다. 꺼내지 않으면 챕터가 멈춥니다",
                )
    for event in story["events"]:
        requires = event.get("requires") or {}
        if event.get("kind") == "side" and not any(requires.values()):
            report.warn(
                f"story.events[{event['event_id']}].requires",
                "조건 없는 서브 이벤트는 챕터가 열리자마자 나올 수 있어요. 앞 장면을 조건으로 거세요",
            )
    ending_steps = [len(item["milestones"]) for item in story["events"] if item.get("ending")]
    steps = sum(len(item["milestones"]) for item in story["events"] if not item.get("ending"))
    steps += max(ending_steps, default=0)
    if steps > STEPS_IN_A_STORY:
        report.warn(
            "story.events",
            f"한 번 놀 때 지나는 꼭 일어나는 일이 {steps}개예요. {STEPS_IN_A_STORY}개 이하로 합치세요. "
            "많으면 놀아도 이야기가 끝나지 않아요. 세세한 동작은 guide로 옮기세요",
        )
    for event in story["events"]:
        if len(event["milestones"]) > STEPS_IN_AN_EVENT:
            report.warn(
                f"story.events[{event['event_id']}].milestones",
                f"한 장면의 꼭 일어나는 일은 {STEPS_IN_AN_EVENT}개까지 권해요",
            )
    stages = story["relationship"]["stages"]
    if len(stages) >= 3 and not any(item.get("stage_floor") for item in chapters):
        report.warn(
            "story.chapters",
            "챕터 최소 관계 단계가 없어요. 이야기가 짧으면 관계가 첫 단계에 머뭅니다",
        )
    if not (story["start"].get("situation") or "").strip():
        report.warn(
            "story.start.situation",
            "두 사람이 아는 것과 모르는 것을 쓰세요. 비우면 없던 과거를 지어냅니다",
        )
    names = {story["lead"]["character_id"]: story["lead"]["expressions"]}
    if card is not None:
        names = {card["identity"]["name"]: story["lead"]["expressions"]}
    names.update({item["name"]: faces_of(item) for item in story.get("npcs") or []})
    opening = story["start"].get("first_message") or ""
    for name, expression in SPEAKER.findall(opening):
        if name in names and expression not in names[name]:
            report.warn(
                "story.start.first_message",
                f"[{name}:{expression}]: 그 인물의 표정 목록에 없는 이름이에요",
            )
    if "*" in opening:
        report.warn("story.start.first_message", "별표로 서술을 감싸지 않아요")


def check_adults(report: Report, bundle: dict, card: dict, adult_age: int, main_age: int) -> None:
    """A 19 work's main states a plain age of `main_age` or more (the studio refuses otherwise).
    Anyone a romance reaches is an adult at any rating, `adult_age` or more."""
    age = str(card["identity"].get("age") or "").strip()
    info = bundle.get("info")
    rating = info.get("rating") if isinstance(info, dict) else None
    if age and not age.isdecimal():
        report.warn("character.identity.age", "나이는 숫자만 써요")
    years = int(age) if age.isdecimal() else None
    if rating == "19" and (years is None or years < main_age):
        report.error(
            "character.identity.age", f"19 작품의 메인은 숫자 나이 {main_age}세 이상이어야 해요"
        )
    romance = any(item.get("mutual") for item in card["relationship_stages"])
    if romance and (years is None or years < adult_age):
        report.warn(
            "character.identity.age",
            f"연애로 이어지는 단계가 있어요. 성인({adult_age}세 이상)으로 두고 나이를 숫자로 쓰세요",
        )


def about_known(about: str, npcs: set[str]) -> bool:
    return about in {"lead", "player", "scene", *npcs}


def check_story(report: Report, story: dict, card: dict | None) -> None:
    chapters = story["chapters"]
    events = {item["event_id"]: item for item in story["events"]}
    places = {item["place_id"] for item in story["places"]}
    flags = {item["key"] for item in story.get("flags") or []}
    images = {item["image_id"]: item for item in story.get("images") or []}
    npcs = story.get("npcs") or []
    npc_ids = {item["npc_id"] for item in npcs}
    stages = [item["stage"] for item in story["relationship"]["stages"]]
    lead = story["lead"]
    outfits = {item["outfit_id"] for item in lead["outfits"]}
    unique(report, "story.chapters", "챕터 ID", [item["chapter_id"] for item in chapters])
    unique(report, "story.events", "이벤트 ID", [item["event_id"] for item in story["events"]])
    unique(report, "story.places", "장소 ID", [item["place_id"] for item in story["places"]])
    unique(report, "story.images", "그림 ID", [i["image_id"] for i in story.get("images") or []])
    unique(report, "story.flags", "표시", [item["key"] for item in story.get("flags") or []])
    unique(report, "story.npcs", "엑스트라 ID", [item["npc_id"] for item in npcs])
    unique(report, "story.npcs", "엑스트라 이름", [item["name"] for item in npcs])
    unique(
        report,
        "story.events",
        "선택지 ID",
        [
            choice["choice_id"]
            for event in story["events"]
            for milestone in event["milestones"]
            for choice in milestone.get("choices") or []
        ],
    )
    widgets = story.get("widgets") or []
    unique(report, "story.widgets", "상태 항목 ID", [item["widget_id"] for item in widgets])
    for widget in widgets:
        where = f"story.widgets[{widget['widget_id']}]"
        if PLAYER_WIDGET.match(widget["widget_id"]):
            report.error(where, "p1, p2…는 플레이어 몫이라 쓸 수 없어요")
        if not about_known(widget.get("about", "lead"), npc_ids):
            report.error(where, "없는 인물을 가리켜요")
        instruction = widget.get("instruction", "")
        if (
            widget.get("kind") == "meter"
            and not widget.get("follows_stage")
            and any(word in widget.get("label", "") + instruction for word in GAUGE_WORDS)
        ):
            report.warn(where, "호감 막대는 follows_stage를 켜세요. 끄면 관계 단계와 어긋납니다")
    for who, expressions, notes in (
        ("lead", lead["expressions"], lead.get("expression_notes") or {}),
        *((item["npc_id"], faces_of(item), item.get("expression_notes") or {}) for item in npcs),
    ):
        for name in notes:
            if name not in expressions:
                report.error(f"story.{who}.expression_notes", f"표정 목록에 없어요: {name}")
    relationship = story["relationship"]
    if relationship["start_stage"] not in stages:
        report.error("story.relationship.start_stage", "단계 목록에 있는 이름을 쓰세요")
    for stage in relationship.get("card_stages") or {}:
        if stage not in stages:
            report.error("story.relationship.card_stages", f"이야기의 단계가 아니에요: {stage}")
    floor = 0
    for chapter in chapters:
        where = f"story.chapters[{chapter['chapter_id']}]"
        for event_id in chapter["ends_with"]:
            event = events.get(event_id)
            if event is None or event["chapter_id"] != chapter["chapter_id"]:
                report.error(f"{where}.ends_with", f"이 챕터 밖의 이벤트예요: {event_id}")
            elif event.get("kind", "main") != "main":
                report.error(f"{where}.ends_with", f"메인 이벤트로 끝나야 해요: {event_id}")
        stage = chapter.get("stage_floor")
        if stage is not None:
            if stage not in stages:
                report.error(f"{where}.stage_floor", "단계 목록에 있는 이름을 쓰세요")
            else:
                rank = stages.index(stage)
                mutual = relationship["stages"][rank].get("mutual")
                if mutual and stage != relationship["start_stage"]:
                    report.error(f"{where}.stage_floor", "두 사람의 말이 필요한 단계는 못 써요")
                if rank < floor:
                    report.error(f"{where}.stage_floor", "앞 챕터보다 낮아요")
                floor = max(floor, rank)
        if chapter.get("outfit") is not None and chapter["outfit"] not in outfits:
            report.error(f"{where}.outfit", "메인의 의상 목록에 있는 ID를 쓰세요")
    chapter_ids = {item["chapter_id"] for item in chapters}
    start_at = story["start"]["at"]
    for event in story["events"]:
        where = f"story.events[{event['event_id']}]"
        at = event.get("at")
        if at is not None and is_datetime(at) and is_datetime(start_at):
            if datetime.fromisoformat(at) < datetime.fromisoformat(start_at):
                report.error(f"{where}.at", "이야기 시작보다 앞이에요")
        if event["chapter_id"] not in chapter_ids:
            report.error(f"{where}.chapter_id", "없는 챕터예요")
        milestones = event["milestones"]
        unique(report, f"{where}.milestones", "단계 ID", [m["milestone_id"] for m in milestones])
        requires = event.get("requires") or {}
        used = [
            *(requires.get("flags_all") or []),
            *(requires.get("flags_none") or []),
            *(event.get("sets_flags") or []),
        ]
        used += [
            flag
            for milestone in milestones
            for choice in milestone.get("choices") or []
            for flag in choice.get("sets_flags") or []
        ]
        for flag in used:
            if flag not in flags:
                report.error(where, f"분기 표시 목록에 없어요: {flag}")
        for done in requires.get("events_done") or []:
            if done not in events:
                report.error(f"{where}.requires", f"없는 이벤트예요: {done}")
        for npc_id in event.get("cast") or []:
            if npc_id not in npc_ids:
                report.error(f"{where}.cast", f"없는 엑스트라예요: {npc_id}")
        stage = requires.get("stage_at_least")
        if stage is not None and stage not in stages:
            report.error(f"{where}.requires", "단계 목록에 있는 이름을 쓰세요")
        for step, milestone in enumerate(milestones):
            cg = milestone.get("cg")
            if cg is not None and images.get(cg, {}).get("kind") != "cg":
                report.error(f"{where}.milestones[{step}].cg", "그림 목록의 CG를 쓰세요")
            if STARTS_AND_ENDS.search(milestone["happens"]):
                report.warn(
                    f"{where}.milestones[{step}].happens",
                    "벌어지는 일과 끝나는 일이 함께 있어요. 두 단계로 나누세요",
                )
        if event.get("outfit") is not None and event["outfit"] not in outfits:
            report.error(f"{where}.outfit", "메인의 의상 목록에 있는 ID를 쓰세요")
    last = set(chapters[-1]["ends_with"])
    for event in story["events"]:
        ending = event.get("ending")
        if ending is None:
            continue
        where = f"story.events[{event['event_id']}].ending"
        if event["event_id"] not in last:
            report.error(where, "엔딩은 마지막 챕터를 끝내는 이벤트에만 붙어요")
        cg = ending.get("cg")
        if cg is not None and images.get(cg, {}).get("kind") != "cg":
            report.error(f"{where}.cg", "그림 목록의 CG를 쓰세요")
    for npc in npcs:
        where = f"story.npcs[{npc['npc_id']}]"
        appears = npc.get("appears_from")
        if appears is not None and appears not in events:
            report.error(f"{where}.appears_from", "없는 이벤트예요")
        secret_from = npc.get("secret_from") or []
        if secret_from and not npc.get("secret"):
            report.error(f"{where}.secret", "비밀이 나올 이벤트를 골랐다면 비밀을 쓰세요")
        for event_id in secret_from:
            if event_id not in events or npc["npc_id"] not in (events[event_id].get("cast") or []):
                report.error(
                    f"{where}.secret_from", f"이 인물이 나오는 이벤트가 아니에요: {event_id}"
                )
    start = story["start"]
    if start["place_id"] not in places:
        report.error("story.start.place_id", "장소 목록에 있는 ID를 쓰세요")
    first = chapters[0]["chapter_id"]
    for event_id in start.get("active_events") or []:
        if event_id not in events or events[event_id]["chapter_id"] != first:
            report.error("story.start.active_events", f"첫 챕터의 이벤트가 아니에요: {event_id}")
    if start.get("outfit") is not None and start["outfit"] not in outfits:
        report.error("story.start.outfit", "메인의 의상 목록에 있는 ID를 쓰세요")
    for place in story["places"]:
        image = place.get("image")
        if image is not None and images.get(image, {}).get("kind") != "background":
            report.error(f"story.places[{place['place_id']}].image", "그림 목록의 배경을 쓰세요")
    speakers = {lead["character_id"]: lead["expressions"]}
    speakers.update({item["npc_id"]: faces_of(item) for item in npcs})
    for image in story.get("images") or []:
        if image.get("kind") != "portrait":
            continue
        where = f"story.images[{image['image_id']}]"
        speaker = image.get("speaker")
        if speaker not in speakers:
            report.error(where, "없는 인물의 초상이에요")
            continue
        if image.get("expression") not in speakers[speaker]:
            report.error(where, "그 인물의 표정 목록에 없어요")
        if speaker == lead["character_id"]:
            if image.get("outfit") not in outfits:
                report.error(where, "메인 초상의 의상을 고르세요")
        elif image.get("outfit") is not None:
            report.error(where, "엑스트라 초상에는 의상을 고르지 않아요")
    style = story.get("style") or {}
    low, high = style.get("reply_min_chars"), style.get("reply_max_chars")
    if low is not None and high is not None and low >= high:
        report.error("story.style", "최소 글자 수는 최대 글자 수보다 작아야 해요")
    for chapter in chapters:
        ends = [events.get(item) for item in chapter["ends_with"]]
        gated = [
            event for event in ends if event and (event.get("requires") or {}).get("flags_all")
        ]
        if gated and len(gated) == len(ends):
            report.warn(
                f"story.chapters[{chapter['chapter_id']}].ends_with",
                "끝내는 이벤트가 모두 표시를 요구해요. 표시 없이 지나는 기본 경로를 두세요",
            )
    if card is None:
        return
    name = card["identity"]["name"]
    if name in {item["name"] for item in npcs}:
        report.error("story.npcs", f"엑스트라 이름이 메인 이름({name})과 같아요")
    if story["player"]["default_name"] in {name, *(item["name"] for item in npcs)}:
        report.error("story.player.default_name", "등장인물 이름과 겹쳐요")
    if lead["character_id"] != card["character_id"]:
        report.error("story.lead.character_id", "character의 character_id와 같아야 해요")
    card_stages = [item["stage"] for item in card["relationship_stages"]]
    mapped = relationship.get("card_stages") or {}
    for target in mapped.values():
        if target not in card_stages:
            report.error("story.relationship.card_stages", f"카드의 단계가 아니에요: {target}")
    unmapped = [item for item in stages if item not in mapped and item not in card_stages]
    if unmapped:
        report.warn(
            "story.relationship",
            f"카드에 같은 이름이 없는 단계: {', '.join(unmapped)}. 이름을 맞추거나 "
            "relationship.card_stages로 이어 주세요",
        )
    first_chapter = chapters[0]["chapter_id"]
    for npc in npcs:
        early = [
            event["title"]
            for event in story["events"]
            if npc["npc_id"] in (event.get("cast") or []) and event["chapter_id"] == first_chapter
        ]
        if npc.get("secret") and not npc.get("secret_from") and early:
            report.warn(
                f"story.npcs[{npc['npc_id']}].secret",
                f"첫 챕터 '{early[0]}'부터 비밀이 캐릭터에게 가요. secret_from을 쓰세요",
            )


def check_one_on_one(report: Report, one: dict, story: dict | None, card: dict | None) -> None:
    """`one` has passed its schema; this is what the schema cannot see."""
    allowed = {"enabled", "opening", "card_stages", "chapters", "ended"}
    for key in one:
        if key not in allowed:
            report.error(f"one_on_one.{key}", "규격에 없는 항목이에요")
    if card is None:
        return
    stages = {item["stage"]: item for item in card["relationship_stages"]}
    opening = one.get("opening")
    openings = {item["opening_id"] for item in card.get("openings") or []}
    if opening not in (None, "none") and opening not in openings:
        report.error("one_on_one.opening", "캐릭터의 만남 ID이거나 none이어야 해요")
    mapped = one.get("card_stages") or {}
    for target in mapped.values():
        if target not in stages:
            report.error("one_on_one.card_stages", f"카드의 단계가 아니에요: {target}")
    floors = one.get("chapters") or []
    ended = one.get("ended")
    if story is None:
        if floors or ended:
            report.error("one_on_one", "1:1만 있는 작품에는 챕터별 관계가 없어요")
        return
    start = story["relationship"]["start_stage"]
    premise = mapped.get(start, start)
    chapters = {item["chapter_id"] for item in story["chapters"]}
    seen: set[str] = set()
    places = []
    for index, item in enumerate(floors):
        where = f"one_on_one.chapters[{index}]"
        chapter_id = item.get("chapter_id")
        if chapter_id not in chapters:
            report.error(f"{where}.chapter_id", "없는 챕터예요")
        elif chapter_id in seen:
            report.error(f"{where}.chapter_id", "같은 챕터가 두 번 있어요")
        seen.add(chapter_id)
        places.append((where, item))
    if ended is not None:
        places.append(("one_on_one.ended", ended))
    for where, item in places:
        stage = item["stage"]
        if stage not in stages:
            report.error(f"{where}.stage", f"카드의 관계 단계 이름을 쓰세요: {stage}")
        elif stages[stage].get("mutual") and stage != premise:
            report.error(f"{where}.stage", "두 사람의 말로만 닿는 단계는 바닥이 될 수 없어요")


def check_info(report: Report, info: dict, derivative: dict | None, limits: dict) -> None:
    """`info` has passed its schema; these are the stricter limits of the studio's own form."""
    title = info["title"].strip()
    if not title or len(title) > limits["title"]:
        report.error("info.title", f"제목은 1~{limits['title']}자예요")
    if len(info.get("logline") or "") > limits["logline"]:
        report.error("info.logline", f"한 줄 소개는 {limits['logline']}자까지예요")
    if len(info.get("description") or "") > limits["description"]:
        report.error("info.description", f"소개글은 {limits['description']}자까지예요")
    genres = info.get("genres") or []
    low, high = limits["genres"]
    if not low <= len(genres) <= high:
        report.error("info.genres", f"장르는 {low}~{high}개 고르세요")
    for genre in genres:
        if genre not in limits["known_genres"]:
            report.error("info.genres", f"목록에 없는 장르예요: {genre}")
    tags = info.get("tags") or []
    canon, own = sort_tags(tags, limits["tag_book"], info.get("rating") == "19")
    if len(canon) > limits["canon_tags"]:
        report.error("info.tags", f"목록에서 고른 태그는 {limits['canon_tags']}개까지예요")
    own_limit = f"직접 적은 태그는 {limits['tags']}개까지, 하나에 {limits['tag_chars']}자 이내예요"
    if len(own) > limits["tags"]:
        report.error("info.tags", own_limit)
    for word in own:
        if len(word) > limits["tag_chars"]:
            report.error("info.tags", f"{own_limit}: {word}")
    if derivative and derivative.get("is"):
        if info.get("rating") == "19":
            report.error("info.rating", "2차 창작은 19가 될 수 없어요")
        source = (derivative.get("source") or "").strip()
        if not source or len(source) > limits["source"]:
            report.error(
                "derivative.source", f"2차 창작이면 원작 이름을 {limits['source']}자 이내로 쓰세요"
            )
        if "2차 창작" not in tags:
            report.error("info.tags", "2차 창작이면 태그에 '2차 창작'을 붙이세요")
    check_tag_rules(report, info, limits["tag_rules"])


def tag_key(word: str) -> str:
    """A word as the studio matches tags: letters and digits only, Latin in lower case, so
    '로 리' and '로*리' are '로리' and '로리타 패션' is not."""
    text = unicodedata.normalize("NFC", word).casefold()
    return "".join(char for char in text if unicodedata.category(char)[0] in "LN")


def sort_tags(tags: list, book: dict, adult: bool) -> tuple[list[str], list[str]]:
    """A work's one list as the studio sorts it when the page is saved: a word for tags in the
    list (`references/work-tags.md`) is those tags and what they bring along, counted apart from
    the creator's own words; a 19 one only on a 19 work. '2차 창작' is neither."""
    canon: list[str] = []
    own: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        word = " ".join(unicodedata.normalize("NFC", tag).split()).lstrip("#")
        if not word or word == "2차 창작":
            continue
        ids = book["words"].get(tag_key(word), [])
        if ids and (adult or not any(tag_id in book["adult"] for tag_id in ids)):
            for tag_id in ids:
                for one in (tag_id, *book["implies"].get(tag_id, [])):
                    if one not in canon:
                        canon.append(one)
        elif word not in own:
            own.append(word)
    return canon, own


def check_tag_rules(report: Report, info: dict, rules: dict) -> None:
    """What no work carries as tags, as the studio refuses it when the page is saved or the
    work published: a banned subject, a 19 tag below 19, school on a 19 work, a pupil in a
    genre of love. Change the tag or the rating; the studio changes neither for you."""
    words = [tag for tag in info.get("tags") or [] if isinstance(tag, str)]

    def having(names: list[str]) -> list[str]:
        keys = {tag_key(name) for name in names}
        return [word for word in words if tag_key(word) in keys]

    for banned in rules["banned"]:
        for word in having(banned["words"]):
            report.error(
                "info.tags",
                f"'{word}' 태그는 라프티에서 쓸 수 없는 소재({banned['label']})예요. 태그를 빼 주세요",
            )
    adult = info.get("rating") == "19"
    if not adult:
        for word in having(rules["adult"]):
            report.error(
                "info.tags",
                f"'{word}' 태그는 19 작품에만 붙어요. 19 작품으로 바꾸거나 태그를 빼 주세요",
            )
    else:
        for label, names in rules["school"].items():
            if having(names):
                report.error("info.tags", f"'{label}' 태그는 19 작품에 붙일 수 없어요")
    student = rules["student"]
    if having(rules["school"][student]):
        romance = [genre for genre in info.get("genres") or [] if genre in rules["romance_genres"]]
        if romance:
            report.error(
                "info.tags",
                f"'{student}' 태그는 {'·'.join(romance)} 장르와 함께 쓸 수 없어요",
            )


def plain(name: object) -> str:
    return " ".join(name.split()) if isinstance(name, str) else ""


def named_in(name: object, names: object) -> bool:
    """Whether a name written in the tags is one of the work's; anything but text is not."""
    return isinstance(name, str) and name in names  # type: ignore[operator]


def check_tags(report: Report, where: str, tags: object, rules: dict) -> None:
    """Tags as the photo tab takes them: one word each, pasted in a comma list."""
    if not isinstance(tags, list):
        report.error(where, "목록이어야 해요")
        return
    soft: dict[str, list[str]] = {"밑줄 대신 띄어 써요": [], "소문자로 써요": []}
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            report.error(where, "태그는 비어 있지 않은 글이어야 해요")
            continue
        word = " ".join(tag.lower().replace("_", " ").split())
        if "," in tag:
            report.error(where, f"태그 하나에 쉼표를 넣지 않아요: {tag}")
        if len(tag) > rules["tag_chars"]:
            report.error(where, f"태그 하나는 {rules['tag_chars']}자까지예요: {tag}")
        if HANGUL.search(tag):
            report.error(where, f"영어 단부루 태그로 쓰세요: {tag}")
        if word in rules["quality_tags"]:
            report.error(where, f"품질 태그는 사진 탭이 붙여요: {tag}")
        if word in rules["young_tags"]:
            report.error(where, f"어려 보이게 하는 태그는 쓰지 않아요: {tag}")
        if word in REAL_TAGS:
            report.error(where, f"실사풍 태그는 쓰지 않아요: {tag}")
        if word in NOT_FOR_ALL:
            report.error(
                where, f"전체 이용가 태그만 써요. 19 그림은 작가가 사진 탭에서 그려요: {tag}"
            )
        if AGE.search(tag):
            report.error(where, f"나이 숫자는 쓰지 않아요: {tag}")
        if "_" in tag:
            soft["밑줄 대신 띄어 써요"].append(tag)
        if tag != tag.lower():
            soft["소문자로 써요"].append(tag)
    for message, found in soft.items():
        if found:
            more = " 등" if len(found) > 5 else ""
            report.warn(where, f"{message}: {', '.join(found[:5])}{more}")


def check_set(report: Report, at: str, item: dict, rules: dict, known: dict) -> str | None:
    """One tag set; its name when it can be pointed at."""
    for key in item:
        if key not in ("name", "who", "outfit", "tags"):
            report.error(here(at, key), "규격에 없는 항목이에요")
    name = plain(item.get("name"))
    if not 1 <= len(name) <= rules["set_name"]:
        report.error(f"{at}.name", f"세트 이름은 1~{rules['set_name']}자예요")
        name = ""
    who, outfit = item.get("who"), item.get("outfit")
    if known["people"] and not named_in(who, known["people"]):
        report.error(f"{at}.who", "캐릭터 이름 칸과 똑같이 쓴 인물이어야 해요")
    if outfit is not None:
        if known["lead"] and who != known["lead"]:
            report.error(
                f"{at}.outfit", "의상 세트는 메인에게만 있어요. 조연의 옷은 그림 태그에 써요"
            )
        elif known["outfits"] and not named_in(outfit, known["outfits"]):
            report.error(f"{at}.outfit", "메인의 의상 이름과 똑같이 쓰세요")
    tags = item.get("tags")
    if not isinstance(tags, list) or not tags:
        report.error(f"{at}.tags", "태그를 하나 이상 넣으세요")
        return name or None
    if len(tags) > rules["set_tags"]:
        report.error(f"{at}.tags", f"세트 하나에 태그는 {rules['set_tags']}개까지예요")
    check_tags(report, f"{at}.tags", tags, rules)
    if outfit is None:
        low, high = LOOK_TAGS
        if not low <= len(tags) <= high:
            report.warn(f"{at}.tags", f"외모 세트는 {low}~{high}개를 권해요(지금 {len(tags)}개)")
        if not any(tag in ADULT_LOOK for tag in tags):
            report.warn(
                f"{at}.tags",
                "성인이면 mature female이나 mature male(노인은 old woman, old man)을 넣으세요",
            )
    return name or None


def check_picture(
    report: Report, at: str, item: dict, rules: dict, known: dict, sets: set[str]
) -> str | None:
    """One picture to draw; the spot it fills, as the coverage counts it."""
    spot = item.get("spot")
    if not named_in(spot, SPOTS):
        report.error(f"{at}.spot", f"고를 수 있는 값이 아니에요: {', '.join(SPOTS)}")
        return None
    own = {"portrait": ("who", "outfit"), "background": ("place",), "cg": ("cg",)}
    for key in item:
        if key not in ("spot", "sets", "tags", *own.get(spot, ())):
            report.error(here(at, key), "이 자리의 그림에는 없는 항목이에요")
    used = item.get("sets", [])
    if not isinstance(used, list):
        report.error(f"{at}.sets", "목록이어야 해요")
        used = []
    for name in used:
        if plain(name) not in sets:
            report.error(f"{at}.sets", f"세트 목록에 없어요: {name}")
    tags = item.get("tags", [])
    check_tags(report, f"{at}.tags", tags, rules)
    if not used and not tags:
        report.error(at, "세트나 장면 태그를 넣으세요")
    if spot == "portrait":
        who, outfit = item.get("who"), item.get("outfit")
        if known["people"] and not named_in(who, known["people"]):
            report.error(f"{at}.who", "캐릭터 이름 칸과 똑같이 쓴 인물이어야 해요")
            return None
        if who == known["lead"] and known["outfits"]:
            if not named_in(outfit, known["outfits"]):
                report.error(f"{at}.outfit", "메인 초상은 메인의 의상 이름을 골라요")
                return None
            return f"초상 {outfit}"
        if outfit is not None and known["lead"]:
            report.error(f"{at}.outfit", "조연 초상에는 의상을 고르지 않아요")
        return f"초상 {who}"
    if spot in ("background", "cg"):
        key, label, names = (
            ("place", "배경", known["places"])
            if spot == "background"
            else ("cg", "CG", known["cgs"])
        )
        value = item.get(key)
        if known["story"] and not named_in(value, names):
            report.error(f"{at}.{key}", f"이야기의 {label} 이름과 똑같이 쓰세요")
            return None
        return f"{label} {value}"
    return SPOTS[spot][0]


def check_pictures(
    report: Report,
    tags: object,
    card: dict | None,
    story: dict | None,
    limits: dict,
    work: bool,
) -> None:
    """The picture tags the author pastes into the photo tab (references/picture-tags.md)."""
    where = "notes.picture_tags"
    if tags is None:
        report.warn(
            where,
            "그림 태그가 없어요. references/picture-tags.md를 따라 work/pictures.json을 쓰세요",
        )
        return
    if not isinstance(tags, dict):
        report.error(where, "묶음이어야 해요")
        return
    for key in tags:
        if key not in ("sets", "pictures", "faces"):
            report.error(here(where, key), "규격에 없는 항목이에요")
    rules = limits["pictures"]
    lead = card["identity"]["name"] if card else None
    npcs = (story.get("npcs") or []) if story else []
    known = {
        "lead": lead,
        "people": {lead, *(item["name"] for item in npcs)} if lead else set(),
        "story": story is not None,
        "outfits": [item["label"] for item in story["lead"]["outfits"]] if story else [],
        "places": [item["name"] for item in story["places"]] if story else [],
        "cgs": [item["label"] for item in story.get("images") or [] if item.get("kind") == "cg"]
        if story
        else [],
    }
    sets = tags.get("sets", [])
    if not isinstance(sets, list):
        report.error(f"{where}.sets", "목록이어야 해요")
        sets = []
    names: list[str] = []
    for index, item in enumerate(sets):
        at = here(f"{where}.sets", index)
        if not isinstance(item, dict):
            report.error(at, "묶음이어야 해요")
            continue
        name = check_set(report, at, item, rules, known)
        if name:
            names.append(name)
    unique(report, f"{where}.sets", "세트 이름", names)
    pictures = tags.get("pictures", [])
    if not isinstance(pictures, list):
        report.error(f"{where}.pictures", "목록이어야 해요")
        pictures = []
    covered: set[str] = set()
    for index, item in enumerate(pictures):
        at = here(f"{where}.pictures", index)
        if not isinstance(item, dict):
            report.error(at, "묶음이어야 해요")
            continue
        spot = check_picture(report, at, item, rules, known, set(names))
        if spot:
            covered.add(spot)
    wanted = ["프로필", *(["표지"] if work else [])]
    if story:
        # The lead once per outfit (or once, with none), each supporting role once.
        wanted += [f"초상 {item}" for item in known["outfits"]] or (
            [f"초상 {lead}"] if lead else []
        )
        wanted += [f"초상 {item['name']}" for item in npcs]
        wanted += [f"배경 {item}" for item in known["places"]]
        wanted += [f"CG {item}" for item in known["cgs"]]
    elif lead:
        wanted.append(f"초상 {lead}")
    missing = [item for item in wanted if item not in covered]
    if missing:
        more = " 등" if len(missing) > 8 else ""
        report.warn(where, f"그림 태그가 없는 자리: {', '.join(missing[:8])}{more}")
    faces = tags.get("faces", {})
    if not isinstance(faces, dict):
        report.error(f"{where}.faces", "묶음이어야 해요")
        faces = {}
    named = []
    if story:
        named = [*story["lead"]["expressions"], *(face for item in npcs for face in faces_of(item))]
    for name, listed in faces.items():
        at = f"{where}.faces.{name}"
        if story and name not in named:
            report.warn(at, "표정 목록에 없는 이름이라 쓰이지 않아요")
        if not isinstance(listed, list) or not listed:
            report.error(at, "태그를 하나 이상 넣으세요")
            continue
        check_tags(report, at, listed, rules)
    left = [
        face
        for face in dict.fromkeys(named)
        if face not in rules["known_faces"] and face not in faces
    ]
    if left:
        report.warn(
            f"{where}.faces", f"사진 탭이 모르는 표정이에요. 표정 태그를 쓰세요: {', '.join(left)}"
        )


def check_text(report: Report, document: object, path: str) -> None:
    if isinstance(document, dict):
        for key, value in document.items():
            check_text(report, value, here(path, key))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            check_text(report, value, here(path, index))
    elif isinstance(document, str) and FOREIGN.search(document):
        report.error(path, "사용자 자리에는 {{{PLAYER_NAME}}}만 써요")


def check_bundle(bundle: dict, assets: Path = ASSETS) -> Report:
    report = Report()
    if bundle.get("format") != FORMAT:
        report.error("format", f"{FORMAT}이어야 해요")
    extra = set(bundle) - {
        "format",
        "info",
        "character",
        "story",
        "one_on_one",
        "derivative",
        "notes",
    }
    for key in sorted(extra):
        report.error(key, "규격에 없는 항목이에요")
    card, story = bundle.get("character"), bundle.get("story")
    one, info = bundle.get("one_on_one"), bundle.get("info")
    derivative = bundle.get("derivative")
    if not isinstance(card, dict):
        report.error("character", "메인 캐릭터 카드가 없어요")
        return report
    limits = json.loads((assets / "work-limits.json").read_text("utf-8"))
    card_fits = fits(report, card, schema_of(assets, "character-card-v2.schema.json"), "character")
    if card_fits:
        check_card(report, card, limits["card"])
        check_adults(report, bundle, card, limits["adult_age"], limits["adult_main_age"])
    story_fits = False
    if story is not None:
        story_fits = fits(report, story, schema_of(assets, "scenario-card-v1.schema.json"), "story")
        if story_fits:
            check_story(report, story, card if card_fits else None)
            check_world(report, story, limits["world_suggested"])
            check_lessons(report, story, card if card_fits else None)
    if one is not None and fits(
        report, one, schema_of(assets, "one-on-one.schema.json"), "one_on_one"
    ):
        check_one_on_one(report, one, story if story_fits else None, card if card_fits else None)
    if derivative is not None and not fits(report, derivative, DERIVATIVE, "derivative"):
        derivative = None
    if info is not None:
        if fits(report, info, schema_of(assets, "work-info.schema.json"), "info"):
            check_info(report, info, derivative, limits)
    elif story is not None or one is not None:
        report.error("info", "작품 정보가 없어요")
    check_text(report, {"character": card, "story": story, "one_on_one": one}, "")
    notes = bundle.get("notes")
    check_pictures(
        report,
        notes.get("picture_tags") if isinstance(notes, dict) else None,
        card if card_fits else None,
        story if story_fits else None,
        limits,
        info is not None,
    )
    return report


def main() -> int:
    if len(sys.argv) != 2:
        print("쓰는 법: python check.py 작품.lafty.json")
        return 2
    try:
        bundle = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"파일을 읽을 수 없어요: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"JSON 형식 오류 ({exc.lineno}행 {exc.colno}열): {exc.msg}")
        return 1
    if not isinstance(bundle, dict):
        print("파일 전체가 하나의 묶음이어야 해요.")
        return 1
    report = check_bundle(bundle)
    for line in report.errors:
        print(f"[수정할 항목] {line}")
    for line in report.warnings:
        print(f"[확인할 항목] {line}")
    print(f"수정할 항목 {len(report.errors)}개, 확인할 항목 {len(report.warnings)}개")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
