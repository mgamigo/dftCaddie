"""
dftCaddie | dftcaddie.calculation
================================

Resolve preparation choices independently of terminal input and file editing.
Defaults are taken from configuration entries; parameters stored in templates
are not read or duplicated here. Callers supply configuration, the target
cluster, and an optional callback for unresolved choices.

Classes
-------
CalculationSpec
    Store resolved calculation selections and preparation options.

Functions
---------
resolve_calculation()
    Validate a request and resolve configured defaults or prompted choices.

Properties and Methods
----------------------
CalculationSpec.soc
    Retrieve the resolved spin-orbit setting, defaulting to disabled.
CalculationSpec.as_namespace()
    Adapt selections to the existing file-editing helper interface.

Private Utilities
-----------------
resolve_calculation.choose()
    Resolve and validate one setting within a calculation request.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable


@dataclass(frozen=True)
class CalculationSpec:
    """
    Store resolved calculation choices and preparation options.

    Parameters
    ----------
    kind : str
        Calculation key from the active configuration.
    flavor : str or None
        Selected flavor key, or None for calculations without flavors.
    code : str
        Selected calculation backend.
    cluster : str
        Target cluster key used for script configuration.
    structure : str or None, optional
        Structure filename, without reading or validating its contents.
    auto : bool, optional
        Whether to request automatic structure, k-grid, k-path, and pseudo setup.
    pseudo : bool, optional
        Whether to configure pseudopotentials after structure setup.
    overwrite : bool, optional
        Whether existing templates may be replaced without confirmation.
    settings : dict of str to str or bool, optional
        Additional resolved settings, such as soc and cell_relaxation.

    Notes
    -----
    This is a record of preparation choices, not all numerical parameters in
    the generated inputs. Use resolve_calculation() to validate requests and
    apply defaults. Fields cannot be reassigned, but the settings dictionary
    itself remains mutable.
    """

    kind: str
    flavor: str | None
    code: str
    cluster: str
    structure: str | None = None
    auto: bool = False
    pseudo: bool = False
    overwrite: bool = False
    settings: dict[str, str | bool] = field(default_factory=dict)

    @property
    def soc(self) -> bool:
        """
        Return the resolved spin-orbit setting.

        Returns
        -------
        bool
            The configured soc value, or False when the setting is absent.
        """
        return self.settings.get("soc", False)

    def as_namespace(self) -> SimpleNamespace:
        """
        Adapt resolved choices to the existing file-editing helpers.

        Returns
        -------
        types.SimpleNamespace
            A new namespace with settings exposed as attributes. Preparation
            fields take precedence over settings with the same names. The
            flavor attribute is omitted when no flavor was selected.
        """
        values = dict(self.settings)
        values.update(
            kind=self.kind,
            code=self.code,
            cluster=self.cluster,
            structure=self.structure,
            auto=self.auto,
            pseudo=self.pseudo,
            overwrite=self.overwrite,
        )
        if self.flavor is not None:
            values["flavor"] = self.flavor
        return SimpleNamespace(**values)


def resolve_calculation(
    request: dict,
    settings: dict,
    *,
    cluster: str,
    prompt: Callable | None = None,
    details: bool = False,
) -> CalculationSpec:
    """
    Resolve defaults and validate a request without editing files.

    Parameters
    ----------
    request : dict
        Explicit calculation selections and preparation options.
    settings : dict
        Configuration containing calculation definitions.
    cluster : str
        Explicitly resolved target cluster.
    prompt : callable, optional
        Callback accepting a label, options, and display labels, and returning
        a selected value. Without it, unresolved choices raise ValueError.
    details : bool, optional
        Ask for settings instead of applying configured defaults.

    Returns
    -------
    CalculationSpec
        Validated choices, including configurable calculation settings.

    Raises
    ------
    ValueError
        A required choice is missing, a selection is invalid, or automatic or
        pseudo setup is requested without a structure argument.

    Notes
    -----
    Explicit values take precedence over defaults. Single-option settings are
    resolved without prompting, including in details mode. Callback exceptions
    propagate to the caller. Neither request nor configuration is modified;
    template parameters, structure contents, and library paths are not checked.
    """
    auto = request.get("auto", False)
    pseudo = request.get("pseudo", False) or auto
    if pseudo and not request.get("structure"):
        raise ValueError("--auto and --pseudo require --structure FILE.")
    if cluster not in settings["clusters"]:
        raise ValueError(f"Unknown cluster: {cluster}")

    def choose(name, options, label, labels=None, default=None):
        """
        Resolve one setting from the request, defaults, or prompt callback.

        Parameters
        ----------
        name : str
            Setting key in the enclosing request.
        options : list of str or list of bool
            Permitted values for the setting.
        label : str
            Question passed to the prompt callback.
        labels : list of str or None, optional
            Display names corresponding to options.
        default : str, bool or None, optional
            Configured default, applied unless details mode is enabled.

        Returns
        -------
        str or bool
            A selected value belonging to options.

        Raises
        ------
        ValueError
            No value can be resolved or the selected value is not permitted.
        """
        value = request.get(name)
        if value is None:
            if default is not None and not details:
                value = default
            elif len(options) == 1:
                value = options[0]
            elif prompt is not None:
                value = prompt(label, options, labels)
            else:
                raise ValueError(f"Missing {name}; choose from {options}.")
        if value not in options:
            raise ValueError(f"Invalid {name}: {value!r}; choose from {options}.")
        return value

    calculations = settings["calculations"]
    kind = choose(
        "kind",
        list(calculations),
        "Available Calculation Types:",
        [entry["name"] for entry in calculations.values()],
    )
    definition = calculations[kind]
    flavor = None
    if "flavors" in definition:
        flavors = definition["flavors"]
        flavor = choose(
            "flavor",
            list(flavors),
            "Available flavors:",
            [entry["name"] for entry in flavors.values()],
        )
        definition = flavors[flavor]
    elif request.get("flavor") is not None:
        raise ValueError(f"Calculation {kind!r} has no flavors.")

    resolved = {}
    for setting in definition["config"]:
        name = setting["name"]
        resolved[name] = choose(
            name,
            setting["options"],
            setting["prompt"],
            default=setting.get("default"),
        )
    return CalculationSpec(
        kind=kind,
        flavor=flavor,
        code=resolved.pop("code"),
        cluster=cluster,
        structure=request.get("structure"),
        auto=auto,
        pseudo=pseudo,
        overwrite=request.get("overwrite", False),
        settings=resolved,
    )
