from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Self


@dataclass
class Transaction:
    id: str
    type: str
    date: date
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        transaction_id = data["id"]
        transaction_type = data["type"]
        transaction_date = data["date"]
        amount = data["amount"]
        category = data["category"]
        memo = data.get("memo", "")
        tags = data.get("tags", [])

        if not isinstance(transaction_id, str) or not transaction_id:
            raise ValueError("id는 비어 있지 않은 문자열이어야 합니다.")
        if transaction_type not in {"income", "expense"}:
            raise ValueError("type은 income 또는 expense여야 합니다.")
        if not isinstance(transaction_date, str):
            raise ValueError("date는 YYYY-MM-DD 문자열이어야 합니다.")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount는 0보다 큰 정수여야 합니다.")
        if not isinstance(category, str) or not category.strip():
            raise ValueError("category는 비어 있지 않은 문자열이어야 합니다.")
        if not isinstance(memo, str):
            raise ValueError("memo는 문자열이어야 합니다.")
        if not isinstance(tags, list) or not all(
            isinstance(tag, str) and tag for tag in tags
        ):
            raise ValueError("tags는 비어 있지 않은 문자열의 목록이어야 합니다.")

        return cls(
            id=transaction_id,
            type=transaction_type,
            date=date.fromisoformat(transaction_date),
            amount=amount,
            category=category,
            memo=memo,
            tags=tags,
        )


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    transaction_count: int
    total_income: int
    total_expense: int
    category_expenses: list[tuple[str, int]]

    @property
    def balance(self) -> int:
        return self.total_income - self.total_expense


@dataclass(frozen=True)
class Budget:
    month: str
    amount: int

    def to_dict(self) -> dict[str, str | int]:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        month = data["month"]
        amount = data["amount"]
        if not isinstance(month, str):
            raise ValueError("month는 YYYY-MM 문자열이어야 합니다.")
        try:
            if len(month) != 7 or month[4] != "-":
                raise ValueError
            year, month_number = map(int, month.split("-"))
            date(year, month_number, 1)
        except ValueError:
            raise ValueError("month는 실제 달력의 YYYY-MM이어야 합니다.") from None
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount는 0보다 큰 정수여야 합니다.")
        return cls(month=month, amount=amount)
