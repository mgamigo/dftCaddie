"""Parent dispatch for the calculation-setting command package."""

from argparse import Namespace
from unittest.mock import Mock

import pytest

from dftcaddie.commands import set as set_command


@pytest.mark.parametrize("name", ["system", "pseudo", "header"])
def test_set_dispatch(monkeypatch, name):
    """Dispatch each public setting name to the matching command module."""
    handlers = {key: Mock(return_value=key) for key in ("system", "pseudo", "header")}
    for key, handler in handlers.items():
        monkeypatch.setattr(getattr(set_command, key), "run", handler)

    args = Namespace(set_action=name)
    assert set_command.run(args) == name
    handlers[name].assert_called_once_with(args)


def test_set_rejects_unknown_action():
    """Reject unregistered setting names when called programmatically."""
    with pytest.raises(ValueError, match="Unknown set action"):
        set_command.run(Namespace(set_action="missing"))
