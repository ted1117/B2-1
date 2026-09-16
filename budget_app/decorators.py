import sys
from collections.abc import Callable
from functools import wraps

from budget_app.errors import DataFileError


def handle_cli_errors[**P](function: Callable[P, int]) -> Callable[P, int]:
    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return function(*args, **kwargs)
        except DataFileError as error:
            print(f"[데이터 오류] {error}", file=sys.stderr)
            print(
                "[힌트] 해당 JSONL 줄을 올바른 JSON과 필수 필드로 수정해 주세요.",
                file=sys.stderr,
            )
        except ValueError as error:
            print(f"[입력 오류] {error}", file=sys.stderr)
            print("[힌트] 입력 형식과 허용 범위를 확인해 주세요.", file=sys.stderr)
        except OSError as error:
            filename = error.filename or "데이터 경로"
            print(f"[파일 오류] {filename}: {error.strerror or error}", file=sys.stderr)
            print(
                "[힌트] 데이터 경로와 파일 쓰기 권한을 확인해 주세요.", file=sys.stderr
            )
        except (EOFError, KeyboardInterrupt):
            print("[입력 중단] 명령을 완료하지 않았습니다.", file=sys.stderr)
            print("[힌트] 명령을 다시 실행해 입력을 완료해 주세요.", file=sys.stderr)

        return 1

    return wrapper
