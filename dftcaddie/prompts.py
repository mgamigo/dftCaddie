"""Terminal-only questions shared by command workflows."""

import re
import sys


class InputRequired(RuntimeError):
    """A required answer cannot be collected without an interactive terminal."""


def _require_terminal(message: str, hint: str) -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise InputRequired(f"{message} No interactive terminal available. {hint}")


def _ask(question):
    """Let the CLI handle cancellation consistently, including end of input."""
    try:
        answer = question.unsafe_ask()
    except EOFError as exc:
        raise KeyboardInterrupt from exc
    if answer is None:
        raise KeyboardInterrupt
    return answer


def select(message, options, labels=None, *, hint="Supply explicit CLI options."):
    """
    Select a configured value by exact name or unique prefix.

    Parameters
    ----------
    message : str
        Question shown next to the input.
    options : list
        Values returned to the caller.
    labels : list of str, optional
        Display names, including legacy bracketed shortcut labels.
    hint : str, optional
        Instructions reported when no interactive terminal is available.

    Returns
    -------
    str or bool
        The selected configuration value.
    """
    _require_terminal(message, hint)
    import questionary
    from prompt_toolkit.shortcuts import CompleteStyle

    if all(type(option) is bool for option in options):
        return confirm(message, default=options[0], hint=hint)
    titles = labels if labels is not None else options
    titles = [re.sub(r"\[([A-Za-z0-9])\]", r"\1", title) for title in titles]

    def resolve(text):
        text = text.strip().casefold()
        if not text:
            raise ValueError("Enter a name or a unique prefix.")
        aliases = [
            {title.casefold(), value.casefold()}
            for title, value in zip(titles, options)
        ]
        matches = [i for i, names in enumerate(aliases) if text in names]
        if not matches:
            matches = [
                i
                for i, names in enumerate(aliases)
                if any(name.startswith(text) for name in names)
            ]
        if len(matches) == 1:
            return options[matches[0]]
        if matches:
            raise ValueError(
                "Ambiguous: "
                + ", ".join(titles[i] for i in matches)
                + ". Type more characters."
            )
        raise ValueError("No matching option. Enter a listed name or prefix.")

    def validate(text):
        try:
            resolve(text)
        except ValueError as exc:
            return str(exc)
        return True

    print("\n".join(f"  {title}" for title in titles))
    answer = _ask(
        questionary.autocomplete(
            message,
            choices=titles,
            ignore_case=True,
            match_middle=False,
            complete_style=CompleteStyle.COLUMN,
            validate=validate,
        )
    )
    return resolve(answer)


def confirm(message: str, *, default: bool = False, hint: str = "") -> bool:
    """
    Ask for confirmation in an interactive terminal.

    Parameters
    ----------
    message : str
        Confirmation question.
    default : bool, optional
        Answer selected by pressing Enter.
    hint : str, optional
        How to provide the answer noninteractively.

    Returns
    -------
    bool
        Whether the user confirmed the operation.
    """
    _require_terminal(message, hint)
    import questionary

    return _ask(questionary.confirm(message, default=default, auto_enter=False))
