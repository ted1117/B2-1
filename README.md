# 나만의 용돈 기입장

Python 표준 라이브러리와 JSONL 파일로 거래를 관리하는 콘솔 가계부입니다.
현재 거래 추가·목록·수정·삭제, 공통 실행 기반, 카테고리 관리, 조건 검색과
CSV 가져오기·내보내기를 사용할 수 있습니다. 월별 요약과 예산은 별도 기능
브랜치에 구현되어 있습니다.

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

카테고리는 별도 명령으로 추가·조회·삭제합니다. 거래가 사용 중인 카테고리는
삭제할 수 없습니다.

```zsh
uv run python -m budget_app category add
uv run python -m budget_app category list
uv run python -m budget_app category remove
```

카테고리가 하나도 없으면 거래를 추가할 수 없습니다. 먼저 `category add`를
실행해야 합니다.

검색 조건은 모두 선택이며 함께 지정하면 AND로 결합됩니다. 결과는 최근 등록
순서로 출력합니다.

```zsh
uv run python -m budget_app search -from 2026-09-01 -to 2026-09-30
uv run python -m budget_app search -category food -type expense -q 점심 -tag meal
```

CSV 가져오기는 전체 행과 카테고리를 검증한 뒤 한 번에 반영합니다. 한 행이라도
잘못되면 기존 거래 파일을 바꾸지 않습니다. 내보내기는 월이나 날짜 범위 중
하나를 지정하며, 기존 출력 파일을 덮어쓰지 않습니다.

```zsh
uv run python -m budget_app import -from import.csv
uv run python -m budget_app export -out september.csv -month 2026-09
uv run python -m budget_app export \
  -out range.csv \
  -from 2026-09-01 \
  -to 2026-09-15
```

CSV 헤더는 아래 순서로 내보냅니다. 가져올 때 열 순서는 자유지만 `date`,
`type`, `category`, `amount`가 필수이고 `memo`, `tags`는 생략할 수 있습니다.

```csv
date,type,category,amount,memo,tags
2026-09-13,expense,food,12000,점심,"meal,work"
```

CSV에는 ID를 포함하지 않습니다. 가져온 순서대로 새 ID를 발급하므로 같은 CSV를
다시 가져오면 기존 내용을 덮어쓰지 않고 새로운 거래로 등록합니다. `tags`는
쉼표로 나누며, 메모의 쉼표·따옴표·줄바꿈은 표준 CSV 인용 규칙으로 보존합니다.

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
힌트를 출력하고 0이 아닌 종료 코드로 끝냅니다. 수정·삭제·CSV 가져오기는 같은
폴더의 임시 파일을 완성한 뒤 원본을 교체합니다.

## 개발 검사

```zsh
uv run python -m unittest discover -v
uv run ruff format .
uv run ruff check .
```

기능별 범위와 완료 조건은 [전체 PRD](docs/PRD.md)와
[PRD-002](docs/PRD-002.md), [PRD-003](docs/PRD-003.md),
[PRD-004](docs/PRD-004.md), [PRD-007](docs/PRD-007.md)에서 확인할 수 있습니다.
