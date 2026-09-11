"""Shared bundled configuration, independent of user settings."""

from copy import deepcopy

import pytest

from dftcaddie.config import load_config
from dftcaddie.checks.workflows import calculation_cases

_BUNDLED_CONFIG, _BUNDLED_RESOURCES = load_config(default_config=True)


@pytest.fixture(scope="session")
def bundled_resources():
    return _BUNDLED_RESOURCES


@pytest.fixture
def bundled_config():
    """Give each test its own mutable copy of the bundled settings."""
    return deepcopy(_BUNDLED_CONFIG)


@pytest.fixture(
    params=list(calculation_cases(_BUNDLED_CONFIG)),
    ids=lambda case: "/".join(value or "default" for value in case),
)
def calculation_case(request):
    return request.param
