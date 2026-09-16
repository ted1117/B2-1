import json
from collections.abc import Callable, Iterator
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
                yield self._parse_line(line, line_number)

    def iter_reverse(self) -> Iterator[Transaction]:
        if not self.path.exists():
            return

        with self.path.open("rb") as file:
            file.seek(0, 2)
            size = file.tell()
            if size == 0:
                return

            file.seek(-1, 2)
            ends_with_newline = file.read(1) == b"\n"
            file.seek(0)
            line_number = sum(
                chunk.count(b"\n") for chunk in iter(lambda: file.read(8192), b"")
            )
            if not ends_with_newline:
                line_number += 1

            position = size
            buffer = b""
            skip_trailing_empty = ends_with_newline
            while position > 0:
                read_size = min(8192, position)
                position -= read_size
                file.seek(position)
                buffer = file.read(read_size) + buffer
                parts = buffer.split(b"\n")
                buffer = parts[0]

                for raw_line in reversed(parts[1:]):
                    if skip_trailing_empty:
                        skip_trailing_empty = False
                        continue
                    if raw_line.strip():
                        yield self._parse_bytes(raw_line, line_number)
                    line_number -= 1

            if line_number >= 1 and buffer.strip():
                yield self._parse_bytes(buffer, line_number)

    def _parse_bytes(self, raw_line: bytes, line_number: int) -> Transaction:
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DataFileError(self.path, line_number, str(error)) from None
        return self._parse_line(line, line_number)

    def _parse_line(self, line: str, line_number: int) -> Transaction:
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise TypeError("JSON 객체여야 합니다.")
            return Transaction.from_dict(data)
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

    def append_atomically(
        self,
        transaction_factory: Callable[[int], Iterator[Transaction]],
    ) -> int:
        temp_path: Path | None = None
        imported_count = 0
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                max_sequence = 0
                for transaction in self.iter_all():
                    temp_file.write(
                        json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n"
                    )
                    prefix, separator, sequence = transaction.id.partition("-")
                    if prefix == "TX" and separator and sequence.isdigit():
                        max_sequence = max(max_sequence, int(sequence))

                for transaction in transaction_factory(max_sequence):
                    temp_file.write(
                        json.dumps(transaction.to_dict(), ensure_ascii=False) + "\n"
                    )
                    imported_count += 1

            temp_path.replace(self.path)
            return imported_count
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

    def delete(self, category: str) -> bool:
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

                for current in self.iter_all():
                    if current == category:
                        deleted = True
                        continue
                    temp_file.write(
                        json.dumps({"name": current}, ensure_ascii=False) + "\n"
                    )

            if deleted:
                temp_path.replace(self.path)

            return deleted
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
