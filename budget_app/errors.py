from pathlib import Path


class DataFileError(ValueError):
    def __init__(self, path: Path, line_number: int, reason: str) -> None:
        self.path = path
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"{path}의 {line_number}번째 줄: {reason}")
