import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Timer:
    expiration: datetime.datetime

    def is_expired(self) -> bool:
        return self.expiration < datetime.datetime.now()

    @staticmethod
    def set_to_expire_in(seconds: int) -> "Timer":
        expiration = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        return Timer(expiration=expiration)
