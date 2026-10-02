"""Запускает функции тестов в отдельных временных директориях."""

import os
import time

import test_crud
import test_decorators

from primitive_db import decorators


def remove_test_directory(directory):
    """Удаляет только временную директорию, созданную данным запуском."""
    for root, directories, filenames in os.walk(directory, topdown=False):
        for filename in filenames:
            os.remove(os.path.join(root, filename))
        for child in directories:
            os.rmdir(os.path.join(root, child))
    os.rmdir(directory)


def run_tests():
    """Возвращает ненулевой код завершения, если хотя бы один тест упал."""
    original_directory = os.getcwd()
    passed = 0
    failed = 0
    for module in (test_crud, test_decorators):
        for name, function in sorted(vars(module).items()):
            if not name.startswith("test_") or not callable(function):
                continue
            directory = os.path.join(
                os.environ.get("TMPDIR", "/tmp"),
                f"primitive-db-test-{os.getpid()}-{time.monotonic_ns()}",
            )
            os.mkdir(directory)
            decorators.input = lambda question: "y"
            try:
                os.chdir(directory)
                function()
                passed += 1
                print(f"PASS: {name}")
            except Exception as error:
                failed += 1
                print(f"FAIL: {name}: {type(error).__name__}: {error}")
            finally:
                os.chdir(original_directory)
                del decorators.input
                remove_test_directory(directory)
    print(f"Passed: {passed}; failed: {failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()
