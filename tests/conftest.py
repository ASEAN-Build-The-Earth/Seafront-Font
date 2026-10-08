# Copyright (c) 2026, BuildTheEarth (buildtheearth.net),
# with Reserved Font Name "BTE Seafront".
# Copyright (c) 2026, ASEAN-BTE (asean.buildtheearth.asia).
#
# This Font Software is licensed under the SIL Open Font License, Version 1.1.
# This license is available with a FAQ at:
# https://openfontlicense.org
"""\
PyTest configuration hooks. Currently use to mark
:code:`--test-designs` integration test to be skipped by default.
"""
import pytest

def pytest_addoption(parser):
    # Add a custom command line flag
    parser.addoption(
        "--test-designs",
        action="store_true",
        default=False,
        help="Run slow tests"
    )

def pytest_collection_modifyitems(config, items):
    def collect_test(args, marker: str, predicate: bool=True):
        for item in args:
            is_design: bool = marker in item.keywords
            if is_design == predicate:
                yield item

    # Exclude all other test if we're testing design projects
    if config.getoption("--test-designs"):
        for test in collect_test(items, "design", False):
            test.add_marker(pytest.mark.skip())
        return

    # Normally skip design projects' test whereas all other test is default for development
    skip = pytest.mark.skip(reason="integration test, use --test-designs")
    for design in collect_test(items, "design"):
        design.add_marker(skip)