"""
dftCaddie | dftcaddie.prompts
============================

Questionary input shared by calculation selection and overwrite workflows.
Typed selections show the question before a vertical option list and a
``Selection:`` field. They accept exact names and unique prefixes, with Tab
completion. Questions require interactive stdin and stdout; unattended callers
receive an actionable error instead of a prompt.

Classes
-------
InputRequired
    Report a required answer that cannot be collected noninteractively.

Functions
---------
select()
    Select a configuration value by name, prefix, or boolean confirmation.
confirm()
    Ask a yes/no question with an explicit default.

Private Utilities
-----------------
_require_terminal()
    Check terminal availability before constructing a question.
_ask()
    Run a question and normalize cancellation to KeyboardInterrupt.
select.resolve()
    Match typed text against configuration keys and cleaned display labels.
select.validate()
    Convert matching errors into Questionary validation feedback.
"""

import re
import sys


class InputRequired(RuntimeError):
    """
    Report a required answer without an interactive terminal.

    Notes
    -----
    The CLI prints the exception message and exits with status 1. Messages
    include the pending question and a hint for supplying input explicitly.
    """


def _require_terminal(message: str, hint: str) -> None:
    """
    Require interactive input and output before asking a question.

    Parameters
    ----------
    message : str
        Pending question included in the error message.
    hint : str
        Instructions for completing the request noninteractively.

    Raises
    ------
    InputRequired
        Standard input or standard output is not connected to a terminal.
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise InputRequired(f"{message} No interactive terminal available. {hint}")


def _ask(question):
    """
    Run a Questionary question with consistent cancellation behavior.

    Parameters
    ----------
    question : questionary.Question
        Prepared question exposing unsafe_ask().

    Returns
    -------
    str or bool
        The submitted answer, including False for a declined confirmation.

    Raises
    ------
    KeyboardInterrupt
        The user cancels, input ends, or the question returns no answer.
    """
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
    options : list of str or list of bool
        Nonempty list of permitted values. Boolean questions expect both
        True and False; single-option settings are resolved by the caller.
    labels : list of str, optional
        Display names corresponding one-to-one with options. Legacy bracketed
        shortcut labels such as [B]ands are displayed as Bands.
    hint : str, optional
        Instructions reported when no interactive terminal is available.

    Returns
    -------
    str or bool
        The selected configuration value.

    Raises
    ------
    InputRequired
        Standard input or output is not an interactive terminal.
    KeyboardInterrupt
        The user cancels or input ends.

    Notes
    -----
    Matching ignores case and surrounding whitespace. Exact matches take
    precedence over prefixes, and both keys and display names are accepted.
    Invalid or ambiguous answers remain in the prompt for correction. Boolean
    questions use the first option as their confirmation default.
    """
    _require_terminal(message, hint)
    import questionary
    from prompt_toolkit.shortcuts import CompleteStyle

    if all(type(option) is bool for option in options):
        return confirm(message, default=options[0], hint=hint)
    titles = labels if labels is not None else options
    titles = [re.sub(r"\[([A-Za-z0-9])\]", r"\1", title) for title in titles]

    def resolve(text):
        """
        Match text against the enclosing configuration keys and labels.

        Parameters
        ----------
        text : str
            Submitted name or prefix.

        Returns
        -------
        str
            The configuration key corresponding to the unique match.

        Raises
        ------
        ValueError
            Input is empty, matches no option, or matches multiple options.
        """
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
        """
        Validate typed input without terminating the interactive question.

        Parameters
        ----------
        text : str
            Current input passed by Questionary.

        Returns
        -------
        bool or str
            True for a unique match, otherwise an explanatory error message.
        """
        try:
            resolve(text)
        except ValueError as exc:
            return str(exc)
        return True

    heading = message.rstrip()
    if not heading.endswith((":", "?")):
        heading += ":"
    print(heading)
    print("\n".join(f"  {title}" for title in titles))
    answer = _ask(
        questionary.autocomplete(
            "Selection:",
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

    Raises
    ------
    InputRequired
        Standard input or output is not an interactive terminal.
    KeyboardInterrupt
        The user cancels or input ends.

    Notes
    -----
    Both yes and no answers require Enter. Declining returns False; the caller
    decides whether to skip or stop the operation.
    """
    _require_terminal(message, hint)
    import questionary

    return _ask(questionary.confirm(message, default=default, auto_enter=False))
