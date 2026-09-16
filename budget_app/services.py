"""거래 관련 애플리케이션 로직을 제공한다."""

from collections import deque
from collections.abc import Iterator
from datetime import date

from budget_app.models import Transaction
from budget_app.repositories import CategoryRepository, TransactionRepository


class TransactionService:
    def __init__(
        self,
        repository: TransactionRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self._repository = repository
        self._category_repository = category_repository

    def add_transaction(
        self,
        transaction_type: str,
        transaction_date: date,
        amount: int,
        category: str,
        memo: str = "",
        tags: list[str] | None = None,
    ) -> Transaction:
        """거래 정보를 받아 새 ID를 부여하고 저장한다."""
        if not self.is_category_registered(category):
            raise ValueError(f"등록되지 않은 카테고리입니다: {category}")

        transaction = Transaction(
            id=self._generate_id(),
            type=transaction_type,
            date=transaction_date,
            amount=amount,
            category=category,
            memo=memo,
            tags=[] if tags is None else tags,
        )
        self._repository.add(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> Iterator[Transaction]:
        """저장된 거래를 최신순으로 조회한다.

        조회 개수가 지정되면 가장 최근에 저장된 거래부터 해당 개수만큼
        반환한다.
        """
        if limit < 1:
            raise ValueError("조회 개수는 1 이상의 정수여야 합니다.")

        transactions = deque(self._repository.iter_all(), maxlen=limit)
        yield from reversed(transactions)

    def search_transactions(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        category: str | None = None,
        transaction_type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Iterator[Transaction]:
        if category is not None and not self.is_category_registered(category):
            raise ValueError(f"등록되지 않은 카테고리입니다: {category}")

        for transaction in self._repository.iter_reverse():
            if from_date is not None and transaction.date < from_date:
                continue
            if to_date is not None and transaction.date > to_date:
                continue
            if category is not None and transaction.category != category:
                continue
            if transaction_type is not None and transaction.type != transaction_type:
                continue
            if query is not None and query not in transaction.memo:
                continue
            if tag is not None and tag not in transaction.tags:
                continue
            yield transaction

    def list_categories(self) -> Iterator[str]:
        """등록된 카테고리 이름을 저장 순서대로 조회한다."""
        yield from self._category_repository.iter_all()

    def has_categories(self) -> bool:
        return next(self._category_repository.iter_all(), None) is not None

    def is_category_registered(self, category: str) -> bool:
        """카테고리가 등록된 목록에 존재하는지 확인한다."""
        return self._category_repository.exists(category)

    def register_category(self, category: str) -> None:
        """아직 등록되지 않은 카테고리를 새로 저장한다."""
        category = category.strip()
        if not category:
            raise ValueError("카테고리 이름은 비워둘 수 없습니다.")
        if not self.is_category_registered(category):
            self._category_repository.add(category)

    def add_category(self, category: str) -> None:
        category = category.strip()
        if not category:
            raise ValueError("카테고리 이름은 비워둘 수 없습니다.")
        if self.is_category_registered(category):
            raise ValueError(f"이미 등록된 카테고리입니다: {category}")
        self._category_repository.add(category)

    def remove_category(self, category: str) -> None:
        category = category.strip()
        if not category:
            raise ValueError("카테고리 이름은 비워둘 수 없습니다.")
        if not self.is_category_registered(category):
            raise ValueError(f"등록되지 않은 카테고리입니다: {category}")
        if any(
            transaction.category == category
            for transaction in self._repository.iter_all()
        ):
            raise ValueError(
                f"사용 중인 카테고리는 삭제할 수 없습니다: {category}. "
                "연결된 거래를 먼저 수정하거나 삭제해 주세요."
            )
        self._category_repository.delete(category)

    def update_transaction(
        self,
        transaction_id: str,
        transaction_type: str | None = None,
        transaction_date: date | None = None,
        amount: int | None = None,
        category: str | None = None,
        memo: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """지정된 거래 필드만 변경하고 나머지 값은 기존 상태로 유지한다."""
        existing_transaction = next(
            (
                transaction
                for transaction in self._repository.iter_all()
                if transaction.id == transaction_id
            ),
            None,
        )
        if existing_transaction is None:
            return False

        if category is not None and not self.is_category_registered(category):
            raise ValueError(f"등록되지 않은 카테고리입니다: {category}")

        updated_transaction = Transaction(
            id=existing_transaction.id,
            type=(
                existing_transaction.type
                if transaction_type is None
                else transaction_type
            ),
            date=(
                existing_transaction.date
                if transaction_date is None
                else transaction_date
            ),
            amount=existing_transaction.amount if amount is None else amount,
            category=(existing_transaction.category if category is None else category),
            memo=existing_transaction.memo if memo is None else memo,
            tags=existing_transaction.tags if tags is None else tags,
        )
        return self._repository.update(updated_transaction)

    def delete_transaction(self, transaction_id: str) -> bool:
        """지정된 ID의 거래를 저장소에서 삭제한다."""
        return self._repository.delete(transaction_id)

    def _generate_id(self) -> str:
        """저장된 거래의 가장 큰 시퀀스 다음 ID를 생성한다.

        ``TX-`` 뒤가 숫자인 ID만 시퀀스 계산에 사용하며, 그 외의 ID는
        무시한다. 저장된 거래가 없으면 ``TX-000001``부터 시작한다.
        """
        max_sequence = 0

        for transaction in self._repository.iter_all():
            prefix, separator, sequence = transaction.id.partition("-")
            if prefix == "TX" and separator and sequence.isdigit():
                max_sequence = max(max_sequence, int(sequence))

        return f"TX-{max_sequence + 1:06d}"
