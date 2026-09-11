"""Resolve calculation requests independently of file preparation."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable


@dataclass(frozen=True)
class CalculationSpec:
    """Resolved calculation choices and preparation options."""

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
        """Return the resolved spin-orbit setting, defaulting to disabled."""
        return self.settings.get("soc", False)

    def as_namespace(self) -> SimpleNamespace:
        """Adapt resolved choices to the existing file-editing helpers."""
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
        A required choice is missing or a selection is invalid.
    """
    auto = request.get("auto", False)
    pseudo = request.get("pseudo", False) or auto
    if pseudo and not request.get("structure"):
        raise ValueError("--auto and --pseudo require --structure FILE.")
    if cluster not in settings["clusters"]:
        raise ValueError(f"Unknown cluster: {cluster}")

    def choose(name, options, label, labels=None, default=None):
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
