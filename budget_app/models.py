from dataclasses import dataclass, field
from datetime import date


@dataclass
class Transaction:
    id: str
    type: str
    date: date
    amount: int
    category: str
    memo: str = ""
    tags: list[str] = field(default_factory=list)
