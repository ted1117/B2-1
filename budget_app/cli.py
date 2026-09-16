import argparse
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

from budget_app.csv_io import TransactionCsvService
from budget_app.decorators import handle_cli_errors
from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository
from budget_app.services import TransactionService
from budget_app.validators import (
    parse_amount,
    parse_date,
    parse_month,
    validate_category_name,
    validate_transaction_type,
)

DEFAULT_DATA_DIRECTORY = Path("data")
DATA_FILE_NAMES = (
    "transactions.jsonl",
    "categories.jsonl",
    "budgets.jsonl",
)


class BudgetArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self.add_argument("-help", action="help", help="사용 방법을 출력한다.")

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"[인자 오류] {message}\n[힌트] -help로 사용 방법을 확인해 주세요.\n",
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = BudgetArgumentParser(prog="budget_app")
    parser.add_argument(
        "-data-dir",
        type=Path,
        default=DEFAULT_DATA_DIRECTORY,
        help="JSONL 데이터 폴더 (기본값: ./data)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("add", help="거래를 추가한다.")

    list_parser = subparsers.add_parser("list", help="거래 목록을 조회한다.")
    list_parser.add_argument("-limit", type=int, default=20, help="조회할 거래 개수")

    update_parser = subparsers.add_parser("update", help="거래를 수정한다.")
    update_parser.add_argument("-id", required=True, help="수정할 거래 ID")
    update_parser.add_argument("-type", dest="transaction_type")
    update_parser.add_argument("-date", dest="transaction_date")
    update_parser.add_argument("-amount")
    update_parser.add_argument("-category")
    update_parser.add_argument("-memo")
    update_parser.add_argument("-tags", help="쉼표로 구분한 태그")

    delete_parser = subparsers.add_parser("delete", help="거래를 삭제한다.")
    delete_parser.add_argument("-id", required=True, help="삭제할 거래 ID")

    category_parser = subparsers.add_parser("category", help="카테고리를 관리한다.")
    category_subparsers = category_parser.add_subparsers(
        dest="category_command", required=True
    )
    category_subparsers.add_parser("add", help="카테고리를 추가한다.")
    category_subparsers.add_parser("list", help="카테고리 목록을 조회한다.")
    category_subparsers.add_parser("remove", help="카테고리를 삭제한다.")

    search_parser = subparsers.add_parser("search", help="거래를 검색한다.")
    search_parser.add_argument("-from", dest="from_date")
    search_parser.add_argument("-to", dest="to_date")
    search_parser.add_argument("-category")
    search_parser.add_argument("-type", dest="transaction_type")
    search_parser.add_argument("-q", dest="query")
    search_parser.add_argument("-tag")

    import_parser = subparsers.add_parser("import", help="CSV 거래를 가져온다.")
    import_parser.add_argument(
        "-from", dest="source", type=Path, required=True, help="입력 CSV 경로"
    )

    export_parser = subparsers.add_parser("export", help="거래를 CSV로 내보낸다.")
    export_parser.add_argument("-out", type=Path, required=True, help="출력 CSV 경로")
    export_parser.add_argument("-month", help="조회 월 (YYYY-MM)")
    export_parser.add_argument("-from", dest="from_date", help="시작일")
    export_parser.add_argument("-to", dest="to_date", help="종료일")

    return parser


def _select_category(service: TransactionService) -> str:
    while True:
        try:
            category = validate_category_name(input("카테고리: "))
        except ValueError as error:
            print(f"[입력 오류] {error}", file=sys.stderr)
            continue

        if service.is_category_registered(category):
            return category

        categories = ", ".join(service.list_categories()) or "없음"
        print(f"[미등록 카테고리] '{category}'는 등록된 목록에 없습니다.")
        print(f"등록된 카테고리: {categories}")

        while True:
            choice = input("새 카테고리로 등록할까요? (y/n): ").strip().lower()
            if choice == "y":
                service.register_category(category)
                print(f"[카테고리 등록 완료] {category}")
                return category
            if choice == "n":
                break
            print("y 또는 n을 입력해 주세요.")


def _add_transaction(service: TransactionService) -> None:
    if not service.has_categories():
        raise ValueError(
            "등록된 카테고리가 없습니다. category add를 먼저 실행해 주세요."
        )

    transaction_date = parse_date(input("날짜 (YYYY-MM-DD): "))
    transaction_type = validate_transaction_type(input("타입 (income/expense): "))
    category = _select_category(service)
    amount = parse_amount(input("금액: "))
    memo = input("메모: ").strip()
    tags = [tag.strip() for tag in input("태그 (쉼표로 구분): ").split(",")]
    tags = [tag for tag in tags if tag]

    transaction = service.add_transaction(
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        amount=amount,
        category=category,
        memo=memo,
        tags=tags,
    )
    print(f"[저장 완료] id={transaction.id}")


def _format_transaction(transaction: Transaction) -> str:
    tags = ",".join(transaction.tags)
    return (
        f"id={transaction.id} date={transaction.date.isoformat()} "
        f"type={transaction.type} category={transaction.category} "
        f"amount={transaction.amount} memo={transaction.memo} tags={tags}"
    )


def _list_transactions(service: TransactionService, limit: int) -> None:
    found = False
    for transaction in service.list_transactions(limit):
        found = True
        print(_format_transaction(transaction))
    if not found:
        print("데이터 없음")


def _update_transaction(service: TransactionService, args: argparse.Namespace) -> bool:
    transaction_date = (
        parse_date(args.transaction_date) if args.transaction_date is not None else None
    )
    transaction_type = (
        validate_transaction_type(args.transaction_type)
        if args.transaction_type is not None
        else None
    )
    amount = parse_amount(args.amount) if args.amount is not None else None
    tags = (
        [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        if args.tags is not None
        else None
    )

    updated = service.update_transaction(
        transaction_id=args.id,
        transaction_type=transaction_type,
        transaction_date=transaction_date,
        amount=amount,
        category=args.category,
        memo=args.memo,
        tags=tags,
    )
    if updated:
        print(f"[수정 완료] id={args.id}")
        return True

    print(f"[수정 실패] 존재하지 않는 ID입니다: {args.id}", file=sys.stderr)
    print(
        "[힌트] list 명령으로 저장된 거래 ID를 확인해 주세요.",
        file=sys.stderr,
    )
    return False


def _delete_transaction(service: TransactionService, transaction_id: str) -> bool:
    deleted = service.delete_transaction(transaction_id)
    if deleted:
        print(f"[삭제 완료] id={transaction_id}")
        return True

    print(
        f"[삭제 실패] 존재하지 않는 ID입니다: {transaction_id}",
        file=sys.stderr,
    )
    print(
        "[힌트] list 명령으로 저장된 거래 ID를 확인해 주세요.",
        file=sys.stderr,
    )
    return False


def _manage_category(service: TransactionService, command: str) -> None:
    if command == "add":
        category = validate_category_name(input("카테고리명: "))
        service.add_category(category)
        print(f"[저장 완료] category={category}")
        return

    if command == "list":
        found = False
        for category in service.list_categories():
            found = True
            print(f"- {category}")
        if not found:
            print("등록된 카테고리 없음")
            print("[안내] category add를 먼저 실행해 주세요.")
        return

    category = validate_category_name(input("삭제할 카테고리명: "))
    service.remove_category(category)
    print(f"[삭제 완료] category={category}")


def _search_transactions(service: TransactionService, args: argparse.Namespace) -> None:
    from_date = parse_date(args.from_date) if args.from_date is not None else None
    to_date = parse_date(args.to_date) if args.to_date is not None else None
    if from_date is not None and to_date is not None and from_date > to_date:
        raise ValueError("검색 시작일은 종료일보다 늦을 수 없습니다.")

    category = args.category.strip() if args.category is not None else None
    query = args.query.strip() if args.query is not None else None
    tag = args.tag.strip() if args.tag is not None else None
    for name, value in (("카테고리", category), ("검색어", query), ("태그", tag)):
        if value == "":
            raise ValueError(f"{name}는 비워둘 수 없습니다.")

    transaction_type = (
        validate_transaction_type(args.transaction_type)
        if args.transaction_type is not None
        else None
    )
    found = False
    for transaction in service.search_transactions(
        from_date=from_date,
        to_date=to_date,
        category=category,
        transaction_type=transaction_type,
        query=query,
        tag=tag,
    ):
        found = True
        print(_format_transaction(transaction))
    if not found:
        print("검색 결과 없음")


def _export_date_range(args: argparse.Namespace) -> tuple[date, date]:
    has_range_value = args.from_date is not None or args.to_date is not None
    if args.month is not None and has_range_value:
        raise ValueError("-month와 -from/-to는 함께 사용할 수 없습니다.")
    if args.month is None and not has_range_value:
        raise ValueError("-month 또는 -from과 -to를 지정해 주세요.")
    if args.month is not None:
        month = parse_month(args.month)
        year, month_number = map(int, month.split("-"))
        return (
            date(year, month_number, 1),
            date(year, month_number, monthrange(year, month_number)[1]),
        )
    if args.from_date is None or args.to_date is None:
        raise ValueError("날짜 범위는 -from과 -to를 모두 지정해야 합니다.")

    from_date = parse_date(args.from_date)
    to_date = parse_date(args.to_date)
    if from_date > to_date:
        raise ValueError("내보내기 시작일은 종료일보다 늦을 수 없습니다.")
    return from_date, to_date


def _initialize_data_files(data_directory: Path) -> None:
    data_directory.mkdir(parents=True, exist_ok=True)
    for file_name in DATA_FILE_NAMES:
        (data_directory / file_name).touch(exist_ok=True)


@handle_cli_errors
def _execute_command(args: argparse.Namespace) -> int:
    data_directory: Path = args.data_dir
    _initialize_data_files(data_directory)

    if args.command == "list" and args.limit < 1:
        raise ValueError("-limit는 1 이상의 정수여야 합니다.")

    repository = TransactionRepository(data_directory / "transactions.jsonl")
    category_repository = CategoryRepository(data_directory / "categories.jsonl")
    service = TransactionService(repository, category_repository)
    csv_service = TransactionCsvService(repository, category_repository)

    match args.command:
        case "add":
            _add_transaction(service)
        case "list":
            _list_transactions(service, args.limit)
        case "update":
            if not _update_transaction(service, args):
                return 1
        case "delete":
            if not _delete_transaction(service, args.id):
                return 1
        case "category":
            _manage_category(service, args.category_command)
        case "search":
            _search_transactions(service, args)
        case "import":
            imported_count = csv_service.import_file(args.source)
            print(f"[완료] imported={imported_count}, skipped=0")
        case "export":
            from_date, to_date = _export_date_range(args)
            exported_count = csv_service.export_file(args.out, from_date, to_date)
            print(f"[완료] path={args.out}, exported={exported_count}")

    return 0


def main() -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return int(error.code)

    return _execute_command(args)
