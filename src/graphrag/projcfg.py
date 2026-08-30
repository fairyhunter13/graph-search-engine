"""`.graphrag.yaml`, parsed strictly.

An unknown key is an error, and the error names the closest known key. A config
silently half-read is the failure this refuses: the operator sets `exclude`,
sees no error, and spends an afternoon asking why a directory is still indexed.

The retired filename is refused by name rather than ignored, for the same
reason. A file the engine skips in silence looks exactly like one it obeyed.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import config, registry


class ConfigError(ValueError):
    """A project config that cannot be obeyed as written."""


@dataclass(slots=True)
class ProjectConfig:
    """Everything a project may say about itself."""

    enabled: bool = True
    # Path globs never indexed, on top of the global set. `*` spans `/`, so
    # `system/*` matches at any depth.
    exclude: list[str] = field(default_factory=list)
    # Globs that keep a discovered member out of the federation. Matched
    # against the link path and the resolved target, because a layout pattern
    # like `*/_worktrees/*` describes only the target.
    federation_exclude: list[str] = field(default_factory=list)
    # Languages to index. Empty means every language with a grammar.
    languages: list[str] = field(default_factory=list)
    # Other projects this one federates. Expanded one level, never transitively.
    members: list[str] = field(default_factory=list)
    # The SCIP overlay, off unless a project asks for it and can build.
    scip: bool = False
    scip_indexers: list[str] = field(default_factory=list)


_FIELDS: dict[str, type] = {
    "enabled": bool,
    "exclude": list,
    "federation_exclude": list,
    "languages": list,
    "members": list,
    "scip": bool,
    "scip_indexers": list,
}


def _suggest(key: str) -> str:
    close = difflib.get_close_matches(key, _FIELDS, n=1, cutoff=0.6)
    return f", did you mean {close[0]!r}" if close else ""


def parse(text: str, *, source: str = "<string>") -> ProjectConfig:
    """One config document. Every rejection names the file and the key."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{source}: not valid YAML: {exc}") from exc
    if raw is None:
        return ProjectConfig()
    if not isinstance(raw, dict):
        raise ConfigError(f"{source}: the document must be a mapping, got {type(raw).__name__}")

    unknown = [k for k in raw if k not in _FIELDS]
    if unknown:
        key = sorted(unknown)[0]
        known = ", ".join(sorted(_FIELDS))
        raise ConfigError(f"{source}: unknown key {key!r}{_suggest(key)}. Known keys: {known}")

    for key, value in raw.items():
        want = _FIELDS[key]
        if want is bool and not isinstance(value, bool):
            raise ConfigError(f"{source}: {key!r} must be true or false")
        if want is list and (
            not isinstance(value, list) or any(not isinstance(v, str) for v in value)
        ):
            raise ConfigError(f"{source}: {key!r} must be a list of strings")
    return ProjectConfig(**raw)


def load(root: Path | str) -> ProjectConfig:
    """The config for one project, or the defaults where there is none."""
    root = Path(root)
    retired = root / config.RETIRED_CONFIG_NAME
    if retired.exists():
        raise ConfigError(
            f"{retired} is the retired config name and is not read. "
            f"Rename it to {config.PROJECT_CONFIG_NAME}."
        )
    path = root / config.PROJECT_CONFIG_NAME
    if not path.exists():
        return ProjectConfig()
    try:
        text = path.read_text()
    except OSError as exc:
        raise ConfigError(f"{path}: unreadable: {exc}") from exc
    return parse(text, source=str(path))


def effective(root: Path | str) -> ProjectConfig:
    """The project's own config, or the excludes it inherits from its roots.

    A member is a repository somebody else owns. Writing a `.graphrag.yaml` into
    it is not on offer, so a member with no config of its own takes `exclude`,
    `languages`, `scip` and `scip_indexers` from every root that claims it. That
    is the only way a rule like "never index CodeIgniter's `system/`", or an
    opt-in to the SCIP overlay, reaches the 360 repositories a workspace
    federates.

    `scip` is true where any claiming root asks for it, and `scip_indexers` is
    the union over those roots. A root turns the overlay on for its members and
    for nobody else's.

    A member carrying its own config keeps it whole. Nothing is merged into a
    file somebody wrote, because a half-obeyed config is what `projcfg` refuses.

    A pass over an unreadable config indexes everything rather than nothing. The
    CLI reports the parse error, so the operator is not left guessing.
    """
    root = Path(root)
    try:
        own = load(root)
    except ConfigError:
        return ProjectConfig()
    if (root / config.PROJECT_CONFIG_NAME).exists():
        return own

    entry = registry.get(root)
    exclude: list[str] = []
    languages: list[str] = []
    scip = False
    scip_indexers: list[str] = []
    for parent in entry.roots if entry else []:
        try:
            inherited = load(Path(parent))
        except ConfigError:
            continue
        exclude.extend(pat for pat in inherited.exclude if pat not in exclude)
        languages.extend(name for name in inherited.languages if name not in languages)
        scip = scip or inherited.scip
        scip_indexers.extend(name for name in inherited.scip_indexers if name not in scip_indexers)
    own.exclude = exclude
    own.languages = languages
    own.scip = scip
    own.scip_indexers = scip_indexers
    return own
