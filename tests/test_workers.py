from __future__ import annotations

import unittest

try:
    from PySide6.QtCore import QCoreApplication
    from repoflow.core.workers import FunctionWorker
    HAS_PYSIDE6 = True
except ModuleNotFoundError:
    HAS_PYSIDE6 = False


@unittest.skipUnless(HAS_PYSIDE6, "PySide6 is not installed in this test environment")
class WorkerSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_worker_emits_error_message(self):
        seen = []

        def fail():
            raise RuntimeError("expected worker failure")

        worker = FunctionWorker(fail)
        worker.signals.error.connect(seen.append)
        worker.run()
        self.assertEqual(seen, ["expected worker failure"])


if __name__ == "__main__":
    unittest.main()
