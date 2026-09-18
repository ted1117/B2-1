# 나만의 용돈 기입장

Python 표준 라이브러리와 JSONL 파일로 동작하는 콘솔 가계부입니다. 거래 CRUD,
조건 검색, 월별 요약, 카테고리 관리, 월 예산, CSV 가져오기·내보내기를 제공하며
프로그램을 종료한 뒤에도 데이터를 유지합니다.

## 실행 환경

- Python 3.12
- 패키지 및 명령 실행: `uv`
- 애플리케이션 외부 라이브러리: 없음

프로젝트 루트에서 다음 명령으로 전체 도움말을 확인합니다.

```zsh
uv run python -m budget_app -help
```

과제 제약사항에 따라 모든 옵션은 `-help`, `-limit`, `-month`처럼 단일 하이픈을
사용합니다. 전역 `-data-dir` 옵션은 하위 명령 앞에 작성합니다.

```zsh
uv run python -m budget_app -data-dir ./my-data list -limit 10
```

## 처음 실행하기

기본 데이터 폴더는 실행 위치의 `./data`입니다. 유효한 명령을 처음 실행하면
폴더와 저장 파일 3개를 자동으로 만듭니다. 초기 카테고리는 자동 생성하지
않으므로 먼저 카테고리를 등록해야 합니다.

```zsh
uv run python -m budget_app category add
uv run python -m budget_app add
uv run python -m budget_app list
```

`category add`와 `add`는 필요한 값을 터미널에서 차례로 입력받습니다.

## 주요 명령

### 1. 거래 추가

날짜, 타입, 카테고리, 금액, 메모, 태그를 대화형으로 입력합니다. 카테고리는
등록된 목록에 있어야 하며, 저장 후 생성된 거래 ID를 출력합니다.

```zsh
uv run python -m budget_app add
```

```text
날짜 (YYYY-MM-DD): 2026-09-13
타입 (income/expense): expense
카테고리: food
금액: 12000
메모: 점심
태그 (쉼표로 구분): meal,weekday
[저장 완료] id=TX-000001
```

### 2. 거래 목록

최근 등록한 거래부터 출력합니다. 기본 조회 개수는 20건입니다.

```zsh
uv run python -m budget_app list
uv run python -m budget_app list -limit 3
```

### 3. 거래 검색

기간, 카테고리, 타입, 메모 키워드, 태그를 선택적으로 지정할 수 있습니다.
여러 조건은 AND로 결합하며 결과는 최근 등록순입니다.

```zsh
uv run python -m budget_app search -from 2026-09-01 -to 2026-09-30
uv run python -m budget_app search \
  -category food \
  -type expense \
  -q 점심 \
  -tag meal
```

### 4. 월별 요약

해당 월의 총수입, 총지출, 잔액과 지출 카테고리 TOP N을 출력합니다. `-top`의
기본값은 3이며, 거래가 없는 달에는 `데이터 없음`을 표시합니다.

```zsh
uv run python -m budget_app summary -month 2026-09
uv run python -m budget_app summary -month 2026-09 -top 5
```

### 5. 월 예산 설정 및 조회

월 예산은 같은 월에 다시 설정하면 새 금액으로 갱신됩니다. 별도 조회 명령 대신
`summary`에서 예산, 사용률과 초과 경고를 확인합니다.

```zsh
uv run python -m budget_app budget set -month 2026-09 -amount 500000
uv run python -m budget_app summary -month 2026-09
```

```text
예산: 500000원 (사용률 43.0%)
```

총지출이 예산보다 크면 `[경고] 예산 초과`를 함께 출력합니다.

### 6. 카테고리 관리

카테고리를 추가·조회·삭제합니다. 거래에서 사용 중인 카테고리는 삭제할 수
없으며, 연결된 거래를 먼저 수정하거나 삭제해야 합니다.

```zsh
uv run python -m budget_app category add
uv run python -m budget_app category list
uv run python -m budget_app category remove
```

### 7. 거래 수정

수정 방식은 옵션 기반으로 고정했습니다. `-id`는 필수이며 지정한 필드만 바꾸고
나머지 값은 유지합니다.

```zsh
uv run python -m budget_app update \
  -id TX-000001 \
  -amount 15000 \
  -memo "저녁" \
  -tags "meal,weekday"
```

