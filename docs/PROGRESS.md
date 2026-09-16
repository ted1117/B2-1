# 작업 진행 상황

## 전체 과제

상태: PRD-001~007 구현 및 `develop` 통합 완료

- 전체 요구사항과 기능별 기준: [PRD](PRD.md)
- 구현 브랜치: `feature/cli-foundation`, `feature/category-management`,
  `feature/transaction-search`, `feature/monthly-summary`,
  `feature/monthly-budget`, `feature/csv-import-export`
- 애플리케이션은 Python 3.12 표준 라이브러리만 사용한다.

## 구현 완료 기능

### PRD-001 거래 CRUD

- 대화형 거래 추가, 최근 등록순 목록, 선택 필드 수정, ID 기반 삭제
- 날짜·타입·금액·등록 카테고리 검증과 순차 ID 발급
- JSONL 추가 및 수정·삭제 원자적 교체

### PRD-002 공통 CLI

- 단일 하이픈 옵션, `-help`, `-data-dir`, 목록 기본 20건
- 거래·카테고리·예산 JSONL 3개 초기화
- 공통 오류 처리 데코레이터, 원인·힌트, 비정상 종료 코드

### PRD-003 카테고리 관리

- 카테고리 추가·목록·삭제, 중복·빈 이름 검증
- 사용 중 카테고리 삭제 차단과 거래 수정 시 등록 검증

### PRD-004 거래 검색

- 기간·카테고리·타입·메모·태그의 AND 검색
- 고정 크기 블록으로 JSONL을 역방향 스트리밍해 등록 역순 출력

### PRD-005 월별 요약

- 총수입·총지출·잔액과 카테고리 지출 TOP N
- 한 번의 거래 순회, 동률 이름 정렬, 빈 달과 수입만 있는 달 처리

### PRD-006 월 예산

- 월별 예산 설정·재설정과 원자적 저장
- 요약의 소수점 한 자리 사용률과 실제 금액 기준 초과 경고

### PRD-007 CSV 입출력

- 엄격한 UTF-8 CSV 헤더·행·값 검증과 새 ID 발급
- 임시 JSONL을 통한 전체 성공 또는 전체 실패 가져오기
- 월 또는 포함 날짜 범위의 등록 역순 내보내기
- 기존 출력 보호, 헤더만 있는 결과, 한글·인용·줄바꿈 왕복

## 최종 검증

- `uv run python -m unittest discover -v`: 85개 통과
- `uv run ruff format .`: 통과
- `uv run ruff check .`: 통과
- `git diff --check`: 통과
- 빈 임시 데이터 경로에서 카테고리 등록, CSV 가져오기, 검색, 월 예산 설정,
  월별 요약, CSV 내보내기 흐름 확인

## 남은 작업

- 없음
