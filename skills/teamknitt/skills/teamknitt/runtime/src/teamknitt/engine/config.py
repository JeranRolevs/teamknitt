"""Strict configuration and preset loading, independent of the parent repository."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from importlib.resources import files
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
import yaml


class ConfigurationError(ValueError):
    pass


_FORMATS = FormatChecker()


@_FORMATS.checks("date-time")
def _timestamp(value: Any) -> bool:
    # Keep timestamp checking active without jsonschema's optional format extras.
    if not isinstance(value, str):
        return True  # The schema's type validator reports this case.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
        return False
    try:
        return datetime.fromisoformat(value.upper().replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


class UniqueKeysLoader(yaml.SafeLoader):
    pass


def _mapping(loader: UniqueKeysLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    value: dict = {}
    for key_node, child in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in value
        except TypeError as exc:
            raise ConfigurationError("YAML mapping keys must be scalar") from exc
        if duplicate:
            raise ConfigurationError(f"duplicate YAML key: {key}")
        value[key] = loader.construct_object(child, deep=deep)
    return value


UniqueKeysLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def parse_yaml(text: str) -> dict[str, Any]:
    try:
        value = yaml.load(text, Loader=UniqueKeysLoader)
        if not isinstance(value, dict):
            raise ConfigurationError("expected a YAML mapping")
        json.dumps(value, allow_nan=False)
        return value
    except (yaml.YAMLError, TypeError, ValueError) as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError(f"invalid YAML/JSON data: {exc}") from exc


def schema(name: str) -> dict[str, Any]:
    return json.loads(files("teamknitt.engine.schemas").joinpath(name).read_text(encoding="utf-8"))


def validate(value: Any, schema_name: str) -> None:
    # Reject nonfinite numbers even when the JSON Schema number type would accept them.
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"not finite JSON data: {exc}") from exc
    errors = sorted(Draft202012Validator(schema(schema_name), format_checker=_FORMATS).iter_errors(value),
                    key=lambda e: tuple(str(p) for p in e.absolute_path))
    if errors:
        error = errors[0]
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        raise ConfigurationError(f"{path}: {error.message}")


def project_file(project: Path, relative: str) -> Path:
    root = project.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ConfigurationError(f"project file escapes teamknitt directory: {relative}")
    if not path.is_file():
        raise ConfigurationError(f"project file not found: {relative}")
    return path


def merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(project: Path, relative: str = "configs/lab.yaml") -> dict:
    defaults = parse_yaml(files("teamknitt.engine.resources").joinpath("defaults.yaml").read_text())
    supplied = parse_yaml(project_file(project, relative).read_text(encoding="utf-8"))
    config = merge(defaults, supplied)
    return validate_config(config)


def validate_config(config: dict) -> dict:
    """Validate resolved settings, including external study overrides."""
    # Fail before any provider initialization. Never reinterpret a legacy analysis.
    statistics = config.get("statistics", {}) if isinstance(config, dict) else {}
    if isinstance(statistics, dict):
        approach = statistics.get("approach")
        legacy_priors = "prior_records" in statistics
        if (isinstance(approach, str) and approach in {"bayesian", "probabilistic"}) or (legacy_priors and statistics["prior_records"] != {}):
            raise ConfigurationError("Bayesian/probabilistic analysis is not available in teamknitt. No statistical method was changed; explicitly review a supported configuration before running.")
        if legacy_priors:
            from copy import deepcopy
            config = deepcopy(config)
            config["statistics"].pop("prior_records")  # Inert legacy field, not a method change.
    validate(config, "lab_config.schema.json")
    if config["budget"]["confirmation_evaluations_reserved"] > config["budget"]["max_evaluations"]:
        raise ConfigurationError("confirmation reserve must fit within the total evaluation budget")
    if config["decisions"]["mode"] != "llm_only" and not config["decisions"]["specialist"]:
        raise ConfigurationError("specialist modes must name a specialist adapter; no SDK is loaded during planning")
    return config


def load_design(project: Path, relative: str) -> tuple[dict, str]:
    text = project_file(project, relative).read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ConfigurationError("lab-design Markdown must start with YAML front matter")
    design = parse_yaml(parts[1])
    validate(design, "lab_design.schema.json")
    ids = [persona["id"] for persona in design["personas"]]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("persona IDs must be unique")
    if not any(persona["role"] == "prime" for persona in design["personas"]):
        raise ConfigurationError("a lab design needs at least one prime persona")
    return design, text
