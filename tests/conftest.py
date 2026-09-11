"""Shared bundled configuration, independent of user settings."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from dftcaddie.checks.workflows import calculation_cases

_RESOURCE_DIR = Path(__file__).resolve().parents[1] / "dftcaddie/resources"
with (_RESOURCE_DIR / "config.yaml").open() as stream:
    _BUNDLED_CONFIG = yaml.safe_load(stream)


@pytest.fixture(scope="session")
def bundled_resources():
    return _RESOURCE_DIR


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
