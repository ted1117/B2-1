import unittest
from datetime import date

from budget_app.models import Transaction


class TransactionTest(unittest.TestCase):
    def test_to_dict_and_from_dict_round_trip(self) -> None:
        transaction = Transaction(
            id="TX-000001",
            type="expense",
            date=date(2026, 9, 11),
            amount=12000,
            category="food",
            memo="점심",
            tags=["meal"],
        )

        data = transaction.to_dict()

        self.assertEqual(data["date"], "2026-09-11")
        self.assertEqual(Transaction.from_dict(data), transaction)

    def test_from_dict_uses_optional_field_defaults(self) -> None:
        transaction = Transaction.from_dict(
            {
                "id": "TX-000001",
                "type": "income",
                "date": "2026-09-11",
                "amount": 1000,
                "category": "salary",
            }
        )

        self.assertEqual(transaction.memo, "")
        self.assertEqual(transaction.tags, [])


if __name__ == "__main__":
    unittest.main()
