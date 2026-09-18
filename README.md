# 나만의 용돈 기입장

## 실행 방법

실행 환경은 Python 3.12이며 애플리케이션은 표준 라이브러리만 사용합니다.
프로젝트 루트에서 `uv`로 실행합니다.

```zsh
uv run python -m budget_app -help
```

옵션은 과제 제약사항에 따라 단일 하이픈을 사용합니다. 기본 데이터 폴더는
`./data`이며, 다른 폴더를 사용하려면 하위 명령 앞에 `-data-dir`을 지정합니다.

```zsh
uv run python -m budget_app -data-dir ./my-data list -limit 10
```

초기 카테고리는 자동 생성하지 않으므로 처음 사용할 때 카테고리를 먼저
등록합니다.

```zsh
uv run python -m budget_app category add
uv run python -m budget_app add
uv run python -m budget_app list
```

## 저장 파일 위치와 형식

유효한 명령을 처음 실행하면 데이터 폴더와 다음 UTF-8 JSONL 파일 3개를
자동으로 생성합니다. JSONL은 한 줄에 JSON 객체 하나를 저장합니다.

```text
data/
├── transactions.jsonl
├── categories.jsonl
└── budgets.jsonl
```

`transactions.jsonl`에는 거래를 저장합니다.

```json
{"id":"TX-000001","type":"expense","date":"2026-09-13","amount":12000,"category":"food","memo":"점심","tags":["meal"]}
```

`categories.jsonl`에는 카테고리를 저장합니다.

```json
{"name":"food"}
```

`budgets.jsonl`에는 월별 예산을 저장합니다.

```json
{"month":"2026-09","amount":500000}
```

## 주요 명령 예시

거래 추가는 날짜, 타입, 카테고리, 금액, 메모와 태그를 대화형으로 입력합니다.

```zsh
uv run python -m budget_app add
```

거래 목록은 최근 등록순이며 기본 20건을 출력합니다.

```zsh
uv run python -m budget_app list
uv run python -m budget_app list -limit 3
```

기간, 카테고리, 타입, 메모와 태그 조건으로 거래를 검색합니다.

```zsh
uv run python -m budget_app search \
  -from 2026-09-01 \
  -to 2026-09-30 \
  -category food \
  -type expense \
  -q 점심 \
  -tag meal
```

월별 합계와 카테고리 지출 TOP N을 조회합니다.

```zsh
uv run python -m budget_app summary -month 2026-09 -top 3
```

월 예산을 설정한 뒤 `summary`에서 사용률과 초과 여부를 확인합니다.

```zsh
uv run python -m budget_app budget set -month 2026-09 -amount 500000
uv run python -m budget_app summary -month 2026-09
```

카테고리를 추가·조회·삭제합니다.

```zsh
uv run python -m budget_app category add
uv run python -m budget_app category list
uv run python -m budget_app category remove
```

거래 수정은 옵션 기반이며 지정한 필드만 변경합니다.

```zsh
uv run python -m budget_app update \
  -id TX-000001 \
  -amount 15000 \
  -memo "저녁"
```

ID로 거래를 삭제합니다.

```zsh
uv run python -m budget_app delete -id TX-000001
```

CSV 거래를 가져오거나 월·날짜 범위의 거래를 내보냅니다.

```zsh
uv run python -m budget_app import -from import.csv
uv run python -m budget_app export -out september.csv -month 2026-09
uv run python -m budget_app export \
  -out range.csv \
  -from 2026-09-01 \
  -to 2026-09-15
```

## import/export CSV 스키마

CSV는 UTF-8과 헤더를 사용합니다. 가져올 때 열 순서는 자유지만 알 수 없는 열과
중복 열은 허용하지 않습니다. `date`, `type`, `category`, `amount`는 필수이고
`memo`, `tags`는 선택입니다. 내보낼 때는 아래 열 순서를 사용합니다.

| 열 | 필수 | 설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` 형식의 실제 날짜 |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 미리 등록된 카테고리 |
| `amount` | Y | 0보다 큰 정수 |
| `memo` | N | 문자열, 생략 시 빈 문자열 |
| `tags` | N | 쉼표로 구분한 문자열, 생략 시 빈 목록 |

```csv
date,type,category,amount,memo,tags
2026-09-13,expense,food,12000,점심,"meal,work"
2026-09-25,income,salary,3000000,,
```

CSV에는 거래 ID를 포함하지 않습니다. 가져온 각 행에는 새 ID를 발급하며,
같은 CSV를 다시 가져오면 새로운 거래로 등록합니다.
