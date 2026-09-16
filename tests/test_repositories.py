import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_app.errors import DataFileError
from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository


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


if __name__ == "__main__":
    unittest.main()
