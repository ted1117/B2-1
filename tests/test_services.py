import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from budget_app.models import Transaction
from budget_app.repositories import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from budget_app.services import TransactionService


class TransactionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        path = Path(self.temp_directory.name) / "transactions.jsonl"
        category_path = Path(self.temp_directory.name) / "categories.jsonl"
        budget_path = Path(self.temp_directory.name) / "budgets.jsonl"
        budget_path.touch()
        self.repository = TransactionRepository(path)
        self.category_repository = CategoryRepository(category_path)
        self.category_repository.add("food")
        self.service = TransactionService(
            self.repository,
            self.category_repository,
            BudgetRepository(budget_path),
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

    def test_summarize_month_calculates_totals_and_category_ranking(self) -> None:
        for transaction in (
            Transaction("TX-000001", "income", date(2026, 9, 1), 10000, "salary"),
            Transaction("TX-000002", "expense", date(2026, 9, 1), 3000, "rent"),
            Transaction("TX-000003", "expense", date(2026, 9, 30), 2000, "food"),
            Transaction("TX-000004", "expense", date(2026, 9, 15), 1000, "food"),
            Transaction("TX-000005", "income", date(2026, 10, 1), 99999, "salary"),
        ):
            self.repository.add(transaction)

        summary = self.service.summarize_month("2026-09", top=2)

        self.assertEqual(summary.transaction_count, 4)
        self.assertEqual(summary.total_income, 10000)
        self.assertEqual(summary.total_expense, 6000)
        self.assertEqual(summary.balance, 4000)
        self.assertEqual(summary.category_expenses, [("food", 3000), ("rent", 3000)])

    def test_summarize_empty_and_income_only_month(self) -> None:
        empty = self.service.summarize_month("2026-08")
        self.repository.add(
            Transaction("TX-000001", "income", date(2026, 9, 1), 10000, "salary")
        )
        income_only = self.service.summarize_month("2026-09")

        self.assertEqual(empty.transaction_count, 0)
        self.assertEqual(empty.balance, 0)
        self.assertEqual(empty.category_expenses, [])
        self.assertEqual(income_only.total_income, 10000)
        self.assertEqual(income_only.total_expense, 0)

    def test_set_and_get_budget(self) -> None:
        first = self.service.set_budget("2026-09", 200000)
        second = self.service.set_budget("2026-09", 300000)

        self.assertEqual(first.amount, 200000)
        self.assertEqual(second.amount, 300000)
        self.assertEqual(self.service.get_budget("2026-09"), second)
        self.assertIsNone(self.service.get_budget("2026-10"))

    def test_set_budget_rejects_non_positive_amount(self) -> None:
        with self.assertRaises(ValueError):
            self.service.set_budget("2026-09", 0)

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
