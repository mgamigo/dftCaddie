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

    calculations = load_config()[0]["calculations"]
    if action.dest == "kind":
        values = list(calculations)
    else:
        kind = getattr(parsed_args, "kind", None)
        definitions = (
            ([calculations[kind]] if kind in calculations else [])
            if kind is not None
            else list(calculations.values())
        )
        flavor = getattr(parsed_args, "flavor", None)
        values = []
        for definition in definitions:
            flavors = definition.get("flavors", {})
            if action.dest == "flavor":
                values.extend(flavors)
                continue
            if flavor is not None:
                variants = [flavors[flavor]] if flavor in flavors else []
            else:
                variants = list(flavors.values()) if flavors else [definition]
            for variant in variants:
                values.extend(variant["files"])
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
