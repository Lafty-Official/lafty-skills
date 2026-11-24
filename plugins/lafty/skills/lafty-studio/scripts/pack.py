#!/usr/bin/env python3
"""Join the pieces of a work into the one file the studio takes.

    python pack.py work/ 작품.lafty.json

`work/` holds character.json and, as the work needs, info.json, story.json (and from a skill
up to 0.1.7, one_on_one.json: works have no 1:1 now, but the studio still takes it),
derivative.json, notes.json and pictures.json. The hidden ids are set here so nobody has to
write them; the studio gives real ones on upload. The picture tags go into the file's notes, and
beside it as `{제목} 그림 태그.md` for the author to paste into the photo tab. The notes also
say which version of this skill made the file (`made_with`), so the studio can tell a file from
an older skill. Exits 1 when the result does not pass check.py.
"""

import json
import sys
from pathlib import Path

# Beside this file, from wherever and however it is called.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check import FORMAT, SPOTS, check_bundle, faces_of  # noqa: E402

SKILL = "lafty-studio"
# Written by the build beside SKILL.md; absent only in the repo's unbuilt sources.
VERSION = Path(__file__).resolve().parents[1] / "VERSION"
CHARACTER_ID = "c-draft"
SCENARIO_ID = "s-draft"
SHEET = "그림 태그.md"
INTRO = (
    "스튜디오의 사진 탭에서 그릴 때 붙여 넣는 태그입니다. 모델은 태그를 읽는 애니 모델 가운데"
    " 고릅니다. 품질 태그와 빼고 싶은 태그는 사진 탭이 붙이니 따로 넣지 않습니다. 한 줄을"
    " 통째로 태그 칸에 붙여 넣으면 쉼표마다 나뉩니다."
)
SETS_HOW = (
    "사진 탭을 「전문가 모드」로 열고 「세트와 조합」으로 갑니다. 아래 세트마다 「새 세트」를"
    " 누르고 이름과 세트 분류를 고른 뒤 「새 세트의 태그」에 태그를 붙여 넣고 「세트 만들기」를"
    " 누릅니다. 그다음 「새 조합」으로 메인 캐릭터에게 늘 넣을 세트를 순서대로 담아"
    " 「조합 만들기」를 누르고, 그 조합의 「이어진 캐릭터」에서 캐릭터 이름을 두 번 눌러"
    " 기본으로 둡니다. 기본 조합은 그 캐릭터를 고르면 먼저 들어갑니다."
)
PICTURES_HOW = (
    "조합 화면의 「그리기에서 열기」를 누르면 기본 조합이 그리기 방에 열립니다. 넣을 세트를"
    " 더하고 장면 태그를 붙여 넣어 그 비율로 그립니다. 마음에 드는 그림은 「갤러리에 넣기」로"
    " 그 자리에 넣습니다."
)
FACES_HOW = (
    "초상을 그린 뒤 「편집」의 「표정」에서 표정을 고르고, 「표정 태그"
    " 보기」에 아래 태그를 붙여 넣습니다. 여기 없는 표정은 사진 탭이 이름으로 씁니다."
)


def read(folder: Path, name: str) -> object | None:
    path = folder / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text("utf-8"))


def items_of(story: dict, key: str) -> list[dict]:
    """The usable items of a list; check.py reports whatever else is there."""
    items = story.get(key)
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def made_with() -> str | None:
    """This skill and its version, as the file's notes carry them."""
    version = VERSION.read_text("utf-8").strip() if VERSION.is_file() else ""
    return f"{SKILL} {version}" if version else None


def pack(folder: Path) -> dict:
    bundle: dict = {"format": FORMAT}
    for name in ("info", "character", "story", "one_on_one", "derivative", "notes"):
        value = read(folder, name)
        if value is not None:
            bundle[name] = value
    pictures = read(folder, "pictures")
    if pictures is not None:
        notes = bundle.setdefault("notes", {})
        if isinstance(notes, dict):
            notes["picture_tags"] = pictures
    maker = made_with()
    if maker:
        notes = bundle.setdefault("notes", {})
        if isinstance(notes, dict):
            notes["made_with"] = maker
    card = bundle.get("character")
    if isinstance(card, dict):
        card["character_id"] = CHARACTER_ID
    story = bundle.get("story")
    if isinstance(story, dict):
        story["scenario_id"] = SCENARIO_ID
        if isinstance(story.get("lead"), dict):
            story["lead"]["character_id"] = CHARACTER_ID
        npcs = {str(item.get("npc_id")) for item in items_of(story, "npcs")}
        for image in items_of(story, "images"):
            if image.get("kind") == "portrait" and str(image.get("speaker")) not in npcs:
                image["speaker"] = CHARACTER_ID
    return bundle


