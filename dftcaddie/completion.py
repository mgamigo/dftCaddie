"""
dftCaddie | dftcaddie.completion
===============================

Configuration-aware shell completion for the argparse command interface.
Callbacks read settings only when completing a value and never prepare files
or prompt for input. Commands, flags, and paths are completed by argcomplete.

Functions
---------
complete_calculation()
    Suggest calculation kinds, flavors, or codes from the active configuration.
complete_header()
    Suggest clusters or headers for the selected or detected cluster.
complete_pseudo_library()
    Suggest configured UPF and POTCAR library names.
"""


def complete_calculation(prefix, parsed_args, action, **kwargs):
    """
    Complete calculation selections using the current configuration.

    Parameters
    ----------
    prefix : str
        Text before the cursor in the value being completed.
    parsed_args : argparse.Namespace
        Arguments already supplied, including optional kind and flavor.
    action : argparse.Action
        Option being completed; its destination identifies the selection.
    **kwargs : dict
        Additional context supplied by argcomplete.

    Returns
    -------
    list of str
        Matching keys, narrowed by the selected kind and flavor. Without a
        selection, return the union of available values in configuration order.
    """
    from dftcaddie.config import load_config
    from dftcaddie.calculation import iter_calculation_definitions

    settings = load_config()[0]
    calculations = settings["calculations"]
    if action.dest == "kind":
        values = list(calculations)
    else:
        kind = getattr(parsed_args, "kind", None)
        flavor = getattr(parsed_args, "flavor", None)
        values = []
        for variant_kind, variant_flavor, definition in iter_calculation_definitions(
            settings
        ):
            if kind is not None and variant_kind != kind:
                continue
            if action.dest == "flavor":
                if variant_flavor is not None:
                    values.append(variant_flavor)
                continue
            if flavor is not None and variant_flavor != flavor:
                continue
            values.extend(definition["files"])
    return [value for value in dict.fromkeys(values) if value.startswith(prefix)]


def complete_header(prefix, parsed_args, action, **kwargs):
    """
    Complete cluster names or cluster-specific SBATCH headers.

    Parameters
    ----------
    prefix : str
        Text before the cursor in the value being completed.
    parsed_args : argparse.Namespace
        Arguments already supplied, including an optional cluster.
    action : argparse.Action
        Option being completed, with destination cluster or header.
    **kwargs : dict
        Additional context supplied by argcomplete.

    Returns
    -------
    list of str
        Matching cluster or header keys. Headers use hostname detection when
        no cluster has been supplied, matching the header command behavior.
    """
    from dftcaddie.config import load_config
    from dftcaddie.utils import resolve_cluster

    clusters = load_config()[0]["clusters"]
    if action.dest == "cluster":
        values = list(clusters)
    else:
        cluster = getattr(parsed_args, "cluster", None)
        if cluster is None:
            cluster = resolve_cluster(clusters)
        values = [
            header["name"] for header in clusters.get(cluster, {}).get("headers", [])
        ]
    return [value for value in dict.fromkeys(values) if value.startswith(prefix)]


def complete_pseudo_library(prefix, parsed_args=None, **kwargs):
    """
    Suggest libraries compatible with the detected calculation code.

    Outside a recognized calculation, or when listing libraries, suggest all
    names. Respect the global -C directory without changing the process cwd.
    """
    from pathlib import Path
    from dftcaddie.config import load_config
    from dftcaddie.utils import resolve_calculation_directory

    libraries = load_config()[0].get("pseudopotentials", {}).get("libraries", {})
    code = None
    if not getattr(parsed_args, "list", False):
        directory = getattr(parsed_args, "directory", None) or Path.cwd()
        try:
            _, _, code = resolve_calculation_directory(Path(directory))
        except (OSError, RuntimeError, ValueError, KeyError):
            pass
    return [
        name
        for name, library in libraries.items()
        if name.startswith(prefix)
        and (code is None or code in library.get("supported_codes", []))
    ]