사용 가능한 수정 옵션은 `-date`, `-type`, `-category`, `-amount`, `-memo`,
`-tags`입니다.

### 8. 거래 삭제

```zsh
uv run python -m budget_app delete -id TX-000001
```

존재하지 않는 ID는 원인과 확인 방법을 출력하고 0이 아닌 종료 코드로 끝납니다.

### 9. CSV 가져오기

CSV 전체를 검증한 뒤 모든 행을 한 번에 반영합니다. 한 행이라도 잘못되면 기존
거래 파일을 변경하지 않습니다. CSV의 ID는 받지 않으며 각 행에 새 ID를
발급합니다. 같은 CSV를 다시 가져오면 새로운 거래로 다시 등록됩니다.

```zsh
uv run python -m budget_app import -from import.csv
```

```text
[완료] imported=5, skipped=0
```

### 10. CSV 내보내기

월 또는 날짜 범위 중 하나를 반드시 지정합니다. 범위의 양 끝 날짜를 포함하고
거래를 최근 등록순으로 기록합니다. 대상이 없으면 헤더만 있는 CSV를 만들며,
이미 존재하는 출력 파일은 덮어쓰지 않습니다.

```zsh
uv run python -m budget_app export -out september.csv -month 2026-09
uv run python -m budget_app export \
  -out range.csv \
  -from 2026-09-01 \
  -to 2026-09-15
```

각 명령의 세부 옵션은 `-help`로 확인할 수 있습니다.

```zsh
uv run python -m budget_app search -help
uv run python -m budget_app budget set -help
```

## 저장 위치와 형식

저장 데이터는 UTF-8 JSONL 파일 3개로 분리됩니다. JSONL은 한 줄에 JSON 객체
하나를 저장하는 형식입니다.

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

다른 저장 폴더를 사용하려면 하위 명령 이름 앞에 `-data-dir`을 지정합니다.

```zsh
uv run python -m budget_app -data-dir ./my-data summary -month 2026-09
```

## CSV 스키마

CSV는 UTF-8과 헤더를 사용합니다. 가져올 때 열 순서는 자유지만 알 수 없는 열과
중복 열은 허용하지 않습니다. 내보낼 때는 아래 순서를 사용합니다.

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

메모의 쉼표·따옴표·줄바꿈과 한글은 표준 CSV 인용 규칙으로 보존합니다.

## 프로젝트 구조

```text
budget_app/
├── __main__.py
├── cli.py
├── models.py
├── repositories.py
├── services.py
├── validators.py
├── csv_io.py
├── decorators.py
└── errors.py
```

- `models.py`: 거래·월별 요약·예산 데이터 구조
- `repositories.py`: JSONL 읽기·쓰기와 원자적 파일 교체
- `services.py`: 거래·검색·요약·카테고리·예산 업무 규칙
- `cli.py`: 명령과 옵션, 대화형 입력, 결과 출력
- `csv_io.py`: CSV 검증, 가져오기와 내보내기
- `validators.py`: 날짜·월·금액·타입·카테고리 입력 검증
- `decorators.py`, `errors.py`: 공통 예외 처리와 오류 정보

## 설계 기준

- **제너레이터:** JSONL을 행 단위로 처리하고 검색은 파일을 역방향 블록으로
  읽어 결과 전체를 메모리에 올리지 않습니다.
- **데코레이터:** 공통 CLI 오류 처리 데코레이터가 입력·파일·JSONL·CSV 오류를
  스택트레이스 없이 원인과 해결 힌트로 변환합니다.
- **타입 힌트:** 함수와 메서드의 인자·반환값에 타입을 명시해 모델, 저장소,
  서비스와 CLI 사이의 계약을 드러냅니다.
- **데이터 안전성:** 수정·삭제·예산 갱신·CSV 가져오기는 같은 폴더에 임시
  파일을 완성한 뒤 원본을 원자적으로 교체합니다.
- **종료 코드:** 정상 처리와 조회 결과 없음은 0, 입력·파일 처리 실패는 0이
  아닌 값으로 종료합니다.

## 테스트와 코드 검사

```zsh
uv run python -m unittest discover -v
uv run ruff format .
uv run ruff check .
```

기능별 요구사항과 구현 상태는 [전체 PRD](docs/PRD.md)와
[진행 상황](docs/PROGRESS.md)에서 확인할 수 있습니다.