def joined(tags: object) -> str:
    items = tags if isinstance(tags, list) else []
    return ", ".join(tag.strip() for tag in items if isinstance(tag, str) and tag.strip())


def faces_by_name(bundle: dict) -> dict[str, list[str]]:
    """Each person's faces, to say which to make from their portrait."""
    story, card = bundle.get("story"), bundle.get("character")
    if not isinstance(story, dict):
        return {}
    found = {str(item.get("name")): faces_of(item) for item in items_of(story, "npcs")}
    lead = story.get("lead")
    if isinstance(card, dict) and isinstance(card.get("identity"), dict) and isinstance(lead, dict):
        found[str(card["identity"].get("name"))] = lead.get("expressions") or []
    return {name: faces for name, faces in found.items() if isinstance(faces, list)}


def sheet(bundle: dict) -> str | None:
    """The picture tags as the author reads them: what to paste where in the photo tab."""
    notes = bundle.get("notes")
    tags = notes.get("picture_tags") if isinstance(notes, dict) else None
    if not isinstance(tags, dict):
        return None
    info = bundle.get("info") if isinstance(bundle.get("info"), dict) else {}
    card = bundle.get("character") if isinstance(bundle.get("character"), dict) else {}
    identity = card.get("identity") if isinstance(card.get("identity"), dict) else {}
    title = info.get("title") or identity.get("name") or "작품"
    lines = [f"# {title} 그림 태그", "", INTRO, ""]
    # Whatever else is there, check.py reports; the sheet keeps to what it can read.
    sets = items_of(tags, "sets")
    if sets:
        lines += ["## 태그 세트", "", SETS_HOW, ""]
        lead = identity.get("name")
        for item in sets:
            if item.get("who") != lead:
                how = "세트 분류는 「인물」입니다. 조합에 넣지 않고, 이 인물을 그릴 때 더합니다."
            elif item.get("outfit"):
                how = "세트 분류는 「의상」입니다. 기본 조합에는 넣지 않고, 이 의상을 그릴 때 더합니다."
            else:
                how = f"세트 분류는 「인물」입니다. {lead}의 기본 조합에 넣습니다."
            lines += [f"### {item.get('name')}", "", how, ""]
            lines += ["```", joined(item.get("tags")), "```", ""]
    faces = faces_by_name(bundle)
    pictures = items_of(tags, "pictures")
    if pictures:
        lines += ["## 그릴 그림", "", PICTURES_HOW, ""]
        for item in pictures:
            spot = str(item.get("spot"))
            label, ratio = SPOTS.get(spot, (spot, ""))
            named = [str(item[key]) for key in ("who", "outfit", "place", "cg") if item.get(key)]
            lines += [f"### {' · '.join([label, *named])} ({ratio})", ""]
            if isinstance(item.get("sets"), list) and item["sets"]:
                lines += [f"넣을 세트: {', '.join(map(str, item['sets']))}", ""]
            if joined(item.get("tags")):
                lines += ["```", joined(item.get("tags")), "```", ""]
            own = [str(face) for face in faces.get(str(item.get("who"))) or []]
            if spot == "portrait" and own:
                rest = f" 나머지는 표정 세트로 만듭니다: {', '.join(own[1:])}" if own[1:] else ""
                lines += [f"이 그림이 「{own[0]}」 표정입니다.{rest}", ""]
    given = tags.get("faces")
    if isinstance(given, dict) and given:
        lines += ["## 표정 태그", "", FACES_HOW, ""]
        lines += [f"- **{name}:** `{joined(listed)}`" for name, listed in given.items()]
        lines.append("")
    return "\n".join(lines)


def sheet_path(target: Path) -> Path:
    stem = target.name.removesuffix(".json").removesuffix(".lafty")
    return target.with_name(f"{stem} {SHEET}")


def main() -> int:
    if len(sys.argv) != 3:
        print("쓰는 법: python pack.py work/ 작품.lafty.json")
        return 2
    try:
        bundle = pack(Path(sys.argv[1]))
    except json.JSONDecodeError as exc:
        print(f"JSON 형식 오류: {exc.lineno}행 {exc.colno}열: {exc.msg}")
        return 1
    report = check_bundle(bundle)
    target = Path(sys.argv[2])
    target.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written = sheet(bundle)
    if written:
        sheet_path(target).write_text(written, encoding="utf-8")
        print(f"그림 태그: {sheet_path(target)}")
    for line in report.errors:
        print(f"[수정할 항목] {line}")
    for line in report.warnings:
        print(f"[확인할 항목] {line}")
    print(f"수정할 항목 {len(report.errors)}개, 확인할 항목 {len(report.warnings)}개: {target}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
