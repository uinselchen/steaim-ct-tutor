import datetime
import io
import os
import platform
import sys
import traceback
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(ROOT, "app", "data", "outputs")
LOG_FILE = os.path.join(LOG_DIR, "test-log.txt")


class TeeStream(io.TextIOBase):
    """Write the test report to both the terminal and the persistent log."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def write_header(stream):
    stream.write("=" * 80 + "\n")
    stream.write("STEaiM-CT Tutor test run\n")
    stream.write(f"Started: {datetime.datetime.now().isoformat(timespec='seconds')}\n")
    stream.write(f"Python: {sys.version.split()[0]}\n")
    stream.write(f"Platform: {platform.platform()}\n")
    stream.write(f"Working directory: {os.getcwd()}\n")
    stream.write(f"Log file: {LOG_FILE}\n")
    stream.write("=" * 80 + "\n\n")


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as log_file:
        stream = TeeStream(sys.stdout, log_file)
        write_header(stream)
        try:
            loader = unittest.defaultTestLoader
            suite = loader.discover(os.path.join(ROOT, "tests"), pattern="test_*.py")
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        except Exception:
            stream.write("\nTEST RUNNER ERROR\n")
            stream.write(traceback.format_exc())
            stream.write("\nResult: ERROR while discovering or running tests\n")
            return 2

        stream.write("\n" + "=" * 80 + "\n")
        stream.write(
            "Result: "
            + ("PASS" if result.wasSuccessful() else "FAIL")
            + f" | tests={result.testsRun}"
            + f" | failures={len(result.failures)}"
            + f" | errors={len(result.errors)}"
            + f" | skipped={len(result.skipped)}\n"
        )
        stream.write(f"Finished: {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
