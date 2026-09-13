import argparse
import sys
from pathlib import Path

from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository
from budget_app.services import TransactionService
from budget_app.validators import (
    parse_amount,
    parse_date,
    validate_category_name,
    validate_transaction_type,
)

TRANSACTION_PATH = Path("data/transactions.jsonl")
CATEGORY_PATH = Path("data/categories.jsonl")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget_app")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("add", help="거래를 추가한다.")

    list_parser = subparsers.add_parser("list", help="거래 목록을 조회한다.")
    list_parser.add_argument("--limit", type=int, help="조회할 거래 개수")

    update_parser = subparsers.add_parser("update", help="거래를 수정한다.")
    update_parser.add_argument("--id", required=True, help="수정할 거래 ID")
    update_parser.add_argument("--type", dest="transaction_type")
    update_parser.add_argument("--date", dest="transaction_date")
    update_parser.add_argument("--amount")
    update_parser.add_argument("--category")
    update_parser.add_argument("--memo")
    update_parser.add_argument("--tags", help="쉼표로 구분한 태그")

    delete_parser = subparsers.add_parser("delete", help="거래를 삭제한다.")
    delete_parser.add_argument("--id", required=True, help="삭제할 거래 ID")

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


def _list_transactions(service: TransactionService, limit: int | None) -> None:
    for transaction in service.list_transactions(limit):
        print(_format_transaction(transaction))


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
    return False


def _delete_transaction(service: TransactionService, transaction_id: str) -> bool:
    deleted = service.delete_transaction(transaction_id)
    if deleted:
        print(f"[삭제 완료] id={transaction_id}")
        return True

    print(f"[삭제 실패] 존재하지 않는 ID입니다: {transaction_id}", file=sys.stderr)
    return False


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "list" and args.limit is not None and args.limit < 1:
        parser.error("--limit는 1 이상의 정수여야 합니다.")

    repository = TransactionRepository(TRANSACTION_PATH)
    category_repository = CategoryRepository(CATEGORY_PATH)
    service = TransactionService(repository, category_repository)

    try:
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
    except ValueError as error:
        print(f"[입력 오류] {error}", file=sys.stderr)
        print("입력 형식과 허용 범위를 확인해 주세요.", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"[파일 오류] {error}", file=sys.stderr)
        print("데이터 파일 경로와 쓰기 권한을 확인해 주세요.", file=sys.stderr)
        return 1

    return 0
