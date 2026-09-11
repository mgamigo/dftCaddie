"""Exercise Questionary with real key input and a terminal-free output driver."""

from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import questionary
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from dftcaddie import prompts


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr(
        prompts,
        "sys",
        SimpleNamespace(
            stdin=Mock(isatty=lambda: True), stdout=Mock(isatty=lambda: True)
        ),
    )
    with create_pipe_input() as pipe:
        for name in ("autocomplete", "confirm"):
            monkeypatch.setattr(
                questionary,
                name,
                partial(getattr(questionary, name), input=pipe, output=DummyOutput()),
            )
        yield pipe


def test_typed_selection_returns_key_and_cleans_labels(terminal, monkeypatch, capsys):
    factory = Mock(wraps=questionary.autocomplete)
    monkeypatch.setattr(questionary, "autocomplete", factory)
    terminal.send_text("dO\r")
    assert prompts.select("Kind", ["bands", "dos"], ["[B]ands", "[D]OS"]) == "dos"
    assert factory.call_args.kwargs["choices"] == [
        "Bands",
        "DOS",
    ]
    assert capsys.readouterr().out == "  Bands\n  DOS\n"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ban", "bands"),
        ("bands", "bands"),
        ("bands_soc", "bands_soc"),
        ("ban\t", "bands"),
    ],
)
def test_prefix_exact_and_tab(terminal, text, expected):
    terminal.send_text(text + "\r")
    options = (
        ["bands", "relax"] if "\t" in text or text == "ban" else ["bands", "bands_soc"]
    )
    assert prompts.select("Kind", options) == expected


@pytest.mark.parametrize("text", ["b", "unknown", ""])
def test_invalid_input_can_be_corrected(terminal, monkeypatch, text):
    factory = Mock(wraps=questionary.autocomplete)
    monkeypatch.setattr(questionary, "autocomplete", factory)
    terminal.send_text(text + "\r\x15bands\r")
    assert prompts.select("Kind", ["bands", "berry"]) == "bands"
    assert factory.call_args.kwargs["validate"](text) is not True


def test_configuration_key_is_accepted(terminal):
    terminal.send_text("fixed_c\r")
    assert (
        prompts.select(
            "Flavor",
            ["fixed_cell", "variable_cell"],
            ["Fixed lattice", "Variable lattice"],
        )
        == "fixed_cell"
    )


def test_boolean_confirmation(terminal):
    terminal.send_text("n\r")
    assert prompts.select("SOC?", [True, False]) is False


@pytest.mark.parametrize("key", ["\x03", "\x04"])
def test_cancel_confirmation(terminal, key):
    terminal.send_text(key)
    with pytest.raises(KeyboardInterrupt):
        prompts.confirm("Overwrite?")


@pytest.mark.parametrize("stream", ["stdin", "stdout"])
def test_noninteractive_never_starts_questionary(monkeypatch, stream):
    monkeypatch.setattr(prompts.sys, stream, Mock(isatty=lambda: False))
    factory = Mock(side_effect=AssertionError("Unexpected prompt"))
    monkeypatch.setattr(questionary, "autocomplete", factory)
    with pytest.raises(prompts.InputRequired, match="--kind"):
        prompts.select("Kind", ["bands", "relax"], hint="Supply --kind.")
    factory.assert_not_called()
