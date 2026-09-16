import argparse
import sys
from pathlib import Path

from budget_app.decorators import handle_cli_errors
from budget_app.models import Budget, MonthlySummary, Transaction
from budget_app.repositories import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from budget_app.services import TransactionService
from budget_app.validators import (
    parse_amount,
    parse_date,
    parse_month,
    parse_positive_integer,
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

    summary_parser = subparsers.add_parser("summary", help="월별 요약을 조회한다.")
    summary_parser.add_argument("-month", required=True, help="조회 월 (YYYY-MM)")
    summary_parser.add_argument("-top", default="3", help="지출 카테고리 개수")

    budget_parser = subparsers.add_parser("budget", help="월 예산을 관리한다.")
    budget_subparsers = budget_parser.add_subparsers(
        dest="budget_command", required=True
    )
    budget_set_parser = budget_subparsers.add_parser("set", help="월 예산을 설정한다.")
    budget_set_parser.add_argument("-month", required=True)
    budget_set_parser.add_argument("-amount", required=True)

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


def _print_summary(summary: MonthlySummary, top: int, budget: Budget | None) -> None:
    print(f"{summary.month} 월별 요약")
    if summary.transaction_count == 0:
        print("데이터 없음")
    print(f"총 수입: {summary.total_income}원")
    print(f"총 지출: {summary.total_expense}원")
    print(f"잔액: {summary.balance}원")
    if budget is not None:
        usage = summary.total_expense / budget.amount * 100
        print(f"예산: {budget.amount}원 (사용률 {usage:.1f}%)")
        if summary.total_expense > budget.amount:
            print("[경고] 예산 초과")
    if not summary.category_expenses:
        print("지출 없음")
        return
    print(f"지출 TOP {top}")
    for rank, (category, amount) in enumerate(summary.category_expenses, start=1):
        print(f"{rank}) {category} {amount}원")


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
    budget_repository = BudgetRepository(data_directory / "budgets.jsonl")
    service = TransactionService(repository, category_repository, budget_repository)

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
        case "summary":
            month = parse_month(args.month)
            top = parse_positive_integer(args.top, "TOP")
            _print_summary(
                service.summarize_month(month, top), top, service.get_budget(month)
            )
        case "budget":
            month = parse_month(args.month)
            amount = parse_amount(args.amount)
            budget = service.set_budget(month, amount)
            print(f"[저장 완료] {budget.month} 예산 {budget.amount}원")

    return 0


def main() -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return int(error.code)

    return _execute_command(args)
