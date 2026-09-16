import csv
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from budget_app.csv_io import CSV_FIELDS, TransactionCsvService
from budget_app.errors import CsvFileError
from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository


class TransactionCsvServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.directory = Path(self.temp_directory.name)
        self.transaction_path = self.directory / "transactions.jsonl"
        self.category_path = self.directory / "categories.jsonl"
        self.repository = TransactionRepository(self.transaction_path)
        self.category_repository = CategoryRepository(self.category_path)
        self.category_repository.add("food")
        self.category_repository.add("salary")
        self.service = TransactionCsvService(self.repository, self.category_repository)

    def write_csv(self, name: str, content: str) -> Path:
        path = self.directory / name
        path.write_text(content, encoding="utf-8", newline="")
        return path

    def test_import_assigns_ids_and_supports_reordered_optional_columns(self) -> None:
        self.repository.add(
            Transaction("TX-000003", "expense", date(2026, 8, 1), 100, "food")
        )
        source = self.write_csv(
            "input.csv",
            "amount,category,type,date\n12000,food,expense,2026-09-13\n"
            "3000000,salary,income,2026-09-14\n",
        )

        imported = self.service.import_file(source)

        transactions = list(self.repository.iter_all())
        self.assertEqual(imported, 2)
        self.assertEqual(
            [item.id for item in transactions],
            ["TX-000003", "TX-000004", "TX-000005"],
        )
        self.assertEqual(transactions[1].memo, "")
        self.assertEqual(transactions[1].tags, [])

        self.assertEqual(self.service.import_file(source), 2)
        self.assertEqual(
            [item.id for item in self.repository.iter_all()],
            [
                "TX-000003",
                "TX-000004",
                "TX-000005",
                "TX-000006",
                "TX-000007",
            ],
        )

    def test_header_only_import_succeeds_with_zero_rows(self) -> None:
        source = self.write_csv("empty.csv", ",".join(CSV_FIELDS) + "\n")

        self.assertEqual(self.service.import_file(source), 0)
        self.assertEqual(list(self.repository.iter_all()), [])

    def test_invalid_later_row_preserves_original_bytes(self) -> None:
        self.repository.add(
            Transaction("TX-000001", "expense", date(2026, 8, 1), 100, "food")
        )
        original = self.transaction_path.read_bytes()
        source = self.write_csv(
            "invalid.csv",
            ",".join(CSV_FIELDS)
            + "\n2026-09-13,expense,food,12000,점심,meal\n"
            + "2026-02-30,expense,food,1000,오류,\n",
        )

        with self.assertRaises(CsvFileError) as context:
            self.service.import_file(source)

        self.assertEqual(context.exception.line_number, 3)
        self.assertEqual(self.transaction_path.read_bytes(), original)

    def test_unknown_category_fails_without_registering_or_importing(self) -> None:
        source = self.write_csv(
            "unknown.csv",
            "date,type,category,amount\n2026-09-13,expense,transport,12000\n",
        )

        with self.assertRaisesRegex(CsvFileError, "등록되지 않은 카테고리"):
            self.service.import_file(source)

        self.assertFalse(self.category_repository.exists("transport"))
        self.assertEqual(list(self.repository.iter_all()), [])

    def test_import_rejects_invalid_headers_width_and_csv_syntax(self) -> None:
        cases = {
            "blank.csv": "",
            "missing.csv": "date,type,amount\n",
            "duplicate.csv": "date,type,category,amount,date\n",
            "unknown-header.csv": "date,type,category,amount,note\n",
            "width.csv": (
                "date,type,category,amount\n2026-09-13,expense,food,1,extra\n"
            ),
            "syntax.csv": (
                'date,type,category,amount,memo\n2026-09-13,expense,food,1,"open\n'
            ),
        }

        for name, content in cases.items():
            with self.subTest(name=name):
                source = self.write_csv(name, content)
                with self.assertRaises(CsvFileError):
                    self.service.import_file(source)
                self.assertEqual(list(self.repository.iter_all()), [])

    def test_export_filters_inclusively_and_uses_latest_registration_order(
        self,
    ) -> None:
        for transaction in (
            Transaction("TX-000001", "expense", date(2026, 8, 31), 1, "food"),
            Transaction("TX-000002", "expense", date(2026, 9, 1), 2, "food"),
            Transaction("TX-000003", "income", date(2026, 9, 30), 3, "salary"),
            Transaction("TX-000004", "expense", date(2026, 10, 1), 4, "food"),
        ):
            self.repository.add(transaction)
        destination = self.directory / "output.csv"

        exported = self.service.export_file(
            destination, date(2026, 9, 1), date(2026, 9, 30)
        )

        with destination.open(encoding="utf-8", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
        self.assertEqual(exported, 2)
        self.assertEqual([row["amount"] for row in rows], ["3", "2"])

    def test_csv_round_trip_preserves_quoted_memo_tags_and_korean(self) -> None:
        original = Transaction(
            "TX-000001",
            "expense",
            date(2026, 9, 13),
            12000,
            "food",
            '점심, "특식"\n두 번째 줄',
            ["meal", "work"],
        )
        self.repository.add(original)
        destination = self.directory / "round-trip.csv"
        self.service.export_file(destination, date(2026, 9, 13), date(2026, 9, 13))
        self.transaction_path.write_text("", encoding="utf-8")

        self.assertEqual(self.service.import_file(destination), 1)

        restored = next(self.repository.iter_all())
        self.assertEqual(restored.memo, original.memo)
        self.assertEqual(restored.tags, original.tags)

    def test_export_writes_header_for_no_results_and_rejects_existing_file(
        self,
    ) -> None:
        destination = self.directory / "empty-export.csv"

        self.assertEqual(
            self.service.export_file(destination, date(2026, 9, 1), date(2026, 9, 30)),
            0,
        )
        self.assertEqual(
            destination.read_text(encoding="utf-8").strip(), ",".join(CSV_FIELDS)
        )

        original = destination.read_bytes()
        with self.assertRaisesRegex(ValueError, "이미 존재"):
            self.service.export_file(destination, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(destination.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
