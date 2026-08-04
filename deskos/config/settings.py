"""Typed settings loaded from YAML, with environment-variable overrides.

Every other module depends on `Settings`, never on raw YAML or env vars
directly. This keeps configuration testable and swappable (e.g. injecting
a `Settings` built purely in-memory for unit tests).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.yaml"


@dataclass(frozen=True)
class CameraSettings:
    device_index: int
    frame_width: int
    frame_height: int
    fps: int


@dataclass(frozen=True)
class PerceptionSettings:
    detection_interval_sec: float
    model_path: str
    confidence_threshold: float


@dataclass(frozen=True)
class EventEngineSettings:
    """All timings are wall-clock seconds, independent of the loop tick rate."""

    confirm_after_sec: float      # how long a label must persist to become an Event
    event_debounce_sec: float     # minimum gap between repeat emissions
    absence_grace_sec: float      # how long a label may vanish without losing progress


@dataclass(frozen=True)
class ContextEngineSettings:
    min_confidence: float
    away_timeout_sec: float      # sustained absence before declaring AWAY
    warmup_sec: float = 20.0     # observe silently before claiming anything
    long_session_sec: float = 2700.0  # unbroken presence before suggesting a break


@dataclass(frozen=True)
class DecisionEngineSettings:
    suggestion_cooldown_sec: float
    min_confidence_to_act: float


@dataclass(frozen=True)
class StorageSettings:
    data_dir: Path
    habits_db: str

    @property
    def habits_db_path(self) -> Path:
        return self.data_dir / self.habits_db


@dataclass(frozen=True)
class UISettings:
    widget_fade_ms: int
    widget_max_visible: int


@dataclass(frozen=True)
class Settings:
    """Root, immutable settings object. Pass this one object around;
    do not extract fields into loose globals.
    """
    camera: CameraSettings
    perception: PerceptionSettings
    event_engine: EventEngineSettings
    context_engine: ContextEngineSettings
    decision_engine: DecisionEngineSettings
    storage: StorageSettings
    ui: UISettings


def _override_from_env(raw: dict) -> dict:
    """Allow `DESKOS_CAMERA__DEVICE_INDEX=1` style overrides for deployment
    flexibility. TODO: extend to nested overrides beyond depth 2 if needed.
    """
    for key, value in os.environ.items():
        if not key.startswith("DESKOS_"):
            continue
        parts = key[len("DESKOS_"):].lower().split("__")
        if len(parts) != 2 or parts[0] not in raw:
            continue
        section, field = parts
        if field in raw[section]:
            current = raw[section][field]
            raw[section][field] = type(current)(value)
    return raw


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from `config_path` (defaults to bundled default_config.yaml),
    applying env-var overrides on top.
    """
    path = config_path or _DEFAULT_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    raw = _override_from_env(raw)

    return Settings(
        camera=CameraSettings(**raw["camera"]),
        perception=PerceptionSettings(**raw["perception"]),
        event_engine=EventEngineSettings(**raw["event_engine"]),
        context_engine=ContextEngineSettings(**raw["context_engine"]),
        decision_engine=DecisionEngineSettings(**raw["decision_engine"]),
        storage=StorageSettings(
            data_dir=Path(raw["storage"]["data_dir"]).expanduser(),
            habits_db=raw["storage"]["habits_db"],
        ),
        ui=UISettings(**raw["ui"]),
    )
