import unittest
from datetime import date

from budget_app.validators import (
    parse_amount,
    parse_date,
    validate_category_name,
    validate_transaction_type,
)


class ValidatorTest(unittest.TestCase):
    def test_parse_date_accepts_valid_date(self) -> None:
        self.assertEqual(parse_date(" 2026-09-11 "), date(2026, 9, 11))

    def test_parse_date_rejects_invalid_format_and_calendar_date(self) -> None:
        for value in ("2026-9-11", "20260911", "2026-13-40"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_date(value)

    def test_parse_amount_accepts_positive_integer(self) -> None:
        self.assertEqual(parse_amount(" 12000 "), 12000)

    def test_parse_amount_rejects_non_positive_or_non_integer_value(self) -> None:
        for value in ("0", "-1000", "abc", "1.5", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)

    def test_validate_transaction_type_accepts_supported_types(self) -> None:
        self.assertEqual(validate_transaction_type(" income "), "income")
        self.assertEqual(validate_transaction_type("expense"), "expense")

    def test_validate_transaction_type_rejects_unsupported_type(self) -> None:
        with self.assertRaises(ValueError):
            validate_transaction_type("payment")

    def test_validate_category_name_rejects_blank_name(self) -> None:
        self.assertEqual(validate_category_name(" food "), "food")

        for value in ("", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_category_name(value)


if __name__ == "__main__":
    unittest.main()
