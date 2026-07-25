from __future__ import annotations

import fcntl
import os
from pathlib import Path


class DuplicateCollectorError(RuntimeError):
    pass


class WriterLease:
    def __init__(self, ledger_path: str | Path) -> None:
        self.path = Path(str(ledger_path) + ".writer.lock")
        self.fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            self.fd = None
            raise DuplicateCollectorError(
                f"Another RFC-007 collector owns {self.path}"
            ) from exc
        os.ftruncate(self.fd, 0)
        os.write(self.fd, f"{os.getpid()}\n".encode())

    def release(self) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()
