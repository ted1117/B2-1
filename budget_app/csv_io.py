import csv
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from budget_app.errors import CsvFileError
from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository
from budget_app.validators import parse_amount, parse_date, validate_transaction_type

CSV_FIELDS = ("date", "type", "category", "amount", "memo", "tags")
REQUIRED_CSV_FIELDS = frozenset(("date", "type", "category", "amount"))


class TransactionCsvService:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._transaction_repository = transaction_repository
        self._category_repository = category_repository

    def import_file(self, source: Path) -> int:
        categories = set(self._category_repository.iter_all())

        def build_transactions(max_sequence: int) -> Iterator[Transaction]:
            yield from self._read_transactions(source, categories, max_sequence)

        return self._transaction_repository.append_atomically(build_transactions)

    def _read_transactions(
        self,
        source: Path,
        categories: set[str],
        max_sequence: int,
    ) -> Iterator[Transaction]:
        line_number = 1
        try:
            with source.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file, strict=True)
                headers = reader.fieldnames
                self._validate_headers(source, headers)

                for offset, row in enumerate(reader, start=1):
                    line_number = reader.line_num
                    if None in row or any(value is None for value in row.values()):
                        raise CsvFileError(
                            source, line_number, "헤더와 데이터의 열 수가 다릅니다."
                        )
                    try:
                        category = row["category"].strip()
                        if category not in categories:
                            raise ValueError(
                                f"등록되지 않은 카테고리입니다: {category}"
                            )
                        yield Transaction(
                            id=f"TX-{max_sequence + offset:06d}",
                            date=parse_date(row["date"]),
                            type=validate_transaction_type(row["type"]),
                            category=category,
                            amount=parse_amount(row["amount"]),
                            memo=row.get("memo", ""),
                            tags=[
                                tag.strip()
                                for tag in row.get("tags", "").split(",")
                                if tag.strip()
                            ],
                        )
                    except ValueError as error:
                        raise CsvFileError(source, line_number, str(error)) from None
        except CsvFileError:
            raise
        except (csv.Error, UnicodeError) as error:
            raise CsvFileError(source, line_number, str(error)) from None

    def _validate_headers(self, source: Path, headers: list[str] | None) -> None:
        if headers is None:
            raise CsvFileError(source, 1, "헤더가 없는 빈 CSV 파일입니다.")
        if len(headers) != len(set(headers)):
            raise CsvFileError(source, 1, "중복된 헤더가 있습니다.")
        unknown_fields = set(headers) - set(CSV_FIELDS)
        if unknown_fields:
            fields = ", ".join(sorted(unknown_fields))
            raise CsvFileError(source, 1, f"알 수 없는 헤더입니다: {fields}")
        missing_fields = REQUIRED_CSV_FIELDS - set(headers)
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise CsvFileError(source, 1, f"필수 헤더가 없습니다: {fields}")

    def export_file(self, destination: Path, from_date: date, to_date: date) -> int:
        if destination.exists():
            raise ValueError(
                f"출력 파일이 이미 존재합니다: {destination}. "
                "다른 경로를 지정해 주세요."
            )

        temp_path: Path | None = None
        exported_count = 0
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=destination.parent,
                delete=False,
            ) as csv_file:
                temp_path = Path(csv_file.name)
                writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
                writer.writeheader()
                for transaction in self._transaction_repository.iter_reverse():
                    if transaction.date < from_date or transaction.date > to_date:
                        continue
                    writer.writerow(
                        {
                            "date": transaction.date.isoformat(),
                            "type": transaction.type,
                            "category": transaction.category,
                            "amount": transaction.amount,
                            "memo": transaction.memo,
                            "tags": ",".join(transaction.tags),
                        }
                    )
                    exported_count += 1
            temp_path.replace(destination)
            return exported_count
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
