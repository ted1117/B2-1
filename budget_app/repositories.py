import json
from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile

from budget_app.errors import DataFileError
from budget_app.models import Transaction


class TransactionRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def add(self, transaction: Transaction) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n")

    def iter_all(self) -> Iterator[Transaction]:
        if not self.path.exists():
            return

        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict):
                        raise TypeError("JSON 객체여야 합니다.")
                    yield Transaction.from_dict(data)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                    raise DataFileError(self.path, line_number, str(error)) from None

    def find_by_id(self, transaction_id: str) -> bool:
        return any(transaction.id == transaction_id for transaction in self.iter_all())

    def update(self, transaction: Transaction) -> bool:
        if not self.path.exists():
            return False

        updated = False
        temp_path: Path | None = None

        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

                for current_transaction in self.iter_all():
                    if current_transaction.id == transaction.id:
                        current_transaction = transaction
                        updated = True

                    temp_file.write(
                        json.dumps(current_transaction.to_dict(), ensure_ascii=False)
                        + "\n"
                    )

            if updated:
                temp_path.replace(self.path)

            return updated
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def delete(self, transaction_id: str) -> bool:
        if not self.path.exists():
            return False

        deleted = False
        temp_path: Path | None = None

        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

                for transaction in self.iter_all():
                    if transaction.id == transaction_id:
                        deleted = True
                        continue

                    temp_file.write(
                        json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n"
                    )

            if deleted:
                temp_path.replace(self.path)

            return deleted
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


class CategoryRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def add(self, category: str) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps({"name": category}, ensure_ascii=False) + "\n")

    def iter_all(self) -> Iterator[str]:
        if not self.path.exists():
            return

        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if not isinstance(data, dict):
                        raise TypeError("JSON 객체여야 합니다.")
                    name = data["name"]
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError("name은 비어 있지 않은 문자열이어야 합니다.")
                    yield name
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                    raise DataFileError(self.path, line_number, str(error)) from None

    def exists(self, category: str) -> bool:
        return any(current == category for current in self.iter_all())
