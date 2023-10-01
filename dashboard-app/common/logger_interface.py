from abc import ABC, abstractmethod
from typing import Optional


class LoggerInterface(ABC):

    @abstractmethod
    def log(self, message: str, fg_color: Optional[str] = None, bg_color: Optional[str] = None) -> None:
        pass
