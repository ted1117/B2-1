# 나만의 용돈 기입장

Python 표준 라이브러리와 JSONL 파일로 거래를 관리하는 콘솔 가계부입니다.
현재 거래 추가·목록·수정·삭제와 PRD-002 공통 실행 기반까지 구현되어 있습니다.
카테고리 관리, 검색, 월별 요약, 예산, CSV 입출력은 각 기능 PRD에 따라 이후
브랜치에서 구현합니다.

## 실행 환경

- Python 3.12
- 패키지 및 명령 실행: `uv`
- 애플리케이션 외부 라이브러리: 없음

```zsh
uv run python -m budget_app -help
```

옵션은 프로젝트 제약사항에 따라 단일 하이픈으로 표기합니다. 전역 `-data-dir`은
하위 명령보다 앞에 작성합니다.

```zsh
uv run python -m budget_app -data-dir ./my-data list -limit 10
```

## 현재 사용할 수 있는 명령

거래 추가는 날짜, 타입, 카테고리, 금액, 메모, 태그를 차례로 입력받습니다.

```zsh
uv run python -m budget_app add
```

목록은 최근 등록한 거래부터 출력하며 기본값은 20건입니다.

```zsh
uv run python -m budget_app list
uv run python -m budget_app list -limit 3
```

수정은 지정한 필드만 바꾸고 나머지는 유지합니다.

```zsh
uv run python -m budget_app update \
  -id TX-000001 \
  -amount 15000 \
  -memo "저녁"
```

```zsh
uv run python -m budget_app delete -id TX-000001
```

각 명령의 옵션은 `-help`로 확인합니다.

```zsh
uv run python -m budget_app list -help
```

## 저장 위치와 형식

기본 저장 폴더는 실행 위치의 `./data`입니다. 유효한 명령을 처음 실행하면
다음 UTF-8 JSONL 파일을 자동 생성합니다. 도움말이나 잘못된 CLI 인자만으로는
파일을 만들지 않습니다.

```text
data/
├── transactions.jsonl
├── categories.jsonl
└── budgets.jsonl
```

거래 한 건은 `transactions.jsonl`의 한 줄에 저장됩니다.

```json
{"id":"TX-000001","type":"expense","date":"2026-09-11","amount":12000,"category":"food","memo":"점심","tags":["meal"]}
```

카테고리 한 개는 `categories.jsonl`의 한 줄에 저장됩니다.

```json
{"name":"food"}
```

`budgets.jsonl`은 PRD-006 구현 전에도 저장 구조를 고정하기 위해 생성합니다.
현재 브랜치에서는 예산을 읽거나 쓰지 않습니다.

손상된 JSONL은 조용히 건너뛰지 않습니다. 파일 경로와 행 번호, 원인과 해결
힌트를 출력하고 0이 아닌 종료 코드로 끝냅니다. 수정·삭제는 같은 폴더의 임시
파일을 완성한 뒤 원본을 교체합니다.

## 개발 검사

```zsh
uv run python -m unittest discover -v
uv run ruff format .
uv run ruff check .
```

기능별 범위와 완료 조건은 [전체 PRD](docs/PRD.md)와
[PRD-002](docs/PRD-002.md)에서 확인할 수 있습니다.
