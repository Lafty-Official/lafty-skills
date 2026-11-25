# Lafty Skills

[라프티(Lafty)](https://lafty.ai) 작품 제작을 위한 공식 AI 스킬 저장소입니다. 두 스킬이 한 묶음으로 설치됩니다.

- **`lafty-novel`** — 아이디어 정리, 설정집, 개요, 소설 초안 작성 후 작품설계서까지 출력
- **`lafty-studio`** — 소설 초안이나 아이디어를 라프티 스튜디오용 작품 파일(`.lafty.json`)과 이미지 태그 파일로 변환

처음부터 쓸 때는 `lafty-novel` → `lafty-studio` 순서를 권장하며, 기존 원고나 아이디어가 있으면 `lafty-studio`만 바로 사용할 수 있습니다.

## 설치

### Claude Code

```text
/plugin marketplace add Lafty-Official/lafty-skills
/plugin install lafty@lafty
```

- 자동 업데이트: `/plugin` › Marketplaces › `lafty` › **Enable auto-update**
- 수동 업데이트: 같은 메뉴에서 **Update marketplace**

### Claude 앱 (웹 / 데스크톱)

1. **Customize › Plugins** › **Add › Add marketplace**에서 `Lafty-Official/lafty-skills` 추가
2. 목록에서 `lafty` 설치
3. 설정에서 코드 실행(Create and edit files) 활성화 *(파일 검증 스크립트 실행에 필요)*

계정 단위로 동기화되므로 같은 계정의 Claude Code에도 함께 적용됩니다. 업데이트는 **Check for updates** 또는 **Sync automatically**를 사용합니다.

### Codex

```text
$skill-installer https://github.com/Lafty-Official/lafty-skills/tree/main/plugins/lafty/skills/lafty-novel
$skill-installer https://github.com/Lafty-Official/lafty-skills/tree/main/plugins/lafty/skills/lafty-studio
```

수동 설치 시 `plugins/lafty/skills/` 아래 두 폴더를 `~/.agents/skills/`에 복사하고 Codex를 재시작합니다.

### 기타 AI 도구

```text
npx skills add Lafty-Official/lafty-skills
```

- 업데이트: `npx skills update`
- 수동 설치: **Code › Download ZIP** 후 `plugins/lafty/skills/` 아래 두 폴더를 도구별 스킬 폴더에 배치

## 사용 흐름

새 대화에서 `"라프티 작품 만들어 줘"` 또는 `"소설부터 같이 써 줘"`로 시작하면 됩니다. 방향을 정해 작품설계서를 확인한 뒤 스튜디오 규격 검증을 거친 파일을 출력합니다.

### 출력 파일별 사용 위치

- **`제목.lafty.json`** — 스튜디오 › 만들기 › **라프티 파일 불러오기**로 업로드 *(신규 작품·캐릭터)*
  - 기존 작품 수정본은 작품 편집 상단 `⋯` › **파일로 불러오기** 사용
- **`제목 그림 태그.md`** — 업로드하지 않고, 스튜디오 사진 탭에서 이미지 생성 시 복사해 사용
- **원고 · 설정집 · 작품설계서** — `lafty-studio`에 넘겨 `.lafty.json`으로 변환

### 스튜디오 반영 순서

1. `.lafty.json` 업로드 → 저작권 확인 후 비공개 초안 생성
2. 스튜디오에서 스토리·DM 테스트 진행 *(수정이 필요하면 AI에게 다시 생성 요청)*
3. `제목 그림 태그.md`를 참고해 사진 탭에서 이미지 생성 후 갤러리에 등록
4. 스튜디오에서 최종 게시

## 버전 및 라이선스

- **변경 이력**: [CHANGELOG.md](CHANGELOG.md) *(구버전 스킬로 만든 파일 업로드 시 스튜디오에서 업데이트 안내 표시)*
- **라이선스**: [Apache License 2.0](LICENSE) · 저작권 고지 [NOTICE](NOTICE) · 제3자 출처 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
  - 수정 재배포 시 `LICENSE`·`NOTICE` 유지 및 변경 사항 명시 필요
  - 스킬로 제작한 원고·설계서·작품 파일의 권리는 제작자에게 있으며, 'Lafty'·'라프티' 명칭과 로고는 라이선스 범위 밖입니다.

## 문의

이 저장소는 PR과 이슈를 받지 않습니다. 문의 및 오류 제보는 라프티 앱 고객센터 또는 contact@lafty.ai로 보내 주세요.
