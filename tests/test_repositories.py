import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_app.errors import DataFileError
from budget_app.models import Budget, Transaction
from budget_app.repositories import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)


def make_transaction(
    transaction_id: str,
    *,
    amount: int = 12000,
    memo: str = "점심",
) -> Transaction:
    return Transaction(
        id=transaction_id,
        type="expense",
        date=date(2026, 9, 11),
        amount=amount,
        category="food",
        memo=memo,
        tags=["meal"],
    )


class TransactionRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.path = Path(self.temp_directory.name) / "transactions.jsonl"
        self.repository = TransactionRepository(self.path)

    def test_iter_all_returns_empty_iterator_when_file_does_not_exist(self) -> None:
        self.assertEqual(list(self.repository.iter_all()), [])

    def test_iter_all_reports_path_and_line_for_invalid_data(self) -> None:
        self.path.write_text("\n{}\n", encoding="utf-8")

        with self.assertRaises(DataFileError) as context:
            list(self.repository.iter_all())

        self.assertEqual(context.exception.path, self.path)
        self.assertEqual(context.exception.line_number, 2)
        self.assertIn("id", context.exception.reason)

    def test_iter_all_rejects_invalid_transaction_field_type(self) -> None:
        self.path.write_text(
            '{"id":"TX-000001","type":"expense","date":"2026-09-11",'
            '"amount":"1000","category":"food"}\n',
            encoding="utf-8",
        )

        with self.assertRaises(DataFileError) as context:
            list(self.repository.iter_all())

        self.assertEqual(context.exception.line_number, 1)
        self.assertIn("amount", context.exception.reason)

    def test_add_appends_jsonl_and_iter_all_restores_transactions(self) -> None:
        first = make_transaction("TX-000001")
        second = make_transaction("TX-000002", amount=3000, memo="간식")

        self.repository.add(first)
        self.repository.add(second)

        self.assertEqual(list(self.repository.iter_all()), [first, second])
        self.assertEqual(
            len(self.path.read_text(encoding="utf-8").splitlines()),
            2,
        )
        self.assertIn("점심", self.path.read_text(encoding="utf-8"))

    def test_iter_reverse_streams_latest_first_across_long_utf8_line(self) -> None:
        first = make_transaction("TX-000001", memo="가" * 9000)
        second = make_transaction("TX-000002", memo="저녁")
        self.repository.add(first)
        self.repository.add(second)
        content = self.path.read_bytes().rstrip(b"\n")
        self.path.write_bytes(b"\n" + content)

        self.assertEqual(list(self.repository.iter_reverse()), [second, first])

    def test_iter_reverse_reports_original_line_number_for_invalid_json(self) -> None:
        self.repository.add(make_transaction("TX-000001"))
        with self.path.open("a", encoding="utf-8") as file:
            file.write("not-json\n")

        with self.assertRaises(DataFileError) as context:
            list(self.repository.iter_reverse())

        self.assertEqual(context.exception.line_number, 2)

    def test_find_by_id_reports_whether_transaction_exists(self) -> None:
        self.repository.add(make_transaction("TX-000001"))

        self.assertTrue(self.repository.find_by_id("TX-000001"))
        self.assertFalse(self.repository.find_by_id("TX-999999"))

    def test_update_replaces_only_matching_transaction(self) -> None:
        first = make_transaction("TX-000001")
        second = make_transaction("TX-000002", amount=3000)
        replacement = make_transaction("TX-000001", amount=15000, memo="저녁")
        self.repository.add(first)
        self.repository.add(second)

        result = self.repository.update(replacement)

        self.assertTrue(result)
        self.assertEqual(list(self.repository.iter_all()), [replacement, second])

    def test_update_missing_id_preserves_original_file(self) -> None:
        transaction = make_transaction("TX-000001")
        self.repository.add(transaction)
        original = self.path.read_text(encoding="utf-8")

        result = self.repository.update(make_transaction("TX-999999"))

        self.assertFalse(result)
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_update_temp_file_failure_preserves_original_file(self) -> None:
        transaction = make_transaction("TX-000001")
        self.repository.add(transaction)
        original = self.path.read_bytes()

        with (
            patch(
                "budget_app.repositories.NamedTemporaryFile",
                side_effect=OSError("임시 파일 생성 실패"),
            ),
            self.assertRaises(OSError),
        ):
            self.repository.update(make_transaction("TX-000001", amount=15000))

        self.assertEqual(self.path.read_bytes(), original)

    def test_delete_removes_only_matching_transaction(self) -> None:
        first = make_transaction("TX-000001")
        second = make_transaction("TX-000002")
        self.repository.add(first)
        self.repository.add(second)

        result = self.repository.delete(first.id)

        self.assertTrue(result)
        self.assertEqual(list(self.repository.iter_all()), [second])

    def test_delete_missing_id_preserves_original_file(self) -> None:
        transaction = make_transaction("TX-000001")
        self.repository.add(transaction)
        original = self.path.read_text(encoding="utf-8")

        result = self.repository.delete("TX-999999")

        self.assertFalse(result)
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)


class CategoryRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.path = Path(self.temp_directory.name) / "categories.jsonl"
        self.repository = CategoryRepository(self.path)

    def test_add_iter_all_and_exists_use_category_jsonl(self) -> None:
        self.repository.add("food")
        self.repository.add("salary")

        self.assertEqual(list(self.repository.iter_all()), ["food", "salary"])
        self.assertTrue(self.repository.exists("food"))
        self.assertFalse(self.repository.exists("transport"))
        self.assertEqual(
            len(self.path.read_text(encoding="utf-8").splitlines()),
            2,
        )

    def test_iter_all_reports_invalid_category_line(self) -> None:
        self.path.write_text('{"name": 1}\n', encoding="utf-8")

        with self.assertRaises(DataFileError) as context:
            list(self.repository.iter_all())

        self.assertEqual(context.exception.line_number, 1)
        self.assertIn("name", context.exception.reason)

    def test_delete_removes_only_matching_category(self) -> None:
        self.repository.add("food")
        self.repository.add("Food")
        self.repository.add("transport")

        result = self.repository.delete("food")

        self.assertTrue(result)
        self.assertEqual(list(self.repository.iter_all()), ["Food", "transport"])

    def test_delete_missing_category_preserves_original_file(self) -> None:
        self.repository.add("food")
        original = self.path.read_bytes()

        result = self.repository.delete("transport")

        self.assertFalse(result)
        self.assertEqual(self.path.read_bytes(), original)

    def test_delete_temp_file_failure_preserves_original_file(self) -> None:
        self.repository.add("food")
        original = self.path.read_bytes()

        with (
            patch(
                "budget_app.repositories.NamedTemporaryFile",
                side_effect=OSError("임시 파일 생성 실패"),
            ),
            self.assertRaises(OSError),
        ):
            self.repository.delete("food")

        self.assertEqual(self.path.read_bytes(), original)


class BudgetRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.path = Path(self.temp_directory.name) / "budgets.jsonl"
        self.path.touch()
        self.repository = BudgetRepository(self.path)

    def test_upsert_adds_and_replaces_month_without_losing_other_month(self) -> None:
        self.repository.upsert(Budget("2026-08", 100000))
        self.repository.upsert(Budget("2026-09", 200000))
        self.repository.upsert(Budget("2026-09", 300000))

        self.assertEqual(
            list(self.repository.iter_all()),
            [Budget("2026-08", 100000), Budget("2026-09", 300000)],
        )
        self.assertEqual(self.repository.find("2026-09"), Budget("2026-09", 300000))

    def test_upsert_failure_preserves_original_file(self) -> None:
        self.repository.upsert(Budget("2026-09", 200000))
        original = self.path.read_bytes()

        with (
            patch(
                "budget_app.repositories.NamedTemporaryFile",
                side_effect=OSError("임시 파일 생성 실패"),
            ),
            self.assertRaises(OSError),
        ):
            self.repository.upsert(Budget("2026-09", 300000))

        self.assertEqual(self.path.read_bytes(), original)

    def test_iter_all_rejects_invalid_stored_month(self) -> None:
        self.path.write_text('{"month":"2026-13","amount":1000}\n', encoding="utf-8")

        with self.assertRaises(DataFileError) as context:
            list(self.repository.iter_all())

        self.assertEqual(context.exception.line_number, 1)
        self.assertIn("YYYY-MM", context.exception.reason)


if __name__ == "__main__":
    unittest.main()
