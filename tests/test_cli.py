import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_app import cli
from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.data_directory = Path(self.temp_directory.name) / "data"
        self.path = self.data_directory / "transactions.jsonl"
        self.category_path = self.data_directory / "categories.jsonl"
        self.budget_path = self.data_directory / "budgets.jsonl"

    def run_cli(
        self,
        *arguments: str,
        inputs: list[str] | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.object(
                sys,
                "argv",
                ["budget_app", "-data-dir", str(self.data_directory), *arguments],
            ),
            patch("builtins.input", side_effect=inputs or []),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = cli.main()

        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_add_update_list_and_delete_commands(self) -> None:
        exit_code, stdout, stderr = self.run_cli(
            "add",
            inputs=[
                "2026-09-11",
                "expense",
                "food",
                "y",
                "12000",
                "점심",
                "meal,weekday",
            ],
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("[저장 완료] id=TX-000001", stdout)
        self.assertIn("[카테고리 등록 완료] food", stdout)
        self.assertEqual(stderr, "")
        self.assertTrue(CategoryRepository(self.category_path).exists("food"))

        exit_code, stdout, stderr = self.run_cli(
            "update",
            "-id",
            "TX-000001",
            "-amount",
            "15000",
            "-memo",
            "저녁",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("[수정 완료] id=TX-000001", stdout)
        self.assertEqual(stderr, "")

        exit_code, stdout, stderr = self.run_cli("list", "-limit", "1")
        self.assertEqual(exit_code, 0)
        self.assertIn("id=TX-000001", stdout)
        self.assertIn("amount=15000", stdout)
        self.assertIn("memo=저녁", stdout)
        self.assertEqual(stderr, "")

        exit_code, stdout, stderr = self.run_cli("delete", "-id", "TX-000001")
        self.assertEqual(exit_code, 0)
        self.assertIn("[삭제 완료] id=TX-000001", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(
            list(TransactionRepository(self.path).iter_all()),
            [],
        )

    def test_unregistered_category_can_be_reentered(self) -> None:
        self.data_directory.mkdir()
        CategoryRepository(self.category_path).add("food")

        exit_code, stdout, stderr = self.run_cli(
            "add",
            inputs=[
                "2026-09-11",
                "expense",
                "transport",
                "n",
                "food",
                "12000",
                "점심",
                "meal",
            ],
        )

        transaction = next(TransactionRepository(self.path).iter_all())
        self.assertEqual(exit_code, 0)
        self.assertIn("[미등록 카테고리] 'transport'", stdout)
        self.assertIn("등록된 카테고리: food", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(transaction.category, "food")
        self.assertFalse(CategoryRepository(self.category_path).exists("transport"))

    def test_invalid_add_input_returns_error_without_writing_transaction(self) -> None:
        exit_code, stdout, stderr = self.run_cli(
            "add",
            inputs=["2026-13-40"],
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("[입력 오류]", stderr)
        self.assertEqual(
            list(TransactionRepository(self.path).iter_all()),
            [],
        )

    def test_update_and_delete_missing_id_return_error(self) -> None:
        exit_code, _, stderr = self.run_cli(
            "update", "-id", "TX-999999", "-amount", "15000"
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("존재하지 않는 ID", stderr)

        exit_code, _, stderr = self.run_cli("delete", "-id", "TX-999999")
        self.assertEqual(exit_code, 1)
        self.assertIn("존재하지 않는 ID", stderr)

    def test_valid_command_initializes_three_data_files(self) -> None:
        exit_code, stdout, stderr = self.run_cli("list")

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout, "데이터 없음\n")
        self.assertEqual(stderr, "")
        self.assertEqual(
            {path.name for path in self.data_directory.iterdir()},
            {"transactions.jsonl", "categories.jsonl", "budgets.jsonl"},
        )
        self.assertTrue(
            all(path.read_text() == "" for path in self.data_directory.iterdir())
        )

    def test_initialization_preserves_existing_transaction_data(self) -> None:
        self.data_directory.mkdir()
        repository = TransactionRepository(self.path)
        repository.add(
            Transaction(
                id="TX-000001",
                type="expense",
                date=date(2026, 9, 11),
                amount=1000,
                category="food",
            )
        )
        original = self.path.read_bytes()

        exit_code, stdout, stderr = self.run_cli("list")

        self.assertEqual(exit_code, 0)
        self.assertIn("id=TX-000001", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(self.category_path.exists())
        self.assertTrue(self.budget_path.exists())

    def test_help_and_argument_error_do_not_initialize_data_files(self) -> None:
        for arguments, expected_code in (
            (("-help",), 0),
            (("list", "-help"), 0),
            (("list", "-unknown"), 2),
        ):
            with self.subTest(arguments=arguments):
                exit_code, _, _ = self.run_cli(*arguments)
                self.assertEqual(exit_code, expected_code)
                self.assertFalse(self.data_directory.exists())

    def test_parser_uses_default_data_directory_without_initializing_it(self) -> None:
        parser = cli._build_parser()

        arguments = parser.parse_args(["list"])

        self.assertEqual(arguments.data_dir, Path("data"))
        self.assertFalse(self.data_directory.exists())

    def test_each_crud_command_supports_help(self) -> None:
        for command in ("add", "list", "update", "delete", "summary", "budget"):
            with self.subTest(command=command):
                exit_code, stdout, stderr = self.run_cli(command, "-help")
                self.assertEqual(exit_code, 0)
                self.assertIn("usage:", stdout)
                self.assertEqual(stderr, "")

        exit_code, stdout, stderr = self.run_cli("budget", "set", "-help")
        self.assertEqual(exit_code, 0)
        self.assertIn("usage:", stdout)
        self.assertEqual(stderr, "")

    def test_list_uses_default_limit_twenty_and_registration_order(self) -> None:
        self.data_directory.mkdir()
        repository = TransactionRepository(self.path)
        for sequence in range(1, 26):
            repository.add(
                Transaction(
                    id=f"TX-{sequence:06d}",
                    type="expense",
                    date=date(2026, 9, 11),
                    amount=sequence,
                    category="food",
                )
            )

        exit_code, stdout, stderr = self.run_cli("list")

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(stdout.count("id=TX-"), 20)
        self.assertTrue(stdout.startswith("id=TX-000025"))
        self.assertIn("id=TX-000006", stdout)
        self.assertNotIn("id=TX-000005", stdout)

    def test_invalid_limit_returns_hint_and_nonzero_exit_code(self) -> None:
        for value in ("0", "-1"):
            with self.subTest(value=value):
                exit_code, _, stderr = self.run_cli("list", "-limit", value)
                self.assertEqual(exit_code, 1)
                self.assertIn("[입력 오류]", stderr)
                self.assertIn("[힌트]", stderr)

        exit_code, _, stderr = self.run_cli("list", "-limit", "abc")
        self.assertEqual(exit_code, 2)
        self.assertIn("[인자 오류]", stderr)
        self.assertIn("-help", stderr)

    def test_corrupt_jsonl_reports_path_and_line_without_traceback(self) -> None:
        self.data_directory.mkdir()
        self.path.write_text(
            '{"id":"TX-000001","type":"expense","date":"2026-09-11",'
            '"amount":1000,"category":"food","memo":"","tags":[]}\n'
            "not-json\n",
            encoding="utf-8",
        )

        exit_code, stdout, stderr = self.run_cli("list")

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn(str(self.path), stderr)
        self.assertIn("2번째 줄", stderr)
        self.assertIn("[힌트]", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_interrupted_input_returns_error_without_saving_transaction(self) -> None:
        exit_code, stdout, stderr = self.run_cli("add", inputs=[EOFError()])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("[입력 중단]", stderr)
        self.assertIn("[힌트]", stderr)
        self.assertEqual(self.path.read_text(), "")

    def test_invalid_data_directory_reports_file_error(self) -> None:
        self.data_directory.write_text("not-a-directory")

        exit_code, stdout, stderr = self.run_cli("list")

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("[파일 오류]", stderr)
        self.assertIn("[힌트]", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_summary_prints_monthly_totals_and_top_categories(self) -> None:
        self.data_directory.mkdir()
        repository = TransactionRepository(self.path)
        for transaction in (
            Transaction("TX-000001", "income", date(2026, 9, 1), 10000, "salary"),
            Transaction("TX-000002", "expense", date(2026, 9, 1), 3000, "rent"),
            Transaction("TX-000003", "expense", date(2026, 9, 30), 3000, "food"),
        ):
            repository.add(transaction)

        exit_code, stdout, stderr = self.run_cli(
            "summary", "-month", "2026-09", "-top", "2"
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("총 수입: 10000원", stdout)
        self.assertIn("총 지출: 6000원", stdout)
        self.assertIn("잔액: 4000원", stdout)
        self.assertLess(stdout.index("food 3000원"), stdout.index("rent 3000원"))

    def test_summary_handles_empty_month_and_invalid_options(self) -> None:
        exit_code, stdout, stderr = self.run_cli("summary", "-month", "2026-09")
        self.assertEqual(exit_code, 0)
        self.assertIn("데이터 없음", stdout)
        self.assertIn("총 수입: 0원", stdout)
        self.assertIn("지출 없음", stdout)
        self.assertEqual(stderr, "")

        for arguments in (
            ("summary", "-month", "2026-13"),
            ("summary", "-month", "2026-09", "-top", "0"),
        ):
            exit_code, _, stderr = self.run_cli(*arguments)
            self.assertEqual(exit_code, 1)
            self.assertIn("[힌트]", stderr)

    def test_budget_set_persists_and_summary_shows_usage_and_warning(self) -> None:
        exit_code, stdout, stderr = self.run_cli(
            "budget", "set", "-month", "2026-09", "-amount", "1000"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("2026-09 예산 1000원", stdout)
        self.assertEqual(stderr, "")

        TransactionRepository(self.path).add(
            Transaction("TX-000001", "expense", date(2026, 9, 1), 1001, "food")
        )
        exit_code, stdout, stderr = self.run_cli("summary", "-month", "2026-09")
        self.assertEqual(exit_code, 0)
        self.assertIn("예산: 1000원 (사용률 100.1%)", stdout)
        self.assertIn("예산 초과", stdout)
        self.assertEqual(stderr, "")

    def test_budget_equal_expense_has_no_warning_and_invalid_amount_is_rejected(
        self,
    ) -> None:
        self.run_cli("budget", "set", "-month", "2026-09", "-amount", "1000")
        TransactionRepository(self.path).add(
            Transaction("TX-000001", "expense", date(2026, 9, 1), 1000, "food")
        )
        exit_code, stdout, stderr = self.run_cli("summary", "-month", "2026-09")
        self.assertEqual(exit_code, 0)
        self.assertIn("사용률 100.0%", stdout)
        self.assertNotIn("예산 초과", stdout)
        self.assertEqual(stderr, "")

        exit_code, _, stderr = self.run_cli(
            "budget", "set", "-month", "2026-09", "-amount", "0"
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("[힌트]", stderr)


if __name__ == "__main__":
    unittest.main()
