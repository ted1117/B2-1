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
        return cls(
            id=data["id"],
            type=data["type"],
            date=date.fromisoformat(data["date"]),
            amount=data["amount"],
            category=data["category"],
            memo=data.get("memo", ""),
            tags=data.get("tags", []),
        )
