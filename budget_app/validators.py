import re
from datetime import date

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
TRANSACTION_TYPES = {"income", "expense"}


def parse_date(value: str) -> date:
    """YYYY-MM-DD 형식의 실제 날짜만 변환한다."""
    value = value.strip()
    if DATE_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해 주세요."
        )

    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            "존재하지 않는 날짜입니다. 실제 달력 날짜를 입력해 주세요."
        ) from None


def parse_amount(value: str) -> int:
    """문자열을 0보다 큰 정수 금액으로 변환한다."""
    value = value.strip()
    if re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError("금액은 0보다 큰 정수로 입력해 주세요.")

    amount = int(value)
    if amount <= 0:
        raise ValueError("금액은 0보다 큰 정수로 입력해 주세요.")

    return amount


def validate_transaction_type(value: str) -> str:
    """거래 타입이 income 또는 expense인지 확인한다."""
    value = value.strip()
    if value not in TRANSACTION_TYPES:
        raise ValueError(
            "거래 타입이 올바르지 않습니다. income 또는 expense를 입력해 주세요."
        )

    return value


def validate_category_name(value: str) -> str:
    """카테고리 이름이 비어 있지 않은지 확인한다."""
    value = value.strip()
    if not value:
        raise ValueError("카테고리 이름은 비워둘 수 없습니다.")

    return value
