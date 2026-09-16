import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository
from budget_app.services import TransactionService


class TransactionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        path = Path(self.temp_directory.name) / "transactions.jsonl"
        category_path = Path(self.temp_directory.name) / "categories.jsonl"
        self.repository = TransactionRepository(path)
        self.category_repository = CategoryRepository(category_path)
        self.category_repository.add("food")
        self.service = TransactionService(
            self.repository,
            self.category_repository,
        )

    def add_transaction(self, amount: int = 1000) -> Transaction:
        return self.service.add_transaction(
            transaction_type="expense",
            transaction_date=date(2026, 9, 11),
            amount=amount,
            category="food",
            memo="점심",
            tags=["meal"],
        )

    def test_add_transaction_generates_sequential_ids(self) -> None:
        first = self.add_transaction()
        second = self.add_transaction()

        self.assertEqual(first.id, "TX-000001")
        self.assertEqual(second.id, "TX-000002")

    def test_add_transaction_rejects_unregistered_category(self) -> None:
        with self.assertRaises(ValueError):
            self.service.add_transaction(
                transaction_type="expense",
                transaction_date=date(2026, 9, 11),
                amount=1000,
                category="transport",
            )

        self.assertEqual(list(self.repository.iter_all()), [])

    def test_register_category_adds_new_name_without_duplicate(self) -> None:
        self.service.register_category("transport")
        self.service.register_category("transport")

        self.assertTrue(self.service.is_category_registered("transport"))
        self.assertEqual(
            list(self.service.list_categories()),
            ["food", "transport"],
        )

    def test_add_category_rejects_duplicate_and_preserves_case(self) -> None:
        self.service.add_category(" Food ")

        with self.assertRaisesRegex(ValueError, "이미 등록된"):
            self.service.add_category("food")

        self.assertEqual(list(self.service.list_categories()), ["food", "Food"])

    def test_remove_unused_category_and_reject_missing_category(self) -> None:
        self.service.add_category("transport")

        self.service.remove_category("transport")

        self.assertFalse(self.service.is_category_registered("transport"))
        with self.assertRaisesRegex(ValueError, "등록되지 않은"):
            self.service.remove_category("transport")

    def test_remove_category_rejects_category_used_by_transaction(self) -> None:
        self.add_transaction()

        with self.assertRaisesRegex(ValueError, "사용 중"):
            self.service.remove_category("food")

        self.assertTrue(self.service.is_category_registered("food"))

    def test_new_id_uses_max_sequence_when_lower_id_was_deleted(self) -> None:
        first = self.add_transaction()
        second = self.add_transaction()
        self.service.delete_transaction(first.id)

        third = self.add_transaction()

        self.assertEqual(first.id, "TX-000001")
        self.assertEqual(second.id, "TX-000002")
        self.assertEqual(third.id, "TX-000003")

    def test_list_transactions_returns_latest_first_and_applies_limit(self) -> None:
        first = self.add_transaction(1000)
        second = self.add_transaction(2000)
        third = self.add_transaction(3000)

        all_transactions = list(self.service.list_transactions())
        transactions = list(self.service.list_transactions(limit=2))

        self.assertEqual(all_transactions, [third, second, first])
        self.assertEqual(transactions, [third, second])
        self.assertNotIn(first, transactions)

    def test_list_transactions_uses_default_limit_twenty(self) -> None:
        transactions = [self.add_transaction(sequence) for sequence in range(1, 26)]

        result = list(self.service.list_transactions())

        self.assertEqual(result, list(reversed(transactions[-20:])))

    def test_update_transaction_changes_only_specified_fields(self) -> None:
        original = self.add_transaction()

        result = self.service.update_transaction(
            original.id,
            amount=15000,
            memo="저녁",
        )

        updated = next(self.repository.iter_all())
        self.assertTrue(result)
        self.assertEqual(updated.amount, 15000)
        self.assertEqual(updated.memo, "저녁")
        self.assertEqual(updated.type, original.type)
        self.assertEqual(updated.date, original.date)
        self.assertEqual(updated.category, original.category)
        self.assertEqual(updated.tags, original.tags)

    def test_update_transaction_rejects_unregistered_category(self) -> None:
        original = self.add_transaction()

        with self.assertRaisesRegex(ValueError, "등록되지 않은"):
            self.service.update_transaction(original.id, category="transport")

        self.assertEqual(next(self.repository.iter_all()), original)

    def test_update_and_delete_return_false_for_missing_id(self) -> None:
        self.assertFalse(self.service.update_transaction("TX-999999", amount=15000))
        self.assertFalse(self.service.delete_transaction("TX-999999"))

    def test_delete_transaction_removes_transaction(self) -> None:
        transaction = self.add_transaction()

        result = self.service.delete_transaction(transaction.id)

        self.assertTrue(result)
        self.assertEqual(list(self.repository.iter_all()), [])


if __name__ == "__main__":
    unittest.main()
