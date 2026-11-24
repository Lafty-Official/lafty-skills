# 라프티 스킬

라프티(Lafty)에서 AI와 함께 작품을 만들 수 있게 돕는 스킬입니다. Claude나 Codex 같은 AI 도구에 설치해서 쓰고, 다 만든 파일은 라프티 스튜디오에서 불러와 씁니다.

| 스킬 | 하는 일 |
|---|---|
| `lafty-novel` | 라프티가 공식으로 추천하는 소설 쓰기 스킬입니다. AI와 이야기하며 브레인스토밍하고, 설정집과 대강을 거쳐 소설 초안을 씁니다. 끝에 작품설계서를 만듭니다. |
| `lafty-studio` | 소설 초안이나 아이디어를 라프티에 게시할 수 있는 작품 파일(`제목.lafty.json`)로 만듭니다. |

라프티가 추천하는 순서는 `lafty-novel`로 시작해서 `lafty-studio`로 옮기는 것입니다. 만들어 둔 아이디어나 작품이 있으면 `lafty-studio`만으로도 옮길 수 있습니다. 두 스킬은 하나로 묶여 있어서 함께 설치됩니다.

## 어떤 파일을 어디에 넣나요

| 파일 | 넣는 곳 |
|---|---|
| `제목.lafty.json` (`lafty-studio`가 만듦) | 스튜디오 › 만들기 › 가져오기 › **라프티 파일**. 캐릭터만 있는 파일도 여기로 올립니다. 이미 올린 작품을 고친 파일은 작품 편집 머리글 ⋯ 메뉴의 **파일로 불러오기**로 올립니다. |
| `제목 그림 태그.md` (`lafty-studio`가 만듦) | 올리지 않습니다. 사진 탭에서 그림을 그릴 때 태그를 복사해 붙여 넣습니다. |
| 원고, 설정집, 작품설계서 (`lafty-novel`이 만듦) | 스튜디오에 올리지 않습니다. `lafty-studio`에게 주면 작품 파일로 만들어 줍니다. |

스튜디오 만들기의 「가져오기 › 다른 앱 카드」는 다른 앱(SillyTavern, RisuAI)의 캐릭터 카드를 넣는 곳입니다. 라프티 작품 파일은 그 옆의 「라프티 파일」로 올립니다.

## 설치

### Claude Code

```text
/plugin marketplace add Lafty-Official/lafty-skills
/plugin install lafty@lafty
```

새 버전은 `/plugin` › Marketplaces에서 `lafty`를 고르고 **Enable auto-update**를 켜 두면 저절로 받습니다. 직접 받으려면 같은 화면에서 **Update marketplace**를 고릅니다.

### Claude 앱 (웹, 데스크톱)

1. **Customize › Plugins**에서 **Add › Add marketplace**를 누르고 `Lafty-Official/lafty-skills`를 넣습니다.
2. 목록에 나온 `lafty`를 설치합니다.
3. 스킬이 스크립트로 파일을 검사하므로, 설정에서 코드 실행(Create and edit files)을 켭니다.

설치한 플러그인은 계정에 붙어서 같은 계정의 Claude Code에도 들어갑니다. 새 버전은 그 마켓플레이스의 **Check for updates**나 **Sync automatically**로 받습니다.

### Codex

Codex에서 `$skill-installer`에게 두 스킬을 설치해 달라고 합니다.

```text
$skill-installer https://github.com/Lafty-Official/lafty-skills/tree/main/plugins/lafty/skills/lafty-novel
$skill-installer https://github.com/Lafty-Official/lafty-skills/tree/main/plugins/lafty/skills/lafty-studio
```

직접 넣으려면 이 저장소의 `plugins/lafty/skills/` 아래 두 폴더를 `~/.agents/skills/`에 둡니다. 스킬이 보이지 않으면 Codex를 다시 시작합니다.

### 그 밖의 AI 도구

```text
npx skills add Lafty-Official/lafty-skills
```

새 버전은 `npx skills update`로 받습니다.

위 방법을 쓸 수 없는 도구에서는 이 저장소의 **Code › Download ZIP**으로 받아, `plugins/lafty/skills/` 아래 두 폴더를 그 도구의 스킬 넣는 곳에 둡니다.

## 쓰기

새 대화에서 "라프티 작품 만들어 줘"나 "소설부터 같이 써 줘"처럼 말하면 스킬이 시작됩니다. 스킬이 몇 가지를 묻고 작품설계서로 방향을 먼저 보여 줍니다. 작가가 괜찮다고 하면 나머지 칸을 채우고, 스튜디오와 같은 규칙으로 검사해서 파일을 줍니다.

받은 파일은 이렇게 씁니다.

1. 스튜디오 「만들기」 › 「가져오기」 › 「라프티 파일」로 올립니다. 비공개 초안으로 들어가고, 내가 쓴 글이거나 쓸 권리가 있는 글인지 한 번 확인합니다.
2. 테스트를 해 봅니다. 스토리는 엔딩까지 한 번, 메인과의 DM은 몇 턴입니다. 고칠 곳을 AI에게 말하면 파일을 다시 만들어 줍니다.
3. 그림은 파일에 들어가지 않습니다. 스킬은 그림을 그리지 않고, 그림이 들어갈 자리마다 사진 탭에 붙여 넣을 태그를 `제목 그림 태그.md`로 줍니다. 그 태그로 그려 갤러리에 넣습니다.
4. 게시는 작가가 스튜디오에서 합니다.

## 버전

바뀐 점은 [CHANGELOG.md](CHANGELOG.md)에 있습니다. 예전 스킬로 만든 파일을 올리면 스튜디오가 알려 주니, 그때 스킬을 새로 받습니다.

## 라이선스

스킬은 [Apache License 2.0](LICENSE)으로 냅니다. 저작권과 고지는 [NOTICE](NOTICE)에 있습니다. 고쳐서 다시 배포할 때는 `LICENSE`와 `NOTICE`를 함께 두고, 고친 파일에는 고쳤다고 적습니다.

- 스킬로 만든 소설, 작품설계서, 작품 파일은 만든 사람의 것입니다.
- 「Lafty」, 「라프티」 이름과 로고는 라이선스에 들어가지 않습니다.

## 문의

이 저장소는 PR과 이슈를 받지 않습니다. 문의와 오류 제보는 라프티 앱의 고객센터로 보내 주세요. 계정이 없으면 contact@lafty.ai로 보내 주세요.

스킬의 일부는 다른 프로젝트의 방법을 옮겨 고쳐 쓴 것입니다. 출처와 라이선스는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있습니다.
