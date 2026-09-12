"""
dftCaddie | dftcaddie.commands.set
=================================

Parent command for adapting an existing calculation directory. It groups the
system, pseudopotential, and scheduler-header workflows under ``caddie set``.

Functions
---------
add_arguments()
    Register the ``system``, ``pseudo``, and ``header`` subcommands.
run()
    Dispatch a parsed ``caddie set`` request to its command module.
"""

from dftcaddie.commands.set import header, pseudo, system

__all__ = ["add_arguments", "run"]


def add_arguments(parser):
    """
    Add calculation-setting subcommands and their arguments.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parent parser for the ``caddie set`` command.
    """
    commands = parser.add_subparsers(title="Settings", dest="set_action", required=True)

    system_parser = commands.add_parser(
        "system",
        help="Adapt the calculation to a crystal structure",
        description="Adapt the calculation to a crystal structure",
    )
    system.add_arguments(system_parser)

    pseudo_parser = commands.add_parser(
        "pseudo",
        help="Set pseudopotentials",
        description="Set pseudopotentials",
    )
    pseudo.add_arguments(pseudo_parser)

    header_parser = commands.add_parser(
        "header",
        help="Set the scheduler header",
        description="Set the scheduler header in master.sh",
    )
    header.add_arguments(header_parser)


def run(args=None):
    """
    Dispatch a calculation-setting command.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing the selected ``set_action``.

    Returns
    -------
    object
        Return value from the selected command handler.

    Raises
    ------
    ValueError
        ``set_action`` does not identify a registered setting command.
    """
    commands = {
        "system": system.run,
        "pseudo": pseudo.run,
        "header": header.run,
    }
    try:
        command = commands[args.set_action]
    except KeyError as exc:
        raise ValueError(f"Unknown set action: {args.set_action}") from exc
    return command(args)
