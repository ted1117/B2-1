import json
from collections.abc import Iterator
from pathlib import Path

from budget_app.models import Transaction


class TransactionRepository:
    def __init__(self, path: Path):
        self._path = path

    @property
    def path(self):
        return self._path

    def add(self, transaction: Transaction) -> None: ...

    def iter_all(self) -> Iterator[Transaction]:
        if not self.path.exists():
            return

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                yield Transaction.from_dict(json.loads(line))

    def find_by_id(self, transaction_id: str) -> bool: ...

    def update(self, transaction: Transaction) -> bool: ...

    def delete(self, transaction_id: str) -> bool: ...
