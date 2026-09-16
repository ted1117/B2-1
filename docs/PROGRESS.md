# 작업 진행 상황

## 전체 과제 구현 계획

상태: PRD-002~005 기능 브랜치 구현 완료 / PRD-006~007 구현 미착수

- 전체 요구사항과 브랜치별 구현 순서: [PRD](PRD.md)
- PRD-002~007: 공통 CLI, 카테고리 관리, 거래 검색, 월별 요약, 월 예산, CSV 입출력
- PRD 문서 커밋 `eab1007`은 `develop`과 원격 저장소에 반영했다.
- 신규 feature 브랜치 6개도 `eab1007`까지 갱신해 원격 추적 브랜치로 연결했다.
- 현재 브랜치 `feature/monthly-summary`에서 PRD-005를 구현했다.

## PRD-005 월별 요약

상태: 구현 완료

- 월별 총수입·총지출·잔액과 지출 카테고리 TOP N
- 거래 파일 단일 순회와 카테고리 합계만 보관하는 집계
- 동률 카테고리 이름 정렬, 빈 달·수입만 있는 달 안내
- `YYYY-MM` 및 TOP 양수 정수 검증
- 전체 테스트 50개, Ruff 포맷·검사 통과

## PRD-002 공통 CLI 및 실행 기반

상태: 구현 완료

### 완료된 작업

- `-help`, `-data-dir`, `-limit`, `-id` 등 단일 하이픈 옵션 통일
- 전역 데이터 경로 지정 및 JSONL 저장 파일 3개 자동 초기화
- 도움말·CLI 인자 오류에서는 저장 파일을 생성하지 않는 실행 순서
- 거래 목록 기본 20건, 제한된 `deque` 버퍼, 빈 목록 안내
- 공통 오류 처리 데코레이터와 입력·파일·JSONL·입력 중단 오류 메시지
- JSONL 파일 경로·행 번호·필수 필드·필드 타입 검증
- 기존 거래 수정·삭제의 임시 파일 및 원본 보존 회귀 검증
- 현재 구현 범위를 구분한 README와 전체 PRD의 CLI 표기 갱신

### 검증 결과

- `uv run python -m unittest discover -v`: 44개 통과
- `uv run ruff format .`: 통과
- `uv run ruff check .`: 통과
- 실제 CLI에서 빈 임시 경로에 저장 파일 3개 생성 및 `데이터 없음` 출력 확인

### 다음 작업

1. PRD-002 변경을 커밋하고 `feature/cli-foundation`에 푸시한다.
2. 검토 후 `develop`에 반영한다.
3. [PRD-003](PRD-003.md)의 카테고리 관리를 구현한다.

## PRD-001 Transaction 기능

상태: 구현 완료

### 완료된 작업

- `Transaction` 모델 및 JSON 직렬화·역직렬화
- 거래 JSONL 추가·조회·수정·삭제 저장소
- 거래 ID 생성 및 CRUD 서비스
- `add`, `list`, `update`, `delete` CLI
- 날짜, 타입, 금액 입력 검증
- 등록 카테고리 확인 및 미등록 카테고리 등록·재입력 흐름
- 카테고리 이름의 별도 JSONL 저장

### 검증 결과

- `python -m unittest discover -v`: 29개 통과
- `ruff format .`: 통과
- `ruff check .`: 통과

### 남은 작업

- 없음
