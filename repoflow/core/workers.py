from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.success.emit(result)
        except Exception as exc:  # displayed to the user by the UI layer
            message = str(exc).strip() or exc.__class__.__name__
            self.signals.error.emit(message)
            traceback.print_exc()
        finally:
            self.signals.finished.emit()
