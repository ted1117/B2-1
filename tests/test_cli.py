import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_app import cli
from budget_app.repositories import CategoryRepository, TransactionRepository


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.path = Path(self.temp_directory.name) / "transactions.jsonl"
        self.category_path = Path(self.temp_directory.name) / "categories.jsonl"

    def run_cli(
        self,
        *arguments: str,
        inputs: list[str] | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with (
            patch.object(sys, "argv", ["budget_app", *arguments]),
            patch.object(cli, "TRANSACTION_PATH", self.path),
            patch.object(cli, "CATEGORY_PATH", self.category_path),
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
            "--id",
            "TX-000001",
            "--amount",
            "15000",
            "--memo",
            "저녁",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("[수정 완료] id=TX-000001", stdout)
        self.assertEqual(stderr, "")

        exit_code, stdout, stderr = self.run_cli("list", "--limit", "1")
        self.assertEqual(exit_code, 0)
        self.assertIn("id=TX-000001", stdout)
        self.assertIn("amount=15000", stdout)
        self.assertIn("memo=저녁", stdout)
        self.assertEqual(stderr, "")

        exit_code, stdout, stderr = self.run_cli("delete", "--id", "TX-000001")
        self.assertEqual(exit_code, 0)
        self.assertIn("[삭제 완료] id=TX-000001", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(
            list(TransactionRepository(self.path).iter_all()),
            [],
        )

    def test_unregistered_category_can_be_reentered(self) -> None:
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
            "update", "--id", "TX-999999", "--amount", "15000"
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("존재하지 않는 ID", stderr)

        exit_code, _, stderr = self.run_cli("delete", "--id", "TX-999999")
        self.assertEqual(exit_code, 1)
        self.assertIn("존재하지 않는 ID", stderr)


if __name__ == "__main__":
    unittest.main()
