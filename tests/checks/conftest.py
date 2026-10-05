"""Shared configuration for checker tests."""

import pytest


@pytest.fixture
def settings(bundled_config, pseudo_settings):
    bundled_config.update(pseudo_settings)
    return bundled_config
